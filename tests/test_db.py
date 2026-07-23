from daibu import db
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
            kind="timely",
            source_layers=["L1", "L3"],
            n_ideas=3,
        ),
    )

    themes = db.get_themes(conn)
    assert len(themes) == 1
    assert themes[0].id == theme_id and themes[0].name == "AI 近期大事"
    assert themes[0].kind == "timely"
    assert themes[0].source_layers == ["L1", "L3"]


def test_add_and_get_source_filter_by_layer(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    db.add_source(
        conn,
        Source(
            None,
            "TechCrunch",
            "https://techcrunch.com/feed/",
            "L1",
            "rss",
            True,
        ),
    )
    db.add_source(
        conn,
        Source(None, "a16z", "https://a16z.com/feed/", "L5", "rss", True),
    )

    assert len(db.get_sources(conn)) == 2
    assert [
        source.name for source in db.get_sources(conn, layer="L1")
    ] == ["TechCrunch"]


def test_init_schema_creates_all_product_tables(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    table_names = {row["name"] for row in rows}

    assert {"themes", "sources", "config", "ideas", "performance"} <= table_names


def test_add_and_get_candidate_idea(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 大事", 0, "timely", ["L1"], 2),
    )

    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("標題", "角度", 80, "理由", "https://example.com/a"),
        status="候選",
    )

    ideas = db.get_ideas(conn, status="候選")
    assert len(ideas) == 1
    assert ideas[0].id == idea_id
    assert ideas[0].theme_id == theme_id
    assert ideas[0].gate_score == 80
    assert ideas[0].status == "候選"


def test_update_theme_replaces_editable_fields(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "舊名稱", 0, "timely", ["L1"], 2),
    )

    db.update_theme(
        conn,
        Theme(theme_id, "新名稱", 3, "evergreen", ["L2", "L5"], 4),
    )

    theme = db.get_themes(conn)[0]
    assert theme.name == "新名稱"
    assert theme.weekday == 3
    assert theme.kind == "evergreen"
    assert theme.source_layers == ["L2", "L5"]
    assert theme.n_ideas == 4


def test_delete_theme_removes_it(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "待刪除", 0, "timely", ["L1"], 2),
    )

    db.delete_theme(conn, theme_id)

    assert db.get_themes(conn) == []


def test_update_source_replaces_editable_fields(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(None, "舊來源", "https://old.example", "L1", "rss", True),
    )

    db.update_source(
        conn,
        Source(
            source_id,
            "新來源",
            "https://new.example",
            "L5",
            "search",
            False,
        ),
    )

    source = db.get_sources(conn)[0]
    assert source.name == "新來源"
    assert source.url == "https://new.example"
    assert source.layer == "L5"
    assert source.fetch_type == "search"
    assert source.enabled is False


def test_delete_source_removes_it(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(None, "待刪除", "https://example.com", "L1", "rss", True),
    )

    db.delete_source(conn, source_id)

    assert db.get_sources(conn) == []


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
        Idea("舊標題", "舊角度", 80, "理由", ""),
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
        Idea("淘汰題目", "角度", 50, "理由", ""),
    )

    db.delete_idea(conn, idea_id)

    assert db.get_ideas(conn) == []
