from copy import deepcopy
from typing import Mapping


def _rect(raw: Mapping[str, object]) -> dict[str, object]:
    return {key: raw[key] for key in ("x", "y", "w", "h")}


def _child(
    parent: Mapping[str, object],
    *,
    left: float,
    top: float,
    right: float,
    height: float | None = None,
    bottom: float | None = None,
    font_size: float | None = None,
    text_align: str = "left",
) -> dict[str, object]:
    result = {
        "x": float(parent["x"]) + left,
        "y": float(parent["y"]) + top,
        "w": float(parent["w"]) - left - right,
        "h": (
            height
            if height is not None
            else float(parent["h"]) - top - float(bottom)
        ),
    }
    if font_size is not None:
        result.update(font_size=font_size, text_align=text_align)
    return result


def _copy_elements(
    elements: Mapping[str, object], *element_ids: str
) -> dict[str, object]:
    return {element_id: deepcopy(elements[element_id]) for element_id in element_ids}


def _section_layers(
    elements: Mapping[str, object], element_id: str, *,
    left: float = 30, label_top: float = 30, text_top: float = 74,
    label_height: float = 30, bottom: float = 28,
    text_font_size: float = 22,
) -> dict[str, object]:
    parent = elements[element_id]
    assert isinstance(parent, Mapping)
    return {
        f"{element_id}-bg": _rect(parent),
        f"{element_id}-label": _child(
            parent,
            left=left,
            top=label_top,
            right=left,
            height=label_height,
            font_size=18,
        ),
        f"{element_id}-text": _child(
            parent,
            left=left,
            top=text_top,
            right=left,
            bottom=bottom,
            font_size=text_font_size,
        ),
    }


def _upgrade_cover(elements: Mapping[str, object]) -> dict[str, object]:
    upgraded = _copy_elements(
        elements, "company-logo", "company-name", "positioning", "mascot"
    )
    upgraded["heading"] = deepcopy(
        elements.get(
            "heading",
            {
                "x": 140,
                "y": 655,
                "w": 800,
                "h": 90,
                "font_size": 34,
                "text_align": "center",
            },
        )
    )
    return upgraded


def _upgrade_who(elements: Mapping[str, object]) -> dict[str, object]:
    upgraded = _copy_elements(elements, "heading", "logo", "mascot")
    upgraded.update(
        {
            "page-label": {
                "x": 153,
                "y": 158,
                "w": 300,
                "h": 28,
                "font_size": 18,
                "text_align": "left",
            },
            "identity-product": {
                "x": 142,
                "y": 300,
                "w": 235,
                "h": 65,
                "font_size": 14,
                "text_align": "center",
            },
            "identity-arrow-1": {
                "x": 387,
                "y": 310,
                "w": 35,
                "h": 44,
                "font_size": 25,
                "text_align": "center",
            },
            "identity-user": {
                "x": 432,
                "y": 300,
                "w": 235,
                "h": 65,
                "font_size": 14,
                "text_align": "center",
            },
            "identity-arrow-2": {
                "x": 677,
                "y": 310,
                "w": 35,
                "h": 44,
                "font_size": 25,
                "text_align": "center",
            },
            "identity-value": {
                "x": 722,
                "y": 300,
                "w": 215,
                "h": 65,
                "font_size": 14,
                "text_align": "center",
            },
        }
    )
    upgraded.update(_section_layers(elements, "positioning"))
    upgraded.update(_section_layers(elements, "facts"))
    upgraded.update(
        _section_layers(
            elements,
            "reason",
            left=42,
            label_top=37,
            text_top=81,
            bottom=32,
            text_font_size=25,
        )
    )
    return upgraded


def _upgrade_problem(elements: Mapping[str, object]) -> dict[str, object]:
    upgraded = _copy_elements(elements, "heading", "spine", "mascot")
    upgraded.update(
        {
            "page-label": {
                "x": 153,
                "y": 158,
                "w": 330,
                "h": 28,
                "font_size": 18,
                "text_align": "left",
            },
            "question-mark": {"x": 735, "y": 115, "w": 260, "h": 400},
        }
    )
    upgraded.update(
        _section_layers(
            elements,
            "current",
            label_top=42,
            text_top=100,
            label_height=32,
            bottom=40,
        )
    )
    upgraded.update(
        _section_layers(
            elements,
            "opportunity",
            label_top=42,
            text_top=100,
            label_height=32,
            bottom=40,
        )
    )
    for index in range(1, 4):
        element_id = f"stage-{index}"
        parent = elements[element_id]
        assert isinstance(parent, Mapping)
        upgraded.update(
            {
                f"{element_id}-bg": _rect(parent),
                f"{element_id}-icon": _child(
                    parent, left=345, top=100, right=24, height=112
                ),
                f"{element_id}-index": _child(
                    parent,
                    left=30,
                    top=32,
                    right=float(parent["w"]) - 80,
                    height=50,
                    font_size=18,
                    text_align="center",
                ),
                f"{element_id}-title": _child(
                    parent,
                    left=30,
                    top=96,
                    right=161,
                    height=36,
                    font_size=24,
                ),
                f"{element_id}-text": _child(
                    parent,
                    left=30,
                    top=144,
                    right=151,
                    height=62,
                    font_size=20,
                ),
            }
        )
    return upgraded


def _upgrade_how_ai(elements: Mapping[str, object]) -> dict[str, object]:
    upgraded = _copy_elements(elements, "heading", "mascot")
    upgraded.update(
        {
            "page-label": {
                "x": 148,
                "y": 153,
                "w": 300,
                "h": 28,
                "font_size": 18,
                "text_align": "left",
            },
            "flow-arrow-1": {"x": 393, "y": 520, "w": 44, "h": 44},
            "flow-arrow-2": {"x": 663, "y": 520, "w": 44, "h": 44},
        }
    )
    for index in range(1, 4):
        element_id = f"step-{index}"
        parent = elements[element_id]
        assert isinstance(parent, Mapping)
        upgraded.update(
            {
                f"{element_id}-bg": _rect(parent),
                f"{element_id}-tag": _child(
                    parent,
                    left=22,
                    top=40,
                    right=22,
                    height=32,
                    font_size=18,
                    text_align="center",
                ),
                f"{element_id}-title": _child(
                    parent,
                    left=22,
                    top=122,
                    right=22,
                    height=42,
                    font_size=24,
                    text_align="center",
                ),
                f"{element_id}-text": _child(
                    parent,
                    left=22,
                    top=184,
                    right=22,
                    height=68,
                    font_size=20,
                    text_align="center",
                ),
            }
        )
    for element_id in ("traditional", "ai-role", "human", "difference"):
        upgraded.update(
            _section_layers(
                elements,
                element_id,
                left=28,
                label_top=28,
                text_top=68,
                label_height=28,
                bottom=28,
                text_font_size=20,
            )
        )
    return upgraded


def _upgrade_results(elements: Mapping[str, object]) -> dict[str, object]:
    upgraded = _copy_elements(elements, "heading", "mascot")
    upgraded["page-label"] = {
        "x": 153,
        "y": 158,
        "w": 330,
        "h": 28,
        "font_size": 18,
        "text_align": "left",
    }
    upgraded.update(
        _section_layers(
            elements,
            "audience",
            left=28,
            label_top=18,
            text_top=53,
            label_height=26,
            bottom=22,
        )
    )
    for element_id in ("before", "intervention", "after"):
        parent = elements[element_id]
        assert isinstance(parent, Mapping)
        tag_role = "arrow" if element_id == "intervention" else "tag"
        tag = _child(
            parent, left=22, top=52, right=22, height=30
        )
        if tag_role == "tag":
            tag.update(font_size=18, text_align="center")
        upgraded.update(
            {
                f"{element_id}-bg": _rect(parent),
                f"{element_id}-{tag_role}": tag,
                f"{element_id}-title": _child(
                    parent,
                    left=22,
                    top=142,
                    right=22,
                    height=48,
                    font_size=26,
                    text_align="center",
                ),
                f"{element_id}-text": _child(
                    parent,
                    left=22,
                    top=214,
                    right=22,
                    height=74,
                    font_size=22,
                    text_align="center",
                ),
            }
        )
    upgraded.update(
        _section_layers(
            elements,
            "core-difference",
            label_top=30,
            text_top=74,
            bottom=30,
        )
    )
    upgraded.update(
        _section_layers(
            elements,
            "value",
            label_top=30,
            text_top=74,
            bottom=30,
        )
    )
    return upgraded


def _upgrade_pages_v3_to_v4(
    pages: Mapping[str, object],
) -> dict[str, object]:
    upgrades = {
        "cover": _upgrade_cover,
        "who": _upgrade_who,
        "problem": _upgrade_problem,
        "how-ai": _upgrade_how_ai,
        "results": _upgrade_results,
    }
    result: dict[str, object] = {}
    for page_type, raw_page in pages.items():
        if not isinstance(raw_page, Mapping):
            result[page_type] = deepcopy(raw_page)
            continue
        raw_elements = raw_page.get("elements")
        if page_type in upgrades and isinstance(raw_elements, Mapping):
            result[page_type] = {"elements": upgrades[page_type](raw_elements)}
        else:
            result[page_type] = deepcopy(raw_page)
    return result


def normalize_layout_mapping(value: Mapping[str, object]) -> dict[str, object]:
    version = value.get("schema_version")
    if version == 4:
        return deepcopy(dict(value))
    if version != 3:
        raise ValueError(f"不支援的 schema_version：{version}")
    result = deepcopy(dict(value))
    pages = result.get("pages")
    if isinstance(pages, Mapping):
        result["pages"] = _upgrade_pages_v3_to_v4(pages)
    result["schema_version"] = 4
    return result
