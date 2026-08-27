import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from daibu.cards.schema import (
    BrandAsset,
    CarouselDraft,
    CarouselPage,
    ContentSection,
    DiagramNode,
    DiagramSpec,
    EvidenceQuote,
    VerifiedSource,
    validate_draft,
    validate_sources,
)
from daibu.clock import now as _now
from daibu.llm.base import Idea
from daibu.models import (
    CompanyEligibility,
    EligibilityEvidence,
    Source,
    StoredIdea,
    Theme,
)


SINGLE_SERIES_CLEANUP_KEY = "single_series_cleanup_v1"
SINGLE_SERIES_NAME = "AI 新創介紹"
STARTUP_SOURCE_STRATEGY_KEY = "startup_source_strategy_v1"
STARTUP_DIVERSITY_COUNT_KEY = "startup_diversity_count_v1"
STARTUP_DISCOVERY_SOURCES = (
    (
        "YC Launches",
        "https://www.ycombinator.com/launches",
        "directory",
    ),
    (
        "YC Companies",
        "https://www.ycombinator.com/companies",
        "directory",
    ),
    (
        "a16z Speedrun Companies",
        "https://speedrun.a16z.com/companies",
        "directory",
    ),
    (
        "TechCrunch Startups",
        "https://techcrunch.com/category/startups/feed/",
        "rss",
    ),
)


@dataclass(frozen=True)
class CarouselDraftMeta:
    idea_id: int
    template_version_id: int
    content_revision: int
    updated_at: str


class RevisionConflict(RuntimeError):
    def __init__(self, expected_revision: int, actual_revision: int) -> None:
        self.expected_revision = expected_revision
        self.actual_revision = actual_revision
        super().__init__(
            "草稿版本衝突："
            f"預期 revision {expected_revision}，實際為 {actual_revision}"
        )


def connect(path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {
        row["name"] for row in conn.execute(f"PRAGMA table_info({table})")
    }


def _needs_legacy_migration(conn: sqlite3.Connection) -> bool:
    return (
        "source_layers" in _table_columns(conn, "themes")
        or "layer" in _table_columns(conn, "sources")
        or "gate_score" in _table_columns(conn, "ideas")
    )


def _migrate_legacy_schema(conn: sqlite3.Connection) -> None:
    if "gate_score" in _table_columns(conn, "ideas"):
        conn.execute(
            """
            CREATE TABLE ideas_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme_id INTEGER,
                title TEXT NOT NULL,
                angle TEXT NOT NULL,
                source_url TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                published_at TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO ideas_new (
                id, theme_id, title, angle, source_url, status, body,
                created_at
            )
            SELECT
                id,
                theme_id,
                title,
                angle,
                source_url,
                CASE
                    WHEN status IN ('草稿', '已排程') THEN '採用'
                    ELSE status
                END,
                body,
                created_at
            FROM ideas
            """
        )
        conn.execute("DROP TABLE ideas")
        conn.execute("ALTER TABLE ideas_new RENAME TO ideas")

    if "layer" in _table_columns(conn, "sources"):
        conn.execute(
            """
            CREATE TABLE sources_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                layer TEXT NOT NULL,
                fetch_type TEXT NOT NULL,
                enabled INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO sources_new (
                id, name, url, layer, fetch_type, enabled
            )
            SELECT id, name, url, layer, fetch_type, enabled
            FROM sources
            WHERE fetch_type != 'manual'
            """
        )
        conn.execute("DROP TABLE sources")
        conn.execute("ALTER TABLE sources_new RENAME TO sources")

    if (
        "source_layers" in _table_columns(conn, "themes")
        and "layer" in _table_columns(conn, "sources")
    ):
        conn.execute("DROP TABLE IF EXISTS theme_sources")
        conn.execute(
            """
            CREATE TABLE theme_sources (
                theme_id INTEGER NOT NULL,
                source_id INTEGER NOT NULL,
                PRIMARY KEY (theme_id, source_id),
                FOREIGN KEY (theme_id) REFERENCES themes(id),
                FOREIGN KEY (source_id) REFERENCES sources(id)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO theme_sources (theme_id, source_id)
            SELECT themes.id, sources.id
            FROM themes
            JOIN sources
              ON instr(
                    ',' || replace(themes.source_layers, ' ', '') || ',',
                    ',' || sources.layer || ','
                 ) > 0
            """
        )

    if "source_layers" in _table_columns(conn, "themes"):
        conn.execute(
            """
            CREATE TABLE themes_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                weekday INTEGER NOT NULL,
                n_ideas INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO themes_new (id, name, weekday, n_ideas)
            SELECT id, name, weekday, n_ideas
            FROM themes
            """
        )
        conn.execute("DROP TABLE themes")
        conn.execute("ALTER TABLE themes_new RENAME TO themes")

    if "layer" in _table_columns(conn, "sources"):
        conn.execute(
            """
            CREATE TABLE sources_final (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                fetch_type TEXT NOT NULL,
                enabled INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO sources_final (
                id, name, url, fetch_type, enabled
            )
            SELECT id, name, url, fetch_type, enabled
            FROM sources
            """
        )
        conn.execute("DROP TABLE sources")
        conn.execute("ALTER TABLE sources_final RENAME TO sources")


def _cleanup_to_single_series(conn: sqlite3.Connection) -> bool:
    marked = conn.execute(
        "SELECT 1 FROM config WHERE key = ?",
        (SINGLE_SERIES_CLEANUP_KEY,),
    ).fetchone()
    if marked:
        return True

    theme_count = conn.execute(
        "SELECT COUNT(*) AS count FROM themes"
    ).fetchone()["count"]
    if theme_count == 0:
        conn.execute(
            "INSERT INTO config (key, value) VALUES (?, '1')",
            (SINGLE_SERIES_CLEANUP_KEY,),
        )
        return True

    targets = conn.execute(
        "SELECT id FROM themes WHERE name = ?",
        (SINGLE_SERIES_NAME,),
    ).fetchall()
    if len(targets) != 1:
        return False

    target_id = targets[0]["id"]
    conn.execute("SAVEPOINT single_series_cleanup")
    try:
        conn.execute(
            "DELETE FROM carousel_drafts WHERE idea_id IN "
            "(SELECT id FROM ideas "
            "WHERE theme_id IS NOT NULL AND theme_id != ?)",
            (target_id,),
        )
        for table in (
            "performance",
            "carousel_pages",
            "carousel_sources",
            "idea_sources",
        ):
            conn.execute(
                f"DELETE FROM {table} WHERE idea_id IN "
                "(SELECT id FROM ideas "
                "WHERE theme_id IS NOT NULL AND theme_id != ?)",
                (target_id,),
            )
        conn.execute(
            "DELETE FROM ideas "
            "WHERE theme_id IS NOT NULL AND theme_id != ?",
            (target_id,),
        )
        conn.execute(
            "DELETE FROM theme_sources WHERE theme_id != ?",
            (target_id,),
        )
        conn.execute(
            "DELETE FROM carousel_template_settings WHERE theme_id != ?",
            (target_id,),
        )
        conn.execute(
            "DELETE FROM carousel_template_versions WHERE theme_id != ?",
            (target_id,),
        )
        conn.execute("DELETE FROM themes WHERE id != ?", (target_id,))
        conn.execute(
            "INSERT INTO config (key, value) VALUES (?, '1')",
            (SINGLE_SERIES_CLEANUP_KEY,),
        )
        conn.execute("RELEASE SAVEPOINT single_series_cleanup")
    except Exception:
        conn.execute("ROLLBACK TO SAVEPOINT single_series_cleanup")
        conn.execute("RELEASE SAVEPOINT single_series_cleanup")
        raise
    return True


def _migrate_startup_source_strategy(conn: sqlite3.Connection) -> bool:
    if conn.execute(
        "SELECT 1 FROM config WHERE key = ?",
        (STARTUP_SOURCE_STRATEGY_KEY,),
    ).fetchone():
        return True
    theme = conn.execute(
        "SELECT id FROM themes WHERE name = ?",
        (SINGLE_SERIES_NAME,),
    ).fetchone()
    if theme is None:
        return False

    conn.execute("SAVEPOINT startup_source_strategy")
    try:
        for name, url, fetch_type in STARTUP_DISCOVERY_SOURCES:
            conn.execute(
                """
                INSERT INTO sources (name, url, fetch_type, enabled)
                SELECT ?, ?, ?, 1
                WHERE NOT EXISTS (
                    SELECT 1 FROM sources WHERE name = ?
                )
                """,
                (name, url, fetch_type, name),
            )
        conn.execute(
            "UPDATE sources SET enabled = 0 WHERE name = 'a16z'"
        )
        conn.execute(
            "DELETE FROM theme_sources WHERE theme_id = ?",
            (theme["id"],),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO theme_sources (theme_id, source_id)
            SELECT ?, id
            FROM sources
            WHERE name IN (?, ?, ?, ?)
            """,
            (
                theme["id"],
                *(item[0] for item in STARTUP_DISCOVERY_SOURCES),
            ),
        )
        conn.execute(
            "INSERT INTO config (key, value) VALUES (?, '1')",
            (STARTUP_SOURCE_STRATEGY_KEY,),
        )
        conn.execute("RELEASE SAVEPOINT startup_source_strategy")
    except Exception:
        conn.execute("ROLLBACK TO SAVEPOINT startup_source_strategy")
        conn.execute("RELEASE SAVEPOINT startup_source_strategy")
        raise
    return True


def _backfill_carousel_template_metadata(
    conn: sqlite3.Connection,
) -> None:
    from daibu.cards import layout_repository

    rows = conn.execute(
        """
        SELECT DISTINCT ideas.id, ideas.theme_id
        FROM ideas
        JOIN carousel_pages ON carousel_pages.idea_id = ideas.id
        WHERE ideas.theme_id IS NOT NULL
        """
    ).fetchall()
    for row in rows:
        version = layout_repository.ensure_default_version(
            conn,
            int(row["theme_id"]),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO carousel_drafts (
                idea_id, template_version_id, content_revision, updated_at
            ) VALUES (?, ?, 1, ?)
            """,
            (int(row["id"]), version.id, _now()),
        )


def _seed_v3_template_versions(conn: sqlite3.Connection) -> None:
    from daibu.cards.layout_schema import layout_to_mapping, load_builtin_layout

    layout = load_builtin_layout()
    layout_json = json.dumps(
        layout_to_mapping(layout),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    theme_ids = [
        int(row["id"])
        for row in conn.execute("SELECT id FROM themes ORDER BY id")
    ]
    for theme_id in theme_ids:
        cursor = conn.execute(
            """
            INSERT INTO carousel_template_versions (
                theme_id, version_no, schema_version, layout_json
            ) VALUES (?, 1, 3, ?)
            """,
            (theme_id, layout_json),
        )
        conn.execute(
            """
            INSERT INTO carousel_template_settings (theme_id, active_version_id)
            VALUES (?, ?)
            """,
            (theme_id, int(cursor.lastrowid)),
        )


def _migrate_to_six_page_v57(conn: sqlite3.Connection) -> None:
    """Replace legacy carousel state while preserving research and ideas."""
    legacy = conn.execute(
        """
        SELECT 1
        FROM carousel_template_versions
        WHERE schema_version IN (1, 2)
        LIMIT 1
        """
    ).fetchone()
    if legacy is None:
        return

    with conn:
        conn.execute("DELETE FROM carousel_drafts")
        conn.execute("DELETE FROM carousel_pages")
        conn.execute("DELETE FROM carousel_sources")
        conn.execute("DELETE FROM carousel_template_settings")
        conn.execute("DELETE FROM carousel_template_versions")
        _seed_v3_template_versions(conn)

def init_schema(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "themes") and _needs_legacy_migration(conn):
        try:
            _migrate_legacy_schema(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            weekday INTEGER NOT NULL,
            n_ideas INTEGER NOT NULL,
            content_kind TEXT NOT NULL DEFAULT 'general'
        );

        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            fetch_type TEXT NOT NULL,
            enabled INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS theme_sources (
            theme_id INTEGER NOT NULL,
            source_id INTEGER NOT NULL,
            PRIMARY KEY (theme_id, source_id),
            FOREIGN KEY (theme_id) REFERENCES themes(id),
            FOREIGN KEY (source_id) REFERENCES sources(id)
        );

        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme_id INTEGER,
            title TEXT NOT NULL,
            angle TEXT NOT NULL,
            source_url TEXT NOT NULL DEFAULT '',
            company TEXT NOT NULL DEFAULT '',
            source_excerpt TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            published_at TEXT,
            FOREIGN KEY (theme_id) REFERENCES themes(id)
        );

        CREATE TABLE IF NOT EXISTS performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            likes INTEGER NOT NULL,
            reach INTEGER NOT NULL,
            engagement REAL NOT NULL,
            posted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (idea_id) REFERENCES ideas(id)
        );

        CREATE TABLE IF NOT EXISTS carousel_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id INTEGER NOT NULL,
            page_no INTEGER NOT NULL,
            page_type TEXT NOT NULL,
            heading TEXT NOT NULL DEFAULT '',
            body TEXT NOT NULL DEFAULT '',
            grounding TEXT NOT NULL DEFAULT 'model',
            source_quote TEXT NOT NULL DEFAULT '',
            sections_json TEXT NOT NULL DEFAULT '[]',
            diagram_json TEXT NOT NULL DEFAULT '',
            source_label TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (idea_id) REFERENCES ideas(id)
        );

        CREATE TABLE IF NOT EXISTS carousel_sources (
            idea_id INTEGER NOT NULL,
            source_key TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            publisher TEXT NOT NULL,
            published_at TEXT NOT NULL,
            url TEXT NOT NULL,
            excerpt TEXT NOT NULL,
            source_kind TEXT NOT NULL DEFAULT 'manual',
            PRIMARY KEY (idea_id, source_key),
            FOREIGN KEY (idea_id) REFERENCES ideas(id)
        );

        CREATE TABLE IF NOT EXISTS carousel_template_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme_id INTEGER NOT NULL,
            version_no INTEGER NOT NULL,
            schema_version INTEGER NOT NULL,
            layout_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (theme_id, version_no),
            FOREIGN KEY (theme_id) REFERENCES themes(id)
        );

        CREATE TABLE IF NOT EXISTS carousel_template_settings (
            theme_id INTEGER PRIMARY KEY,
            active_version_id INTEGER NOT NULL,
            FOREIGN KEY (theme_id) REFERENCES themes(id),
            FOREIGN KEY (active_version_id)
                REFERENCES carousel_template_versions(id)
        );

        CREATE TABLE IF NOT EXISTS carousel_drafts (
            idea_id INTEGER PRIMARY KEY,
            template_version_id INTEGER NOT NULL,
            content_revision INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (idea_id) REFERENCES ideas(id),
            FOREIGN KEY (template_version_id)
                REFERENCES carousel_template_versions(id)
        );

        CREATE TABLE IF NOT EXISTS idea_sources (
            idea_id INTEGER NOT NULL,
            source_key TEXT NOT NULL,
            publisher TEXT NOT NULL,
            published_at TEXT NOT NULL,
            url TEXT NOT NULL,
            excerpt TEXT NOT NULL,
            source_kind TEXT NOT NULL DEFAULT 'manual',
            PRIMARY KEY (idea_id, source_key),
            FOREIGN KEY (idea_id) REFERENCES ideas(id)
        );

        CREATE TABLE IF NOT EXISTS brand_assets (
            company_key TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            local_path TEXT NOT NULL,
            official_source_url TEXT NOT NULL,
            verified_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS company_eligibility (
            company_key TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            verdict TEXT NOT NULL CHECK (
                verdict IN ('eligible', 'ineligible', 'unknown')
            ),
            founded_year INTEGER,
            ownership_status TEXT NOT NULL CHECK (
                ownership_status IN (
                    'private_independent', 'public', 'acquired', 'unknown'
                )
            ),
            reason TEXT NOT NULL,
            evidence_json TEXT NOT NULL DEFAULT '[]',
            checked_at TEXT NOT NULL
        );
        """
    )
    theme_columns = _table_columns(conn, "themes")
    if "content_kind" not in theme_columns:
        conn.execute(
            "ALTER TABLE themes ADD COLUMN content_kind "
            "TEXT NOT NULL DEFAULT 'general'"
        )
        conn.execute(
            """
            UPDATE themes
            SET content_kind = 'company_profile'
            WHERE name = 'AI 新創介紹'
            """
        )
    diversity_count_migrated = conn.execute(
        "SELECT 1 FROM config WHERE key = ?",
        (STARTUP_DIVERSITY_COUNT_KEY,),
    ).fetchone()
    if not diversity_count_migrated:
        conn.execute(
            "UPDATE themes SET n_ideas = 5 WHERE content_kind = 'company_profile'"
        )
        conn.execute(
            "INSERT INTO config (key, value) VALUES (?, '1')",
            (STARTUP_DIVERSITY_COUNT_KEY,),
        )
    idea_columns = _table_columns(conn, "ideas")
    for column in ("company", "source_excerpt"):
        if column not in idea_columns:
            conn.execute(
                f"ALTER TABLE ideas ADD COLUMN {column} TEXT NOT NULL DEFAULT ''"
            )
    page_columns = _table_columns(conn, "carousel_pages")
    structured_columns = {
        "sections_json": "'[]'",
        "diagram_json": "''",
        "source_label": "''",
    }
    for column, default in structured_columns.items():
        if column not in page_columns:
            conn.execute(
                "ALTER TABLE carousel_pages "
                f"ADD COLUMN {column} TEXT NOT NULL DEFAULT {default}"
            )
    source_columns = _table_columns(conn, "carousel_sources")
    if "position" not in source_columns:
        conn.execute(
            "ALTER TABLE carousel_sources "
            "ADD COLUMN position INTEGER NOT NULL DEFAULT 0"
        )
    for table in ("carousel_sources", "idea_sources"):
        if "source_kind" not in _table_columns(conn, table):
            conn.execute(
                f"ALTER TABLE {table} "
                "ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'manual'"
            )
    _cleanup_to_single_series(conn)
    already_pruned = conn.execute(
        "SELECT 1 FROM config WHERE key = 'startup_sources_pruned'"
    ).fetchone()
    if not already_pruned and _table_exists(conn, "theme_sources"):
        conn.execute(
            """
            DELETE FROM theme_sources
            WHERE theme_id IN (
                SELECT id FROM themes WHERE name = 'AI 新創介紹'
            )
              AND source_id NOT IN (
                  SELECT id FROM sources WHERE name IN (
                      'Product Hunt AI', 'Y Combinator Blog',
                      'a16z', 'TechCrunch', 'INSIDE'
                  )
              )
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
            ("startup_sources_pruned", "1"),
        )
    already_fixed = conn.execute(
        "SELECT 1 FROM config WHERE key = 'startup_sources_fixed'"
    ).fetchone()
    if not already_fixed and _table_exists(conn, "sources"):
        conn.execute(
            "UPDATE sources SET url = ?, fetch_type = 'rss' WHERE name = ?",
            (
                "https://www.ycombinator.com/blog/rss",
                "Y Combinator Blog",
            ),
        )
        conn.execute(
            "UPDATE sources SET url = ?, fetch_type = 'rss' WHERE name = ?",
            ("https://www.inside.com.tw/feed/rss", "INSIDE"),
        )
        conn.execute(
            """
            INSERT INTO sources (name, url, fetch_type, enabled)
            SELECT 'VentureBeat AI',
                   'https://venturebeat.com/category/ai/feed/', 'rss', 1
            WHERE EXISTS (
                SELECT 1 FROM themes WHERE name = 'AI 新創介紹'
            )
              AND NOT EXISTS (
                SELECT 1 FROM sources WHERE name = 'VentureBeat AI'
            )
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO theme_sources (theme_id, source_id)
            SELECT themes.id, sources.id
            FROM themes, sources
            WHERE themes.name = 'AI 新創介紹'
              AND sources.name = 'VentureBeat AI'
            """
        )
        conn.execute(
            """
            DELETE FROM theme_sources
            WHERE theme_id IN (
                SELECT id FROM themes WHERE name = 'AI 新創介紹'
            )
              AND source_id IN (
                  SELECT id FROM sources WHERE name = 'a16z'
              )
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
            ("startup_sources_fixed", "1"),
        )
    _migrate_startup_source_strategy(conn)
    conn.execute(
        "DELETE FROM config WHERE key = ?",
        ("gate_line",),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO config (key, value)
        SELECT 'seeds_loaded', '1'
        WHERE EXISTS (SELECT 1 FROM themes)
        """
    )
    _migrate_to_six_page_v57(conn)
    _backfill_carousel_template_metadata(conn)
    conn.commit()


def add_theme(conn: sqlite3.Connection, theme: Theme) -> int:
    cursor = conn.execute(
        """
        INSERT INTO themes (name, weekday, n_ideas, content_kind)
        VALUES (?, ?, ?, ?)
        """,
        (
            theme.name,
            theme.weekday,
            theme.n_ideas,
            theme.content_kind,
        ),
    )
    theme_id = cursor.lastrowid
    conn.executemany(
        """
        INSERT INTO theme_sources (theme_id, source_id)
        VALUES (?, ?)
        """,
        [(theme_id, source_id) for source_id in theme.source_ids],
    )
    conn.commit()
    return theme_id


def get_themes(conn: sqlite3.Connection) -> list[Theme]:
    rows = conn.execute("SELECT * FROM themes ORDER BY id").fetchall()
    source_rows = conn.execute(
        """
        SELECT theme_id, source_id
        FROM theme_sources
        ORDER BY theme_id, source_id
        """
    ).fetchall()
    source_ids_by_theme: dict[int, list[int]] = {}
    for row in source_rows:
        source_ids_by_theme.setdefault(row["theme_id"], []).append(
            row["source_id"]
        )
    return [
        Theme(
            id=row["id"],
            name=row["name"],
            weekday=row["weekday"],
            source_ids=source_ids_by_theme.get(row["id"], []),
            n_ideas=row["n_ideas"],
            content_kind=row["content_kind"],
        )
        for row in rows
    ]


def update_theme(conn: sqlite3.Connection, theme: Theme) -> None:
    if theme.id is None:
        raise ValueError("更新主題需要 id")
    conn.execute(
        """
        UPDATE themes
        SET name = ?, weekday = ?, n_ideas = ?, content_kind = ?
        WHERE id = ?
        """,
        (
            theme.name,
            theme.weekday,
            theme.n_ideas,
            theme.content_kind,
            theme.id,
        ),
    )
    conn.execute(
        "DELETE FROM theme_sources WHERE theme_id = ?",
        (theme.id,),
    )
    conn.executemany(
        """
        INSERT INTO theme_sources (theme_id, source_id)
        VALUES (?, ?)
        """,
        [(theme.id, source_id) for source_id in theme.source_ids],
    )
    conn.commit()


def delete_theme(conn: sqlite3.Connection, theme_id: int) -> None:
    with conn:
        conn.execute(
            """
            DELETE FROM carousel_drafts
            WHERE idea_id IN (SELECT id FROM ideas WHERE theme_id = ?)
            """,
            (theme_id,),
        )
        conn.execute(
            """
            DELETE FROM performance
            WHERE idea_id IN (
                SELECT id FROM ideas WHERE theme_id = ?
            )
            """,
            (theme_id,),
        )
        conn.execute(
            """
            DELETE FROM carousel_pages
            WHERE idea_id IN (
                SELECT id FROM ideas WHERE theme_id = ?
            )
            """,
            (theme_id,),
        )
        conn.execute(
            """
            DELETE FROM carousel_sources
            WHERE idea_id IN (SELECT id FROM ideas WHERE theme_id = ?)
            """,
            (theme_id,),
        )
        conn.execute(
            """
            DELETE FROM idea_sources
            WHERE idea_id IN (SELECT id FROM ideas WHERE theme_id = ?)
            """,
            (theme_id,),
        )
        conn.execute("DELETE FROM ideas WHERE theme_id = ?", (theme_id,))
        conn.execute(
            "DELETE FROM carousel_template_settings WHERE theme_id = ?",
            (theme_id,),
        )
        conn.execute(
            "DELETE FROM carousel_template_versions WHERE theme_id = ?",
            (theme_id,),
        )
        conn.execute(
            "DELETE FROM theme_sources WHERE theme_id = ?",
            (theme_id,),
        )
        conn.execute("DELETE FROM themes WHERE id = ?", (theme_id,))


def count_theme_content(
    conn: sqlite3.Connection,
    theme_id: int,
) -> dict[str, int]:
    counts = {
        "候選": 0,
        "採用": 0,
        "已發": 0,
        "輪播草稿": 0,
        "模板版本": 0,
    }
    rows = conn.execute(
        """
        SELECT status, COUNT(*) AS count
        FROM ideas
        WHERE theme_id = ?
        GROUP BY status
        """,
        (theme_id,),
    ).fetchall()
    for row in rows:
        if row["status"] in counts:
            counts[row["status"]] = int(row["count"])
    carousel_row = conn.execute(
        """
        SELECT COUNT(DISTINCT carousel_pages.idea_id) AS count
        FROM carousel_pages
        JOIN ideas ON ideas.id = carousel_pages.idea_id
        WHERE ideas.theme_id = ?
        """,
        (theme_id,),
    ).fetchone()
    counts["輪播草稿"] = int(carousel_row["count"])
    version_row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM carousel_template_versions
        WHERE theme_id = ?
        """,
        (theme_id,),
    ).fetchone()
    counts["模板版本"] = int(version_row["count"])
    return counts


def add_source(conn: sqlite3.Connection, source: Source) -> int:
    cursor = conn.execute(
        """
        INSERT INTO sources (name, url, fetch_type, enabled)
        VALUES (?, ?, ?, ?)
        """,
        (
            source.name,
            source.url,
            source.fetch_type,
            source.enabled,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_sources(conn: sqlite3.Connection) -> list[Source]:
    rows = conn.execute("SELECT * FROM sources ORDER BY id").fetchall()
    return [
        Source(
            id=row["id"],
            name=row["name"],
            url=row["url"],
            fetch_type=row["fetch_type"],
            enabled=bool(row["enabled"]),
        )
        for row in rows
    ]


def count_themes_using_source(
    conn: sqlite3.Connection,
    source_id: int,
) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM theme_sources
        WHERE source_id = ?
        """,
        (source_id,),
    ).fetchone()
    return int(row["count"])


def update_source(conn: sqlite3.Connection, source: Source) -> None:
    if source.id is None:
        raise ValueError("更新來源需要 id")
    conn.execute(
        """
        UPDATE sources
        SET name = ?, url = ?, fetch_type = ?, enabled = ?
        WHERE id = ?
        """,
        (
            source.name,
            source.url,
            source.fetch_type,
            source.enabled,
            source.id,
        ),
    )
    conn.commit()


def delete_source(conn: sqlite3.Connection, source_id: int) -> None:
    conn.execute(
        "DELETE FROM theme_sources WHERE source_id = ?",
        (source_id,),
    )
    conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
    conn.commit()


def set_config(
    conn: sqlite3.Connection,
    key: str,
    value: str,
) -> None:
    conn.execute(
        """
        INSERT INTO config (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )
    conn.commit()


def get_config(
    conn: sqlite3.Connection,
    key: str,
    default: str = "",
) -> str:
    row = conn.execute(
        "SELECT value FROM config WHERE key = ?",
        (key,),
    ).fetchone()
    return str(row["value"]) if row else default


def add_idea(
    conn: sqlite3.Connection,
    theme_id: int | None,
    idea: Idea,
    status: str = "候選",
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO ideas (
            theme_id, title, angle, source_url, company, source_excerpt,
            status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            theme_id,
            idea.title,
            idea.angle,
            idea.source_url,
            idea.company,
            idea.source_excerpt,
            status,
            _now(),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def add_ideas_atomic(
    conn: sqlite3.Connection,
    theme_id: int | None,
    ideas: list[Idea],
    status: str = "候選",
) -> list[int]:
    conn.execute("SAVEPOINT add_ideas_atomic")
    ids: list[int] = []
    try:
        for idea in ideas:
            cursor = conn.execute(
                """
                INSERT INTO ideas (
                    theme_id, title, angle, source_url, company,
                    source_excerpt, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    theme_id,
                    idea.title,
                    idea.angle,
                    idea.source_url,
                    idea.company,
                    idea.source_excerpt,
                    status,
                    _now(),
                ),
            )
            ids.append(cursor.lastrowid)
    except Exception:
        conn.execute("ROLLBACK TO SAVEPOINT add_ideas_atomic")
        conn.execute("RELEASE SAVEPOINT add_ideas_atomic")
        raise
    conn.execute("RELEASE SAVEPOINT add_ideas_atomic")
    conn.commit()
    return ids


def get_ideas(
    conn: sqlite3.Connection,
    status: str | None = None,
) -> list[StoredIdea]:
    query = "SELECT * FROM ideas"
    parameters: tuple[str, ...] = ()
    if status is not None:
        query += " WHERE status = ?"
        parameters = (status,)
    query += " ORDER BY created_at DESC, id DESC"

    rows = conn.execute(query, parameters).fetchall()
    return [
        StoredIdea(
            id=row["id"],
            theme_id=row["theme_id"],
            title=row["title"],
            angle=row["angle"],
            source_url=row["source_url"],
            status=row["status"],
            body=row["body"],
            created_at=row["created_at"],
            published_at=row["published_at"],
            company=row["company"],
            source_excerpt=row["source_excerpt"],
        )
        for row in rows
    ]


def get_rejected_titles(
    conn: sqlite3.Connection,
    theme_id: int | None,
) -> list[str]:
    rows = conn.execute(
        """
        SELECT title
        FROM ideas
        WHERE theme_id = ? AND status = '已淘汰'
        ORDER BY id
        """,
        (theme_id,),
    ).fetchall()
    return [row["title"] for row in rows]


def get_idea_exclusions(
    conn: sqlite3.Connection,
    theme_id: int | None,
) -> tuple[list[str], list[str]]:
    rows = conn.execute(
        """
        SELECT title, company
        FROM ideas
        WHERE theme_id = ?
        ORDER BY created_at, id
        """,
        (theme_id,),
    ).fetchall()
    titles = [row["title"] for row in rows]
    companies = [
        row["company"].strip()
        for row in rows
        if row["company"].strip()
    ]
    return titles, companies


def _company_eligibility_from_row(
    row: sqlite3.Row,
) -> CompanyEligibility:
    evidence = tuple(
        EligibilityEvidence(
            claim=str(item.get("claim", "")),
            source_url=str(item.get("source_url", "")),
            quote=str(item.get("quote", "")),
        )
        for item in json.loads(row["evidence_json"])
        if isinstance(item, dict)
    )
    return CompanyEligibility(
        company_key=row["company_key"],
        company=row["company"],
        verdict=row["verdict"],
        founded_year=row["founded_year"],
        ownership_status=row["ownership_status"],
        reason=row["reason"],
        evidence=evidence,
        checked_at=row["checked_at"],
    )


def save_company_eligibility(
    conn: sqlite3.Connection,
    record: CompanyEligibility,
) -> None:
    conn.execute(
        """
        INSERT INTO company_eligibility (
            company_key, company, verdict, founded_year,
            ownership_status, reason, evidence_json, checked_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(company_key) DO UPDATE SET
            company = excluded.company,
            verdict = excluded.verdict,
            founded_year = excluded.founded_year,
            ownership_status = excluded.ownership_status,
            reason = excluded.reason,
            evidence_json = excluded.evidence_json,
            checked_at = excluded.checked_at
        """,
        (
            record.company_key,
            record.company,
            record.verdict,
            record.founded_year,
            record.ownership_status,
            record.reason,
            json.dumps(
                [asdict(item) for item in record.evidence],
                ensure_ascii=False,
            ),
            record.checked_at,
        ),
    )
    conn.commit()


def get_company_eligibility(
    conn: sqlite3.Connection,
    company_key: str,
) -> CompanyEligibility | None:
    row = conn.execute(
        "SELECT * FROM company_eligibility WHERE company_key = ?",
        (company_key.strip().casefold(),),
    ).fetchone()
    return None if row is None else _company_eligibility_from_row(row)


def get_company_eligibilities(
    conn: sqlite3.Connection,
) -> dict[str, CompanyEligibility]:
    rows = conn.execute(
        "SELECT * FROM company_eligibility ORDER BY company_key"
    ).fetchall()
    return {
        row["company_key"]: _company_eligibility_from_row(row)
        for row in rows
    }


def update_idea_content(
    conn: sqlite3.Connection,
    idea_id: int,
    title: str,
    angle: str,
) -> None:
    conn.execute(
        "UPDATE ideas SET title = ?, angle = ? WHERE id = ?",
        (title, angle, idea_id),
    )
    conn.commit()


def set_idea_company(
    conn: sqlite3.Connection,
    idea_id: int,
    company: str,
) -> None:
    conn.execute(
        "UPDATE ideas SET company = ? WHERE id = ?",
        (company.strip(), idea_id),
    )
    conn.commit()


def delete_idea(conn: sqlite3.Connection, idea_id: int) -> None:
    with conn:
        conn.execute(
            "DELETE FROM carousel_drafts WHERE idea_id = ?",
            (idea_id,),
        )
        conn.execute(
            "DELETE FROM carousel_pages WHERE idea_id = ?",
            (idea_id,),
        )
        conn.execute(
            "DELETE FROM carousel_sources WHERE idea_id = ?",
            (idea_id,),
        )
        conn.execute(
            "DELETE FROM idea_sources WHERE idea_id = ?",
            (idea_id,),
        )
        conn.execute("DELETE FROM ideas WHERE id = ?", (idea_id,))


def save_idea_sources(
    conn: sqlite3.Connection,
    idea_id: int,
    sources: tuple[VerifiedSource, ...],
) -> None:
    validate_sources(sources)
    with conn:
        _replace_idea_sources(conn, idea_id, sources)


def save_copy_draft(
    conn: sqlite3.Connection,
    idea_id: int,
    sources: tuple[VerifiedSource, ...],
    body: str,
) -> None:
    validate_sources(sources)
    if not body.strip():
        raise ValueError("初稿不可空白")
    with conn:
        _replace_idea_sources(conn, idea_id, sources)
        conn.execute(
            "UPDATE ideas SET body = ? WHERE id = ?",
            (body, idea_id),
        )


def _replace_idea_sources(
    conn: sqlite3.Connection,
    idea_id: int,
    sources: tuple[VerifiedSource, ...],
) -> None:
    conn.execute(
        "DELETE FROM idea_sources WHERE idea_id = ?",
        (idea_id,),
    )
    conn.executemany(
        """
        INSERT INTO idea_sources (
            idea_id, source_key, publisher, published_at, url, excerpt,
            source_kind
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                idea_id,
                source.source_id,
                source.publisher,
                source.published_at,
                source.url,
                source.excerpt,
                source.source_kind,
            )
            for source in sources
        ],
    )


def get_idea_sources(
    conn: sqlite3.Connection,
    idea_id: int,
) -> tuple[VerifiedSource, ...]:
    rows = conn.execute(
        """
        SELECT source_key, publisher, published_at, url, excerpt, source_kind
        FROM idea_sources
        WHERE idea_id = ?
        ORDER BY source_key
        """,
        (idea_id,),
    ).fetchall()
    return tuple(
        VerifiedSource(
            row["source_key"],
            row["publisher"],
            row["published_at"],
            row["url"],
            row["excerpt"],
            row["source_kind"],
        )
        for row in rows
    )


def save_brand_asset(
    conn: sqlite3.Connection,
    asset: BrandAsset,
) -> None:
    with conn:
        conn.execute(
            """
            INSERT INTO brand_assets (
                company_key, company, local_path,
                official_source_url, verified_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(company_key) DO UPDATE SET
                company = excluded.company,
                local_path = excluded.local_path,
                official_source_url = excluded.official_source_url,
                verified_at = excluded.verified_at
            """,
            (
                asset.company.strip().casefold(),
                asset.company,
                str(asset.local_path),
                asset.official_source_url,
                asset.verified_at,
            ),
        )


def get_brand_asset(
    conn: sqlite3.Connection,
    company: str,
) -> BrandAsset | None:
    row = conn.execute(
        """
        SELECT company, local_path, official_source_url, verified_at
        FROM brand_assets
        WHERE company_key = ?
        """,
        (company.strip().casefold(),),
    ).fetchone()
    if row is None:
        return None
    return BrandAsset(
        row["company"],
        Path(row["local_path"]),
        row["official_source_url"],
        row["verified_at"],
    )


def save_carousel(
    conn: sqlite3.Connection,
    idea_id: int,
    rows: list[dict],
) -> None:
    conn.execute("DELETE FROM carousel_pages WHERE idea_id = ?", (idea_id,))
    conn.executemany(
        """
        INSERT INTO carousel_pages (
            idea_id, page_no, page_type, heading, body,
            grounding, source_quote, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                idea_id,
                row["page_no"],
                row["page_type"],
                row["heading"],
                row["body"],
                row["grounding"],
                row["source_quote"],
                _now(),
            )
            for row in rows
        ],
    )
    conn.commit()


def get_carousel(
    conn: sqlite3.Connection,
    idea_id: int,
) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM carousel_pages WHERE idea_id = ? ORDER BY page_no",
        (idea_id,),
    ).fetchall()


def save_carousel_draft(
    conn: sqlite3.Connection,
    idea_id: int,
    draft: CarouselDraft,
    expected_revision: int | None = None,
) -> CarouselDraftMeta | None:
    validate_draft(draft)
    existing = get_carousel_draft_meta(conn, idea_id)
    if existing is not None:
        with conn:
            current = get_carousel_draft_meta(conn, idea_id)
            assert current is not None
            if (
                expected_revision is not None
                and expected_revision != current.content_revision
            ):
                raise RevisionConflict(
                    expected_revision,
                    current.content_revision,
                )
            _replace_carousel_draft(conn, idea_id, draft)
            conn.execute(
                """
                UPDATE carousel_drafts
                SET content_revision = ?, updated_at = ?
                WHERE idea_id = ?
                """,
                (current.content_revision + 1, _now(), idea_id),
            )
        return get_carousel_draft_meta(conn, idea_id)

    idea = conn.execute(
        "SELECT theme_id FROM ideas WHERE id = ?",
        (idea_id,),
    ).fetchone()
    if idea is None:
        raise ValueError(f"找不到候選：{idea_id}")
    if idea["theme_id"] is None:
        with conn:
            _replace_carousel_draft(conn, idea_id, draft)
        return None

    from daibu.cards import layout_repository

    active = layout_repository.get_active_version(
        conn,
        int(idea["theme_id"]),
    )
    with conn:
        _replace_carousel_draft(conn, idea_id, draft)
        conn.execute(
            """
            INSERT INTO carousel_drafts (
                idea_id, template_version_id, content_revision, updated_at
            ) VALUES (?, ?, 1, ?)
            """,
            (idea_id, active.id, _now()),
        )
    return get_carousel_draft_meta(conn, idea_id)


def get_carousel_draft_meta(
    conn: sqlite3.Connection,
    idea_id: int,
) -> CarouselDraftMeta | None:
    row = conn.execute(
        "SELECT * FROM carousel_drafts WHERE idea_id = ?",
        (idea_id,),
    ).fetchone()
    if row is None:
        return None
    return CarouselDraftMeta(
        idea_id=int(row["idea_id"]),
        template_version_id=int(row["template_version_id"]),
        content_revision=int(row["content_revision"]),
        updated_at=str(row["updated_at"]),
    )


def upgrade_carousel_template(
    conn: sqlite3.Connection,
    idea_id: int,
    template_version_id: int,
) -> CarouselDraftMeta:
    metadata = get_carousel_draft_meta(conn, idea_id)
    if metadata is None:
        raise ValueError("這份草稿尚未綁定模板版本")
    idea = conn.execute(
        "SELECT theme_id FROM ideas WHERE id = ?",
        (idea_id,),
    ).fetchone()
    if idea is None or idea["theme_id"] is None:
        raise ValueError("這份草稿不屬於任何內容系列")

    from daibu.cards import layout_repository

    version = layout_repository.get_version(conn, template_version_id)
    if version.theme_id != int(idea["theme_id"]):
        raise ValueError("模板版本不屬於這份草稿的內容系列")
    with conn:
        conn.execute(
            """
            UPDATE carousel_drafts
            SET template_version_id = ?, content_revision = ?, updated_at = ?
            WHERE idea_id = ?
            """,
            (
                template_version_id,
                metadata.content_revision + 1,
                _now(),
                idea_id,
            ),
        )
    upgraded = get_carousel_draft_meta(conn, idea_id)
    assert upgraded is not None
    return upgraded


def _replace_carousel_draft(
    conn: sqlite3.Connection,
    idea_id: int,
    draft: CarouselDraft,
) -> None:
    conn.execute(
        "DELETE FROM carousel_pages WHERE idea_id = ?",
        (idea_id,),
    )
    conn.execute(
        "DELETE FROM carousel_sources WHERE idea_id = ?",
        (idea_id,),
    )
    conn.executemany(
        """
        INSERT INTO carousel_sources (
            idea_id, source_key, position, publisher,
            published_at, url, excerpt, source_kind
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                idea_id,
                source.source_id,
                position,
                source.publisher,
                source.published_at,
                source.url,
                source.excerpt,
                source.source_kind,
            )
            for position, source in enumerate(draft.sources)
        ],
    )
    conn.executemany(
        """
        INSERT INTO carousel_pages (
            idea_id, page_no, page_type, heading, body,
            grounding, source_quote, sections_json, diagram_json,
            source_label, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'source', '', ?, ?, ?, ?)
        """,
        [
            (
                idea_id,
                page.page_no,
                page.page_type,
                page.heading,
                "\n".join(section.text for section in page.sections),
                json.dumps(
                    [asdict(section) for section in page.sections],
                    ensure_ascii=False,
                ),
                (
                    json.dumps(asdict(page.diagram), ensure_ascii=False)
                    if page.diagram
                    else ""
                ),
                page.source_label,
                _now(),
            )
            for page in draft.pages
        ],
    )


def save_researched_draft(
    conn: sqlite3.Connection,
    idea_id: int,
    draft: CarouselDraft,
) -> CarouselDraftMeta | None:
    """Replace research pack and immutable draft snapshot together."""
    from daibu.cards.schema import validate_grounded_draft

    validate_grounded_draft(draft)
    existing = get_carousel_draft_meta(conn, idea_id)
    active_version_id: int | None = None
    if existing is None:
        idea = conn.execute(
            "SELECT theme_id FROM ideas WHERE id = ?",
            (idea_id,),
        ).fetchone()
        if idea is None:
            raise ValueError(f"找不到候選：{idea_id}")
        if idea["theme_id"] is not None:
            from daibu.cards import layout_repository

            active_version_id = layout_repository.get_active_version(
                conn,
                int(idea["theme_id"]),
            ).id
    with conn:
        _replace_idea_sources(conn, idea_id, draft.sources)
        _replace_carousel_draft(conn, idea_id, draft)
        if existing is not None:
            conn.execute(
                """
                UPDATE carousel_drafts
                SET content_revision = ?, updated_at = ?
                WHERE idea_id = ?
                """,
                (existing.content_revision + 1, _now(), idea_id),
            )
        elif active_version_id is not None:
            conn.execute(
                """
                INSERT INTO carousel_drafts (
                    idea_id, template_version_id,
                    content_revision, updated_at
                ) VALUES (?, ?, 1, ?)
                """,
                (idea_id, active_version_id, _now()),
            )
    return get_carousel_draft_meta(conn, idea_id)


def get_carousel_draft(
    conn: sqlite3.Connection,
    idea_id: int,
) -> CarouselDraft | None:
    source_rows = conn.execute(
        """
        SELECT source_key, publisher, published_at, url, excerpt, source_kind
        FROM carousel_sources
        WHERE idea_id = ?
        ORDER BY position, source_key
        """,
        (idea_id,),
    ).fetchall()
    page_rows = conn.execute(
        """
        SELECT page_no, page_type, heading, sections_json,
               diagram_json, source_label
        FROM carousel_pages
        WHERE idea_id = ? AND sections_json != '[]'
        ORDER BY page_no
        """,
        (idea_id,),
    ).fetchall()
    if not page_rows:
        return None

    sources = tuple(
        VerifiedSource(
            row["source_key"],
            row["publisher"],
            row["published_at"],
            row["url"],
            row["excerpt"],
            row["source_kind"],
        )
        for row in source_rows
    )
    pages = []
    for row in page_rows:
        sections = tuple(
            ContentSection(
                item["label"],
                item["text"],
                tuple(item["source_ids"]),
                tuple(
                    EvidenceQuote(
                        evidence["source_id"],
                        evidence["quote"],
                    )
                    for evidence in item.get("evidence_quotes", [])
                ),
            )
            for item in json.loads(row["sections_json"])
        )
        raw_diagram = (
            json.loads(row["diagram_json"])
            if row["diagram_json"]
            else None
        )
        diagram = (
            DiagramSpec(
                raw_diagram["kind"],
                tuple(
                    DiagramNode(
                        node["title"],
                        node["text"],
                        node.get("expression", ""),
                    )
                    for node in raw_diagram["nodes"]
                ),
            )
            if raw_diagram
            else None
        )
        pages.append(
            CarouselPage(
                row["page_no"],
                row["page_type"],
                row["heading"],
                sections,
                diagram,
                row["source_label"],
            )
        )
    draft = CarouselDraft(sources, tuple(pages))
    validate_draft(draft)
    return draft


def update_carousel_page(
    conn: sqlite3.Connection,
    page_id: int,
    heading: str,
    body: str,
) -> None:
    conn.execute(
        """
        UPDATE carousel_pages
        SET heading = ?, body = ?, updated_at = ?
        WHERE id = ?
        """,
        (heading, body, _now(), page_id),
    )
    conn.commit()
