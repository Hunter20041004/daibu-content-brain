import pytest

from daibu.cards.layout_registry import ELEMENT_REGISTRY
from daibu.cards import pages as carousel_pages
from daibu.cards.layout_schema import (
    LayoutValidationError,
    layout_to_mapping,
    load_builtin_layout,
    parse_layout,
    replace_element,
)


def valid_layout_mapping():
    pages = {}
    for page_type, rules in ELEMENT_REGISTRY.items():
        elements = {}
        for element_id, rule in rules.items():
            element = {
                "x": 0,
                "y": 0,
                "w": max(rule.min_w, 120),
                "h": max(rule.min_h, 120),
            }
            if rule.text:
                element.update(
                    {
                        "font_size": max(rule.min_font_size, 22),
                        "text_align": "left",
                    }
                )
            elements[element_id] = element
        pages[page_type] = {"elements": elements}
    return {
        "schema_version": 3,
        "canvas": {"width": 1080, "height": 1350},
        "pages": pages,
    }


def test_builtin_layout_is_six_page_schema_v3():
    document = load_builtin_layout()

    assert document.schema_version == 3
    assert tuple(document.pages) == carousel_pages.PAGE_TYPES
    assert "why-care" not in document.pages
    assert parse_layout(layout_to_mapping(document)) == document


def test_layout_rejects_unknown_element():
    value = valid_layout_mapping()
    value["pages"]["cover"]["elements"]["unknown-widget"] = {
        "x": 0, "y": 0, "w": 100, "h": 100
    }

    with pytest.raises(LayoutValidationError, match="unknown-widget"):
        parse_layout(value)


def test_layout_rejects_negative_element_size():
    value = valid_layout_mapping()
    value["pages"]["who"]["elements"]["heading"]["w"] = -1

    with pytest.raises(LayoutValidationError, match="heading.*尺寸"):
        parse_layout(value)


def test_layout_rejects_element_outside_canvas():
    value = valid_layout_mapping()
    value["pages"]["cover"]["elements"]["company-logo"]["x"] = 1000

    with pytest.raises(LayoutValidationError, match="company-logo.*畫布"):
        parse_layout(value)


def test_layout_rejects_unknown_text_alignment():
    value = valid_layout_mapping()
    value["pages"]["who"]["elements"]["heading"]["text_align"] = "justify"

    with pytest.raises(LayoutValidationError, match="heading.*對齊"):
        parse_layout(value)


def test_layout_rejects_unknown_element_property():
    value = valid_layout_mapping()
    value["pages"]["who"]["elements"]["heading"]["rotate"] = 10

    with pytest.raises(LayoutValidationError, match="heading.*rotate"):
        parse_layout(value)


def test_layout_requires_fixed_canvas_size():
    value = valid_layout_mapping()
    value["canvas"]["height"] = 1080

    with pytest.raises(LayoutValidationError, match="1080×1350"):
        parse_layout(value)


def test_layout_rejects_unknown_schema_version():
    value = valid_layout_mapping()
    value["schema_version"] = 2

    with pytest.raises(LayoutValidationError, match="schema_version"):
        parse_layout(value)


def test_layout_rejects_non_finite_geometry():
    value = valid_layout_mapping()
    value["pages"]["cover"]["elements"]["company-logo"]["x"] = "NaN"

    with pytest.raises(LayoutValidationError, match="company-logo.*數字"):
        parse_layout(value)


def test_layout_enforces_registered_minimum_size():
    value = valid_layout_mapping()
    value["pages"]["cover"]["elements"]["mascot"]["w"] = 100

    with pytest.raises(LayoutValidationError, match="mascot.*最小尺寸"):
        parse_layout(value)


def test_layout_enforces_registered_minimum_font_size():
    value = valid_layout_mapping()
    value["pages"]["who"]["elements"]["heading"]["font_size"] = 10

    with pytest.raises(LayoutValidationError, match="heading.*字級"):
        parse_layout(value)


def test_layout_enforces_registered_maximum_font_size():
    value = valid_layout_mapping()
    value["pages"]["who"]["elements"]["heading"]["font_size"] = 200

    with pytest.raises(LayoutValidationError, match="heading.*字級"):
        parse_layout(value)


def test_layout_requires_every_registered_page():
    value = valid_layout_mapping()
    del value["pages"]["who"]

    with pytest.raises(LayoutValidationError, match="缺少.*who"):
        parse_layout(value)


def test_layout_requires_every_registered_element():
    value = valid_layout_mapping()
    del value["pages"]["cover"]["elements"]["company-name"]

    with pytest.raises(LayoutValidationError, match="company-name"):
        parse_layout(value)


def test_layout_rejects_unknown_top_level_property():
    value = valid_layout_mapping()
    value["unsafe_css"] = "position: fixed"

    with pytest.raises(LayoutValidationError, match="unsafe_css"):
        parse_layout(value)


def test_layout_rejects_unknown_page_property():
    value = valid_layout_mapping()
    value["pages"]["cover"]["background_script"] = "alert(1)"

    with pytest.raises(LayoutValidationError, match="background_script"):
        parse_layout(value)


def test_layout_rejects_unknown_canvas_property():
    value = valid_layout_mapping()
    value["canvas"]["zoom"] = 1.5

    with pytest.raises(LayoutValidationError, match="zoom"):
        parse_layout(value)


def test_layout_round_trips_to_canonical_mapping():
    value = valid_layout_mapping()

    serialized = layout_to_mapping(parse_layout(value))

    assert serialized == value


def test_replace_element_returns_new_validated_document():
    original = parse_layout(valid_layout_mapping())

    updated = replace_element(original, "who", "heading", x=40, font_size=48)

    assert original.pages["who"].elements["heading"].rect.x == 0
    assert updated.pages["who"].elements["heading"].rect.x == 40
    assert updated.pages["who"].elements["heading"].text_style.font_size == 48


def test_replace_element_rejects_unknown_page():
    original = parse_layout(valid_layout_mapping())

    with pytest.raises(LayoutValidationError, match="missing-page"):
        replace_element(original, "missing-page", "heading", x=40)


def test_replace_element_rejects_unknown_element():
    original = parse_layout(valid_layout_mapping())

    with pytest.raises(LayoutValidationError, match="missing-element"):
        replace_element(original, "cover", "missing-element", x=40)


def test_replace_element_rejects_text_style_on_non_text_element():
    original = parse_layout(valid_layout_mapping())

    with pytest.raises(LayoutValidationError, match="mascot.*font_size"):
        replace_element(original, "cover", "mascot", font_size=48)


def test_builtin_layout_covers_every_registered_element():
    document = load_builtin_layout()

    assert set(document.pages) == set(ELEMENT_REGISTRY)
    for page_type, rules in ELEMENT_REGISTRY.items():
        assert set(document.pages[page_type].elements) == set(rules)


def test_results_flow_cards_must_remain_equal_size():
    value = valid_layout_mapping()
    value["pages"]["results"]["elements"]["intervention"]["w"] += 10

    with pytest.raises(LayoutValidationError, match="等寬等高"):
        parse_layout(value)
