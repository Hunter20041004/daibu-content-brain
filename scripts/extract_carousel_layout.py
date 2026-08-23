from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Mapping

from playwright.sync_api import Page, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from daibu.cards.layout_registry import ELEMENT_REGISTRY


CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1350

SELECTORS: Mapping[str, Mapping[str, str]] = {
    "cover": {
        "series": ".series",
        "company-logo": ".cover-logo-v151",
        "company-name": ".cover-word",
        "heading": "h2",
        "rule": ".cover-line",
        "positioning": ".cover-copy",
        "mascot": ".mascot",
    },
    "who": {
        "header": ".post-head",
        "heading": ".post-title",
        "positioning": ".profile-main-v15",
        "facts": ".profile-detail-v15",
        "mascot": ".mascot",
    },
    "problem": {
        "header": ".post-head",
        "heading": ".post-title",
        "spine": ".problem-spine-v15",
        "stage-1": ".problem-stage-v15:nth-of-type(1)",
        "stage-2": ".problem-stage-v15:nth-of-type(2)",
        "stage-3": ".problem-stage-v15:nth-of-type(3)",
        "mascot": ".mascot",
    },
    "how-ai": {
        "header": ".post-head",
        "heading": ".post-title",
        "spine": ".how-spine-v15",
        "step-1": ".how-step-v15:nth-of-type(1)",
        "step-2": ".how-step-v15:nth-of-type(2)",
        "step-3": ".how-step-v15:nth-of-type(3)",
        "caution": ".how-caution-v15",
        "mascot": ".mascot",
    },
    "results": {
        "header": ".post-head",
        "before-title": ".results-before-v15 .result-title-v15",
        "before-copy": ".results-before-v15 .result-copy-v15",
        "axis": ".result-axis-v15",
        "to": ".result-to-v15",
        "after-title": ".results-after-v15 .result-title-v15",
        "after-copy": ".results-after-v15 .result-copy-v15",
        "summary": ".result-summary-v15",
        "mascot": ".mascot",
    },
    "why-care": {
        "header": ".post-head",
        "heading": ".post-title",
        "signal-1": ".signal-primary-v15",
        "signal-2": ".signal-secondary-v15:nth-child(1)",
        "signal-3": ".signal-secondary-v15:nth-child(2)",
        "mascot": ".mascot",
    },
    "cta": {
        "header": ".post-head",
        "heading": ".post-title",
        "thesis": ".closing-lead-v15",
        "question": ".closing-question-v15",
        "invitation": ".closing-cta-v15",
        "mascot": ".mascot",
    },
}


def _localize_assets(source: str, asset_root: Path) -> str:
    replacements = {
        "/files/line-rg.otf": asset_root / "fonts" / "LINESeedTW_OTF_Rg.otf",
        "/files/line-bd.otf": asset_root / "fonts" / "LINESeedTW_OTF_Bd.otf",
        "/files/line-eb.otf": asset_root / "fonts" / "LINESeedTW_OTF_Eb.otf",
        "/files/mascot-point.svg": asset_root / "mascot" / "point.svg",
        "/files/mascot-note.svg": asset_root / "mascot" / "note.svg",
    }
    localized = source
    for remote_path, local_path in replacements.items():
        if not local_path.is_file():
            raise FileNotFoundError(local_path)
        localized = localized.replace(remote_path, local_path.resolve().as_uri())
    localized = localized.replace(
        "/files/mascot-${pose}.svg",
        f"{(asset_root / 'mascot').resolve().as_uri()}/${{pose}}.svg",
    )
    return localized.replace(
        '<script src="/files/editorial-v15-contract.js"></script>',
        "",
    )


def _measure_page(page: Page, page_index: int, page_type: str) -> dict[str, object]:
    post = page.locator(
        f"#companyView .cards .frame:nth-child({page_index}) .post"
    )
    post_box = post.bounding_box()
    if post_box is None:
        raise RuntimeError(f"找不到 {page_type} 頁畫布")
    scale_x = CANVAS_WIDTH / post_box["width"]
    scale_y = CANVAS_HEIGHT / post_box["height"]

    elements: dict[str, object] = {}
    for element_id, selector in SELECTORS[page_type].items():
        locator = post.locator(selector)
        if locator.count() != 1:
            raise RuntimeError(
                f"{page_type}.{element_id} selector 應命中 1 個元素，實際為 {locator.count()}"
            )
        box = locator.bounding_box()
        if box is None:
            raise RuntimeError(f"{page_type}.{element_id} 沒有可量測矩形")
        element: dict[str, object] = {
            "x": round((box["x"] - post_box["x"]) * scale_x, 3),
            "y": round((box["y"] - post_box["y"]) * scale_y, 3),
            "w": round(box["width"] * scale_x, 3),
            "h": round(box["height"] * scale_y, 3),
        }
        rule = ELEMENT_REGISTRY[page_type][element_id]
        if rule.text:
            computed = locator.evaluate(
                "element => ({fontSize: getComputedStyle(element).fontSize, "
                "textAlign: getComputedStyle(element).textAlign})"
            )
            element["font_size"] = round(
                float(computed["fontSize"].removesuffix("px")) * scale_x,
                3,
            )
            element["text_align"] = {
                "start": "left",
                "end": "right",
            }.get(computed["textAlign"], computed["textAlign"])
        elements[element_id] = element
    return {"elements": elements}


def extract_layout(source_path: Path, asset_root: Path) -> dict[str, object]:
    source = _localize_assets(source_path.read_text(encoding="utf-8"), asset_root)
    with TemporaryDirectory() as directory:
        prototype_path = Path(directory) / "prototype.html"
        prototype_path.write_text(source, encoding="utf-8")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                args=["--allow-file-access-from-files"]
            )
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(prototype_path.as_uri(), wait_until="load")
            page.add_style_tag(
                content=(
                    "*,*::before,*::after{"
                    "animation:none!important;transition:none!important}"
                )
            )
            page.evaluate("renderCompany('sun')")
            page.locator("#companyView .cards .frame").nth(6).wait_for()
            page.wait_for_function(
                "[...document.querySelectorAll('#companyView img')].every("
                "image => image.complete && image.naturalWidth > 0)"
            )
            page.evaluate("document.fonts.ready")
            pages = {
                page_type: _measure_page(page, index, page_type)
                for index, page_type in enumerate(SELECTORS, start=1)
            }
            browser.close()
    return {
        "schema_version": 1,
        "canvas": {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT},
        "pages": pages,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--asset-root",
        type=Path,
        default=PROJECT_ROOT / "assets",
    )
    args = parser.parse_args()

    layout = extract_layout(args.source, args.asset_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(layout, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
