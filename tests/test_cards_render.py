import html as html_lib
import inspect
import re
from dataclasses import replace
from pathlib import Path

from PIL import Image
import pytest

from daibu.cards import render
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


def _markup(output: str) -> str:
    return output.split("</style>", 1)[1]


def test_renderer_uses_sticky_notebook_v1_only(tmp_path):
    output = _render(tmp_path)

    assert 'data-template="sticky-notebook-v1"' in output
    assert "editorial-v15.1" not in output


def test_renderer_exposes_every_editable_value_once(tmp_path):
    draft = carousel_draft()
    asset = brand_asset(_logo(tmp_path))
    output = "".join(
        render.page_html(page, "ElevenLabs", asset) for page in draft.pages
    )
    found = re.findall(r'data-edit-key="([^"]+)"', output)

    assert set(found) == set(editable_values(draft))
    assert len(found) == len(set(found))


def test_cover_makes_company_logo_name_and_positioning_the_hierarchy(tmp_path):
    output = _render(tmp_path)
    markup = _markup(output)

    assert 'data-page-type="cover"' in markup
    assert 'alt="ElevenLabs Logo"' in markup
    assert '>ElevenLabs</h1>' in markup
    assert "ElevenLabs 用 AI 生成與轉換保有語氣的聲音。" in markup
    assert "產業分類" not in markup
    assert 'data-layout-id="company-logo"' in markup
    assert 'data-layout-id="company-name"' in markup
    assert 'data-layout-id="positioning"' in markup


def test_cover_renders_the_editable_page_heading_in_the_preview(tmp_path):
    page = carousel_draft().pages[0]
    markup = _markup(_render(tmp_path))

    assert html_lib.escape(page.heading) in markup
    assert (
        '<span data-edit-key="page.cover.heading">'
        f"{html_lib.escape(page.heading)}</span>"
    ) in markup
    assert 'class="editor-metadata-hook" data-edit-key="page.cover.heading"' not in markup


def test_layout_css_uses_saved_v3_geometry(tmp_path):
    layout = replace_element(
        load_builtin_layout(), "cover", "company-name", x=123, y=234, w=500, h=190
    )

    output = render.page_html(
        carousel_draft().pages[0],
        "ElevenLabs",
        brand_asset(_logo(tmp_path)),
        layout,
    )

    assert '[data-layout-id="company-name"]' in output
    assert "left:123px" in output
    assert "top:234px" in output
    assert "width:500px" in output
    assert "height:190px" in output


def test_who_renders_all_three_approved_sticky_sections(tmp_path):
    page = carousel_draft().pages[1]
    markup = _markup(_render(tmp_path, 1))

    for element_id in ("heading", "logo", "positioning", "facts", "reason", "mascot"):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    for section in page.sections:
        assert html_lib.escape(section.text) in markup


def test_content_sync_targets_text_span_without_replacing_sticky_label(tmp_path):
    markup = _markup(_render(tmp_path, 1))

    assert '<b>白話定位</b><span data-edit-key="page.who.section.0.text">' in markup
    assert 'data-layout-id="positioning" data-edit-key=' not in markup


def test_problem_renders_context_and_three_connected_flow_cards(tmp_path):
    page = carousel_draft().pages[2]
    markup = _markup(_render(tmp_path, 2))

    for element_id in (
        "heading", "current", "opportunity", "spine", "stage-1", "stage-2", "stage-3", "mascot"
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    assert page.diagram is not None
    for section in page.sections:
        assert html_lib.escape(section.text) in markup
    for node in page.diagram.nodes:
        assert html_lib.escape(node.title) in markup
        assert html_lib.escape(node.text) in markup
    assert markup.count('class="card-icon"') == 3
    for index in range(3):
        assert f'data-card-icon="problem-{index + 1}"' in markup


def test_problem_requires_its_flow_diagram(tmp_path):
    page = replace(carousel_draft().pages[2], diagram=None)

    with pytest.raises(ValueError, match="第 3 頁缺少問題流程圖解"):
        render.page_html(page, "ElevenLabs", brand_asset(_logo(tmp_path)))


def test_how_ai_renders_one_arrow_system_and_four_context_notes(tmp_path):
    page = carousel_draft().pages[3]
    markup = _markup(_render(tmp_path, 3))

    assert markup.count('class="flow-arrows"') == 1
    for label in ("IN", "AI", "OUT"):
        assert f">{label}</i>" in markup
    for internal_expression in ("listen", "think", "happy"):
        assert f">{internal_expression}</i>" not in markup
    for element_id in (
        "heading", "step-1", "step-2", "step-3", "traditional", "ai-role", "human", "difference", "mascot"
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    for section in page.sections:
        assert html_lib.escape(section.text) in markup


def test_results_uses_three_equal_cards_with_approved_roles(tmp_path):
    page = carousel_draft().pages[4]
    output = _render(tmp_path, 4)
    markup = _markup(output)
    layout = load_builtin_layout().pages["results"].elements

    cards = [layout[item].rect for item in ("before", "intervention", "after")]
    assert max(card.w for card in cards) - min(card.w for card in cards) <= 1
    assert max(card.h for card in cards) - min(card.h for card in cards) <= 1
    assert 'class="result-flow"' in markup
    assert page.diagram is not None
    assert [node.title for node in page.diagram.nodes] == ["使用前", "產品介入", "使用後"]
    for label in ("BEFORE", "→", "AFTER"):
        assert f">{label}</i>" in markup
    for internal_expression in ("concerned", "think", "happy"):
        assert f">{internal_expression}</i>" not in markup
    for element_id in (
        "heading", "audience", "before", "intervention", "after", "core-difference", "value", "mascot"
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1


def test_cta_contains_only_the_approved_centered_two_lines(tmp_path):
    markup = _markup(_render(tmp_path, 5))

    assert 'data-page-type="cta"' in markup
    assert "追蹤呆一布 AI 共學實驗室\n帶你看更多最新 AI 資訊" in markup
    assert "收束結論" not in markup
    assert "給讀者的問題" not in markup
    assert 'data-layout-id="invitation"' in markup
    assert 'data-layout-id="mascot"' in markup


def test_renderer_escapes_unsafe_text_on_all_pages(tmp_path):
    unsafe = '<script>alert("unsafe")</script>'
    asset = brand_asset(_logo(tmp_path))
    for page in carousel_draft().pages:
        sections = tuple(replace(section, text=unsafe) for section in page.sections)
        diagram = page.diagram
        if diagram is not None:
            diagram = replace(
                diagram,
                nodes=tuple(replace(node, title=unsafe, text=unsafe) for node in diagram.nodes),
            )
        output = render.page_html(
            replace(page, heading=unsafe, sections=sections, diagram=diagram),
            "ElevenLabs",
            asset,
        )
        assert unsafe not in output
        assert html_lib.escape(unsafe) in output


def test_renderer_has_no_why_care_implementation():
    source = inspect.getsource(render)

    assert "_why_care" not in source
    assert '"why-care"' not in source
