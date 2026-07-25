import sqlite3

from daibu.llm.base import Idea
from daibu.models import Source, StoredIdea, Theme


def connect(path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_schema(conn: sqlite3.Connection) -> None:
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
        "DELETE FROM theme_sources WHERE theme_id = ?",
        (theme_id,),
    )
    conn.execute("DELETE FROM themes WHERE id = ?", (theme_id,))
    conn.commit()


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
            theme_id, title, angle, source_url, status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            theme_id,
            idea.title,
            idea.angle,
            idea.source_url,
            status,
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
    query += " ORDER BY id"

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
        )
        for row in rows
    ]


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


def delete_idea(conn: sqlite3.Connection, idea_id: int) -> None:
    # TODO(需澄清): spec 沒有「淘汰」狀態；v1 先把淘汰候選移除。
    conn.execute("DELETE FROM ideas WHERE id = ?", (idea_id,))
    conn.commit()
