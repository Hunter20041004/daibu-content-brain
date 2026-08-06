import re
from html.parser import HTMLParser
from pathlib import Path

from playwright.sync_api import sync_playwright


HTML_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "2026-08-05-我怎麼用-vibe-coding-搭出呆一布內容工作站.html"
)


class StoryParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.tech_terms = set()
        self.removed_features = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        if attributes.get("data-tech"):
            self.tech_terms.add(attributes["data-tech"])
        if attributes.get("data-removed-feature"):
            self.removed_features.add(attributes["data-removed-feature"])


def test_story_opens_with_problem_and_product_outcome():
    source = HTML_PATH.read_text(encoding="utf-8")

    assert '<html lang="zh-TW">' in source
    assert "我怎麼用 Vibe Coding 搭出呆一布內容工作站" in source
    assert 'id="problem"' in source
    assert "找題材" in source
    assert "七張輪播圖" in source
    assert "<svg" in source


def test_story_contains_complete_build_journey_and_plain_language_notes():
    source = HTML_PATH.read_text(encoding="utf-8")
    parser = StoryParser()
    parser.feed(source)

    assert {
        "problem",
        "collaboration",
        "system-map",
        "content-journey",
        "timeline",
        "testing",
        "lessons",
        "recipe",
    } <= parser.ids
    assert {
        "Streamlit",
        "Python",
        "SQLite",
        "RSS",
        "Tavily",
        "Gemini",
        "Playwright",
        "TDD",
        "Mock",
        "契約測試",
    } <= parser.tech_terms
    assert {"守門線", "來源分層", "常青時效分類"} <= parser.removed_features
    assert "先說想要什麼，再讓 AI 幫我拆成可以驗收的小步驟" in source
    assert "99 個測試都通過，實際操作仍找到 24 個問題" in source


def _file_url() -> str:
    return HTML_PATH.resolve().as_uri()


def test_story_interactions_update_without_reload():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(_file_url())

        draft_step = page.locator('[data-journey-step="draft"]')
        draft_step.click()

        assert draft_step.get_attribute("aria-selected") == "true"
        assert "AI 正文" in page.locator("#journey-detail").inner_text()
        first_note = page.locator("details.tech-note").first
        first_note.locator("summary").click()
        assert first_note.get_attribute("open") == ""
        assert page.locator("#vt-comment-trigger").count() == 1
        browser.close()


def test_story_mobile_layout_focus_and_reduced_motion():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 375, "height": 812})
        page.goto(_file_url())

        overflow = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        assert overflow <= 0
        heights = page.locator("button").evaluate_all(
            "buttons => buttons.map(button => button.getBoundingClientRect().height).filter(height => height > 0)"
        )
        assert heights and min(heights) >= 44
        first_step = page.locator("[data-journey-step]").first
        first_step.focus()
        assert first_step.evaluate("el => getComputedStyle(el).outlineStyle") != "none"
        page.emulate_media(reduced_motion="reduce")
        assert page.locator("body").evaluate(
            "el => getComputedStyle(el).getPropertyValue('--motion-distance').trim()"
        ) == "0px"
        browser.close()


def test_story_contains_no_secrets_placeholders_or_local_links():
    source = HTML_PATH.read_text(encoding="utf-8")

    assert not re.search(r"(?:GEMINI|GROQ|TAVILY)_API_KEY\s*=", source)
    assert "/Users/" not in source
    assert "file:///" not in source
    assert not re.search(r"\b(?:TBD|TODO|Lorem ipsum|__TITLE__)\b", source)
    assert "window.vtCollectComments = function" in source
    assert 'id="vt-comment-trigger"' in source
