from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from daibu.cards import layout_validation, render
from daibu.cards.layout_schema import load_builtin_layout, replace_element
from tests.card_fixtures import brand_asset, carousel_draft


def _asset(tmp_path: Path):
    logo_path = tmp_path / "logo.png"
    Image.new("RGBA", (240, 80), (71, 129, 154, 255)).save(logo_path)
    return brand_asset(logo_path)


def test_layout_validator_reports_text_overflow_with_page_and_element(
    tmp_path,
):
    layout = replace_element(
        load_builtin_layout(),
        "cover",
        "heading",
        h=24,
    )
    html_text = render.page_html(
        carousel_draft().pages[0],
        "ElevenLabs",
        _asset(tmp_path),
        layout,
    )

    issues = layout_validation.inspect_layout(html_text, "cover")

    assert [(item.element_id, item.code) for item in issues] == [
        ("heading", "text-overflow")
    ]
    assert "第 1 頁" in issues[0].message
    assert "封面標題" in issues[0].message


def test_layout_validator_reports_mascot_outside_canvas(tmp_path):
    html_text = render.page_html(
        carousel_draft().pages[0],
        "ElevenLabs",
        _asset(tmp_path),
    ).replace("left:744.15px", "left:1000px")

    issues = layout_validation.inspect_layout(html_text, "cover")

    assert [(item.element_id, item.code) for item in issues] == [
        ("mascot", "out-of-canvas")
    ]
    assert "呆一布機器人" in issues[0].message


def test_layout_validator_reports_invisible_logo(tmp_path):
    html_text = render.page_html(
        carousel_draft().pages[0],
        "ElevenLabs",
        _asset(tmp_path),
    ).replace(
        '<div data-layout-id="company-logo"',
        '<div style="display:none" data-layout-id="company-logo"',
        1,
    )

    issues = layout_validation.inspect_layout(html_text, "cover")

    assert [(item.element_id, item.code) for item in issues] == [
        ("company-logo", "not-visible")
    ]
    assert "企業 Logo" in issues[0].message


def test_layout_validator_reports_missing_required_element(tmp_path):
    html_text = render.page_html(
        carousel_draft().pages[0],
        "ElevenLabs",
        _asset(tmp_path),
    )
    style, markup = html_text.split("</style>", 1)
    markup = markup.replace(
        'data-layout-id="company-logo"',
        'data-missing-layout-id="company-logo"',
        1,
    )

    issues = layout_validation.inspect_layout(
        style + "</style>" + markup,
        "cover",
    )

    assert [(item.element_id, item.code) for item in issues] == [
        ("company-logo", "not-visible")
    ]


def test_layout_validator_reports_collision_between_avoid_elements(
    tmp_path,
):
    layout = replace_element(
        load_builtin_layout(),
        "cover",
        "positioning",
        y=420,
    )
    html_text = render.page_html(
        carousel_draft().pages[0],
        "ElevenLabs",
        _asset(tmp_path),
        layout,
    )

    issues = layout_validation.inspect_layout(html_text, "cover")

    assert [(item.element_id, item.code) for item in issues] == [
        ("positioning", "collision")
    ]
    assert "封面標題" in issues[0].message
    assert "一句話定位" in issues[0].message


def test_layout_validator_allows_mascot_to_overlap_content(tmp_path):
    layout = replace_element(
        load_builtin_layout(),
        "cover",
        "mascot",
        x=120,
        y=340,
    )
    html_text = render.page_html(
        carousel_draft().pages[0],
        "ElevenLabs",
        _asset(tmp_path),
        layout,
    )

    issues = layout_validation.inspect_layout(html_text, "cover")

    assert all(item.code != "collision" for item in issues)


def test_short_heading_uses_one_rendered_line(tmp_path):
    page = replace(carousel_draft().pages[0], heading="聲音生成")
    html_text = render.page_html(
        page,
        "ElevenLabs",
        _asset(tmp_path),
    )

    assert layout_validation.visual_line_count(html_text, "heading") == 1


def test_heading_wraps_to_two_lines_only_when_needed(tmp_path):
    html_text = render.page_html(
        carousel_draft().pages[0],
        "ElevenLabs",
        _asset(tmp_path),
    )

    assert layout_validation.visual_line_count(html_text, "heading") == 2
    assert not any(
        issue.element_id == "heading"
        for issue in layout_validation.inspect_layout(html_text, "cover")
    )


def test_explicit_heading_newline_preserves_phrase_boundary(tmp_path):
    heading = "讓每段文字\n保留說話方式"
    page = replace(carousel_draft().pages[0], heading=heading)
    html_text = render.page_html(
        page,
        "ElevenLabs",
        _asset(tmp_path),
    )

    assert heading in html_text
    assert layout_validation.visual_line_count(html_text, "heading") == 2


def test_cover_heading_fourth_line_is_reported_as_text_overflow(tmp_path):
    page = replace(
        carousel_draft().pages[0],
        heading="讓每段\n文字保留\n原本的\n說話方式",
    )
    layout = replace_element(
        load_builtin_layout(),
        "cover",
        "heading",
        h=500,
    )
    html_text = render.page_html(
        page,
        "ElevenLabs",
        _asset(tmp_path),
        layout,
    )

    issues = layout_validation.inspect_layout(html_text, "cover")

    assert ("heading", "text-overflow") in {
        (issue.element_id, issue.code) for issue in issues
    }


def test_validate_rendered_pages_raises_actionable_first_issue(tmp_path):
    layout = replace_element(
        load_builtin_layout(),
        "cover",
        "heading",
        h=24,
    )
    html_text = render.page_html(
        carousel_draft().pages[0],
        "ElevenLabs",
        _asset(tmp_path),
        layout,
    )

    with pytest.raises(RuntimeError, match="第 1 頁.*封面標題"):
        layout_validation.validate_rendered_pages({"cover": html_text})
