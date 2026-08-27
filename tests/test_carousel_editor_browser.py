import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from daibu import db
from daibu.cards import assets
from daibu.llm.base import Idea
from daibu.models import Theme
from tests.browser_support import running_streamlit
from tests.card_fixtures import renderable_carousel_draft, solid_png


def _seed(database_path: Path, logo_path: Path) -> None:
    old_logo_dir = os.environ.get("DAIBU_LOGO_DIR")
    os.environ["DAIBU_LOGO_DIR"] = str(logo_path)
    try:
        conn = db.connect(str(database_path))
        db.init_schema(conn)
        theme_id = db.add_theme(
            conn,
            Theme(None, "AI 新創介紹", 4, [], 1, "company_profile"),
        )
        idea_id = db.add_idea(
            conn,
            theme_id,
            Idea("逐頁編輯測試", "採用角度", "正文", company="ElevenLabs"),
            status="採用",
        )
        draft = renderable_carousel_draft()
        db.save_idea_sources(conn, idea_id, draft.sources)
        db.save_carousel_draft(conn, idea_id, draft)
        assets.store_logo(
            conn,
            "ElevenLabs",
            "official.png",
            solid_png(240, 80),
            "https://elevenlabs.io/about",
            "2026-08-23",
        )
    finally:
        if old_logo_dir is None:
            os.environ.pop("DAIBU_LOGO_DIR", None)
        else:
            os.environ["DAIBU_LOGO_DIR"] = old_logo_dir


def test_switching_pages_preserves_unsaved_value_and_database(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/選題", wait_until="networkidle")
            page.get_by_text("輪播製作", exact=True).click()
            editor = page.locator('[data-role="editor-shell"]')
            expect(editor).to_be_visible(timeout=15_000)
            editor.locator('button[data-page-type="problem"]').click()
            field = editor.locator('textarea[name="page.problem.diagram.0.text"]')
            field.fill("新的流程節點")
            editor.locator('button[data-page-type="results"]').click()
            editor.locator('button[data-page-type="problem"]').click()

            expect(field).to_have_value("新的流程節點")
            expect(
                editor.locator(
                    '[data-edit-key="page.problem.diagram.0.text"]'
                )
            ).to_contain_text("新的流程節點")
            conn = db.connect(str(tmp_path / "browser.db"))
            assert (
                db.get_carousel_draft(conn, 1).pages[2].diagram.nodes[0].text
                != "新的流程節點"
            )
            browser.close()


def test_hard_limit_marks_page_and_blocks_save_and_generation(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/選題", wait_until="networkidle")
            page.get_by_text("輪播製作", exact=True).click()
            editor = page.locator('[data-role="editor-shell"]')
            expect(editor).to_be_visible(timeout=15_000)
            editor.locator('button[data-page-type="problem"]').click()
            editor.locator(
                'textarea[name="page.problem.diagram.0.text"]'
            ).fill("超" * 49)

            expect(
                editor.locator('button[data-page-type="problem"]')
            ).to_have_attribute("data-status", "error")
            expect(
                editor.get_by_role("button", name="儲存全部變更")
            ).to_be_disabled()
            expect(page.get_by_role("button", name="產生六張圖")).to_be_disabled()
            browser.close()


def test_legal_save_updates_database_and_keeps_current_page(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/選題", wait_until="networkidle")
            page.get_by_text("輪播製作", exact=True).click()
            editor = page.locator('[data-role="editor-shell"]')
            expect(editor).to_be_visible(timeout=15_000)
            editor.locator('button[data-page-type="problem"]').click()
            editor.locator(
                'textarea[name="page.problem.diagram.0.text"]'
            ).fill("新的合法流程節點")
            editor.get_by_role("button", name="儲存全部變更").click()

            expect(page.get_by_text("六頁變更已全部儲存。")).to_be_visible(
                timeout=15_000
            )
            editor = page.locator('[data-role="editor-shell"]')
            expect(
                editor.locator('button[data-page-type="problem"]')
            ).to_have_attribute("aria-current", "page")
            expect(editor.locator('[data-role="action-bar"]')).to_have_attribute(
                "data-status", "saved"
            )
            conn = db.connect(str(tmp_path / "browser.db"))
            assert (
                db.get_carousel_draft(conn, 1).pages[2].diagram.nodes[0].text
                == "新的合法流程節點"
            )
            browser.close()
