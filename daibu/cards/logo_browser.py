"""Read Logo references that only exist after a public site renders."""

from collections.abc import Callable
from dataclasses import dataclass

from playwright.sync_api import sync_playwright


BACKGROUND_JS = r"""
nodes => nodes.flatMap(node => {
  const style = getComputedStyle(node);
  const match = style.backgroundImage.match(/url\(["']?(.*?)["']?\)/);
  if (!match || node.getClientRects().length === 0) return [];
  const description = [node.id, node.className, node.getAttribute('aria-label')]
    .filter(Boolean).join(' ');
  if (!/(logo|brand)/i.test(description) && !node.closest('a[href="/"]')) return [];
  return [[new URL(match[1], document.baseURI).href, description]];
})
"""


@dataclass(frozen=True)
class RenderedPage:
    html: str
    background_assets: tuple[tuple[str, str], ...]


def render_site(
    url: str,
    *,
    timeout_ms: int = 15_000,
    playwright_factory: Callable[..., object] = sync_playwright,
) -> RenderedPage:
    """Render one public page and return its DOM plus visible brand backgrounds."""
    with playwright_factory() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )
            page.wait_for_timeout(300)
            html = page.content()
            backgrounds = tuple(
                tuple(item)
                for item in page.locator("header *, nav *").evaluate_all(
                    BACKGROUND_JS
                )
            )
            return RenderedPage(html, backgrounds)
        finally:
            browser.close()
