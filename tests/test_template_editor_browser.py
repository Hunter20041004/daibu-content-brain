import json

from playwright.sync_api import expect, sync_playwright

from daibu import db
from daibu.models import Theme
from tests.browser_support import running_streamlit


def _seed(database_path,logo_path):
    del logo_path
    conn=db.connect(str(database_path));db.init_schema(conn)
    db.add_theme(conn,Theme(None,"AI 新創介紹",4,[],1,"company_profile"))


def test_template_canvas_drag_syncs_property_without_saving(tmp_path):
    with running_streamlit(tmp_path,_seed) as base_url:
        with sync_playwright() as driver:
            browser=driver.chromium.launch();page=browser.new_page(viewport={"width":1280,"height":900})
            page.goto(f"{base_url}/設定",wait_until="networkidle")
            editor=page.locator('[data-role="template-editor"]');expect(editor).to_be_visible(timeout=15000)
            actual=editor.locator('.template-document [data-layout-id="heading"]')
            actual.click(position={"x":20,"y":20})
            x_input=editor.locator('[data-role="property-panel"] input[name="x"]')
            before=float(x_input.input_value());box=editor.locator('.selection-box')
            actual_before=actual.bounding_box();box_before=box.bounding_box()
            page.mouse.move(box_before["x"]+box_before["width"]/2,box_before["y"]+box_before["height"]/2)
            page.mouse.down();page.mouse.move(box_before["x"]+box_before["width"]/2+16,box_before["y"]+box_before["height"]/2)
            actual_during=actual.bounding_box();box_during=box.bounding_box()
            actual_dx=actual_during["x"]-actual_before["x"]
            box_dx=box_during["x"]-box_before["x"]
            assert actual_dx>0
            assert abs(actual_dx-box_dx)<=1
            page.mouse.up()
            expect(x_input).not_to_have_value(str(before))
            conn=db.connect(str(tmp_path/"browser.db"))
            assert conn.execute("SELECT COUNT(*) FROM carousel_template_versions").fetchone()[0]==1
            browser.close()


def test_template_property_x_moves_actual_element_and_selection_together(
    tmp_path,
):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15000)
            actual = editor.locator(
                '.template-document [data-layout-id="heading"]'
            )
            actual.click(position={"x": 20, "y": 20})
            box = editor.locator(".selection-box")
            actual_before = actual.bounding_box()
            box_before = box.bounding_box()
            x_input = editor.locator(
                '[data-role="property-panel"] input[name="x"]'
            )
            x_input.fill(str(float(x_input.input_value()) + 40))
            x_input.press("Tab")
            actual_after = actual.bounding_box()
            box_after = box.bounding_box()
            actual_dx = actual_after["x"] - actual_before["x"]
            box_dx = box_after["x"] - box_before["x"]
            assert actual_dx > 0
            assert abs(actual_dx - box_dx) <= 1
            browser.close()


def test_who_facts_body_font_size_updates_the_real_text_node(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15000)
            editor.get_by_role("button", name="02 公司身分卡").click()
            expect(
                editor.locator(
                    '.template-document [data-layout-id="facts-body"]'
                )
            ).to_be_visible(timeout=15000)
            actual = editor.locator(
                '.template-document [data-layout-id="facts-body"]'
            )
            actual.click(position={"x": 20, "y": 20})
            before = float(
                actual.evaluate(
                    "element => getComputedStyle(element).fontSize.slice(0, -2)"
                )
            )
            font_input = editor.locator(
                '[data-role="property-panel"] input[name="font_size"]'
            )
            font_input.fill(str(float(font_input.input_value()) + 8))
            font_input.press("Tab")
            after = float(
                actual.evaluate(
                    "element => getComputedStyle(element).fontSize.slice(0, -2)"
                )
            )
            assert after == before + 8
            actual_box = actual.bounding_box()
            selection_box = editor.locator(".selection-box").bounding_box()
            for field in ("x", "y", "width", "height"):
                assert abs(actual_box[field] - selection_box[field]) <= 1
            browser.close()


def test_moving_who_label_does_not_move_its_body_or_background(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15000)
            editor.get_by_role("button", name="02 公司身分卡").click()
            label = editor.locator(
                '.template-document [data-layout-id="facts-label"]'
            )
            body = editor.locator(
                '.template-document [data-layout-id="facts-body"]'
            )
            background = editor.locator(
                '.template-document [data-layout-id="facts-bg"]'
            )
            expect(label).to_be_visible(timeout=15000)
            body_before = body.bounding_box()
            background_before = background.bounding_box()
            label_before = label.bounding_box()

            label.click(position={"x": 10, "y": 10})
            x_input = editor.locator(
                '[data-role="property-panel"] input[name="x"]'
            )
            x_input.fill(str(float(x_input.input_value()) + 24))
            x_input.press("Tab")

            label_after = label.bounding_box()
            body_after = body.bounding_box()
            background_after = background.bounding_box()
            assert label_after["x"] > label_before["x"]
            assert body_after == body_before
            assert background_after == background_before
            browser.close()


def test_template_canvas_resize_undo_and_redo_keep_opposite_anchor(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15000)
            actual = editor.locator(
                '.template-document [data-layout-id="heading"]'
            )
            actual.click(position={"x": 20, "y": 20})
            actual_before = actual.bounding_box()
            width_input = editor.locator(
                '[data-role="property-panel"] input[name="w"]'
            )
            before = float(width_input.input_value())
            handle = editor.locator('.resize-handle[data-handle="se"]')
            bounds = handle.bounding_box()
            page.mouse.move(bounds["x"] + 3, bounds["y"] + 3)
            page.mouse.down()
            page.mouse.move(bounds["x"] + 19, bounds["y"] + 19)
            page.mouse.up()
            resized = float(width_input.input_value())
            assert resized > before
            actual_resized = actual.bounding_box()
            assert actual_resized["width"] > actual_before["width"]
            editor.get_by_role("button", name="復原").click()
            expect(width_input).to_have_value(str(before))
            actual_undone = actual.bounding_box()
            assert abs(
                actual_undone["width"] - actual_before["width"]
            ) <= 1
            editor.get_by_role("button", name="重做").click()
            assert float(width_input.input_value()) == resized
            actual_redone = actual.bounding_box()
            assert abs(
                actual_redone["width"] - actual_resized["width"]
            ) <= 1
            browser.close()


def test_template_canvas_escape_cancels_active_drag(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15000)
            actual = editor.locator(
                '.template-document [data-layout-id="heading"]'
            )
            actual.click(position={"x": 20, "y": 20})
            actual_before = actual.bounding_box()
            x_input = editor.locator(
                '[data-role="property-panel"] input[name="x"]'
            )
            before = x_input.input_value()
            bounds = editor.locator('.selection-box').bounding_box()
            page.mouse.move(
                bounds["x"] + bounds["width"] / 2,
                bounds["y"] + bounds["height"] / 2,
            )
            page.mouse.down()
            page.mouse.move(
                bounds["x"] + bounds["width"] / 2 + 24,
                bounds["y"] + bounds["height"] / 2,
            )
            page.keyboard.press("Escape")
            page.mouse.up()
            expect(x_input).to_have_value(before)
            actual_after = actual.bounding_box()
            assert abs(actual_after["x"] - actual_before["x"]) <= 1
            assert abs(actual_after["y"] - actual_before["y"]) <= 1
            expect(
                editor.get_by_role("button", name="儲存為新版本")
            ).to_be_disabled()
            browser.close()


def test_template_property_panel_clamps_values_to_registered_limits(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15000)
            editor.locator(
                '.template-document [data-layout-id="mascot"]'
            ).click(position={"x": 20, "y": 20})
            width_input = editor.locator(
                '[data-role="property-panel"] input[name="w"]'
            )
            width_input.fill("1")
            width_input.press("Tab")
            expect(width_input).to_have_value("120")
            browser.close()


def test_template_save_creates_inactive_version_before_explicit_activation(
    tmp_path,
):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15000)
            editor.locator(
                '.template-document [data-layout-id="heading"]'
            ).click(position={"x": 20, "y": 20})
            x_input = editor.locator(
                '[data-role="property-panel"] input[name="x"]'
            )
            before = float(x_input.input_value())
            x_input.fill(str(before + 8))
            x_input.press("Tab")
            editor.get_by_role("button", name="儲存為新版本").click()
            expect(page.get_by_label("模板版本")).to_have_value(
                "v2 · 尚未啟用", timeout=60000
            )
            conn = db.connect(str(tmp_path / "browser.db"))
            versions = conn.execute(
                "SELECT id, version_no FROM carousel_template_versions "
                "ORDER BY version_no"
            ).fetchall()
            assert [row["version_no"] for row in versions] == [1, 2]
            active = conn.execute(
                "SELECT active_version_id FROM carousel_template_settings"
            ).fetchone()[0]
            assert active == versions[0]["id"]
            page.get_by_text(
                "我了解現有草稿不會自動換版", exact=True
            ).last.click(force=True)
            expect(
                page.get_by_label("我了解現有草稿不會自動換版")
            ).to_be_checked()
            page.get_by_role(
                "button", name="設為之後新貼文的啟用版"
            ).click()
            expect(page.get_by_label("模板版本")).to_have_value(
                "v2 · 目前啟用", timeout=15000
            )
            active = conn.execute(
                "SELECT active_version_id FROM carousel_template_settings"
            ).fetchone()[0]
            assert active == versions[1]["id"]
            browser.close()


def test_text_font_size_round_trips_through_saved_v2_and_browser_reload(
    tmp_path,
):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15000)
            editor.get_by_role("button", name="02 公司身分卡").click()
            body = editor.locator(
                '.template-document [data-layout-id="facts-body"]'
            )
            expect(body).to_be_visible(timeout=15000)
            body.click(position={"x": 10, "y": 10})
            font_input = editor.locator(
                '[data-role="property-panel"] input[name="font_size"]'
            )
            saved_size = float(font_input.input_value()) + 6
            font_input.fill(str(saved_size))
            font_input.press("Tab")
            editor.get_by_role("button", name="儲存為新版本").click()
            expect(page.get_by_label("模板版本")).to_have_value(
                "v2 · 尚未啟用", timeout=60000
            )

            conn = db.connect(str(tmp_path / "browser.db"))
            row = conn.execute(
                "SELECT schema_version, layout_json "
                "FROM carousel_template_versions WHERE version_no = 2"
            ).fetchone()
            assert row["schema_version"] == 2
            assert (
                json.loads(row["layout_json"])["pages"]
                ["who"]["elements"]["facts-body"]["font_size"]
                == saved_size
            )

            page.reload(wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            expect(editor).to_be_visible(timeout=15000)
            expect(page.get_by_label("模板版本")).to_have_value(
                "v2 · 尚未啟用"
            )
            editor.get_by_role("button", name="02 公司身分卡").click()
            body = editor.locator(
                '.template-document [data-layout-id="facts-body"]'
            )
            expect(body).to_be_visible(timeout=15000)
            rendered_size = float(
                body.evaluate(
                    "element => getComputedStyle(element).fontSize.slice(0, -2)"
                )
            )
            assert rendered_size == saved_size
            browser.close()


def test_template_editor_mobile_is_read_only_without_overflow(tmp_path):
    with running_streamlit(tmp_path,_seed) as base_url:
        with sync_playwright() as driver:
            browser=driver.chromium.launch();page=browser.new_page(viewport={"width":375,"height":812})
            page.goto(f"{base_url}/設定",wait_until="networkidle")
            expect(page.get_by_text("請改用桌面寬度調整模板",exact=False)).to_be_visible(timeout=15000)
            assert page.evaluate("document.documentElement.scrollWidth") == 375
            expect(page.locator('.overlay-layer')).to_be_hidden()
            browser.close()
