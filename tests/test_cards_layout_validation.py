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


def test_layout_validator_reports_text_overflow_with_page_and_element(tmp_path):
    layout = replace_element(load_builtin_layout(), "who", "heading", h=24)
    html_text = render.page_html(
        carousel_draft().pages[1], "ElevenLabs", _asset(tmp_path), layout
    )

    issues = layout_validation.inspect_layout(html_text, "who")

    assert ("heading", "text-overflow") in {
        (item.element_id, item.code) for item in issues
    }
    assert "第 2 頁" in next(item.message for item in issues if item.element_id == "heading")


def test_layout_validator_reports_missing_required_element(tmp_path):
    html_text = render.page_html(
        carousel_draft().pages[0], "ElevenLabs", _asset(tmp_path)
    )
    style, markup = html_text.split("</style>", 1)
    markup = markup.replace(
        'data-layout-id="company-logo"',
        'data-missing-layout-id="company-logo"',
        1,
    )

    issues = layout_validation.inspect_layout(style + "</style>" + markup, "cover")

    assert ("company-logo", "not-visible") in {
        (item.element_id, item.code) for item in issues
    }


def test_layout_validator_reports_collision_between_avoid_elements(tmp_path):
    layout = replace_element(
        load_builtin_layout(), "cover", "positioning", y=300
    )
    html_text = render.page_html(
        carousel_draft().pages[0], "ElevenLabs", _asset(tmp_path), layout
    )

    issues = layout_validation.inspect_layout(html_text, "cover")

    assert ("positioning", "collision") in {
        (item.element_id, item.code) for item in issues
    }


def test_layout_validator_allows_mascot_to_overlap_content(tmp_path):
    layout = replace_element(
        load_builtin_layout(), "cover", "mascot", x=300, y=760
    )
    html_text = render.page_html(
        carousel_draft().pages[0], "ElevenLabs", _asset(tmp_path), layout
    )

    issues = layout_validation.inspect_layout(html_text, "cover")

    assert all(item.code != "collision" for item in issues)


def test_validate_rendered_pages_raises_actionable_first_issue(tmp_path):
    layout = replace_element(load_builtin_layout(), "who", "heading", h=24)
    html_text = render.page_html(
        carousel_draft().pages[1], "ElevenLabs", _asset(tmp_path), layout
    )

    with pytest.raises(RuntimeError, match="第 2 頁.*頁面標題"):
        layout_validation.validate_rendered_pages({"who": html_text})


def test_builtin_independent_layers_have_no_false_collision_issues(tmp_path):
    draft = carousel_draft()
    asset = _asset(tmp_path)
    pages_html = {
        page.page_type: render.page_html(page, "ElevenLabs", asset)
        for page in draft.pages[1:5]
    }

    issues = layout_validation.inspect_pages(pages_html)

    assert [issue for issue in issues if issue.code == "collision"] == []
