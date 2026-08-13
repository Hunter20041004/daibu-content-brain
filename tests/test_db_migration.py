from daibu import db
from daibu.llm.base import Idea
from daibu.models import CompanyEligibility, Source, Theme


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


def test_startup_source_strategy_migrates_without_changing_content(tmp_path):
    conn = db.connect(str(tmp_path / "startup-sources.db"))
    db.init_schema(conn)
    yc_id = db.add_source(
        conn,
        Source(
            None,
            "Y Combinator Blog",
            "https://www.ycombinator.com/blog/rss",
            "rss",
            True,
        ),
    )
    a16z_id = db.add_source(
        conn,
        Source(None, "a16z", "https://a16z.com/feed/", "rss", True),
    )
    other_id = db.add_source(
        conn,
        Source(None, "Hacker News", "https://hnrss.org/frontpage", "rss", True),
    )
    theme_id = db.add_theme(
        conn,
        Theme(
            None,
            "AI 新創介紹",
            4,
            [yc_id, a16z_id],
            3,
            "company_profile",
        ),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            "Existing idea",
            "Existing angle",
            "https://example.com/existing",
            company="ExistingCo",
            source_excerpt="Exact excerpt",
        ),
    )
    conn.execute(
        """
        INSERT INTO idea_sources (
            idea_id, source_key, publisher, published_at,
            url, excerpt, source_kind
        ) VALUES (?, 'primary', 'Publisher', '2026-08-01',
                  'https://example.com/source', 'Quote', 'manual')
        """,
        (idea_id,),
    )
    conn.execute(
        """
        INSERT INTO carousel_sources (
            idea_id, source_key, position, publisher, published_at,
            url, excerpt, source_kind
        ) VALUES (?, 'primary', 0, 'Publisher', '2026-08-01',
                  'https://example.com/source', 'Quote', 'manual')
        """,
        (idea_id,),
    )
    conn.execute(
        """
        INSERT INTO carousel_pages (
            idea_id, page_no, page_type, heading, body
        ) VALUES (?, 1, 'cover', 'Heading', 'Body')
        """,
        (idea_id,),
    )
    db.save_company_eligibility(
        conn,
        CompanyEligibility(
            "existingco",
            "ExistingCo",
            "eligible",
            2022,
            "private_independent",
            "Verified",
            (),
            "2026-08-01 09:00:00",
        ),
    )
    conn.commit()
    protected_tables = (
        "ideas",
        "idea_sources",
        "carousel_sources",
        "carousel_pages",
        "company_eligibility",
    )
    before = {
        table: [
            tuple(row)
            for row in conn.execute(
                f"SELECT * FROM {table} ORDER BY rowid"
            )
        ]
        for table in protected_tables
    }

    db.init_schema(conn)
    db.init_schema(conn)

    by_name = {source.name: source for source in db.get_sources(conn)}
    theme = next(
        item for item in db.get_themes(conn) if item.id == theme_id
    )
    bound_names = {
        by_name[source_name].name
        for source_name in by_name
        if by_name[source_name].id in theme.source_ids
    }
    after = {
        table: [
            tuple(row)
            for row in conn.execute(
                f"SELECT * FROM {table} ORDER BY rowid"
            )
        ]
        for table in protected_tables
    }

    assert by_name["Y Combinator Blog"].enabled is True
    assert by_name["a16z"].enabled is False
    assert by_name["Hacker News"].id == other_id
    assert bound_names == {
        "YC Launches",
        "YC Companies",
        "a16z Speedrun Companies",
        "TechCrunch Startups",
    }
    assert before == after
    assert db.get_config(conn, "startup_source_strategy_v1") == "1"


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


def test_migration_adds_content_kind_without_changing_existing_data(tmp_path):
    path = tmp_path / "content-kind.db"
    conn = db.connect(str(path))
    db.init_schema(conn)
    conn.executemany(
        "INSERT INTO themes (name, weekday, n_ideas) VALUES (?, ?, ?)",
        [
            ("AI 新創介紹", 4, 3),
            ("AI 近期大事", 0, 3),
        ],
    )
    startup_id = conn.execute(
        "SELECT id FROM themes WHERE name = 'AI 新創介紹'"
    ).fetchone()["id"]
    conn.executemany(
        """
        INSERT INTO ideas (theme_id, title, angle, status, body)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (startup_id, "候選公司", "角度", "候選", ""),
            (startup_id, "已採用公司", "角度", "採用", "保留正文"),
        ],
    )
    conn.execute("ALTER TABLE themes DROP COLUMN content_kind")
    conn.commit()
    before = [
        tuple(row)
        for row in conn.execute(
            "SELECT title, status, body FROM ideas ORDER BY id"
        )
    ]
    conn.close()

    conn = db.connect(str(path))
    db.init_schema(conn)

    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(themes)")
    }
    kinds = {
        row["name"]: row["content_kind"]
        for row in conn.execute("SELECT name, content_kind FROM themes")
    }
    after = [
        tuple(row)
        for row in conn.execute(
            "SELECT title, status, body FROM ideas ORDER BY id"
        )
    ]
    assert "content_kind" in columns
    assert kinds == {
        "AI 新創介紹": "company_profile",
        "AI 近期大事": "general",
    }
    assert after == before
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


def test_migration_adds_source_kind_without_changing_old_rows(tmp_path):
    from daibu.llm.base import Idea
    from tests.card_fixtures import carousel_draft

    path = tmp_path / "source-kind.db"
    conn = db.connect(str(path))
    db.init_schema(conn)
    idea_id = db.add_idea(conn, None, Idea("t", "a", ""))
    original = carousel_draft()
    db.save_idea_sources(conn, idea_id, original.sources)
    db.save_carousel_draft(conn, idea_id, original)
    for table in ("idea_sources", "carousel_sources"):
        conn.execute(f"ALTER TABLE {table} DROP COLUMN source_kind")
    before = {
        table: [tuple(row) for row in conn.execute(
            f"SELECT idea_id, source_key, publisher, published_at, url, excerpt "
            f"FROM {table} ORDER BY source_key"
        )]
        for table in ("idea_sources", "carousel_sources")
    }

    db.init_schema(conn)

    for table in ("idea_sources", "carousel_sources"):
        columns = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table})")
        }
        assert "source_kind" in columns
        assert {
            row["source_kind"]
            for row in conn.execute(f"SELECT source_kind FROM {table}")
        } == {"manual"}
        after = [tuple(row) for row in conn.execute(
            f"SELECT idea_id, source_key, publisher, published_at, url, excerpt "
            f"FROM {table} ORDER BY source_key"
        )]
        assert after == before[table]


def test_migration_adds_brand_assets_idempotently(tmp_path):
    path = tmp_path / "brand-assets.db"
    conn = db.connect(str(path))
    db.init_schema(conn)
    conn.execute("DROP TABLE IF EXISTS brand_assets")
    conn.commit()

    db.init_schema(conn)
    db.init_schema(conn)

    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(brand_assets)")
    }
    assert {
        "company_key",
        "company",
        "local_path",
        "official_source_url",
        "verified_at",
    } <= columns


def test_single_series_cleanup_keeps_target_graph_and_shared_assets(tmp_path):
    conn = db.connect(str(tmp_path / "single-series.db"))
    db.init_schema(conn)
    conn.execute(
        "DELETE FROM config WHERE key = 'single_series_cleanup_v1'"
    )
    source_id = conn.execute(
        """
        INSERT INTO sources (name, url, fetch_type, enabled)
        VALUES ('共同來源', 'https://example.com/feed', 'rss', 1)
        """
    ).lastrowid
    target_id = conn.execute(
        """
        INSERT INTO themes (name, weekday, n_ideas, content_kind)
        VALUES ('AI 新創介紹', 4, 3, 'company_profile')
        """
    ).lastrowid
    other_id = conn.execute(
        """
        INSERT INTO themes (name, weekday, n_ideas, content_kind)
        VALUES ('其他系列', 1, 2, 'general')
        """
    ).lastrowid
    conn.executemany(
        "INSERT INTO theme_sources (theme_id, source_id) VALUES (?, ?)",
        [(target_id, source_id), (other_id, source_id)],
    )
    kept_idea_id = conn.execute(
        """
        INSERT INTO ideas (theme_id, title, angle, status, body)
        VALUES (?, '保留題目', '保留角度', '採用', '保留正文')
        """,
        (target_id,),
    ).lastrowid
    removed_idea_id = conn.execute(
        """
        INSERT INTO ideas (theme_id, title, angle, status, body)
        VALUES (?, '刪除題目', '刪除角度', '候選', '刪除正文')
        """,
        (other_id,),
    ).lastrowid
    for idea_id, label in (
        (kept_idea_id, "保留"),
        (removed_idea_id, "刪除"),
    ):
        conn.execute(
            """
            INSERT INTO performance (
                idea_id, platform, likes, reach, engagement
            ) VALUES (?, 'Instagram', 1, 10, 0.1)
            """,
            (idea_id,),
        )
        conn.execute(
            """
            INSERT INTO carousel_pages (
                idea_id, page_no, page_type, heading, body
            ) VALUES (?, 1, 'cover', ?, ?)
            """,
            (idea_id, f"{label}標題", f"{label}內文"),
        )
        for table in ("carousel_sources", "idea_sources"):
            conn.execute(
                f"""
                INSERT INTO {table} (
                    idea_id, source_key, publisher, published_at,
                    url, excerpt
                ) VALUES (?, 'S1', '官方網站', '2026-08-01',
                          'https://example.com/source', ?)
                """,
                (idea_id, f"{label}摘錄"),
            )
    conn.execute(
        """
        INSERT INTO brand_assets (
            company_key, company, local_path,
            official_source_url, verified_at
        ) VALUES (
            'target', '目標公司', '/tmp/logo.svg',
            'https://example.com/brand', '2026-08-01'
        )
        """
    )
    conn.commit()

    db.init_schema(conn)

    assert [
        row["name"] for row in conn.execute("SELECT name FROM themes")
    ] == ["AI 新創介紹"]
    assert [
        row["title"] for row in conn.execute("SELECT title FROM ideas")
    ] == ["保留題目"]
    for table in (
        "performance",
        "carousel_pages",
        "carousel_sources",
        "idea_sources",
    ):
        assert conn.execute(
            f"SELECT COUNT(*) AS count FROM {table}"
        ).fetchone()["count"] == 1
    assert conn.execute(
        "SELECT COUNT(*) AS count FROM sources"
    ).fetchone()["count"] == 5
    assert conn.execute(
        "SELECT COUNT(*) AS count FROM sources WHERE name = '共同來源'"
    ).fetchone()["count"] == 1
    assert conn.execute(
        "SELECT COUNT(*) AS count FROM brand_assets"
    ).fetchone()["count"] == 1
    assert conn.execute(
        "SELECT value FROM config WHERE key = 'single_series_cleanup_v1'"
    ).fetchone()["value"] == "1"


def test_single_series_cleanup_runs_only_once(tmp_path):
    conn = db.connect(str(tmp_path / "single-series-once.db"))
    db.init_schema(conn)
    conn.execute(
        "DELETE FROM config WHERE key = 'single_series_cleanup_v1'"
    )
    conn.executemany(
        """
        INSERT INTO themes (name, weekday, n_ideas, content_kind)
        VALUES (?, 1, 2, ?)
        """,
        [
            ("AI 新創介紹", "company_profile"),
            ("應被清除", "general"),
        ],
    )
    conn.commit()
    db.init_schema(conn)

    db.add_theme(
        conn,
        Theme(None, "未來程式新增系列", 2, [], 3),
    )
    db.init_schema(conn)

    assert [theme.name for theme in db.get_themes(conn)] == [
        "AI 新創介紹",
        "未來程式新增系列",
    ]


def test_single_series_cleanup_preserves_data_when_target_is_missing(
    tmp_path,
):
    conn = db.connect(str(tmp_path / "single-series-missing.db"))
    db.init_schema(conn)
    conn.execute(
        "DELETE FROM config WHERE key = 'single_series_cleanup_v1'"
    )
    conn.executemany(
        """
        INSERT INTO themes (name, weekday, n_ideas, content_kind)
        VALUES (?, 1, 2, 'general')
        """,
        [("系列甲",), ("系列乙",)],
    )
    conn.commit()

    db.init_schema(conn)

    assert [theme.name for theme in db.get_themes(conn)] == [
        "系列甲",
        "系列乙",
    ]
    assert conn.execute(
        "SELECT 1 FROM config WHERE key = 'single_series_cleanup_v1'"
    ).fetchone() is None


def test_single_series_cleanup_preserves_data_when_target_is_ambiguous(
    tmp_path,
):
    conn = db.connect(str(tmp_path / "single-series-ambiguous.db"))
    db.init_schema(conn)
    conn.execute(
        "DELETE FROM config WHERE key = 'single_series_cleanup_v1'"
    )
    conn.executemany(
        """
        INSERT INTO themes (name, weekday, n_ideas, content_kind)
        VALUES ('AI 新創介紹', ?, 2, 'company_profile')
        """,
        [(1,), (2,)],
    )
    conn.commit()

    db.init_schema(conn)

    assert conn.execute(
        "SELECT COUNT(*) AS count FROM themes"
    ).fetchone()["count"] == 2
    assert conn.execute(
        "SELECT 1 FROM config WHERE key = 'single_series_cleanup_v1'"
    ).fetchone() is None
