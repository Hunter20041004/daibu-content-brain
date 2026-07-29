import json

from daibu import db
from daibu.cards import draft, pages
from daibu.llm.base import Idea


def _fake_response() -> str:
    return json.dumps(
        [
            {
                "page_type": page_type,
                "heading": f"標題{index}",
                "body": f"內文{index}",
                "grounding": "source" if index == 0 else "model",
                "source_quote": "原文" if index == 0 else "",
            }
            for index, page_type in enumerate(pages.PAGE_TYPES)
        ],
        ensure_ascii=False,
    )


def test_generate_saves_seven_pages(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea(
            title="讓文字開口說話",
            angle="配音成本被改寫",
            source_url="https://example.com/a",
            company="ElevenLabs",
            source_excerpt="2022 年於倫敦成立。",
        ),
    )
    idea = [
        item for item in db.get_ideas(conn) if item.id == idea_id
    ][0]

    rows = draft.generate(conn, idea, lambda _prompt: _fake_response())

    assert len(rows) == 7
    assert len(db.get_carousel(conn, idea_id)) == 7
    conn.close()


def test_generate_passes_company_into_the_prompt(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea(
            title="t",
            angle="a",
            source_url="",
            company="ElevenLabs",
            source_excerpt="片段",
        ),
    )
    idea = [
        item for item in db.get_ideas(conn) if item.id == idea_id
    ][0]
    seen = {}

    def spy(prompt_text: str) -> str:
        seen["text"] = prompt_text
        return _fake_response()

    draft.generate(conn, idea, spy)

    assert "ElevenLabs" in seen["text"]
    assert "片段" in seen["text"]
    conn.close()


def test_generate_refuses_when_company_is_empty(tmp_path):
    """沒有公司名就不該送出去燒額度。"""
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea(title="t", angle="a", source_url=""),
    )
    idea = [
        item for item in db.get_ideas(conn) if item.id == idea_id
    ][0]

    called = []

    try:
        draft.generate(
            conn,
            idea,
            lambda text: called.append(text) or "",
        )
    except ValueError as error:
        assert "公司" in str(error)
    else:
        raise AssertionError("空公司名應該要擋下來")

    assert called == []
    conn.close()
