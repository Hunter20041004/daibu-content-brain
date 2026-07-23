import sqlite3

from daibu.models import Source, Theme


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
            kind TEXT NOT NULL,
            source_layers TEXT NOT NULL,
            n_ideas INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            layer TEXT NOT NULL,
            fetch_type TEXT NOT NULL,
            enabled INTEGER NOT NULL
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
            gate_score INTEGER NOT NULL CHECK (gate_score BETWEEN 0 AND 100),
            gate_reason TEXT NOT NULL,
            source_url TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
        INSERT INTO themes (name, weekday, kind, source_layers, n_ideas)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            theme.name,
            theme.weekday,
            theme.kind,
            ",".join(theme.source_layers),
            theme.n_ideas,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_themes(conn: sqlite3.Connection) -> list[Theme]:
    rows = conn.execute("SELECT * FROM themes ORDER BY id").fetchall()
    return [
        Theme(
            id=row["id"],
            name=row["name"],
            weekday=row["weekday"],
            kind=row["kind"],
            source_layers=row["source_layers"].split(",")
            if row["source_layers"]
            else [],
            n_ideas=row["n_ideas"],
        )
        for row in rows
    ]


def add_source(conn: sqlite3.Connection, source: Source) -> int:
    cursor = conn.execute(
        """
        INSERT INTO sources (name, url, layer, fetch_type, enabled)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            source.name,
            source.url,
            source.layer,
            source.fetch_type,
            source.enabled,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_sources(
    conn: sqlite3.Connection, layer: str | None = None
) -> list[Source]:
    query = "SELECT * FROM sources"
    parameters: tuple[str, ...] = ()
    if layer is not None:
        query += " WHERE layer = ?"
        parameters = (layer,)
    query += " ORDER BY id"

    rows = conn.execute(query, parameters).fetchall()
    return [
        Source(
            id=row["id"],
            name=row["name"],
            url=row["url"],
            layer=row["layer"],
            fetch_type=row["fetch_type"],
            enabled=bool(row["enabled"]),
        )
        for row in rows
    ]
