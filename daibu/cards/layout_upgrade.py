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
    for page_type in (
        "who",
        "problem",
        "how-ai",
        "results",
        "why-care",
        "cta",
    ):
        raw_page = pages[page_type]
        assert isinstance(raw_page, dict)
        page_elements = raw_page["elements"]
        assert isinstance(page_elements, dict)
        header = page_elements.pop("header")
        assert isinstance(header, dict)
        hx = float(header["x"])
        hy = float(header["y"])
        hw = float(header["w"])
        hh = float(header["h"])
        page_elements["series"] = {
            "x": hx,
            "y": hy,
            "w": min(420, hw * 0.5),
            "h": hh,
            "font_size": 27,
            "text_align": "left",
        }
        company_width = min(360, hw * 0.45)
        page_elements["company-name"] = {
            "x": hx + hw - company_width,
            "y": hy,
            "w": company_width,
            "h": hh,
            "font_size": 27,
            "text_align": "right",
        }
    problem_page = pages["problem"]
    assert isinstance(problem_page, dict)
    problem_elements = problem_page["elements"]
    assert isinstance(problem_elements, dict)
    for index in range(1, 4):
        stage = problem_elements.pop(f"stage-{index}")
        assert isinstance(stage, dict)
        sx = float(stage["x"])
        sy = float(stage["y"])
        sw = float(stage["w"])
        sh = float(stage["h"])
        text_width = sw - (308 if index == 3 else 76)
        problem_elements[f"stage-{index}-bg"] = {
            "x": sx,
            "y": sy,
            "w": sw,
            "h": sh,
        }
        problem_elements[f"stage-{index}-label"] = {
            "x": sx + 38,
            "y": sy + 32,
            "w": text_width,
            "h": 32,
            "font_size": 25,
            "text_align": "left",
        }
        problem_elements[f"stage-{index}-body"] = {
            "x": sx + 38,
            "y": sy + 72,
            "w": text_width,
            "h": 58,
            "font_size": 48,
            "text_align": "left",
        }
        if index in {1, 3}:
            problem_elements[f"stage-{index}-context"] = {
                "x": sx + 38,
                "y": sy + 142,
                "w": text_width,
                "h": max(30, sh - 174),
                "font_size": 28,
                "text_align": "left",
            }
    how_page = pages["how-ai"]
    assert isinstance(how_page, dict)
    how_elements = how_page["elements"]
    assert isinstance(how_elements, dict)
    for index in range(1, 4):
        step = how_elements.pop(f"step-{index}")
        assert isinstance(step, dict)
        sx = float(step["x"])
        sy = float(step["y"])
        sw = float(step["w"])
        sh = float(step["h"])
        how_elements[f"step-{index}-bg"] = {
            "x": sx,
            "y": sy,
            "w": sw,
            "h": sh,
        }
        how_elements[f"step-{index}-label"] = {
            "x": sx + 36,
            "y": sy + 30,
            "w": sw - 72,
            "h": 32,
            "font_size": 25,
            "text_align": "left",
        }
        how_elements[f"step-{index}-body"] = {
            "x": sx + 36,
            "y": sy + 72,
            "w": sw - 72,
            "h": max(48, sh - 102),
            "font_size": 49,
            "text_align": "left",
        }
    caution = how_elements.pop("caution")
    assert isinstance(caution, dict)
    cx = float(caution["x"])
    cy = float(caution["y"])
    cw = float(caution["w"])
    ch = float(caution["h"])
    how_elements["caution-bg"] = {
        "x": cx,
        "y": cy,
        "w": cw,
        "h": ch,
    }
    how_elements["caution-label"] = {
        "x": cx + 38,
        "y": cy + 26,
        "w": cw - 346,
        "h": 32,
        "font_size": 25,
        "text_align": "left",
    }
    how_elements["caution-body"] = {
        "x": cx + 38,
        "y": cy + 68,
        "w": cw - 346,
        "h": max(42, ch - 94),
        "font_size": 35,
        "text_align": "left",
    }
    results_page = pages["results"]
    assert isinstance(results_page, dict)
    results_elements = results_page["elements"]
    assert isinstance(results_elements, dict)
    results_elements["results-before-bg"] = {
        "x": 0,
        "y": 0,
        "w": 540,
        "h": 1350,
    }
    results_elements["results-after-bg"] = {
        "x": 540,
        "y": 0,
        "w": 540,
        "h": 1350,
    }
    before_copy = results_elements.pop("before-copy")
    assert isinstance(before_copy, dict)
    bx = float(before_copy["x"])
    by = float(before_copy["y"])
    bw = float(before_copy["w"])
    results_elements["before-body"] = {
        "x": bx,
        "y": by,
        "w": bw,
        "h": 120,
        "font_size": 50,
        "text_align": "left",
    }
    results_elements["before-context"] = {
        "x": bx,
        "y": by + 138,
        "w": bw,
        "h": 112,
        "font_size": 28,
        "text_align": "left",
    }
    after_copy = results_elements.pop("after-copy")
    assert isinstance(after_copy, dict)
    ax = float(after_copy["x"])
    ay = float(after_copy["y"])
    aw = float(after_copy["w"])
    results_elements["after-label"] = {
        "x": ax,
        "y": ay,
        "w": aw,
        "h": 52,
        "font_size": 22,
        "text_align": "left",
    }
    results_elements["after-body"] = {
        "x": ax,
        "y": ay + 66,
        "w": aw,
        "h": 120,
        "font_size": 50,
        "text_align": "left",
    }
    results_elements["after-context"] = {
        "x": ax,
        "y": ay + 204,
        "w": aw,
        "h": 92,
        "font_size": 28,
        "text_align": "left",
    }
    signals_page = pages["why-care"]
    assert isinstance(signals_page, dict)
    signals_elements = signals_page["elements"]
    assert isinstance(signals_elements, dict)
    for index in range(1, 4):
        signal = signals_elements.pop(f"signal-{index}")
        assert isinstance(signal, dict)
        sx = float(signal["x"])
        sy = float(signal["y"])
        sw = float(signal["w"])
        sh = float(signal["h"])
        inset_left = 42 if index == 1 else (0 if index == 2 else 42)
        inset_right = 330 if index == 1 else (42 if index == 2 else 0)
        text_width = sw - inset_left - inset_right
        signals_elements[f"signal-{index}-bg"] = {
            "x": sx,
            "y": sy,
            "w": sw,
            "h": sh,
        }
        signals_elements[f"signal-{index}-label"] = {
            "x": sx + inset_left,
            "y": sy + 36,
            "w": text_width,
            "h": 32,
            "font_size": 25,
            "text_align": "left",
        }
        signals_elements[f"signal-{index}-body"] = {
            "x": sx + inset_left,
            "y": sy + 78,
            "w": text_width,
            "h": 118,
            "font_size": 52,
            "text_align": "left",
        }
        signals_elements[f"signal-{index}-context"] = {
            "x": sx + inset_left,
            "y": sy + 214,
            "w": text_width,
            "h": max(42, sh - 250),
            "font_size": 30,
            "text_align": "left",
        }
    cta_page = pages["cta"]
    assert isinstance(cta_page, dict)
    cta_elements = cta_page["elements"]
    assert isinstance(cta_elements, dict)
    for name in ("thesis", "question"):
        block = cta_elements.pop(name)
        assert isinstance(block, dict)
        bx = float(block["x"])
        by = float(block["y"])
        bw = float(block["w"])
        bh = float(block["h"])
        inset = 42 if name == "thesis" else 54
        body_width = bw - (84 if name == "thesis" else 354)
        cta_elements[f"{name}-bg"] = {
            "x": bx,
            "y": by,
            "w": bw,
            "h": bh,
        }
        cta_elements[f"{name}-label"] = {
            "x": bx + inset,
            "y": by + 34 if name == "thesis" else by + 54,
            "w": body_width,
            "h": 34,
            "font_size": 26,
            "text_align": "left",
        }
        cta_elements[f"{name}-body"] = {
            "x": bx + inset,
            "y": by + 78 if name == "thesis" else by + 105,
            "w": body_width,
            "h": max(70, bh - (110 if name == "thesis" else 255)),
            "font_size": 41 if name == "thesis" else 74,
            "text_align": "left",
        }
    normalized["schema_version"] = 2
    return normalized
