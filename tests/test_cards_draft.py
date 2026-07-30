from daibu import db
from daibu.cards import draft
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


def test_generate_retries_once_after_an_invalid_structured_response(tmp_path):
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
    responses = iter(["不是 JSON", structured_llm_response()])
    calls = []

    result = draft.generate(
        conn,
        idea,
        verified_sources(),
        lambda text: calls.append(text) or next(responses),
    )

    assert result == db.get_carousel_draft(conn, idea_id)
    assert len(calls) == 2
    assert calls[1] != calls[0]
    assert "不是 JSON" in calls[1]
    assert "LLM 回覆中找不到 JSON 陣列" in calls[1]
    assert "source_id" in calls[1]
    conn.close()


def test_generate_only_applies_repaired_pages_that_failed_validation(tmp_path):
    from dataclasses import replace

    from daibu.cards.schema import ContentSection
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
    original = carousel_draft()
    cover = original.pages[0]
    bad_cover = replace(
        cover,
        sections=(
            ContentSection("一句話定位", "內容", ()),
            cover.sections[1],
        ),
    )
    invalid = replace(
        original,
        pages=(bad_cover, *original.pages[1:]),
    )
    changed_problem = replace(
        original.pages[2],
        heading="修稿時不該改動這一頁",
    )
    repaired = replace(
        original,
        pages=(
            *original.pages[:2],
            changed_problem,
            *original.pages[3:],
        ),
    )
    responses = iter(
        [
            structured_llm_response(invalid),
            structured_llm_response(repaired),
        ]
    )

    result = draft.generate(
        conn,
        idea,
        verified_sources(),
        lambda _text: next(responses),
    )

    assert result.pages[0] == original.pages[0]
    assert result.pages[2] == original.pages[2]
    conn.close()


def test_generate_preserves_valid_pages_when_repairing_page_order(tmp_path):
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
    original = carousel_draft()
    invalid = replace(
        original,
        pages=(
            original.pages[0],
            original.pages[2],
            original.pages[1],
            *original.pages[3:],
        ),
    )
    changed_results = replace(
        original.pages[4],
        heading="修復頁序時不該改動這一頁",
    )
    repaired = replace(
        original,
        pages=(
            *original.pages[:4],
            changed_results,
            *original.pages[5:],
        ),
    )
    responses = iter(
        [
            structured_llm_response(invalid),
            structured_llm_response(repaired),
        ]
    )

    result = draft.generate(
        conn,
        idea,
        verified_sources(),
        lambda _text: next(responses),
    )

    assert [page.page_type for page in result.pages] == [
        page.page_type for page in original.pages
    ]
    assert result.pages[4].heading == original.pages[4].heading
    assert result == db.get_carousel_draft(conn, idea_id)
    conn.close()


def test_generate_does_not_replace_valid_pages_when_dropping_an_extra_page(
    tmp_path,
):
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
    original = carousel_draft()
    extra = replace(original.pages[-1], page_no=8)
    invalid = replace(original, pages=(*original.pages, extra))
    changed_cover = replace(
        original.pages[0],
        heading="第二稿不該覆寫原本合格的封面",
    )
    repaired = replace(
        original,
        pages=(changed_cover, *original.pages[1:]),
    )
    responses = iter(
        [
            structured_llm_response(invalid),
            structured_llm_response(repaired),
        ]
    )

    result = draft.generate(
        conn,
        idea,
        verified_sources(),
        lambda _text: next(responses),
    )

    assert result == original
    assert result == db.get_carousel_draft(conn, idea_id)
    conn.close()
