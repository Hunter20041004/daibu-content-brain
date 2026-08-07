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


def test_story_has_four_chapter_structure():
    source = HTML_PATH.read_text(encoding="utf-8")
    parser = StoryParser()
    parser.feed(source)

    assert {"build", "system", "verify", "recipe"} <= parser.ids

    retired = {"collaboration", "system-map", "content-journey", "timeline", "lessons"}
    assert not (retired & parser.ids), f"舊章節仍在：{sorted(retired & parser.ids)}"


def test_story_opens_with_title_and_outcome():
    source = HTML_PATH.read_text(encoding="utf-8")

    assert '<html lang="zh-TW">' in source
    assert "我怎麼用 Vibe Coding 搭出呆一布內容工作站" in source
    assert 'id="hero"' in source
    assert "七張輪播圖" in source
    assert "<svg" in source


def test_story_keeps_tech_notes_and_removed_features():
    source = HTML_PATH.read_text(encoding="utf-8")
    parser = StoryParser()
    parser.feed(source)

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
    # 這幾個數字都要對得上專案紀錄，不能憑印象寫：
    # 24 條問題與 99 個測試出自 docs/history/HANDOFF-2026-07-26-qa-fixes.md，
    # 134 字的草稿消失是那份文件裡第 4 條的原始描述。
    assert "24 個問題" in source
    assert "99 個" in source
    assert "134 字" in source


def _file_url() -> str:
    return HTML_PATH.resolve().as_uri()


def test_hero_states_multi_series_architecture_with_one_series_today():
    source = HTML_PATH.read_text(encoding="utf-8")

    assert "架構上可以跑不同的內容系列" in source
    assert "AI 新創介紹" in source
    # 成品必須被介紹成「某個系列的產出」，不能被寫成這個工具唯一能做的事
    assert "不是這個工具唯一能做的東西" in source


def test_story_quotes_no_raw_conversation():
    """設計決定：不引用任何對話原文。這裡守住最容易被貼回來的幾句。"""
    source = HTML_PATH.read_text(encoding="utf-8")

    for quote in (
        "我不要 薄荷綠",
        "可以 你做吧",
        "我覺得很好",
        "這種手繪風格還不錯",
        "然後我選 Playwright",
        "可以 就先這樣",
    ):
        assert quote not in source, f"文中出現對話原文：{quote}"


def test_carousel_output_images_are_embedded_and_render():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(_file_url())

        images = page.locator('#build img')
        assert images.count() == 7

        srcs = images.evaluate_all("nodes => nodes.map(node => node.getAttribute('src'))")
        assert all(src.startswith("data:image/") for src in srcs), "圖片必須內嵌，分享後才不會失效"

        widths = images.evaluate_all(
            "nodes => nodes.map(node => node.naturalWidth)"
        )
        assert all(width > 0 for width in widths), f"有圖片載入失敗：{widths}"

        alts = images.evaluate_all("nodes => nodes.map(node => node.getAttribute('alt'))")
        assert all(alt and alt.strip() for alt in alts), "每張圖都要有替代文字"

        browser.close()


def test_page_loads_and_interacts_without_console_errors():
    """頁面載入與操作都不能丟錯。舊版曾經同時載入兩套 journey 腳本而不自知。"""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
        page.on(
            "console",
            lambda msg: errors.append(f"console.{msg.type}: {msg.text}")
            if msg.type == "error"
            else None,
        )

        page.goto(_file_url())
        page.wait_for_timeout(600)

        for step in page.locator("[data-journey-step]").all():
            step.click()
        page.locator("details.tech-note").first.locator("summary").click()
        page.wait_for_timeout(300)

        assert not errors, "頁面丟出錯誤：\n" + "\n".join(errors)
        browser.close()


def test_no_horizontal_overflow_at_any_width():
    """雜誌版面讓圖片突出文字欄，中等寬度最容易因此撐出橫向捲動。"""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(_file_url())

        offenders = {}
        for width in (375, 414, 768, 1000, 1024, 1100, 1280, 1440, 1920):
            page.set_viewport_size({"width": width, "height": 900})
            overflow = page.evaluate(
                "document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            if overflow > 0:
                offenders[width] = overflow

        assert not offenders, f"這些寬度出現橫向捲動：{offenders}"
        browser.close()


def test_deep_brand_tones_carry_the_structure():
    """舊版只用了品牌最淡的幾階，整頁沒有重量。深色階必須用在結構上。"""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(_file_url())

        deep = "rgb(36, 74, 91)"  # #244A5B

        heading_color = page.locator("#verify h2").evaluate(
            "el => getComputedStyle(el).color"
        )
        assert heading_color == deep, f"章節標題不是深色階：{heading_color}"

        rule_color = page.locator("#verify .chapter__head").evaluate(
            "el => getComputedStyle(el).borderTopColor"
        )
        assert rule_color == deep, f"章節分隔線不是深色階：{rule_color}"

        fonts = page.evaluate(
            """() => ({
                body: getComputedStyle(document.body).fontFamily,
                heading: getComputedStyle(document.querySelector('h1')).fontFamily,
                mono: getComputedStyle(document.querySelector('.chapter__num')).fontFamily,
            })"""
        )
        assert "Noto Serif TC" in fonts["heading"], fonts["heading"]
        assert "Noto Sans TC" in fonts["body"], fonts["body"]
        assert "JetBrains Mono" in fonts["mono"], fonts["mono"]

        browser.close()


def test_output_gallery_is_asymmetric_not_an_equal_card_grid():
    """spec 明訂不使用等大卡片網格；成品圖用雜誌式的主圖加小圖。"""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(_file_url())

        lead = page.locator("#build .carousel-out__lead img").evaluate(
            "el => el.getBoundingClientRect().width"
        )
        rest = page.locator("#build .carousel-out__rest img").first.evaluate(
            "el => el.getBoundingClientRect().width"
        )
        assert lead > rest * 1.4, f"主圖沒有明顯大於其他圖：{lead} vs {rest}"

        browser.close()


def test_before_after_comparison_is_side_by_side_then_stacks():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(_file_url())

        figures = page.locator("#verify .compare figure")
        assert figures.count() == 2

        images = page.locator("#verify .compare img")
        widths = images.evaluate_all("nodes => nodes.map(node => node.naturalWidth)")
        assert all(width > 0 for width in widths), f"對照圖載入失敗：{widths}"

        boxes = figures.evaluate_all(
            "nodes => nodes.map(node => node.getBoundingClientRect())"
        )
        assert boxes[0]["top"] == boxes[1]["top"], "桌機時兩張要並排"
        assert boxes[0]["left"] < boxes[1]["left"]

        page.set_viewport_size({"width": 375, "height": 812})
        stacked = figures.evaluate_all(
            "nodes => nodes.map(node => node.getBoundingClientRect())"
        )
        assert stacked[1]["top"] > stacked[0]["top"], "手機時要上下堆疊"

        overflow = page.evaluate(
            "document.documentElement.scrollWidth - document.documentElement.clientWidth"
        )
        assert overflow <= 0, f"手機出現橫向捲動：溢出 {overflow}px"

        browser.close()


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
