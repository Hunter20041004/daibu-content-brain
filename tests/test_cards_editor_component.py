from daibu.cards import editor_component


def test_content_component_has_navigation_working_copy_and_save_trigger():
    assert 'data-role="page-rail"' in editor_component.CONTENT_HTML
    assert 'setTriggerValue("save"' in editor_component.CONTENT_JS
    assert "sessionStorage" in editor_component.CONTENT_JS
    assert "data-edit-key" in editor_component.CONTENT_JS
    assert "beforeunload" in editor_component.CONTENT_JS
    assert "textContent" in editor_component.CONTENT_JS


def test_component_css_uses_editorial_tokens_and_responsive_three_columns():
    css = editor_component.CONTENT_CSS

    assert "132px minmax(320px,1fr) minmax(360px,.9fr)" in css
    assert "--ink:#102f3d" in css.replace(" ", "")
    assert "@media (max-width: 700px)" in css
    assert "overflow-x: hidden" in css


def test_normalize_event_returns_dirty_and_optional_save_payload():
    event = editor_component.normalize_event(
        type("Result", (), {"dirty": True, "save": {"revision": 3, "values": {}}})()
    )

    assert event.dirty is True
    assert event.save_payload == {"revision": 3, "values": {}}
    assert editor_component.normalize_event(None).save_payload is None
