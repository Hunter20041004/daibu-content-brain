from pathlib import Path
from html.parser import HTMLParser


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
