import pytest
from types import SimpleNamespace

from daibu.cards.layout_schema import load_builtin_layout, replace_element
from daibu.cards.template_editor_payload import (
    apply_template_values,
    reset_layout_page,
    summarize_layout_diff,
    template_editor_payload,
)


def _raw(element):
    value = {"x": element.rect.x, "y": element.rect.y, "w": element.rect.w, "h": element.rect.h}
    if element.text_style:
        value.update(font_size=element.text_style.font_size, text_align=element.text_style.text_align)
    return value


def test_template_values_update_registered_geometry_and_text_style():
    original = load_builtin_layout()
    values = {key: _raw(value) for key, value in original.pages["cover"].elements.items()}
    values["heading"].update(x=104, w=620, font_size=78, text_align="left")
    edited = apply_template_values(original, "cover", values)
    assert edited.pages["cover"].elements["heading"].rect.x == 104
    assert edited.pages["cover"].elements["heading"].rect.w == 620
    assert edited.pages["cover"].elements["heading"].text_style.font_size == 78


def test_unknown_template_property_is_rejected():
    original = load_builtin_layout()
    values = {key: _raw(value) for key, value in original.pages["cover"].elements.items()}
    values["heading"]["rotate"] = 10
    with pytest.raises(ValueError, match="不允許"):
        apply_template_values(original, "cover", values)


def test_reset_only_restores_selected_page():
    base = load_builtin_layout()
    working = replace_element(base, "cover", "heading", x=104)
    working = replace_element(working, "who", "heading", x=120)
    reset = reset_layout_page(working, base, "cover")
    assert reset.pages["cover"] == base.pages["cover"]
    assert reset.pages["who"] != base.pages["who"]


def test_layout_diff_summarizes_moves_and_resizes():
    base = load_builtin_layout()
    working = replace_element(base, "results", "before-title", x=80, w=300)
    summary = summarize_layout_diff(base, working)
    assert "第 5 頁：移動 1 個元素、調整 1 個文字框" in summary


def test_template_payload_exposes_collision_policy_without_unsafe_style_data():
    layout = load_builtin_layout()
    version = SimpleNamespace(
        id=11,
        version_no=1,
        created_at="2026-08-23T10:00:00",
        layout=layout,
    )
    payload = template_editor_payload(
        SimpleNamespace(id=7, name="AI 新創介紹"),
        [version],
        version,
        "cover",
        "<main></main>",
    )
    by_id = {item["elementId"]: item for item in payload["elements"]}
    assert by_id["heading"]["collision"] == "avoid"
    assert by_id["company-name"]["collision"] == "allow"
    assert by_id["rule"]["collision"] == "background"
    assert "css" not in payload


def test_template_payload_reports_missing_renderer_layout_hooks():
    layout = load_builtin_layout()
    version = SimpleNamespace(
        id=11,
        version_no=1,
        created_at="2026-08-23T10:00:00",
        layout=layout,
    )
    payload = template_editor_payload(
        SimpleNamespace(id=7, name="AI 新創介紹"),
        [version],
        version,
        "cover",
        '<main data-layout-id="heading"></main>',
    )
    assert payload["previewSyncError"].startswith("預覽缺少版面元素：")
    assert "company-name" in payload["previewSyncError"]


def test_template_payload_identifies_layout_schema_and_registry_revision():
    layout = load_builtin_layout()
    version = SimpleNamespace(
        id=11,
        version_no=1,
        created_at="2026-08-23T10:00:00",
        layout=layout,
    )

    payload = template_editor_payload(
        SimpleNamespace(id=7, name="AI 新創介紹"),
        [version],
        version,
        "who",
        "<main></main>",
    )

    assert payload["layoutSchemaVersion"] == 2
    assert isinstance(payload["registryFingerprint"], str)
    assert len(payload["registryFingerprint"]) == 64
