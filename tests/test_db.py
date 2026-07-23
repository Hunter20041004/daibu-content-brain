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
