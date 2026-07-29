from daibu import db, performance
from daibu.llm.base import Idea
from daibu.models import Source, Theme


def test_add_and_get_theme(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    theme_id = db.add_theme(
        conn,
        Theme(
            None,
            "AI 近期大事",
            weekday=0,
            source_ids=[],
            n_ideas=3,
        ),
    )

    themes = db.get_themes(conn)
    assert len(themes) == 1
    assert themes[0].id == theme_id and themes[0].name == "AI 近期大事"
    assert themes[0].source_ids == []


def test_add_and_get_theme_keeps_its_bound_sources(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_a = db.add_source(
        conn,
        Source(None, "來源 A", "https://a.example", "rss", True),
    )
    source_b = db.add_source(
        conn,
        Source(None, "來源 B", "https://b.example", "search", True),
    )

    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 近期大事", 0, [source_a, source_b], 3),
    )

    theme = db.get_themes(conn)[0]
    assert theme.id == theme_id
    assert theme.source_ids == [source_a, source_b]


def test_update_theme_replaces_its_bound_sources(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_a = db.add_source(
        conn,
        Source(None, "來源 A", "https://a.example", "rss", True),
    )
    source_b = db.add_source(
        conn,
        Source(None, "來源 B", "https://b.example", "rss", True),
    )
    theme_id = db.add_theme(
        conn,
        Theme(None, "主題", 0, [source_a], 2),
    )

    db.update_theme(
        conn,
        Theme(theme_id, "主題", 0, [source_b], 2),
    )

    assert db.get_themes(conn)[0].source_ids == [source_b]


def test_add_and_get_sources_without_layers(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    db.add_source(
        conn,
        Source(
            None,
            "TechCrunch",
            "https://techcrunch.com/feed/",
            "rss",
            True,
        ),
    )
    db.add_source(
        conn,
        Source(None, "a16z", "https://a16z.com/feed/", "rss", True),
    )

    assert [source.name for source in db.get_sources(conn)] == [
        "TechCrunch",
        "a16z",
    ]


def test_count_themes_using_source(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(None, "共用來源", "https://example.com/feed", "rss", True),
    )
    db.add_theme(conn, Theme(None, "主題 A", 0, [source_id], 1))
    db.add_theme(conn, Theme(None, "主題 B", 1, [source_id], 1))
    db.add_theme(conn, Theme(None, "未使用", 2, [], 1))

    assert db.count_themes_using_source(conn, source_id) == 2


def test_get_ideas_returns_newest_first(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "排序主題", 0, [], 1),
    )
    older_id = db.add_idea(
        conn,
        theme_id,
        Idea("較早候選", "角度", ""),
    )
    newer_id = db.add_idea(
        conn,
        theme_id,
        Idea("最新候選", "角度", ""),
    )
    conn.execute(
        "UPDATE ideas SET created_at = ? WHERE id = ?",
        ("2026-07-25 09:00:00", older_id),
    )
    conn.execute(
        "UPDATE ideas SET created_at = ? WHERE id = ?",
        ("2026-07-25 10:00:00", newer_id),
    )
    conn.commit()

    assert [
        idea.id for idea in db.get_ideas(conn, status="候選")
    ] == [newer_id, older_id]


def test_init_schema_creates_all_product_tables(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    table_names = {row["name"] for row in rows}

    assert {
        "themes",
        "sources",
        "theme_sources",
        "config",
        "ideas",
        "performance",
    } <= table_names


def test_add_and_get_candidate_idea(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 大事", 0, [], 2),
    )

    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("標題", "角度", "https://example.com/a"),
        status="候選",
    )

    ideas = db.get_ideas(conn, status="候選")
    assert len(ideas) == 1
    assert ideas[0].id == idea_id
    assert ideas[0].theme_id == theme_id
    assert ideas[0].source_url == "https://example.com/a"
    assert not hasattr(ideas[0], "gate_score")
    assert ideas[0].status == "候選"


def test_add_and_get_idea_keeps_company_and_excerpt(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea = Idea(
        title="讓文字開口說話",
        angle="語音合成的成本結構被改寫",
        source_url="https://example.com/a",
        company="ElevenLabs",
        source_excerpt="ElevenLabs 於 2022 年在倫敦成立。",
    )

    idea_id = db.add_idea(conn, None, idea)
    stored = [item for item in db.get_ideas(conn) if item.id == idea_id][0]

    assert stored.company == "ElevenLabs"
    assert stored.source_excerpt == "ElevenLabs 於 2022 年在倫敦成立。"
    conn.close()


def test_add_idea_records_local_created_time(monkeypatch, tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    local_time = "2031-02-03 20:09:10"
    monkeypatch.setattr(db, "_now", lambda: local_time, raising=False)

    db.add_idea(conn, None, Idea("本機時間題目", "角度", ""))

    idea = db.get_ideas(conn)[0]
    assert idea.created_at == local_time


def test_ideas_table_has_no_gate_columns(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(ideas)")
    }

    assert "gate_score" not in columns
    assert "gate_reason" not in columns


def test_update_theme_replaces_editable_fields(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "舊名稱", 0, [], 2),
    )

    db.update_theme(
        conn,
        Theme(theme_id, "新名稱", 3, [], 4),
    )

    theme = db.get_themes(conn)[0]
    assert theme.name == "新名稱"
    assert theme.weekday == 3
    assert theme.source_ids == []
    assert theme.n_ideas == 4


def test_delete_theme_removes_it(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(None, "來源", "https://example.com", "rss", True),
    )
    theme_id = db.add_theme(
        conn,
        Theme(None, "待刪除", 0, [source_id], 2),
    )

    db.delete_theme(conn, theme_id)

    assert db.get_themes(conn) == []
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM theme_sources WHERE theme_id = ?",
            (theme_id,),
        ).fetchone()[0]
        == 0
    )


def test_delete_theme_also_deletes_its_ideas(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "連內容刪除", 0, [], 3))
    for status in ("候選", "採用", "已發"):
        idea_id = db.add_idea(
            conn,
            theme_id,
            Idea(f"{status}題目", "角度", ""),
            status=status,
        )
    performance.record(conn, idea_id, "Threads", 1, 10, 2.0)

    db.delete_theme(conn, theme_id)

    assert db.get_ideas(conn) == []
    assert conn.execute("SELECT COUNT(*) FROM performance").fetchone()[0] == 0


def test_delete_theme_leaves_other_themes_ideas_untouched(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    deleted_theme_id = db.add_theme(
        conn,
        Theme(None, "刪除這個", 0, [], 1),
    )
    kept_theme_id = db.add_theme(
        conn,
        Theme(None, "保留這個", 1, [], 1),
    )
    db.add_idea(conn, deleted_theme_id, Idea("一起刪除", "角度", ""))
    kept_idea_id = db.add_idea(
        conn,
        kept_theme_id,
        Idea("必須保留", "角度", ""),
    )

    db.delete_theme(conn, deleted_theme_id)

    assert [idea.id for idea in db.get_ideas(conn)] == [kept_idea_id]


def test_count_theme_content_reports_what_will_be_deleted(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "刪除預覽", 0, [], 9))
    other_theme_id = db.add_theme(
        conn,
        Theme(None, "不列入預覽", 1, [], 1),
    )
    for index in range(8):
        db.add_idea(conn, theme_id, Idea(f"候選 {index}", "角度", ""))
    db.add_idea(
        conn,
        theme_id,
        Idea("已發布", "角度", ""),
        status="已發",
    )
    db.add_idea(conn, other_theme_id, Idea("別的主題", "角度", ""))

    counts = db.count_theme_content(conn, theme_id)

    assert counts == {"候選": 8, "採用": 0, "已發": 1}


def test_update_source_replaces_editable_fields(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(None, "舊來源", "https://old.example", "rss", True),
    )

    db.update_source(
        conn,
        Source(
            source_id,
            "新來源",
            "https://new.example",
            "search",
            False,
        ),
    )

    source = db.get_sources(conn)[0]
    assert source.name == "新來源"
    assert source.url == "https://new.example"
    assert source.fetch_type == "search"
    assert source.enabled is False


def test_delete_source_removes_it(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(None, "待刪除", "https://example.com", "rss", True),
    )

    db.delete_source(conn, source_id)

    assert db.get_sources(conn) == []


def test_deleting_a_source_unbinds_it_from_themes(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(None, "待刪除", "https://example.com", "rss", True),
    )
    theme_id = db.add_theme(
        conn,
        Theme(None, "主題", 0, [source_id], 2),
    )

    db.delete_source(conn, source_id)

    theme = next(
        theme for theme in db.get_themes(conn) if theme.id == theme_id
    )
    assert theme.source_ids == []


def test_set_config_upserts_value(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    db.set_config(conn, "gate_line", "第一版")
    db.set_config(conn, "gate_line", "第二版")

    assert db.get_config(conn, "gate_line") == "第二版"
    assert db.get_config(conn, "missing", default="預設") == "預設"


def test_update_idea_content_saves_tweaked_title_and_angle(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea("舊標題", "舊角度", ""),
    )

    db.update_idea_content(conn, idea_id, "新標題", "新角度")

    idea = db.get_ideas(conn)[0]
    assert idea.title == "新標題"
    assert idea.angle == "新角度"


def test_delete_idea_removes_rejected_candidate(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea("淘汰題目", "角度", ""),
    )

    db.delete_idea(conn, idea_id)

    assert db.get_ideas(conn) == []
