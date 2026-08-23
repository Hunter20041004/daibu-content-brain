import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from playwright.sync_api import sync_playwright

from daibu.cards import pages
from daibu.cards.layout_registry import ELEMENT_REGISTRY, ElementRule


@dataclass(frozen=True)
class LayoutIssue:
    page_type: str
    element_id: str
    code: str
    message: str


def _page_number(page_type: str) -> int:
    try:
        return pages.PAGE_TYPES.index(page_type) + 1
    except ValueError as error:
        raise ValueError(f"未知頁型：{page_type}") from error


def _measure(html_text: str) -> list[dict[str, object]]:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "layout.html"
        path.write_text(html_text, encoding="utf-8")
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            try:
                page = browser.new_page(
                    viewport={"width": 1080, "height": 1350},
                    device_scale_factor=1,
                )
                page.goto(path.as_uri(), wait_until="load")
                page.evaluate("() => document.fonts.ready")
                return page.evaluate(
                    """() => {
                      const canvas = document.querySelector(
                        ".carousel-canvas"
                      );
                      if (!canvas) throw new Error("missing carousel canvas");
                      const canvasRect = canvas.getBoundingClientRect();
                      return [...canvas.querySelectorAll(
                        "[data-layout-id]"
                      )].map((element) => {
                        const rect = element.getBoundingClientRect();
                        const style = getComputedStyle(element);
                        const image = element.querySelector("img");
                        const imageRect = image?.getBoundingClientRect();
                        const range = document.createRange();
                        range.selectNodeContents(element);
                        const lineTops = [];
                        for (const lineRect of range.getClientRects()) {
                          if (lineRect.width <= 0 || lineRect.height <= 0) continue;
                          if (!lineTops.some(
                            top => Math.abs(top - lineRect.top) <= 1
                          )) lineTops.push(lineRect.top);
                        }
                        return {
                          id: element.dataset.layoutId,
                          left: rect.left - canvasRect.left,
                          top: rect.top - canvasRect.top,
                          right: rect.right - canvasRect.left,
                          bottom: rect.bottom - canvasRect.top,
                          width: rect.width,
                          height: rect.height,
                          clientWidth: element.clientWidth,
                          clientHeight: element.clientHeight,
                          scrollWidth: element.scrollWidth,
                          scrollHeight: element.scrollHeight,
                          fontSize: Number.parseFloat(style.fontSize),
                          ariaHidden:
                            element.getAttribute("aria-hidden") === "true",
                          visible:
                            style.display !== "none" &&
                            style.visibility !== "hidden" &&
                            Number(style.opacity) > 0 &&
                            rect.width > 1 && rect.height > 1 &&
                            (!image || (
                              image.complete && image.naturalWidth > 0 &&
                              imageRect.width > 1 && imageRect.height > 1
                            )),
                          visualLines: lineTops.length,
                        };
                      });
                    }"""
                )
            finally:
                browser.close()


def visual_line_count(html_text: str, element_id: str) -> int:
    for item in _measure(html_text):
        if item["id"] == element_id:
            return int(item["visualLines"])
    raise ValueError(f"畫面缺少版面元素：{element_id}")


def _overflow_issue(
    page_type: str,
    element_id: str,
    rule: ElementRule,
) -> LayoutIssue:
    page_number = _page_number(page_type)
    return LayoutIssue(
        page_type,
        element_id,
        "text-overflow",
        f"第 {page_number} 頁「{rule.label}」文字超出文字框",
    )


def _bounds_issue(
    page_type: str,
    element_id: str,
    rule: ElementRule,
) -> LayoutIssue:
    page_number = _page_number(page_type)
    return LayoutIssue(
        page_type,
        element_id,
        "out-of-canvas",
        f"第 {page_number} 頁「{rule.label}」超出 1080×1350 畫布",
    )


def _visibility_issue(
    page_type: str,
    element_id: str,
    rule: ElementRule,
) -> LayoutIssue:
    page_number = _page_number(page_type)
    return LayoutIssue(
        page_type,
        element_id,
        "not-visible",
        f"第 {page_number} 頁「{rule.label}」在畫面上不可見",
    )


def _collision_issue(
    page_type: str,
    element_id: str,
    label: str,
    other_label: str,
) -> LayoutIssue:
    page_number = _page_number(page_type)
    return LayoutIssue(
        page_type,
        element_id,
        "collision",
        f"第 {page_number} 頁「{label}」與「{other_label}」發生碰撞",
    )


def _intersects(left: dict[str, object], right: dict[str, object]) -> bool:
    return (
        float(left["left"]) < float(right["right"]) - 1
        and float(left["right"]) > float(right["left"]) + 1
        and float(left["top"]) < float(right["bottom"]) - 1
        and float(left["bottom"]) > float(right["top"]) + 1
    )


def inspect_layout(
    html_text: str,
    page_type: str,
    registry=ELEMENT_REGISTRY,
) -> tuple[LayoutIssue, ...]:
    if page_type not in registry:
        raise ValueError(f"未知頁型：{page_type}")
    measured = {str(item["id"]): item for item in _measure(html_text)}
    issues = []
    for element_id, rule in registry[page_type].items():
        item = measured.get(element_id)
        if item is None:
            issues.append(_visibility_issue(page_type, element_id, rule))
            continue
        if not item["visible"]:
            issues.append(_visibility_issue(page_type, element_id, rule))
            continue
        if (
            float(item["left"]) < -1
            or float(item["top"]) < -1
            or float(item["right"]) > 1081
            or float(item["bottom"]) > 1351
        ):
            issues.append(_bounds_issue(page_type, element_id, rule))
        if not rule.text or item["ariaHidden"]:
            continue
        horizontal_overflow = float(item["scrollWidth"]) > (
            float(item["clientWidth"]) + 1
        )
        vertical_overflow = float(item["scrollHeight"]) > (
            float(item["clientHeight"])
            + max(2, float(item["fontSize"]) * 0.4)
        )
        max_title_lines = 3 if page_type == "cover" else 2
        too_many_title_lines = (
            "標題" in rule.label
            and int(item["visualLines"]) > max_title_lines
        )
        if horizontal_overflow or vertical_overflow or too_many_title_lines:
            issues.append(_overflow_issue(page_type, element_id, rule))
    avoid_elements = (
        (element_id, rule, measured.get(element_id))
        for element_id, rule in registry[page_type].items()
        if rule.collision == "avoid"
    )
    visible_avoid_elements = tuple(
        (element_id, rule, item)
        for element_id, rule, item in avoid_elements
        if item is not None and item["visible"]
    )
    for (left_id, left_rule, left), (right_id, right_rule, right) in combinations(
        visible_avoid_elements,
        2,
    ):
        if _intersects(left, right):
            issues.append(
                _collision_issue(
                    page_type,
                    right_id,
                    right_rule.label,
                    left_rule.label,
                )
            )
    return tuple(issues)


def validate_rendered_pages(pages_html: Mapping[str, str]) -> None:
    for page_type, html_text in pages_html.items():
        issues = inspect_layout(html_text, page_type)
        if issues:
            raise RuntimeError(issues[0].message)
