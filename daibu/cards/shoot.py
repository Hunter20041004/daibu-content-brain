import tempfile
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from daibu.cards import render
from daibu.cards.schema import BrandAsset, CarouselDraft, validate_draft

WIDTH = 1080
HEIGHT = 1350


@dataclass(frozen=True)
class LayoutReport:
    canvas_overflow: bool
    content_overflow: bool
    source_bottom: float
    logo_visible: bool


def _open_html(page: Page, path: Path) -> None:
    page.goto(path.as_uri(), wait_until="load")
    page.evaluate("() => document.fonts.ready")
    fonts_loaded = page.evaluate(
        """() => [400, 700, 800].every(
            weight => document.fonts.check(`${weight} 32px "LINE Seed TW"`)
        )"""
    )
    if not fonts_loaded:
        raise RuntimeError("LINE Seed TW bundled fonts failed to load")


def _report(page: Page) -> LayoutReport:
    raw = page.evaluate(
        """() => {
          const canvas = document.querySelector(".canvas");
          const card = document.querySelector(".card");
          const source = document.querySelector(".source-label");
          const logo = document.querySelector(".company-logo");
          const children = [...card.querySelectorAll("*")];
          const cardRect = card.getBoundingClientRect();
          return {
            canvasOverflow:
              canvas.scrollWidth > canvas.clientWidth ||
              canvas.scrollHeight > canvas.clientHeight,
            contentOverflow: children.some((element) => {
              const rect = element.getBoundingClientRect();
              return rect.right > cardRect.right + 1 ||
                     rect.bottom > cardRect.bottom + 1 ||
                     rect.left < cardRect.left - 1;
            }),
            sourceBottom: source ? source.getBoundingClientRect().bottom : 0,
            logoVisible: Boolean(
              logo && logo.getBoundingClientRect().width > 20 &&
              logo.getBoundingClientRect().height > 20
            ),
          };
        }"""
    )
    return LayoutReport(
        raw["canvasOverflow"],
        raw["contentOverflow"],
        float(raw["sourceBottom"]),
        raw["logoVisible"],
    )


def carousel_pngs(
    draft: CarouselDraft,
    company: str,
    brand_asset: BrandAsset | None,
) -> list[bytes]:
    validate_draft(draft)
    html_pages = [
        render.page_html(page, company, brand_asset) for page in draft.pages
    ]
    outputs = []
    with tempfile.TemporaryDirectory() as directory:
        paths = []
        for index, html_text in enumerate(html_pages, start=1):
            path = Path(directory) / f"{index:02d}.html"
            path.write_text(html_text, encoding="utf-8")
            paths.append(path)
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            try:
                page = browser.new_page(
                    viewport={"width": WIDTH, "height": HEIGHT},
                    device_scale_factor=1,
                )
                for path in paths:
                    _open_html(page, path)
                    report = _report(page)
                    if report.canvas_overflow or report.content_overflow:
                        raise RuntimeError(f"輪播內容超出版面：{path.name}")
                    outputs.append(
                        page.locator(".canvas").screenshot(type="png")
                    )
            finally:
                browser.close()
    return outputs


def inspect_html(html_text: str) -> LayoutReport:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "card.html"
        path.write_text(html_text, encoding="utf-8")
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            try:
                page = browser.new_page(
                    viewport={"width": WIDTH, "height": HEIGHT}
                )
                _open_html(page, path)
                return _report(page)
            finally:
                browser.close()


def png_bytes(html_text: str) -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "card.html"
        path.write_text(html_text, encoding="utf-8")
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            try:
                page = browser.new_page(
                    viewport={"width": WIDTH, "height": HEIGHT}
                )
                _open_html(page, path)
                return page.locator(".canvas").screenshot(type="png")
            finally:
                browser.close()
