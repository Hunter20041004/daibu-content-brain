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


def _open_results(editor):
    editor.get_by_role(
        "button", name=f"05 {card_pages.label('results')}"
    ).dispatch_event("click")
    expect(
        editor.locator('.template-document article[data-page-type="results"]')
    ).to_be_attached(timeout=15_000)


def test_six_page_template_editor_exposes_every_registered_layout_hook(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15_000)

            for page_index, page_type in enumerate(card_pages.PAGE_TYPES, start=1):
                if page_index > 1:
                    editor.get_by_role(
                        "button", name=f"{page_index:02d} {card_pages.label(page_type)}"
                    ).dispatch_event("click")
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


def test_results_background_has_no_font_control_but_title_changes_only_itself(
    tmp_path,
):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15_000)
            _open_results(editor)
            background = editor.locator(
                '.template-document [data-layout-id="before-bg"]'
            )
            background.click(position={"x": 10, "y": 10})
            expect(
                editor.locator(
                    '[data-role="property-panel"] input[name="font_size"]'
                )
            ).to_have_count(0)
            title = editor.locator(
                '.template-document [data-layout-id="before-title"]'
            )
            body = editor.locator(
                '.template-document [data-layout-id="before-text"]'
            )
            body_size = body.evaluate("el => getComputedStyle(el).fontSize")
            title.click(position={"x": 10, "y": 10})
            font = editor.locator(
                '[data-role="property-panel"] input[name="font_size"]'
            )
            font.fill("41")
            font.press("Tab")
            expect(title).to_have_css("font-size", "41px")
            assert body.evaluate("el => getComputedStyle(el).fontSize") == body_size
            browser.close()


def test_results_background_drag_does_not_move_its_title(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15_000)
            _open_results(editor)
            background = editor.locator(
                '.template-document [data-layout-id="before-bg"]'
            )
            title = editor.locator(
                '.template-document [data-layout-id="before-title"]'
            )
            background.click(position={"x": 6, "y": 6})
            title_before = title.bounding_box()
            background_box = background.bounding_box()
            page.mouse.move(background_box["x"] + 6, background_box["y"] + 6)
            page.mouse.down()
            page.mouse.move(background_box["x"] + 26, background_box["y"] + 6)
            page.mouse.up()

            title_after = title.bounding_box()
            assert title_after["x"] == title_before["x"]
            assert title_after["y"] == title_before["y"]
            assert float(
                editor.locator(
                    '[data-role="property-panel"] input[name="x"]'
                ).input_value()
            ) > 153
            browser.close()


def test_results_title_undo_redo_and_escape_preserve_only_committed_change(
    tmp_path,
):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15_000)
            _open_results(editor)
            title = editor.locator(
                '.template-document [data-layout-id="before-title"]'
            )
            title.click(position={"x": 10, "y": 10})
            x_input = editor.locator(
                '[data-role="property-panel"] input[name="x"]'
            )
            original = float(x_input.input_value())
            changed = original + 8
            x_input.fill(str(changed))
            x_input.press("Tab")
            editor.get_by_role("button", name="復原").click()
            expect(x_input).to_have_value(str(int(original)))
            editor.get_by_role("button", name="重做").click()
            expect(x_input).to_have_value(str(int(changed)))

            box = title.bounding_box()
            page.mouse.move(box["x"] + 10, box["y"] + 10)
            page.mouse.down()
            page.mouse.move(box["x"] + 40, box["y"] + 10)
            page.keyboard.press("Escape")
            page.mouse.up()
            expect(x_input).to_have_value(str(int(changed)))
            browser.close()


def test_schema_v3_session_copy_is_ignored_after_v4_upgrade(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.add_init_script(
                """() => sessionStorage.setItem(
                  'daibu-template-1-1',
                  JSON.stringify({
                    schemaIdentity: '3:legacy',
                    state: {
                      past: [], future: [], selected: 'before', dirty: true,
                      guides: [], present: {schema_version: 3, pages: {}}
                    }
                  })
                )"""
            )
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15_000)
            _open_results(editor)

            expect(
                editor.locator(
                    '.template-document [data-layout-id="before-bg"]'
                )
            ).to_have_count(1)
            expect(
                editor.locator('.template-document [data-layout-id="before"]')
            ).to_have_count(0)
            expect(editor.locator(".property-title")).to_have_text("選擇一個元素")
            expect(editor.get_by_role("button", name="儲存為新版本")).to_be_disabled()
            browser.close()


def test_template_save_persists_schema_v4_as_an_inactive_version(tmp_path):
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
            assert row["schema_version"] == 4
            assert json.loads(row["layout_json"])["schema_version"] == 4
            active_version_id = conn.execute(
                "SELECT active_version_id FROM carousel_template_settings"
            ).fetchone()[0]
            assert active_version_id == 1
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
