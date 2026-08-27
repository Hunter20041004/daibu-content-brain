import json

from playwright.sync_api import expect, sync_playwright

from daibu import db
from daibu.cards import pages as card_pages
from daibu.cards.layout_registry import ELEMENT_REGISTRY
from daibu.models import Theme
from tests.browser_support import running_streamlit


def _seed(database_path, logo_path):
    del logo_path
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(conn, Theme(None, "AI 新創介紹", 4, [], 1, "company_profile"))


def test_six_page_template_editor_exposes_every_registered_layout_hook(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15_000)

            for page_index, page_type in enumerate(card_pages.PAGE_TYPES, start=1):
                editor.get_by_role(
                    "button", name=f"{page_index:02d} {card_pages.label(page_type)}"
                ).click()
                expect(
                    editor.locator(
                        f'.template-document article[data-page-type="{page_type}"]'
                    )
                ).to_be_attached(timeout=15_000)
                for element_id in ELEMENT_REGISTRY[page_type]:
                    assert editor.locator(
                        f'.template-document [data-layout-id="{element_id}"]'
                    ).count() == 1
            browser.close()


def test_template_canvas_drag_syncs_company_name_without_saving(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15_000)
            actual = editor.locator(
                '.template-document [data-layout-id="company-name"]'
            )
            actual.click(position={"x": 20, "y": 20})
            x_input = editor.locator('[data-role="property-panel"] input[name="x"]')
            before = float(x_input.input_value())
            box = editor.locator(".selection-box").bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(box["x"] + box["width"] / 2 + 16, box["y"] + box["height"] / 2)
            page.mouse.up()
            assert float(x_input.input_value()) > before
            conn = db.connect(str(tmp_path / "browser.db"))
            assert conn.execute(
                "SELECT COUNT(*) FROM carousel_template_versions"
            ).fetchone()[0] == 1
            browser.close()


def test_template_save_persists_schema_v3_as_an_inactive_version(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15_000)
            actual = editor.locator(
                '.template-document [data-layout-id="company-name"]'
            )
            actual.click(position={"x": 20, "y": 20})
            x_input = editor.locator('[data-role="property-panel"] input[name="x"]')
            x_input.fill(str(float(x_input.input_value()) + 8))
            x_input.press("Tab")
            editor.get_by_role("button", name="儲存為新版本").click()
            expect(page.get_by_label("模板版本")).to_have_value(
                "v2 · 尚未啟用", timeout=60_000
            )
            conn = db.connect(str(tmp_path / "browser.db"))
            row = conn.execute(
                "SELECT schema_version, layout_json FROM carousel_template_versions "
                "WHERE version_no = 2"
            ).fetchone()
            assert row["schema_version"] == 3
            assert json.loads(row["layout_json"])["schema_version"] == 3
            browser.close()


def test_template_editor_mobile_is_read_only_without_overflow(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 375, "height": 812})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            expect(page.get_by_text("請改用桌面寬度調整模板", exact=False)).to_be_visible(
                timeout=15_000
            )
            assert page.evaluate("document.documentElement.scrollWidth") == 375
            expect(page.locator(".overlay-layer")).to_be_hidden()
            browser.close()
