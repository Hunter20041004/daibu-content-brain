from dataclasses import asdict, replace

import pytest

from tests.card_fixtures import carousel_draft


def test_complete_seven_page_draft_passes_the_content_contract():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()

    validate_draft(draft)

    assert len(draft.pages) == 7
    assert draft.pages[3].diagram.kind == "ai-generate"


def test_draft_rejects_incomplete_source_metadata():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()
    bad_source = replace(draft.sources[0], publisher="")

    with pytest.raises(ValueError, match="來源資料不完整"):
        validate_draft(replace(draft, sources=(bad_source, *draft.sources[1:])))


def test_draft_rejects_unknown_source_ids():
    from daibu.cards.schema import ContentSection, validate_draft

    draft = carousel_draft()
    first_page = draft.pages[0]
    bad_section = ContentSection("一句話定位", "內容", ("S404",))
    bad_page = replace(
        first_page,
        sections=(bad_section, first_page.sections[1]),
    )

    with pytest.raises(ValueError, match="不存在的來源"):
        validate_draft(replace(draft, pages=(bad_page, *draft.pages[1:])))


def test_draft_rejects_duplicate_source_ids():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()
    duplicate = replace(draft.sources[1], source_id=draft.sources[0].source_id)

    with pytest.raises(ValueError, match="來源 ID 不可重複"):
        validate_draft(replace(draft, sources=(draft.sources[0], duplicate)))


def test_draft_rejects_non_https_source_urls():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()
    bad_source = replace(draft.sources[0], url="http://example.com/source")

    with pytest.raises(ValueError, match="來源網址必須是 https"):
        validate_draft(replace(draft, sources=(bad_source, *draft.sources[1:])))


def test_draft_rejects_non_iso_source_dates():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()
    bad_source = replace(draft.sources[0], published_at="July 12, 2026")

    with pytest.raises(ValueError, match="來源日期必須是 YYYY-MM-DD"):
        validate_draft(replace(draft, sources=(bad_source, *draft.sources[1:])))


def test_draft_requires_all_seven_pages_in_order():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()

    with pytest.raises(ValueError, match="固定順序包含七頁"):
        validate_draft(replace(draft, pages=draft.pages[:-1]))


def test_draft_requires_each_pages_named_content_sections():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()
    who = replace(draft.pages[1], sections=draft.pages[1].sections[:1])

    with pytest.raises(ValueError, match="who 缺少 section：基本資料"):
        validate_draft(replace(draft, pages=(draft.pages[0], who, *draft.pages[2:])))


def test_draft_requires_a_compatible_diagram_for_explanatory_pages():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()
    problem = replace(draft.pages[2], diagram=None)

    with pytest.raises(ValueError, match="problem 缺少品牌圖解"):
        validate_draft(
            replace(draft, pages=(*draft.pages[:2], problem, *draft.pages[3:]))
        )


def test_draft_rejects_a_diagram_kind_that_does_not_match_the_page():
    from daibu.cards.schema import DiagramSpec, validate_draft

    draft = carousel_draft()
    problem = draft.pages[2]
    wrong_diagram = DiagramSpec("signals", problem.diagram.nodes)
    problem = replace(problem, diagram=wrong_diagram)

    with pytest.raises(ValueError, match="problem 使用了不相容的圖解"):
        validate_draft(
            replace(draft, pages=(*draft.pages[:2], problem, *draft.pages[3:]))
        )


def test_draft_rejects_a_main_diagram_on_non_diagram_pages():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()
    cover = replace(draft.pages[0], diagram=draft.pages[2].diagram)

    with pytest.raises(ValueError, match="cover 不應放主圖解"):
        validate_draft(replace(draft, pages=(cover, *draft.pages[1:])))


def test_draft_enforces_the_inner_page_narrative_density():
    from daibu.cards.schema import ContentSection, validate_draft

    draft = carousel_draft()
    who = replace(
        draft.pages[1],
        sections=(
            ContentSection("白話定位", "太短", ("S1",)),
            ContentSection("基本資料", "仍然太短", ("S1",)),
        ),
    )

    with pytest.raises(ValueError, match="who 文字需為 140–220 字"):
        validate_draft(replace(draft, pages=(draft.pages[0], who, *draft.pages[2:])))


def test_draft_requires_sources_for_factual_sections():
    from daibu.cards.schema import ContentSection, validate_draft

    draft = carousel_draft()
    cover = draft.pages[0]
    unsourced = ContentSection("一句話定位", "AI 語音公司", ())
    cover = replace(cover, sections=(unsourced, cover.sections[1]))

    with pytest.raises(ValueError, match="一句話定位 是事實區塊，必須附來源"):
        validate_draft(replace(draft, pages=(cover, *draft.pages[1:])))


def test_draft_rejects_external_or_investment_calls_to_action():
    from daibu.cards.schema import ContentSection, validate_draft

    draft = carousel_draft()
    cta = draft.pages[-1]
    external = ContentSection("互動邀請", "現在就註冊試用。", ())
    cta = replace(cta, sections=(*cta.sections[:-1], external))

    with pytest.raises(ValueError, match="第 7 頁只能邀請按讚或追蹤"):
        validate_draft(replace(draft, pages=(*draft.pages[:-1], cta)))


def test_page_mapping_uses_verified_sources_to_build_the_source_label():
    from daibu.cards.schema import page_from_mapping

    draft = carousel_draft()
    page = page_from_mapping(
        {
            "page_no": 1,
            "page_type": "cover",
            "heading": "標題",
            "sections": [
                {
                    "label": "一句話定位",
                    "text": "內容",
                    "source_ids": ["S1"],
                },
                {
                    "label": "產業分類",
                    "text": "語音",
                    "source_ids": ["S1"],
                },
            ],
            "diagram": None,
            "source_label": "模型捏造的來源",
        },
        draft.sources,
    )

    assert page.source_label == "來源：ElevenLabs · 2026-07-12"


def test_page_mapping_builds_structured_diagram_nodes():
    from daibu.cards.schema import page_from_mapping

    draft = carousel_draft()
    expected = draft.pages[2]

    page = page_from_mapping(asdict(expected), draft.sources)

    assert page.diagram == expected.diagram
