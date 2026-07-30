from daibu import db


def _old_connection(tmp_path):
    conn = db.connect(str(tmp_path / "legacy.db"))
    conn.executescript(
        """
        CREATE TABLE themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            weekday INTEGER NOT NULL,
            kind TEXT NOT NULL,
            source_layers TEXT NOT NULL,
            n_ideas INTEGER NOT NULL
        );

        CREATE TABLE sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            layer TEXT NOT NULL,
            fetch_type TEXT NOT NULL,
            enabled INTEGER NOT NULL
        );

        CREATE TABLE config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            theme_id INTEGER,
            title TEXT NOT NULL,
            angle TEXT NOT NULL,
            gate_score INTEGER NOT NULL,
            gate_reason TEXT NOT NULL,
            source_url TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            likes INTEGER NOT NULL,
            reach INTEGER NOT NULL,
            engagement REAL NOT NULL,
            posted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.executemany(
        """
        INSERT INTO themes (
            id, name, weekday, kind, source_layers, n_ideas
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "AI 近期大事", 0, "timely", "L1,L3", 3),
            (2, "熱門 Skill", 2, "timely", "L2", 2),
        ],
    )
    conn.executemany(
        """
        INSERT INTO sources (
            id, name, url, layer, fetch_type, enabled
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "RSS A", "https://a.example/feed", "L1", "rss", 1),
            (2, "Manual", "https://manual.example", "L3", "manual", 1),
            (3, "Search B", "example.com", "L2", "search", 1),
            (4, "RSS C", "https://c.example/feed", "L3", "rss", 1),
        ],
    )
    conn.executemany(
        """
        INSERT INTO ideas (
            id, theme_id, title, angle, gate_score, gate_reason,
            source_url, status, body, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                1,
                1,
                "候選題",
                "角度",
                80,
                "理由",
                "https://a.example/1",
                "候選",
                "",
                "2026-07-20 10:00:00",
            ),
            (
                2,
                1,
                "草稿題",
                "角度",
                70,
                "理由",
                "",
                "草稿",
                "保留這段正文",
                "2026-07-21 10:00:00",
            ),
            (
                3,
                2,
                "排程題",
                "角度",
                75,
                "理由",
                "",
                "已排程",
                "排程正文",
                "2026-07-22 10:00:00",
            ),
            (
                4,
                2,
                "已發題",
                "角度",
                90,
                "理由",
                "",
                "已發",
                "已發正文",
                "2026-07-23 10:00:00",
            ),
        ],
    )
    conn.execute(
        """
        INSERT INTO performance (
            id, idea_id, platform, likes, reach, engagement
        )
        VALUES (1, 4, 'Threads', 10, 100, 0.1)
        """
    )
    conn.commit()
    return conn


def test_migration_drops_gate_columns_and_keeps_ideas(tmp_path):
    conn = _old_connection(tmp_path)

    db.init_schema(conn)

    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(ideas)")
    }
    ideas = conn.execute(
        "SELECT id, title FROM ideas ORDER BY id"
    ).fetchall()
    assert "gate_score" not in columns
    assert "gate_reason" not in columns
    assert [(row["id"], row["title"]) for row in ideas] == [
        (1, "候選題"),
        (2, "草稿題"),
        (3, "排程題"),
        (4, "已發題"),
    ]


def test_migration_folds_retired_statuses_into_adopted(tmp_path):
    conn = _old_connection(tmp_path)

    db.init_schema(conn)

    statuses = {
        row["title"]: row["status"]
        for row in conn.execute("SELECT title, status FROM ideas")
    }
    assert statuses["草稿題"] == "採用"
    assert statuses["排程題"] == "採用"
    assert statuses["候選題"] == "候選"
    assert statuses["已發題"] == "已發"


def test_migration_keeps_written_body(tmp_path):
    conn = _old_connection(tmp_path)

    db.init_schema(conn)

    bodies = {
        row["title"]: row["body"]
        for row in conn.execute("SELECT title, body FROM ideas")
    }
    assert bodies["草稿題"] == "保留這段正文"
    assert bodies["已發題"] == "已發正文"


def test_migration_deletes_manual_sources(tmp_path):
    conn = _old_connection(tmp_path)

    db.init_schema(conn)

    sources = conn.execute(
        "SELECT name, fetch_type FROM sources ORDER BY id"
    ).fetchall()
    assert [(row["name"], row["fetch_type"]) for row in sources] == [
        ("RSS A", "rss"),
        ("Search B", "search"),
        ("RSS C", "rss"),
    ]


def test_migration_turns_layers_into_direct_source_bindings(tmp_path):
    conn = _old_connection(tmp_path)

    db.init_schema(conn)

    bindings = conn.execute(
        """
        SELECT theme_id, source_id
        FROM theme_sources
        ORDER BY theme_id, source_id
        """
    ).fetchall()
    assert [
        (row["theme_id"], row["source_id"]) for row in bindings
    ] == [(1, 1), (1, 4), (2, 3)]


def test_migration_drops_layer_and_kind_columns(tmp_path):
    conn = _old_connection(tmp_path)

    db.init_schema(conn)

    theme_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(themes)")
    }
    source_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(sources)")
    }
    assert "kind" not in theme_columns
    assert "source_layers" not in theme_columns
    assert "layer" not in source_columns


def test_migration_adds_published_at_as_null(tmp_path):
    conn = _old_connection(tmp_path)

    db.init_schema(conn)

    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(ideas)")
    }
    published_values = [
        row["published_at"]
        for row in conn.execute(
            "SELECT published_at FROM ideas ORDER BY id"
        )
    ]
    assert "published_at" in columns
    assert published_values == [None, None, None, None]


def test_migration_is_idempotent(tmp_path):
    conn = _old_connection(tmp_path)
    db.init_schema(conn)
    expected_counts = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in (
            "themes",
            "sources",
            "theme_sources",
            "ideas",
            "performance",
        )
    }

    db.init_schema(conn)

    actual_counts = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in expected_counts
    }
    assert actual_counts == expected_counts


def test_migration_marks_database_with_existing_themes_as_seeded(tmp_path):
    conn = _old_connection(tmp_path)

    db.init_schema(conn)

    assert db.get_config(conn, "seeds_loaded") == "1"


def test_migration_removes_retired_gate_line_config(tmp_path):
    conn = _old_connection(tmp_path)
    conn.executemany(
        "INSERT INTO config (key, value) VALUES (?, ?)",
        [
            ("gate_line", "已停用的守門線"),
            ("llm_provider", "groq"),
        ],
    )
    conn.commit()

    db.init_schema(conn)

    config = {
        row["key"]: row["value"]
        for row in conn.execute("SELECT key, value FROM config")
    }
    assert "gate_line" not in config
    assert config["llm_provider"] == "groq"


def test_adds_company_and_excerpt_columns_to_existing_db(tmp_path):
    """舊資料庫升級後要多出兩欄，且既有題目不得消失。"""
    path = tmp_path / "old.db"
    conn = db.connect(str(path))
    db.init_schema(conn)
    conn.execute(
        """
        INSERT INTO ideas (theme_id, title, angle, status)
        VALUES (NULL, '舊題目', '舊切角', '候選')
        """
    )
    conn.commit()
    # 模擬舊結構：把新欄位拿掉
    conn.execute("ALTER TABLE ideas DROP COLUMN company")
    conn.execute("ALTER TABLE ideas DROP COLUMN source_excerpt")
    conn.commit()
    conn.close()

    conn = db.connect(str(path))
    db.init_schema(conn)

    columns = {row["name"] for row in conn.execute("PRAGMA table_info(ideas)")}
    assert "company" in columns
    assert "source_excerpt" in columns

    rows = conn.execute("SELECT title, company FROM ideas").fetchall()
    assert len(rows) == 1
    assert rows[0]["title"] == "舊題目"
    assert rows[0]["company"] == ""
    conn.close()


def test_migration_adds_structured_carousel_storage_idempotently(tmp_path):
    path = tmp_path / "carousel.db"
    conn = db.connect(str(path))
    db.init_schema(conn)
    conn.execute("ALTER TABLE carousel_pages DROP COLUMN sections_json")
    conn.execute("ALTER TABLE carousel_pages DROP COLUMN diagram_json")
    conn.execute("ALTER TABLE carousel_pages DROP COLUMN source_label")
    conn.execute("DROP TABLE carousel_sources")
    conn.commit()

    db.init_schema(conn)
    db.init_schema(conn)

    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(carousel_pages)")
    }
    assert {"sections_json", "diagram_json", "source_label"} <= columns
    assert conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name='carousel_sources'"
    ).fetchone()


def test_migration_adds_carousel_source_position_idempotently(tmp_path):
    path = tmp_path / "carousel-sources.db"
    conn = db.connect(str(path))
    db.init_schema(conn)
    conn.execute("ALTER TABLE carousel_sources DROP COLUMN position")
    conn.commit()

    db.init_schema(conn)
    db.init_schema(conn)

    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(carousel_sources)")
    }
    assert "position" in columns
    conn.close()


def test_migration_adds_idea_source_pack_idempotently(tmp_path):
    path = tmp_path / "pack.db"
    conn = db.connect(str(path))
    db.init_schema(conn)
    conn.execute("DROP TABLE IF EXISTS idea_sources")
    conn.commit()

    db.init_schema(conn)
    db.init_schema(conn)

    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(idea_sources)")
    }
    assert {
        "idea_id",
        "source_key",
        "publisher",
        "published_at",
        "url",
        "excerpt",
    } <= columns
