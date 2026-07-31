import pytest

from daibu import db
from daibu.cards import draft
from daibu.llm import base
from daibu.llm.base import Idea
from daibu.models import Theme


LONG_EXCERPT = (
    "ElevenLabs 於 2022 年在倫敦成立，專注於讓合成語音保留自然語氣與節奏。"
    "團隊的產品已用於有聲書、遊戲和內容製作，讓小型團隊能降低配音成本。"
)


def test_generate_validates_and_saves_structured_draft(tmp_path):
    from tests.card_fixtures import (
        structured_llm_response,
        verified_sources,
    )

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
            source_excerpt=LONG_EXCERPT,
        ),
    )
    idea = [
        item for item in db.get_ideas(conn) if item.id == idea_id
    ][0]

    result = draft.generate(
        conn,
        idea,
        verified_sources(),
        lambda _text: structured_llm_response(),
    )

    assert result == db.get_carousel_draft(conn, idea_id)
    conn.close()


def test_generate_passes_company_into_the_prompt(tmp_path):
    from tests.card_fixtures import (
        structured_llm_response,
        verified_sources,
    )

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
            source_excerpt=f"片段：{LONG_EXCERPT}",
        ),
    )
    idea = [
        item for item in db.get_ideas(conn) if item.id == idea_id
    ][0]
    seen = {}

    def spy(prompt_text: str) -> str:
        seen["text"] = prompt_text
        return structured_llm_response()

    draft.generate(conn, idea, verified_sources(), spy)

    assert "ElevenLabs" in seen["text"]
    assert '"source_id": "S1"' in seen["text"]
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
    from tests.card_fixtures import verified_sources

    try:
        draft.generate(
            conn,
            idea,
            verified_sources(),
            lambda text: called.append(text) or "",
        )
    except ValueError as error:
        assert "公司" in str(error)
    else:
        raise AssertionError("空公司名應該要擋下來")

    assert called == []
    conn.close()


def test_generate_rejects_an_empty_verified_source_pack(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(
            id=None,
            name="AI 新創介紹",
            weekday=4,
            source_ids=[],
            n_ideas=3,
        ),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            title="t",
            angle="a",
            source_url="https://example.com/a",
            company="Vela",
            source_excerpt=LONG_EXCERPT,
        ),
        status="採用",
    )
    idea = [
        item for item in db.get_ideas(conn) if item.id == idea_id
    ][0]
    called = []

    try:
        draft.generate(
            conn,
            idea,
            (),
            lambda text: called.append(text) or "[]",
        )
    except ValueError as error:
        assert "至少需要一筆已查證來源" in str(error)
    else:
        raise AssertionError("空來源包應該要擋下來")

    assert called == []
    conn.close()


def test_generate_rejects_invalid_sources_before_calling_the_llm(tmp_path):
    from dataclasses import replace

    from tests.card_fixtures import (
        structured_llm_response,
        verified_sources,
    )

    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea(
            title="t",
            angle="a",
            source_url="https://example.com/a",
            company="ElevenLabs",
            source_excerpt=LONG_EXCERPT,
        ),
    )
    idea = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    sources = verified_sources()
    invalid = (replace(sources[0], publisher=""), *sources[1:])
    called = []

    try:
        draft.generate(
            conn,
            idea,
            invalid,
            lambda text: called.append(text) or structured_llm_response(),
        )
    except ValueError as error:
        assert "來源資料不完整" in str(error)
    else:
        raise AssertionError("不完整來源應該在呼叫 LLM 前被擋下")

    assert called == []
    conn.close()


def test_generate_reports_invalid_json_after_exactly_one_llm_call(tmp_path):
    from tests.card_fixtures import verified_sources

    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea(
            title="t",
            angle="a",
            source_url="https://example.com/a",
            company="ElevenLabs",
            source_excerpt=LONG_EXCERPT,
        ),
    )
    idea = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    calls = []

    with pytest.raises(base.LLMResponseError, match="回傳內容無法解析"):
        draft.generate(
            conn,
            idea,
            verified_sources(),
            lambda text: calls.append(text) or "不是 JSON",
        )

    assert len(calls) == 1
    assert db.get_carousel_draft(conn, idea_id) is None
    conn.close()
