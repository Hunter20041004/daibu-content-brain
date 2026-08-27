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


def test_generate_replaces_model_cta_with_fixed_brand_copy(tmp_path):
    from dataclasses import replace

    from daibu.cards import pages
    from tests.card_fixtures import (
        carousel_draft,
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
    generated = carousel_draft()
    generated_cta = generated.pages[-1]
    generated = replace(
        generated,
        pages=(
            *generated.pages[:-1],
            replace(
                generated_cta,
                sections=(
                    replace(
                        generated_cta.sections[0],
                        text="留言告訴我你最想試哪個功能",
                    ),
                ),
            ),
        ),
    )

    result = draft.generate(
        conn,
        idea,
        verified_sources(),
        lambda _text: structured_llm_response(generated),
    )

    assert result.pages[-1].sections[0].text == pages.CTA_TEXT
    assert result.pages[-1].sections[0].source_ids == ()
    assert result.pages[-1].sections[0].evidence_quotes == ()
    assert db.get_carousel_draft(conn, idea_id) == result
    conn.close()


def test_generate_retries_once_with_validation_feedback(tmp_path):
    from dataclasses import replace

    from tests.card_fixtures import (
        carousel_draft,
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
    valid = carousel_draft()
    how_ai = valid.pages[3]
    human_role = replace(
        how_ai.sections[2],
        source_ids=(),
        evidence_quotes=(),
    )
    invalid = replace(
        valid,
        pages=(
            *valid.pages[:3],
            replace(
                how_ai,
                sections=(
                    *how_ai.sections[:2],
                    human_role,
                    *how_ai.sections[3:],
                ),
            ),
            *valid.pages[4:],
        ),
    )
    prompts = []

    def respond(prompt_text: str) -> str:
        prompts.append(prompt_text)
        generated = invalid if len(prompts) == 1 else valid
        return structured_llm_response(generated)

    result = draft.generate(conn, idea, verified_sources(), respond)

    assert result == valid
    assert len(prompts) == 2
    assert "人仍負責 是事實區塊，必須附來源" in prompts[1]
    conn.close()


@pytest.mark.parametrize(
    "provider_error",
    [
        base.LLMTimeoutError("timeout"),
        base.LLMQuotaError("quota"),
        base.LLMUnavailableError("unavailable"),
    ],
)
def test_provider_failures_are_not_retried_or_persisted(
    tmp_path,
    provider_error,
):
    from tests.card_fixtures import carousel_draft, verified_sources

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
    original = carousel_draft()
    db.save_carousel_draft(conn, idea_id, original)
    calls = []

    def fail(prompt_text: str) -> str:
        calls.append(prompt_text)
        raise provider_error

    with pytest.raises(type(provider_error)) as raised:
        draft.generate(conn, idea, verified_sources(), fail)

    assert raised.value is provider_error
    assert len(calls) == 1
    assert db.get_carousel_draft(conn, idea_id) == original
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


def test_generate_reports_invalid_json_after_one_repair_attempt(tmp_path):
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

    assert len(calls) == 2
    assert "LLM 回覆中找不到 JSON 陣列" in calls[1]
    assert db.get_carousel_draft(conn, idea_id) is None
    conn.close()


def test_generate_accepts_concise_inner_headings_without_repeating_company(tmp_path):
    from dataclasses import replace

    from tests.card_fixtures import (
        carousel_draft,
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
    concise = carousel_draft()
    page_four = replace(concise.pages[3], heading="AI 扮演什麼樣的角色？")
    concise = replace(
        concise,
        pages=(*concise.pages[:3], page_four, *concise.pages[4:]),
    )

    result = draft.generate(
        conn,
        idea,
        verified_sources(),
        lambda _text: structured_llm_response(concise),
    )

    assert result.pages[3].heading == "AI 扮演什麼樣的角色？"
    assert db.get_carousel_draft(conn, idea_id) == result
    conn.close()
