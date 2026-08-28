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


def test_layout_css_uses_saved_v4_geometry(tmp_path):
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

    for element_id in (
        "heading",
        "logo",
        "positioning-bg",
        "positioning-label",
        "positioning-text",
        "facts-bg",
        "facts-label",
        "facts-text",
        "reason-bg",
        "reason-label",
        "reason-text",
        "mascot",
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    for section in page.sections:
        assert html_lib.escape(section.text) in markup


def test_who_text_roles_are_independent_layout_nodes(tmp_path):
    markup = _markup(_render(tmp_path, 1))

    assert 'data-layout-id="positioning-bg"' in markup
    assert (
        'data-layout-id="positioning-text" '
        'data-edit-key="page.who.section.0.text"' in markup
    )
    assert 'data-layout-id="positioning-label"' in markup
    assert markup.count('data-layout-id="positioning-text"') == 1
    assert 'data-layout-id="positioning"' not in markup


def test_who_restores_the_approved_v57_identity_map_and_page_label(tmp_path):
    markup = _markup(_render(tmp_path, 1))

    assert 'data-layout-id="page-label">COMPANY FILE</div>' in markup
    assert '<div class="identity-map"' in markup
    assert markup.count('data-visual="identity-node"') == 3
    assert '<div class="profile-grid schema-profile">' in markup


def test_problem_restores_the_approved_v57_story_layers(tmp_path):
    markup = _markup(_render(tmp_path, 2))

    assert 'data-layout-id="page-label">THE OPPORTUNITY</div>' in markup
    assert 'data-layout-id="question-mark"' in markup
    assert markup.count('data-visual="cycle-icon"') == 1
    assert markup.count('data-visual="target-icon"') == 1
    assert markup.count('data-visual="growth-icon"') == 1
    assert markup.count('data-visual="causal-spine"') == 1


def test_problem_node_title_body_icon_and_background_are_independent(tmp_path):
    markup = _markup(_render(tmp_path, 2))

    for element_id in (
        "stage-1-bg",
        "stage-1-icon",
        "stage-1-index",
        "stage-1-title",
        "stage-1-text",
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    assert (
        'data-layout-id="stage-1-title" '
        'data-edit-key="page.problem.diagram.0.title"' in markup
    )
    assert (
        'data-layout-id="stage-1-text" '
        'data-edit-key="page.problem.diagram.0.text"' in markup
    )


def test_how_ai_restores_the_approved_v57_flow_layers(tmp_path):
    markup = _markup(_render(tmp_path, 3))

    assert 'data-layout-id="page-label">HOW AI WORKS</div>' in markup
    assert '<div class="route schema-route">' in markup
    assert markup.count('data-visual="flow-arrow"') == 2
    assert '<div class="how-context">' in markup


def test_how_ai_step_roles_and_context_roles_are_independent(tmp_path):
    markup = _markup(_render(tmp_path, 3))

    for element_id in (
        "step-1-bg",
        "step-1-tag",
        "step-1-title",
        "step-1-text",
        "traditional-bg",
        "traditional-label",
        "traditional-text",
        "flow-arrow-1",
        "flow-arrow-2",
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    assert (
        'data-layout-id="step-1-title" '
        'data-edit-key="page.how-ai.diagram.0.title"' in markup
    )
    assert (
        'data-layout-id="traditional-text" '
        'data-edit-key="page.how-ai.section.0.text"' in markup
    )


def test_results_restores_the_approved_v57_page_layers(tmp_path):
    markup = _markup(_render(tmp_path, 4))

    assert 'data-layout-id="page-label">BEFORE &amp; AFTER</div>' in markup
    assert '<div class="sheet shared-sheet model-sheet results-sheet">' in markup
    assert markup.count('data-layout-id="before-bg"') == 1
    assert markup.count('data-layout-id="intervention-bg"') == 1
    assert markup.count('data-layout-id="after-bg"') == 1


def test_results_text_roles_are_direct_layout_and_edit_nodes(tmp_path):
    markup = _markup(_render(tmp_path, 4))

    for element_id in (
        "before-bg",
        "before-tag",
        "before-title",
        "before-text",
        "intervention-bg",
        "intervention-arrow",
        "intervention-title",
        "intervention-text",
        "after-bg",
        "after-tag",
        "after-title",
        "after-text",
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    assert (
        'data-layout-id="before-title" '
        'data-edit-key="page.results.diagram.0.title"' in markup
    )
    assert (
        'data-layout-id="before-text" '
        'data-edit-key="page.results.diagram.0.text"' in markup
    )
    assert 'data-layout-id="before"' not in markup


def test_cta_restores_the_approved_v57_centered_copy_layer(tmp_path):
    markup = _markup(_render(tmp_path, 5))

    assert '<div class="sheet shared-sheet close-sheet">' in markup
    assert 'class="cta-copy cta-center"' in markup
    assert "追蹤呆一布 AI 共學實驗室" in markup
    assert "帶你看更多最新 AI 資訊" in markup


def test_builtin_layout_uses_the_approved_v57_interior_geometry():
    layout = load_builtin_layout()

    who = layout.pages["who"].elements
    problem = layout.pages["problem"].elements
    how_ai = layout.pages["how-ai"].elements

    assert who["logo"].rect.w >= 700
    assert who["reason-bg"].rect.w >= 700
    assert problem["current-bg"].rect.w < problem["stage-1-bg"].rect.w
    assert problem["stage-1-bg"].rect.w == problem["stage-2-bg"].rect.w == problem["stage-3-bg"].rect.w
    assert how_ai["step-1-bg"].rect.w == how_ai["step-2-bg"].rect.w == how_ai["step-3-bg"].rect.w
    assert 680 <= how_ai["heading"].rect.w <= 700
    assert how_ai["heading"].text_style.font_size <= 60


def test_content_sync_targets_text_span_without_replacing_sticky_label(tmp_path):
    markup = _markup(_render(tmp_path, 1))

    assert 'data-layout-id="positioning-label">白話定位</div>' in markup
    assert (
        'data-layout-id="positioning-text" '
        'data-edit-key="page.who.section.0.text"' in markup
    )


def test_problem_renders_context_and_three_connected_flow_cards(tmp_path):
    page = carousel_draft().pages[2]
    markup = _markup(_render(tmp_path, 2))

    for element_id in (
        "heading", "current-bg", "opportunity-bg", "spine", "stage-1-bg", "stage-2-bg", "stage-3-bg", "mascot"
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
        "heading", "step-1-bg", "step-2-bg", "step-3-bg", "traditional-bg", "ai-role-bg", "human-bg", "difference-bg", "mascot"
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    for section in page.sections:
        assert html_lib.escape(section.text) in markup


def test_results_uses_three_equal_cards_with_approved_roles(tmp_path):
    page = carousel_draft().pages[4]
    output = _render(tmp_path, 4)
    markup = _markup(output)
    layout = load_builtin_layout().pages["results"].elements

    cards = [layout[item].rect for item in ("before-bg", "intervention-bg", "after-bg")]
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
        "heading", "audience-bg", "before-bg", "intervention-bg", "after-bg", "core-difference-bg", "value-bg", "mascot"
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1


def test_results_layout_css_targets_title_and_body_independently(tmp_path):
    layout = replace_element(
        load_builtin_layout(), "results", "before-title", font_size=41
    )
    layout = replace_element(layout, "results", "before-text", font_size=23)

    output = render.page_html(
        carousel_draft().pages[4],
        "ElevenLabs",
        brand_asset(_logo(tmp_path)),
        layout,
    )

    assert '[data-layout-id="before-title"]{position:absolute!important' in output
    assert "font-size:41px" in output
    assert '[data-layout-id="before-text"]{position:absolute!important' in output
    assert "font-size:23px" in output


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
