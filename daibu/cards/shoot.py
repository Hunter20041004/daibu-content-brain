import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

WIDTH = 1080
HEIGHT = 1350


def png_bytes(html_text: str) -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        html_path = Path(directory) / "card.html"
        html_path.write_text(html_text, encoding="utf-8")

        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            try:
                page = browser.new_page(
                    viewport={"width": WIDTH, "height": HEIGHT},
                    device_scale_factor=1,
                )
                page.goto(html_path.as_uri(), wait_until="load")
                page.evaluate("() => document.fonts.ready")
                fonts_loaded = page.evaluate(
                    """() => [400, 700, 800].every(
                        weight => document.fonts.check(
                            `${weight} 32px "LINE Seed TW"`
                        )
                    )"""
                )
                if not fonts_loaded:
                    raise RuntimeError("LINE Seed TW bundled fonts failed to load")
                return page.locator(".canvas").screenshot(type="png")
            finally:
                browser.close()
