from daibu.cards import template_editor_component


def test_template_component_exposes_canvas_and_eight_resize_handles():
    assert 'data-role="template-canvas"' in template_editor_component.TEMPLATE_HTML
    assert 'HANDLE_DIRECTIONS = ["n","ne","e","se","s","sw","w","nw"]' in template_editor_component.TEMPLATE_JS
    assert 'setTriggerValue("saveLayout"' in template_editor_component.TEMPLATE_JS
    assert "clientDeltaToCanvas" in template_editor_component.TEMPLATE_JS
    assert "sessionStorage" in template_editor_component.TEMPLATE_JS
    assert "HISTORY_LIMIT = 50" in template_editor_component.TEMPLATE_JS


def test_template_component_has_desktop_canvas_and_mobile_read_only_mode():
    css = template_editor_component.TEMPLATE_CSS
    assert "1080px" in css
    assert "aspect-ratio: 4 / 5" in css
    assert "@media (max-width: 767px)" in css
    assert "請改用桌面寬度調整模板" in template_editor_component.TEMPLATE_HTML


def test_template_component_exposes_all_renderer_color_tokens():
    css = template_editor_component.TEMPLATE_CSS
    assert "--ink-deep:#102f3d" in css
    assert "--cyan-soft:#dceff1" in css
    assert "--coral:#ec9870" in css
    assert "--muted:#61747d" in css


def test_mobile_read_only_mode_hides_template_save_action():
    css = template_editor_component.TEMPLATE_CSS
    mobile_css = css.split("@media (max-width: 767px)", 1)[1]
    assert '[data-role="version-bar"] button { display:none; }' in mobile_css


def test_template_component_applies_working_geometry_to_renderer_dom():
    script = template_editor_component.TEMPLATE_JS
    assert "function applyWorkingLayout()" in script
    assert 'style.setProperty(property,value,"important")' in script
    assert "const missing = applyWorkingLayout();" in script


def test_template_component_blocks_save_when_preview_hooks_are_missing():
    script = template_editor_component.TEMPLATE_JS
    assert "data.previewSyncError" in script
    assert "save.disabled=!state.dirty||Boolean(syncError)" in script
    assert "preview-sync-error" in script


def test_template_component_cache_is_scoped_to_schema_and_registry():
    script = template_editor_component.TEMPLATE_JS

    assert "data.layoutSchemaVersion" in script
    assert "data.registryFingerprint" in script
    assert "stored?.schemaIdentity === schemaIdentity" in script
