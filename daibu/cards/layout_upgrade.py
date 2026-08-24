from __future__ import annotations

from copy import deepcopy
from typing import Mapping


def normalize_layout_mapping(
    value: Mapping[str, object],
) -> dict[str, object]:
    normalized = deepcopy(dict(value))
    if normalized.get("schema_version") != 1:
        return normalized
    pages = normalized["pages"]
    assert isinstance(pages, dict)
    who = pages.get("who")
    if not isinstance(who, dict):
        return normalized
    elements = who.get("elements")
    if not isinstance(elements, dict) or not {
        "facts",
        "positioning",
    } <= set(elements):
        return normalized
    assert isinstance(who, dict)
    facts = elements.pop("facts")
    assert isinstance(facts, dict)
    x = float(facts["x"])
    y = float(facts["y"])
    w = float(facts["w"])
    h = float(facts["h"])
    elements["facts-bg"] = {"x": x, "y": y, "w": w, "h": h}
    elements["facts-label"] = {
        "x": x + 46,
        "y": y + 24,
        "w": w - 92,
        "h": 38,
        "font_size": 27,
        "text_align": "left",
    }
    elements["facts-body"] = {
        "x": x + 46,
        "y": y + 73,
        "w": w - 92,
        "h": max(24, h - 97),
        "font_size": float(facts.get("font_size", 28)),
        "text_align": str(facts.get("text_align", "left")),
    }
    positioning = elements.pop("positioning")
    assert isinstance(positioning, dict)
    px = float(positioning["x"])
    py = float(positioning["y"])
    pw = float(positioning["w"])
    ph = float(positioning["h"])
    elements["positioning-bg"] = {
        "x": px,
        "y": py,
        "w": pw,
        "h": ph,
    }
    elements["positioning-label"] = {
        "x": px + 54,
        "y": py + 44,
        "w": pw - 108,
        "h": 38,
        "font_size": 27,
        "text_align": "left",
    }
    elements["positioning-body"] = {
        "x": px + 54,
        "y": py + 98,
        "w": pw - 108,
        "h": max(24, ph - 142),
        "font_size": float(positioning.get("font_size", 28)),
        "text_align": str(positioning.get("text_align", "left")),
    }
    normalized["schema_version"] = 2
    return normalized
