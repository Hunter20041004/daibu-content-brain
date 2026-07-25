from daibu import db, performance
from daibu.llm.base import Idea
from daibu.models import Theme


def _idea(conn, theme_id):
    return db.add_idea(
        conn,
        theme_id,
        Idea("標題", "角度", ""),
        status="已發",
    )


def test_record_saves_post_metrics(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = _idea(conn, None)

    performance.record(
        conn,
        idea_id,
        platform="Instagram",
        likes=12,
        reach=300,
        engagement=4.5,
    )

    row = conn.execute("SELECT * FROM performance").fetchone()
    assert row["idea_id"] == idea_id
    assert row["platform"] == "Instagram"
    assert row["likes"] == 12
    assert row["reach"] == 300
    assert row["engagement"] == 4.5


def test_summary_groups_average_engagement_by_theme(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_a = db.add_theme(
        conn,
        Theme(None, "A", 0, [], 1),
    )
    theme_b = db.add_theme(
        conn,
        Theme(None, "B", 1, [], 1),
    )
    idea_a = _idea(conn, theme_a)
    idea_b = _idea(conn, theme_b)
    performance.record(conn, idea_a, "Instagram", 20, 200, 8.0)
    performance.record(conn, idea_b, "Instagram", 5, 100, 3.0)

    summary = performance.summary_by_theme(conn)

    by_theme = {row["theme"]: row for row in summary}
    assert set(by_theme) == {"A", "B"}
    assert by_theme["A"]["avg_engagement"] == 8.0
    assert by_theme["B"]["avg_engagement"] == 3.0


def test_suggest_names_strongest_and_weakest_themes():
    summary = [
        {"theme": "A", "avg_engagement": 8.0},
        {"theme": "B", "avg_engagement": 3.0},
    ]

    text = performance.suggest(summary)

    assert "表現最好" in text and "A" in text
    assert "優先補強" in text and "B" in text
