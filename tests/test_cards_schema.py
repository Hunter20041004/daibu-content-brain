from dataclasses import asdict, replace

import pytest

from tests.card_fixtures import carousel_draft


def test_complete_seven_page_draft_passes_the_content_contract():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()

    validate_draft(draft)

    assert len(draft.pages) == 7
    assert draft.pages[3].diagram.kind == "ai-generate"


def test_complete_fixture_passes_the_grounded_evidence_contract():
    from daibu.cards.schema import validate_grounded_draft

    validate_grounded_draft(carousel_draft())


def test_pages_four_through_seven_must_name_the_company_in_the_heading():
    from daibu.cards.schema import validate_company_headings

    draft = carousel_draft()
    pages = tuple(
        replace(page, heading=f"ElevenLabs：{page.heading}")
        if 4 <= page.page_no <= 7
        else page
        for page in draft.pages
    )
    pages = (*pages[:3], replace(pages[3], heading="AI 重建說話方式"), *pages[4:])

    with pytest.raises(ValueError, match="第 4 頁標題必須寫出 ElevenLabs"):
        validate_company_headings(replace(draft, pages=pages), "ElevenLabs")


def test_new_cta_contract_closes_with_a_conclusion_and_reader_question():
    from daibu.cards import pages

    assert pages.SECTION_LABELS["cta"] == (
        "收束結論",
        "給讀者的問題",
        "互動邀請",
    )


def test_legacy_four_section_cta_remains_readable():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()
    cta = draft.pages[-1]
    sourced = cta.sections[0]
    legacy = replace(
        cta,
        sections=(
            replace(sourced, label="公司定位"),
            replace(sourced, label="AI 的角色"),
            replace(sourced, label="觀察重點"),
            cta.sections[-1],
        ),
    )

    validate_draft(replace(draft, pages=(*draft.pages[:-1], legacy)))


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


def test_draft_rejects_unknown_source_kind():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()
    bad_source = replace(draft.sources[0], source_kind="influencer")

    with pytest.raises(ValueError, match="來源類別無效"):
        validate_draft(replace(draft, sources=(bad_source, *draft.sources[1:])))


def test_grounded_draft_rejects_a_quote_absent_from_its_source():
    from daibu.cards.schema import (
        EvidenceQuote,
        validate_grounded_draft,
    )

    draft = carousel_draft()
    cover = draft.pages[0]
    unsupported = replace(
        cover.sections[0],
        evidence_quotes=(EvidenceQuote("S1", "來源裡不存在"),),
    )
    cover = replace(cover, sections=(unsupported, cover.sections[1]))

    with pytest.raises(ValueError, match="查證引文不在 S1 原文"):
        validate_grounded_draft(
            replace(draft, pages=(cover, *draft.pages[1:])),
        )


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


def test_draft_rejects_extra_or_reordered_section_labels():
    from daibu.cards.schema import ContentSection, validate_draft

    draft = carousel_draft()
    cover = draft.pages[0]
    extra = ContentSection("模型自創欄位", "不應出現在固定版型", ("S1",))
    cover = replace(cover, sections=(*cover.sections, extra))

    with pytest.raises(ValueError, match="cover section 必須依固定順序"):
        validate_draft(replace(draft, pages=(cover, *draft.pages[1:])))


def test_draft_rejects_blank_page_headings():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()
    cover = replace(draft.pages[0], heading="   ")

    with pytest.raises(ValueError, match="cover 標題不可空白"):
        validate_draft(replace(draft, pages=(cover, *draft.pages[1:])))


def test_draft_rejects_blank_required_section_text():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()
    cover = draft.pages[0]
    blank = replace(cover.sections[0], text=" \n ")
    cover = replace(cover, sections=(blank, cover.sections[1]))

    with pytest.raises(ValueError, match="cover 一句話定位 內容不可空白"):
        validate_draft(replace(draft, pages=(cover, *draft.pages[1:])))


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


def test_draft_requires_three_nodes_for_each_main_diagram():
    from daibu.cards.schema import DiagramSpec, validate_draft

    draft = carousel_draft()
    problem = replace(
        draft.pages[2],
        diagram=DiagramSpec("problem-chain", ()),
    )

    with pytest.raises(ValueError, match="problem 圖解必須有 3 個節點"):
        validate_draft(
            replace(draft, pages=(*draft.pages[:2], problem, *draft.pages[3:]))
        )


def test_draft_rejects_blank_diagram_node_content():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()
    problem = draft.pages[2]
    blank_node = replace(problem.diagram.nodes[0], title=" ")
    problem = replace(
        problem,
        diagram=replace(
            problem.diagram,
            nodes=(blank_node, *problem.diagram.nodes[1:]),
        ),
    )

    with pytest.raises(ValueError, match="problem 圖解節點不可空白"):
        validate_draft(
            replace(draft, pages=(*draft.pages[:2], problem, *draft.pages[3:]))
        )


def test_draft_rejects_a_main_diagram_on_non_diagram_pages():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()
    cover = replace(draft.pages[0], diagram=draft.pages[2].diagram)

    with pytest.raises(ValueError, match="cover 不應放主圖解"):
        validate_draft(replace(draft, pages=(cover, *draft.pages[1:])))


def test_draft_allows_a_shorter_grounded_inner_page():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()
    who_page = draft.pages[1]
    who = replace(
        who_page,
        sections=(
            replace(who_page.sections[0], text="只寫有原文支持的公司定位。"),
            replace(who_page.sections[1], text="公開資料不足，不為湊字數補造。"),
        ),
    )

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


def test_page_mapping_derives_source_ids_from_evidence_quotes():
    from daibu.cards.schema import EvidenceQuote, page_from_mapping

    draft = carousel_draft()
    quote = draft.sources[0].excerpt
    page = page_from_mapping(
        {
            "page_no": 1,
            "page_type": "cover",
            "heading": "標題",
            "sections": [
                {
                    "label": "一句話定位",
                    "text": "內容",
                    "evidence_quotes": [
                        {"source_id": "S1", "quote": quote},
                    ],
                },
                {
                    "label": "產業分類",
                    "text": "語音",
                    "evidence_quotes": [
                        {"source_id": "S1", "quote": quote},
                    ],
                },
            ],
            "diagram": None,
        },
        draft.sources,
    )

    assert page.sections[0].source_ids == ("S1",)
    assert page.sections[0].evidence_quotes == (EvidenceQuote("S1", quote),)


def test_draft_rejects_a_noncanonical_source_label():
    from daibu.cards.schema import validate_draft

    draft = carousel_draft()
    cover = replace(draft.pages[0], source_label="模型自己寫的來源")

    with pytest.raises(ValueError, match="cover 來源標示必須由程式產生"):
        validate_draft(replace(draft, pages=(cover, *draft.pages[1:])))


def test_page_mapping_builds_structured_diagram_nodes():
    from daibu.cards.schema import page_from_mapping

    draft = carousel_draft()
    expected = draft.pages[2]

    page = page_from_mapping(asdict(expected), draft.sources)

    assert page.diagram == expected.diagram


def test_draft_reports_all_validation_errors_in_one_review():
    from daibu.cards.schema import ContentSection, validate_draft

    draft = carousel_draft()
    cover = replace(
        draft.pages[0],
        sections=(
            ContentSection("一句話定位", "內容", ()),
            ContentSection("產業分類", "語音", ()),
        ),
    )
    who = draft.pages[1]
    too_long = replace(
        who.sections[0],
        text=who.sections[0].text + ("補" * 100),
    )
    who = replace(who, sections=(too_long, who.sections[1]))
    broken = replace(
        draft,
        pages=(cover, who, *draft.pages[2:]),
    )

    with pytest.raises(ValueError) as error:
        validate_draft(broken)

    message = str(error.value)
    assert "一句話定位 是事實區塊，必須附來源" in message
    assert "產業分類 是事實區塊，必須附來源" in message
    assert "who 文字最多 220 字" in message
    assert error.value.page_types == frozenset({"cover", "who"})
    assert error.value.has_global_issues is False
