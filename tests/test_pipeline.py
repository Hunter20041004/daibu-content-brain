import pytest

from daibu import db, pipeline
from daibu.llm.base import Idea


def _candidate(conn):
    return db.add_idea(
        conn,
        None,
        Idea("標題", "角度", 80, "理由", ""),
        status="候選",
    )


def test_set_status_updates_idea(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = _candidate(conn)

    pipeline.set_status(conn, idea_id, "採用")

    ideas = db.get_ideas(conn, status="採用")
    assert [idea.id for idea in ideas] == [idea_id]


def test_set_status_rejects_unknown_value(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = _candidate(conn)

    with pytest.raises(ValueError, match="不合法"):
        pipeline.set_status(conn, idea_id, "已淘汰")


def test_update_body_saves_draft_content(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = _candidate(conn)

    pipeline.update_body(conn, idea_id, "這是貼文草稿")

    idea = db.get_ideas(conn)[0]
    assert idea.body == "這是貼文草稿"
