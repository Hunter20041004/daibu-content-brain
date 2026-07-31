import html as html_lib
import re
from dataclasses import replace
from pathlib import Path

from PIL import Image

from daibu.cards import pages, render
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


def test_every_page_has_logo_and_inner_pages_keep_their_source(tmp_path):
    asset = brand_asset(_logo(tmp_path))
    outputs = [
        render.page_html(page, "ElevenLabs", asset)
        for page in carousel_draft().pages
    ]

    assert all('class="company-logo' in output for output in outputs)
    assert 'company-logo company-logo--cover' in outputs[0]
    assert all('company-logo company-logo--small' in output for output in outputs[1:])
    assert "原本的代價" in outputs[2]
    assert 'data-diagram-kind="ai-generate"' in outputs[3]
    assert "來源：ElevenLabs" not in outputs[0]
    assert "來源：ElevenLabs" in outputs[4]
    assert "margin-top: auto" not in outputs[4]
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

    assert '<div class="series-lockup">一布懂 AI 新創</div>' in output
    assert (
        '<h1 class="cover-hook">讓每段文字保留說話方式</h1>'
        in output
    )
    assert 'class="cover-positioning"' in output
    assert "生成式語音" not in output
    assert "來源：ElevenLabs" not in output
    assert 'class="company-name company-name--short"' in output


def test_html_escapes_heading_section_and_company_text(tmp_path):
    unsafe = '<script>alert("x")</script>'
    page = carousel_draft().pages[1]
    unsafe_section = replace(page.sections[0], label=unsafe, text=unsafe)
    unsafe_page = replace(page, heading=unsafe, sections=(unsafe_section,))
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


def test_card_uses_approved_geometry(tmp_path):
    output = _render(tmp_path)

    for declaration in (
        "inset: 48px 48px 64px",
        "border-radius: 40px",
        "0 6px 36px rgba(38, 38, 65, .06)",
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

    assert "#D5E6F4" in output
    assert "#FBFCFE" in output
    assert "#47819A" in output
    for retired in ("#2E5C9E", "#F6BCC8", "#E8912D", "#5B8FC9"):
        assert retired not in output, f"{retired} 是改版前的舊色，不該出現"


def test_type_hierarchy_uses_approved_sizes(tmp_path):
    output = _render(tmp_path)

    for declaration in (
        "font-size: 21px",
        "font-size: 29px",
        "font-size: 56px",
        "font-size: 96px",
    ):
        assert declaration in output


def test_feed_microcopy_is_large_and_high_contrast(tmp_path):
    from daibu import theme

    output = _render(tmp_path)
    page_tag_rule = re.search(r"\.page-tag \{(?P<body>.*?)\}", output, re.S)
    source_rule = re.search(r"\.page-source \{(?P<body>.*?)\}", output, re.S)

    assert "font-size: 24px" in page_tag_rule.group("body")
    assert "font-size: 30px" in source_rule.group("body")
    assert theme.contrast_ratio("#4F5362", "#FBFCFE") >= 4.5
    assert "color: var(--muted)" in page_tag_rule.group("body")
    assert "color: var(--muted)" in source_rule.group("body")


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

    assert ".page--how-ai .diagram-copy strong { font-size: 36px; }" in output
    assert "font-size: 30px;" in output.split(
        ".page--how-ai .diagram-copy span", 1
    )[1].split("}", 1)[0]


def test_html_includes_approved_frame_decorations(tmp_path):
    output = _render(tmp_path)

    assert 'class="frame-pattern frame-pattern--stripes"' in output
    assert 'class="frame-pattern frame-pattern--dots"' in output


def test_handle_sits_in_the_frame_below_the_card(tmp_path):
    output = _render(tmp_path)

    assert 'class="handle"' in output
    assert "@呆一布" in output
    assert "bottom: 16px" in output


def test_html_uses_local_tokens_without_theme_dependent_colors(tmp_path):
    output = _render(tmp_path)

    assert ":root" in output
    assert "--paper: #FBFCFE" in output
    assert "light-dark(" not in output
    assert "prefers-color-scheme" not in output


def test_html_has_no_unapproved_weights_or_italics(tmp_path):
    output = _render(tmp_path)

    assert "font-weight: 500" not in output
    assert "font-weight: 600" not in output
    assert "font-style: italic" not in output


def test_inner_page_has_page_type_class_and_label(tmp_path):
    output = _render(tmp_path, page_index=3)

    assert 'class="canvas page--how-ai shot--evidence"' in output
    assert "04｜AI 在裡面扮演什麼角色" in output


def test_seven_pages_use_three_distinct_story_shots(tmp_path):
    asset = brand_asset(_logo(tmp_path))
    outputs = [
        render.page_html(page, "ElevenLabs", asset)
        for page in carousel_draft().pages
    ]

    assert 'shot--hero' in outputs[0]
    assert 'shot--hero' in outputs[6]
    assert 'shot--editorial' in outputs[1]
    assert 'shot--editorial' in outputs[2]
    assert all('shot--evidence' in outputs[index] for index in (3, 4, 5))


def test_every_page_uses_its_storytelling_mascot_and_chinese_lab_signature(
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
        assert "呆一布 AI 實驗室" in output
    assert "DAIBU AI LAB" not in "".join(outputs)
    assert "CASE FILE" not in "".join(outputs)


def test_story_css_prioritizes_series_source_readability_and_full_outline_blocks(
    tmp_path,
):
    output = _render(tmp_path)

    assert ".series-lockup" in output
    assert "font-size: 80px" in output
    assert ".page-source" in output
    assert "font-size: 30px" in output
    assert ".story-mascot" in output
    assert "border-left:" not in output
    assert "text-transform: uppercase" not in output
