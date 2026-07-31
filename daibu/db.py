import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from daibu.cards.schema import (
    BrandAsset,
    CarouselDraft,
    CarouselPage,
    ContentSection,
    DiagramNode,
    DiagramSpec,
    VerifiedSource,
    validate_draft,
    validate_sources,
)
from daibu.clock import now as _now
from daibu.llm.base import Idea
from daibu.models import Source, StoredIdea, Theme


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
            n_ideas INTEGER NOT NULL
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
        """
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
    conn.commit()


def add_theme(conn: sqlite3.Connection, theme: Theme) -> int:
    cursor = conn.execute(
        """
        INSERT INTO themes (name, weekday, n_ideas)
        VALUES (?, ?, ?)
        """,
        (
            theme.name,
            theme.weekday,
            theme.n_ideas,
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
        )
        for row in rows
    ]


def update_theme(conn: sqlite3.Connection, theme: Theme) -> None:
    if theme.id is None:
        raise ValueError("更新主題需要 id")
    conn.execute(
        """
        UPDATE themes
        SET name = ?, weekday = ?, n_ideas = ?
        WHERE id = ?
        """,
        (
            theme.name,
            theme.weekday,
            theme.n_ideas,
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
        "DELETE FROM theme_sources WHERE theme_id = ?",
        (theme_id,),
    )
    conn.execute("DELETE FROM themes WHERE id = ?", (theme_id,))
    conn.commit()


def count_theme_content(
    conn: sqlite3.Connection,
    theme_id: int,
) -> dict[str, int]:
    counts = {"候選": 0, "採用": 0, "已發": 0, "輪播草稿": 0}
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
    conn.execute("DELETE FROM carousel_pages WHERE idea_id = ?", (idea_id,))
    conn.execute("DELETE FROM carousel_sources WHERE idea_id = ?", (idea_id,))
    conn.execute("DELETE FROM idea_sources WHERE idea_id = ?", (idea_id,))
    conn.execute("DELETE FROM ideas WHERE id = ?", (idea_id,))
    conn.commit()


def save_idea_sources(
    conn: sqlite3.Connection,
    idea_id: int,
    sources: tuple[VerifiedSource, ...],
) -> None:
    validate_sources(sources)
    with conn:
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
) -> None:
    validate_draft(draft)
    with conn:
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
