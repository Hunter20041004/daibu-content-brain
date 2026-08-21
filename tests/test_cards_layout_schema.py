import pytest

from daibu.cards.layout_registry import ELEMENT_REGISTRY
from daibu.cards.layout_schema import (
    LayoutValidationError,
    layout_to_mapping,
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
        "schema_version": 1,
        "canvas": {"width": 1080, "height": 1350},
        "pages": pages,
    }


def test_layout_rejects_unknown_element():
    value = {
        "schema_version": 1,
        "canvas": {"width": 1080, "height": 1350},
        "pages": {
            "cover": {
                "elements": {
                    "unknown-widget": {
                        "x": 0,
                        "y": 0,
                        "w": 100,
                        "h": 100,
                    }
                }
            }
        },
    }

    with pytest.raises(LayoutValidationError, match="unknown-widget"):
        parse_layout(value)


def test_layout_rejects_negative_element_size():
    value = {
        "schema_version": 1,
        "canvas": {"width": 1080, "height": 1350},
        "pages": {
            "cover": {
                "elements": {
                    "heading": {
                        "x": 80,
                        "y": 360,
                        "w": -1,
                        "h": 220,
                        "font_size": 76,
                        "text_align": "left",
                    }
                }
            }
        },
    }

    with pytest.raises(LayoutValidationError, match="heading.*尺寸"):
        parse_layout(value)


def test_layout_rejects_element_outside_canvas():
    value = {
        "schema_version": 1,
        "canvas": {"width": 1080, "height": 1350},
        "pages": {
            "cover": {
                "elements": {
                    "company-logo": {
                        "x": 1000,
                        "y": 70,
                        "w": 100,
                        "h": 90,
                    }
                }
            }
        },
    }

    with pytest.raises(LayoutValidationError, match="company-logo.*畫布"):
        parse_layout(value)


def test_layout_rejects_unknown_text_alignment():
    value = {
        "schema_version": 1,
        "canvas": {"width": 1080, "height": 1350},
        "pages": {
            "cover": {
                "elements": {
                    "heading": {
                        "x": 80,
                        "y": 360,
                        "w": 620,
                        "h": 220,
                        "font_size": 76,
                        "text_align": "justify",
                    }
                }
            }
        },
    }

    with pytest.raises(LayoutValidationError, match="heading.*對齊"):
        parse_layout(value)


def test_layout_rejects_unknown_element_property():
    value = {
        "schema_version": 1,
        "canvas": {"width": 1080, "height": 1350},
        "pages": {
            "cover": {
                "elements": {
                    "heading": {
                        "x": 80,
                        "y": 360,
                        "w": 620,
                        "h": 220,
                        "font_size": 76,
                        "text_align": "left",
                        "rotate": 10,
                    }
                }
            }
        },
    }

    with pytest.raises(LayoutValidationError, match="heading.*rotate"):
        parse_layout(value)


def test_layout_requires_fixed_canvas_size():
    value = {
        "schema_version": 1,
        "canvas": {"width": 1080, "height": 1080},
        "pages": {},
    }

    with pytest.raises(LayoutValidationError, match="1080×1350"):
        parse_layout(value)


def test_layout_rejects_unknown_schema_version():
    value = {
        "schema_version": 2,
        "canvas": {"width": 1080, "height": 1350},
        "pages": {},
    }

    with pytest.raises(LayoutValidationError, match="schema_version"):
        parse_layout(value)


def test_layout_rejects_non_finite_geometry():
    value = {
        "schema_version": 1,
        "canvas": {"width": 1080, "height": 1350},
        "pages": {
            "cover": {
                "elements": {
                    "company-logo": {
                        "x": "NaN",
                        "y": 70,
                        "w": 100,
                        "h": 90,
                    }
                }
            }
        },
    }

    with pytest.raises(LayoutValidationError, match="company-logo.*數字"):
        parse_layout(value)


def test_layout_enforces_registered_minimum_size():
    value = {
        "schema_version": 1,
        "canvas": {"width": 1080, "height": 1350},
        "pages": {
            "cover": {
                "elements": {
                    "mascot": {
                        "x": 800,
                        "y": 1050,
                        "w": 100,
                        "h": 120,
                    }
                }
            }
        },
    }

    with pytest.raises(LayoutValidationError, match="mascot.*最小尺寸"):
        parse_layout(value)


def test_layout_enforces_registered_minimum_font_size():
    value = {
        "schema_version": 1,
        "canvas": {"width": 1080, "height": 1350},
        "pages": {
            "cover": {
                "elements": {
                    "heading": {
                        "x": 80,
                        "y": 360,
                        "w": 620,
                        "h": 220,
                        "font_size": 10,
                        "text_align": "left",
                    }
                }
            }
        },
    }

    with pytest.raises(LayoutValidationError, match="heading.*字級"):
        parse_layout(value)


def test_layout_enforces_registered_maximum_font_size():
    value = {
        "schema_version": 1,
        "canvas": {"width": 1080, "height": 1350},
        "pages": {
            "cover": {
                "elements": {
                    "heading": {
                        "x": 80,
                        "y": 360,
                        "w": 620,
                        "h": 220,
                        "font_size": 200,
                        "text_align": "left",
                    }
                }
            }
        },
    }

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

    updated = replace_element(original, "cover", "heading", x=40, font_size=48)

    assert original.pages["cover"].elements["heading"].rect.x == 0
    assert updated.pages["cover"].elements["heading"].rect.x == 40
    assert updated.pages["cover"].elements["heading"].text_style.font_size == 48


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
