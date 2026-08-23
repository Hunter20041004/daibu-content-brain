import html as html_lib
import re
from dataclasses import replace
from pathlib import Path

from PIL import Image
import pytest

from daibu.cards import pages, render
from daibu.cards.editor_payload import editable_values
from daibu.cards.layout_schema import load_builtin_layout, replace_element
from tests.card_fixtures import brand_asset, carousel_draft


def _logo(tmp_path: Path) -> Path:
    path = tmp_path / "logo.png"
    Image.new("RGBA", (120, 60), (71, 129, 154, 255)).save(path)
    return path


def _render(tmp_path: Path, page_index: int = 0) -> str:
    return render.page_html(
        carousel_draft().pages[page_index],
        "ElevenLabs",
        brand_asset(_logo(tmp_path)),
    )


def test_renderer_exposes_every_editable_value_once(tmp_path):
    draft = carousel_draft()
    expected = set(editable_values(draft))
    asset = brand_asset(_logo(tmp_path))
    outputs = [
        render.page_html(page, "ElevenLabs", asset)
        for page in draft.pages
    ]
    found = re.findall(r'data-edit-key="([^"]+)"', "".join(outputs))

    assert set(found) == expected
    assert len(found) == len(expected)


def test_cover_uses_editorial_v15_1_without_page_number_or_source(tmp_path):
    output = _render(tmp_path)

    assert 'data-template="editorial-v15.1"' in output
    assert 'data-page-type="cover"' in output
    for element_id in (
        "company-logo",
        "company-name",
        "heading",
        "positioning",
        "mascot",
    ):
        assert f'data-layout-id="{element_id}"' in output
    assert 'alt="ElevenLabs Logo"' in output
    assert 'class="company-name"' in output
    assert "讓每段文字保留說話方式" in output
    assert "ElevenLabs 用 AI 生成與轉換保有語氣的聲音。" in output
    assert 'class="page-tag"' not in output
    assert 'class="page-source' not in output
    assert "來源：" not in output


def test_layout_css_uses_saved_geometry(tmp_path):
    layout = replace_element(
        load_builtin_layout(),
        "cover",
        "heading",
        x=123,
        y=234,
        w=500,
        h=190,
    )

    output = render.page_html(
        carousel_draft().pages[0],
        "ElevenLabs",
        brand_asset(_logo(tmp_path)),
        layout,
    )

    assert '[data-layout-id="heading"]' in output
    assert "left:123px" in output
    assert "top:234px" in output
    assert "width:500px" in output
    assert "height:190px" in output


def test_who_uses_only_positioning_and_facts_sections(tmp_path):
    page = carousel_draft().pages[1]
    output = _render(tmp_path, page_index=1)
    markup = output.split("</style>", 1)[1]

    assert 'data-template="editorial-v15.1"' in output
    assert 'data-page-type="who"' in output
    for element_id in ("header", "heading", "positioning", "facts", "mascot"):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    assert page.sections[0].text in output
    assert page.sections[1].text in output
    assert "本頁定位" not in output
    assert "一句話看懂" not in output
    assert 'class="page-source' not in output
    assert "來源：" not in output


def test_problem_renders_three_diagram_nodes_as_story_stages(tmp_path):
    page = carousel_draft().pages[2]
    output = _render(tmp_path, page_index=2)
    markup = output.split("</style>", 1)[1]

    assert 'data-template="editorial-v15.1"' in output
    assert 'data-page-type="problem"' in output
    for element_id in (
        "header",
        "heading",
        "spine",
        "stage-1",
        "stage-2",
        "stage-3",
        "mascot",
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    assert page.diagram is not None
    for node in page.diagram.nodes:
        assert html_lib.escape(node.title) in markup
        assert html_lib.escape(node.text) in markup
    for section in page.sections:
        assert html_lib.escape(section.text) in markup
    assert "來源：" not in markup


def test_problem_requires_its_problem_flow_diagram(tmp_path):
    page = replace(carousel_draft().pages[2], diagram=None)

    with pytest.raises(ValueError, match="第 3 頁缺少問題流程圖解"):
        render.page_html(page, "ElevenLabs", brand_asset(_logo(tmp_path)))


def test_how_ai_maps_diagram_steps_and_human_role_by_label(tmp_path):
    original = carousel_draft().pages[3]
    page = replace(original, sections=tuple(reversed(original.sections)))
    output = render.page_html(
        page,
        "ElevenLabs",
        brand_asset(_logo(tmp_path)),
    )
    markup = output.split("</style>", 1)[1]

    assert 'data-page-type="how-ai"' in markup
    for element_id in (
        "header",
        "heading",
        "spine",
        "step-1",
        "step-2",
        "step-3",
        "caution",
        "mascot",
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    assert page.diagram is not None
    for node in page.diagram.nodes:
        assert html_lib.escape(node.title) in markup
        assert html_lib.escape(node.text) in markup
    human_role = next(
        section for section in page.sections if section.label == "人仍負責"
    )
    caution = markup.split('data-layout-id="caution"', 1)[1]
    assert html_lib.escape(human_role.text) in caution
    assert "來源：" not in markup


def test_results_uses_equal_before_after_fields_and_visible_to(tmp_path):
    page = carousel_draft().pages[4]
    output = _render(tmp_path, page_index=4)
    markup = output.split("</style>", 1)[1]

    assert 'data-page-type="results"' in markup
    for element_id in (
        "header",
        "before-title",
        "before-copy",
        "axis",
        "to",
        "after-title",
        "after-copy",
        "summary",
        "mascot",
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    assert ">到<" in markup
    assert page.diagram is not None
    before, transition, after = page.diagram.nodes
    for node in (before, after):
        assert html_lib.escape(node.title) in markup
        assert html_lib.escape(node.text) in markup
    assert "改變之後｜" in markup
    assert (
        f'data-edit-key="page.results.diagram.1.title">'
        f"{html_lib.escape(transition.title)}"
        in markup
    )
    assert html_lib.escape(transition.text) not in markup
    for section in page.sections:
        assert html_lib.escape(section.text) in markup
    assert ".results-before {" in output
    assert ".results-after {" in output
    assert "width: 50%;" in output


def test_why_care_renders_three_signals_without_evidence_footnote_grid(
    tmp_path,
):
    page = carousel_draft().pages[5]
    output = _render(tmp_path, page_index=5)
    markup = output.split("</style>", 1)[1]

    assert 'data-page-type="why-care"' in markup
    for element_id in (
        "header",
        "heading",
        "signal-1",
        "signal-2",
        "signal-3",
        "mascot",
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    assert page.diagram is not None
    for node in page.diagram.nodes:
        assert html_lib.escape(node.title) in markup
        assert html_lib.escape(node.text) in markup
    for section in page.sections[:3]:
        assert html_lib.escape(section.text) in markup
    limitation = next(
        section for section in page.sections if section.label == "證據限制"
    )
    assert html_lib.escape(limitation.text) not in markup
    assert "hashtag" not in markup.casefold()


def test_cta_maps_conclusion_question_and_invitation_by_role(tmp_path):
    original = carousel_draft().pages[6]
    page = replace(original, sections=tuple(reversed(original.sections)))
    output = render.page_html(
        page,
        "ElevenLabs",
        brand_asset(_logo(tmp_path)),
    )
    markup = output.split("</style>", 1)[1]

    assert 'data-page-type="cta"' in markup
    for element_id in (
        "header",
        "heading",
        "thesis",
        "question",
        "invitation",
        "mascot",
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    roles = {section.label: section.text for section in page.sections}
    assert html_lib.escape(roles["收束結論"]) in markup
    assert html_lib.escape(roles["給讀者的問題"]) in markup
    assert html_lib.escape(roles["互動邀請"]) in markup
    assert "來源：" not in markup


def test_editorial_renderer_escapes_unsafe_text_on_all_pages(tmp_path):
    unsafe = '<script>alert("unsafe")</script>'
    asset = brand_asset(_logo(tmp_path))

    for page in carousel_draft().pages:
        sections = tuple(
            replace(section, text=unsafe) for section in page.sections
        )
        diagram = page.diagram
        if diagram is not None:
            diagram = replace(
                diagram,
                nodes=tuple(
                    replace(node, title=unsafe, text=unsafe)
                    for node in diagram.nodes
                ),
            )
        unsafe_page = replace(
            page,
            heading=unsafe,
            sections=sections,
            diagram=diagram,
        )

        output = render.page_html(unsafe_page, "ElevenLabs", asset)

        assert unsafe not in output
        assert html_lib.escape(unsafe) in output


def test_only_cover_shows_official_logo_and_images_omit_source_metadata(
    tmp_path,
):
    asset = brand_asset(_logo(tmp_path))
    outputs = [
        render.page_html(page, "ElevenLabs", asset)
        for page in carousel_draft().pages
    ]

    assert 'data-layout-id="company-logo"' in outputs[0]
    assert 'alt="ElevenLabs Logo"' in outputs[0]
    assert all(
        'data-layout-id="company-logo"'
        not in output.split("</style>", 1)[1]
        for output in outputs[1:]
    )
    assert carousel_draft().pages[2].sections[1].text in outputs[2]
    assert all("來源：" not in output for output in outputs)
    assert all('class="page-source' not in output for output in outputs)
    unsafe_company = "<script>alert(1)</script>"
    assert "<script" not in render.page_html(
        carousel_draft().pages[1],
        unsafe_company,
        replace(asset, company=unsafe_company),
    )


def test_cover_omits_source_and_industry_but_keeps_positioning(tmp_path):
    output = _render(tmp_path)

    assert 'class="source-label source-label--cover"' not in output
    assert "來源：ElevenLabs" not in output
    assert "生成式語音" not in output
    assert "ElevenLabs 用 AI 生成與轉換保有語氣的聲音。" in output


def test_cover_leads_with_series_and_hook_without_industry_or_source(
    tmp_path,
):
    output = _render(tmp_path)

    assert (
        '<div class="series" data-layout-id="series">一布懂 AI 新創</div>'
        in output
    )
    assert (
        '<h1 class="cover-heading" data-layout-id="heading">'
        '<span data-edit-key="page.cover.heading">'
        "讓每段文字保留說話方式</span></h1>"
        in output
    )
    assert 'class="cover-copy" data-layout-id="positioning"' in output
    assert "生成式語音" not in output
    assert "來源：ElevenLabs" not in output
    assert 'class="company-name" data-layout-id="company-name"' in output


def test_html_escapes_heading_section_and_company_text(tmp_path):
    unsafe = '<script>alert("x")</script>'
    page = carousel_draft().pages[1]
    unsafe_section = replace(page.sections[0], text=unsafe)
    unsafe_page = replace(
        page,
        heading=unsafe,
        sections=(unsafe_section, page.sections[1]),
    )
    asset = replace(brand_asset(_logo(tmp_path)), company=unsafe)

    output = render.page_html(unsafe_page, unsafe, asset)

    assert unsafe not in output
    assert html_lib.escape(unsafe) in output


def test_html_declares_exact_canvas_size(tmp_path):
    output = _render(tmp_path)

    for declaration in (
        "width: 1080px",
        "height: 1350px",
    ):
        assert declaration in output


def test_card_uses_full_bleed_approved_geometry(tmp_path):
    output = _render(tmp_path)

    for declaration in (
        "width: 1080px",
        "height: 1350px",
        "overflow: hidden",
    ):
        assert declaration in output


def test_font_is_loaded_from_local_files(tmp_path):
    output = _render(tmp_path)
    style = output.split("</style>", 1)[0]

    assert "LINESeedTW_OTF_Rg.otf" in style
    assert "LINESeedTW_OTF_Bd.otf" in style
    assert "LINESeedTW_OTF_Eb.otf" in style
    assert "http" not in style.replace("file://", "")


def test_colors_match_the_brand_palette(tmp_path):
    output = _render(tmp_path)

    assert "#102f3d" in output
    assert "#86ccd4" in output
    assert "#ec9870" in output
    assert "#fafbf8" in output
    for retired in ("#2E5C9E", "#F6BCC8", "#E8912D", "#5B8FC9"):
        assert retired not in output, f"{retired} 是改版前的舊色，不該出現"


def test_type_hierarchy_uses_approved_sizes(tmp_path):
    output = _render(tmp_path)

    for declaration in (
        "font-size: 27px",
        "font-size: 40px",
        "font-size: 72px",
        "font-size: 113px",
    ):
        assert declaration in output


def test_feed_image_has_no_page_number_source_or_date_microcopy(tmp_path):
    outputs = [
        _render(tmp_path, page_index=index)
        for index in range(7)
    ]

    for output in outputs:
        markup = output.split("</style>", 1)[1]
        assert "page-tag" not in markup
        assert "page-source" not in markup
        assert "來源：" not in markup
        assert "2026-" not in markup


def test_type_hierarchy_uses_approved_weights(tmp_path):
    output = _render(tmp_path)

    for declaration in (
        "font-weight: 400",
        "font-weight: 700",
        "font-weight: 800",
    ):
        assert declaration in output


def test_ai_role_diagram_keeps_readable_step_type(tmp_path):
    output = _render(tmp_path, page_index=3)

    assert ".how-step strong" in output
    assert "font-size: 49px" in output
    assert ".how-caution strong" in output
    assert "font-size: 35px" in output


def test_html_replaces_generic_patterns_with_series_signature(tmp_path):
    output = _render(tmp_path)

    assert "一布懂 AI 新創" in output
    assert 'class="frame-pattern frame-pattern--stripes"' not in output
    assert 'class="frame-pattern frame-pattern--dots"' not in output


def test_feed_image_omits_social_handle_footer(tmp_path):
    output = _render(tmp_path)

    markup = output.split("</style>", 1)[1]
    assert 'class="handle"' not in markup
    assert "@呆一布" not in markup


def test_html_uses_local_tokens_without_theme_dependent_colors(tmp_path):
    output = _render(tmp_path)

    assert ":root" in output
    assert "--paper: #fafbf8" in output
    assert "light-dark(" not in output
    assert "prefers-color-scheme" not in output


def test_html_has_no_unapproved_weights_or_italics(tmp_path):
    output = _render(tmp_path)

    assert "font-weight: 500" not in output
    assert "font-weight: 600" not in output
    assert "font-style: italic" not in output


def test_inner_page_has_template_and_page_type_hooks(tmp_path):
    output = _render(tmp_path, page_index=3)

    assert 'data-template="editorial-v15.1"' in output
    assert 'data-page-type="how-ai"' in output
    assert 'class="card how-v151"' in output


def test_seven_pages_use_seven_semantic_compositions(tmp_path):
    asset = brand_asset(_logo(tmp_path))
    outputs = [
        render.page_html(page, "ElevenLabs", asset)
        for page in carousel_draft().pages
    ]

    classes = (
        "cover-v151",
        "profile-v151",
        "problem-v151",
        "how-v151",
        "results-v151",
        "signals-v151",
        "closing-v151",
    )
    for output, class_name in zip(outputs, classes, strict=True):
        assert f'class="card {class_name}"' in output


def test_every_page_uses_its_storytelling_mascot_and_series_signature(
    tmp_path,
):
    asset = brand_asset(_logo(tmp_path))
    draft = carousel_draft()
    outputs = [
        render.page_html(page, "ElevenLabs", asset)
        for page in draft.pages
    ]

    for page, output in zip(draft.pages, outputs, strict=True):
        pose = pages.MASCOT_FOR[page.page_type]
        assert f'class="story-mascot mascot--{pose}"' in output
        assert f"mascot/{pose}.svg" in output
        assert "一布懂 AI 新創" in output
    assert "DAIBU AI LAB" not in "".join(outputs)
    assert "CASE FILE" not in "".join(outputs)


def test_story_css_prioritizes_heading_readability_without_source_footer(
    tmp_path,
):
    output = _render(tmp_path)

    assert ".editorial-heading" in output
    assert "font-size: 72px" in output
    assert ".page-source" not in output
    assert ".story-mascot" in output
    assert "word-break: auto-phrase" in output
    assert "overflow-wrap: normal" in output


def test_story_mascots_use_approved_reduced_sizes_and_layout_hooks(
    tmp_path,
):
    output = _render(tmp_path)

    assert '.cover-v151 [data-layout-id="mascot"]' in output
    assert "width: 282px" in output
    assert '.problem-v151 [data-layout-id="mascot"]' in output
    assert "width: 260px" in output
    assert '.results-v151 [data-layout-id="mascot"]' in output
    assert "width: 204px" in output
