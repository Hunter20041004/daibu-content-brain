# Six-Page v57 Production Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將正式貼文工具從七頁 editorial-v15.1 完整替換為六頁 v57 粉彩手帳，安全清除舊草稿／模板／PNG，並讓 AI 產稿、編輯器、Renderer、PNG 與 ZIP 使用同一份六頁契約。

**Architecture:** `CarouselDraft` 保留資料型別，但 `PAGE_TYPES` 收斂為六頁；新增 layout schema v3 與 `sticky-notebook-v1` 正式模板。SQLite migration 只在偵測到舊 v1/v2 模板時，於單一 transaction 清除輪播草稿與舊模板，再建立每個 theme 的 v3 active version。所有正式輸出仍經同一 Renderer、版面檢查與 Playwright 截圖流程。

**Tech Stack:** Python 3.11、Streamlit、SQLite、pytest、Playwright、單檔 HTML/CSS、LINE Seed TW、既有 Streamlit Components v2。

## Global Constraints

- 正式頁序固定為 `cover, who, problem, how-ai, results, cta`。
- `why-care` 不得留在正式 prompt、schema、Renderer、編輯器、PNG 或 ZIP。
- 第五頁三張流程便利貼寬高差各不得超過 1 CSS px。
- 舊 `editorial-v15-1` template/layout 與資料庫 v1/v2 版本刪除，不提供舊版入口。
- 破壞性 migration 只刪輪播草稿、來源快照、草稿 meta、模板 settings/versions；ideas、idea_sources、brand_assets、themes 與成效資料不變。
- migration 必須 idempotent、transactional；正式執行前先做 SQLite `.backup`。
- 不呼叫正式 LLM，不新增付費服務或前端套件。
- 每個行為以一次一個失敗測試完成 Red→Green→Refactor；Task 收尾才跑相關測試，全套只在分支完成與 main 合併後各跑一次。
- 前端完成前至少跑兩輪 1280×800 與 375×812 截圖自檢。

---

### Task 1: 六頁內容契約與 fixture

**Files:**
- Modify: `daibu/cards/pages.py`
- Modify: `daibu/cards/schema.py`
- Modify: `tests/card_fixtures.py`
- Modify: `tests/test_cards_pages.py`
- Modify: `tests/test_cards_schema.py`

**Interfaces:**
- Produces: `pages.PAGE_TYPES == ("cover", "who", "problem", "how-ai", "results", "cta")`
- Produces: `carousel_draft()` 與 `renderable_carousel_draft()` 各含六頁。
- Consumes: 既有 `CarouselDraft`、`CarouselPage`、`ContentSection`、`DiagramSpec`。

- [ ] **Step 1: 寫六頁順序紅燈**

```python
def test_six_page_types_in_order():
    assert pages.PAGE_TYPES == (
        "cover", "who", "problem", "how-ai", "results", "cta"
    )
    assert "why-care" not in pages.MASCOT_FOR
    assert "why-care" not in pages.SECTION_LABELS
```

- [ ] **Step 2: 執行紅燈**

Run: `.venv/bin/pytest -q tests/test_cards_pages.py::test_six_page_types_in_order`

Expected: FAIL，actual 仍含 `why-care`。

- [ ] **Step 3: 最小修改 `pages.py` 並轉綠**

刪除 `why-care` 的 page type、mascot、labels、diagram 與顯示名稱；更新六頁 LABELS。

Run: `.venv/bin/pytest -q tests/test_cards_pages.py::test_six_page_types_in_order`

Expected: PASS。

- [ ] **Step 4: 寫六頁 draft 紅燈**

```python
def test_complete_six_page_draft_passes_the_content_contract():
    draft = carousel_draft()
    assert [page.page_type for page in draft.pages] == list(pages.PAGE_TYPES)
    assert len(draft.pages) == 6
    validate_draft(draft)
```

Run: `.venv/bin/pytest -q tests/test_cards_schema.py::test_complete_six_page_draft_passes_the_content_contract`

Expected: FAIL，fixture 仍是七頁或 validation 仍要求七頁。

- [ ] **Step 5: 更新 fixture 與 validation 並轉綠**

移除 why-care fixture；`validate_draft()` 錯誤改成「輪播必須依固定順序包含六頁」。刪除 `validate_company_headings()` 與 draft.create 的呼叫；grounding 範圍改為需要事實的第 1–5 頁，CTA 固定品牌文案可無來源。

Run: `.venv/bin/pytest -q tests/test_cards_schema.py tests/test_cards_pages.py`

Expected: 全綠。

- [ ] **Step 6: Commit**

```bash
git add daibu/cards/pages.py daibu/cards/schema.py daibu/cards/draft.py tests/card_fixtures.py tests/test_cards_pages.py tests/test_cards_schema.py
git commit -m "feat: define six-page carousel contract"
```

---

### Task 2: 六頁 AI prompt 與 Gemini schema

**Files:**
- Modify: `daibu/llm/prompt.py`
- Modify: `daibu/llm/gemini.py`
- Modify: `tests/test_llm.py`
- Modify: `tests/test_cards_draft.py`

**Interfaces:**
- Produces: `build_carousel()` 明示六頁任務且不含 why-care。
- Produces: Gemini `pages` array `minItems == maxItems == 6`，page_type enum 使用六頁 `PAGE_TYPES`。

- [ ] **Step 1: 寫 prompt 紅燈**

```python
def test_carousel_prompt_requests_exact_six_page_story():
    text = prompt.build_carousel("Acme", "題目", "角度", verified_sources())
    assert "剛好六頁" in text
    assert "封面定位、公司輪廓、流程優化機會、AI 的角色、流程改善、社群 CTA" in text
    assert "觀察訊號" not in text
```

Run: `.venv/bin/pytest -q tests/test_llm.py::test_carousel_prompt_requests_exact_six_page_story`

Expected: FAIL，prompt 仍要求七頁。

- [ ] **Step 2: 最小更新 prompt 並轉綠**

將頁數、閱讀任務、section labels、CTA 固定文案與輸出前檢查改成六頁；保留來源與逐字引句規則。

Run: `.venv/bin/pytest -q tests/test_llm.py::test_carousel_prompt_requests_exact_six_page_story`

Expected: PASS。

- [ ] **Step 3: 寫 Gemini schema 紅燈**

```python
def test_carousel_json_schema_requires_six_pages():
    schema = gemini.build_carousel_schema()
    pages_schema = schema["properties"]["pages"]
    assert pages_schema["minItems"] == 6
    assert pages_schema["maxItems"] == 6
    assert pages_schema["items"]["properties"]["page_type"]["enum"] == list(card_pages.PAGE_TYPES)
```

Run: `.venv/bin/pytest -q tests/test_llm.py::test_carousel_json_schema_requires_six_pages`

Expected: FAIL，schema 仍鎖七頁。

- [ ] **Step 4: 更新 schema 與 parser fixture 並轉綠**

Run: `.venv/bin/pytest -q tests/test_llm.py tests/test_cards_draft.py`

Expected: 全綠；真實 API contract 維持 deselected。

- [ ] **Step 5: Commit**

```bash
git add daibu/llm/prompt.py daibu/llm/gemini.py tests/test_llm.py tests/test_cards_draft.py
git commit -m "feat: generate native six-page carousel drafts"
```

---

### Task 3: layout schema v3 與破壞性資料遷移

**Files:**
- Create: `daibu/cards/layouts/sticky-notebook-v1.json`
- Modify: `daibu/cards/layout_registry.py`
- Modify: `daibu/cards/layout_schema.py`
- Modify: `daibu/db.py`
- Modify: `tests/test_cards_layout_schema.py`
- Modify: `tests/test_db_migration.py`

**Interfaces:**
- Produces: `load_builtin_layout()` 回 schema v3 六頁 layout。
- Produces: `registry_for_schema(3)`；正式 parser 只接受 schema v3。
- Produces: `db._migrate_to_six_page_v57(conn)`，idempotent 清除舊輪播資料並為每個 theme 建立 v3 active version。

- [ ] **Step 1: 寫 schema v3 紅燈**

```python
def test_builtin_layout_is_six_page_schema_v3():
    document = load_builtin_layout()
    assert document.schema_version == 3
    assert tuple(document.pages) == pages.PAGE_TYPES
    assert "why-care" not in document.pages
```

Run: `.venv/bin/pytest -q tests/test_cards_layout_schema.py::test_builtin_layout_is_six_page_schema_v3`

Expected: FAIL，builtin 仍是 v1/v2 七頁。

- [ ] **Step 2: 建立 v3 registry 與最小合法 layout**

以六頁 v57 元素登錄建立 `SCHEMA_V3_ELEMENT_REGISTRY`；`registry_for_schema()` 只接受 3。`load_builtin_layout()` 改讀 `sticky-notebook-v1.json`，JSON 頁序與 `PAGE_TYPES` 相同。

Run: `.venv/bin/pytest -q tests/test_cards_layout_schema.py::test_builtin_layout_is_six_page_schema_v3`

Expected: PASS。

- [ ] **Step 3: 寫 migration 紅燈**

```python
def test_v57_migration_removes_legacy_carousel_only_and_seeds_v3(tmp_path):
    conn = migrated_legacy_database(tmp_path)
    before = fingerprint_preserved_tables(conn)
    db._migrate_to_six_page_v57(conn)
    assert conn.execute("SELECT COUNT(*) FROM carousel_pages").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM carousel_sources").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM carousel_drafts").fetchone()[0] == 0
    assert {row[0] for row in conn.execute("SELECT schema_version FROM carousel_template_versions")} == {3}
    assert conn.execute("SELECT COUNT(*) FROM carousel_template_settings").fetchone()[0] == theme_count(conn)
    assert fingerprint_preserved_tables(conn) == before
```

Run: `.venv/bin/pytest -q tests/test_db_migration.py::test_v57_migration_removes_legacy_carousel_only_and_seeds_v3`

Expected: FAIL，舊 rows 與 schema 仍存在。

- [ ] **Step 4: 實作 transactional migration 並轉綠**

偵測任何 v1/v2 version 時，在同一 `with conn:` 依序清 `carousel_pages`、`carousel_sources`、`carousel_drafts`、settings、versions，再為每個 theme 插入 canonical v3 layout 與 active setting。若只存在 v3，立即 return。

Run: `.venv/bin/pytest -q tests/test_db_migration.py::test_v57_migration_removes_legacy_carousel_only_and_seeds_v3`

Expected: PASS。

- [ ] **Step 5: 寫 idempotency／rollback 紅綠切片**

先測連跑兩次 row 數與 layout JSON 不變；再以 monkeypatch 讓 seed 失敗，驗證舊資料仍完整。一次只加入一個測試並各自看紅→綠。

Run: `.venv/bin/pytest -q tests/test_db_migration.py tests/test_cards_layout_schema.py tests/test_cards_layout_repository.py`

Expected: 全綠。

- [ ] **Step 6: Commit**

```bash
git add daibu/cards/layouts/sticky-notebook-v1.json daibu/cards/layout_registry.py daibu/cards/layout_schema.py daibu/db.py tests/test_cards_layout_schema.py tests/test_db_migration.py tests/test_cards_layout_repository.py
git commit -m "feat: migrate carousel templates to six-page schema v3"
```

---

### Task 4: v57 正式 Renderer

**Files:**
- Create: `daibu/cards/templates/sticky-notebook-v1.html`
- Create: `daibu/cards/templates/sticky-notebook-v1.css`
- Modify: `daibu/cards/render.py`
- Delete: `daibu/cards/templates/editorial-v15-1.html`
- Delete: `daibu/cards/templates/editorial-v15-1.css`
- Delete: `daibu/cards/layouts/editorial-v15-1.json`
- Modify: `tests/test_cards_render.py`
- Modify: `tests/test_cards_layout_validation.py`

**Interfaces:**
- Produces: `render.page_html(page, company, asset, layout)` 回傳 v57 六頁之一。
- Produces: 每頁 `.carousel-canvas[data-template="sticky-notebook-v1"]`、正式 `data-layout-id`、`data-edit-key`。

- [ ] **Step 1: 寫模板 identity 紅燈**

```python
def test_renderer_uses_sticky_notebook_v1_only(asset):
    output = render.page_html(carousel_draft().pages[0], "SUN", asset)
    assert 'data-template="sticky-notebook-v1"' in output
    assert "editorial-v15.1" not in output
```

Run: `.venv/bin/pytest -q tests/test_cards_render.py::test_renderer_uses_sticky_notebook_v1_only`

Expected: FAIL，仍輸出 editorial template。

- [ ] **Step 2: 建立模板 shell 並轉綠**

HTML 保留 `__CSS__`、`__LAYOUT_CSS__`、`__PAGE_TYPE__`、`__CONTENT__` tokens；CSS 定義 LINE Seed 與 v57 palette／方格紙／紙張／膠帶／便利貼材質。`_editorial_document()` 改名 `_sticky_document()` 並只讀新檔。

Run: `.venv/bin/pytest -q tests/test_cards_render.py::test_renderer_uses_sticky_notebook_v1_only`

Expected: PASS。

- [ ] **Step 3: 逐頁建立正式 DOM 紅綠切片**

依序為 cover、who、problem、how-ai、results、cta 各新增一個測試，斷言該頁的內容鍵、Logo／mascot、必需圖解節點與 layout hooks；每個測試先紅，再只修改對應 `_cover()`／`_who()`／`_problem()`／`_how_ai()`／`_results()`／`_cta()` 轉綠。

results 測試必須量測：

```python
assert metrics["cardWidthSpread"] <= 1
assert metrics["cardHeightSpread"] <= 1
assert metrics["labels"] == ["使用前", "產品介入", "使用後"]
```

CTA 只允許：

```text
追蹤呆一布 AI 共學實驗室
帶你看更多最新 AI 資訊
```

- [ ] **Step 4: 刪除 why-care 與舊模板檔**

先新增 `assert "_why_care" not in inspect.getsource(render)` 的紅燈，再刪除函式、dispatch 與三個舊 template/layout 檔。

Run: `.venv/bin/pytest -q tests/test_cards_render.py tests/test_cards_layout_validation.py`

Expected: 全綠。

- [ ] **Step 5: Commit**

```bash
git add daibu/cards/render.py daibu/cards/templates/sticky-notebook-v1.html daibu/cards/templates/sticky-notebook-v1.css daibu/cards/layouts/sticky-notebook-v1.json daibu/cards/templates/editorial-v15-1.html daibu/cards/templates/editorial-v15-1.css daibu/cards/layouts/editorial-v15-1.json tests/test_cards_render.py tests/test_cards_layout_validation.py
git commit -m "feat: render approved v57 sticky notebook carousel"
```

---

### Task 5: 六頁內容編輯器與模板編輯器

**Files:**
- Modify: `daibu/cards/editor_component.py`
- Modify: `daibu/cards/editor_payload.py`
- Modify: `daibu/cards/editor_service.py`
- Modify: `daibu/cards/editor_ui.py`
- Modify: `daibu/cards/template_editor_payload.py`
- Modify: `daibu/cards/template_editor_ui.py`
- Modify: `daibu/cards/template_stress.py`
- Modify: `pages/1_選題.py`
- Modify: `tests/test_cards_editor_payload.py`
- Modify: `tests/test_cards_editor_service.py`
- Modify: `tests/test_cards_template_editor_payload.py`
- Modify: `tests/test_cards_template_editor_ui.py`
- Modify: `tests/test_carousel_editor_browser.py`
- Modify: `tests/test_template_editor_browser.py`
- Modify: `tests/test_app_smoke.py`

**Interfaces:**
- Produces: 六頁 rail、六頁 preview payload、六頁 atomic save。
- Consumes: schema v3 layout 與六頁 `CarouselDraft`。

- [ ] **Step 1: 寫內容 rail 六頁紅燈**

```python
def test_editor_payload_contains_six_pages_in_order(asset):
    payload = build_editor_payload(carousel_draft(), "SUN", asset, ...)
    assert [page["pageType"] for page in payload["pages"]] == list(pages.PAGE_TYPES)
    assert len(payload["pages"]) == 6
```

Run: `.venv/bin/pytest -q tests/test_cards_editor_payload.py::test_editor_payload_contains_six_pages_in_order`

Expected: FAIL，fixture／文案仍為七頁。

- [ ] **Step 2: 更新 payload、UI 文案與 JS aria label 並轉綠**

所有「七頁」使用者文案改為「六頁」；page rail 以 payload 數量產生，不 hardcode。模板管理 spinner 改成「三家公司與六頁內容」。

Run: `.venv/bin/pytest -q tests/test_cards_editor_payload.py tests/test_cards_template_editor_payload.py tests/test_cards_template_editor_ui.py`

Expected: 全綠。

- [ ] **Step 3: 寫真實瀏覽器六頁儲存紅燈**

更新 browser fixture 後，要求六個 rail item；修改第 5 頁文字、切頁再返回仍保留；儲存後 DB 恰有六列且 content revision +1。

Run: `.venv/bin/pytest -q tests/test_carousel_editor_browser.py::test_six_page_edit_survives_navigation_and_saves_atomically`

Expected: FAIL，舊元件仍呈七頁或舊文案。

- [ ] **Step 4: 最小更新元件與 service 並轉綠**

Run: `.venv/bin/pytest -q tests/test_carousel_editor_browser.py tests/test_cards_editor_service.py tests/test_template_editor_browser.py`

Expected: 全綠。

- [ ] **Step 5: Commit**

```bash
git add daibu/cards/editor_component.py daibu/cards/editor_payload.py daibu/cards/editor_service.py daibu/cards/editor_ui.py daibu/cards/template_editor_payload.py daibu/cards/template_editor_ui.py daibu/cards/template_stress.py pages/1_選題.py tests/test_cards_editor_payload.py tests/test_cards_editor_service.py tests/test_cards_template_editor_payload.py tests/test_cards_template_editor_ui.py tests/test_carousel_editor_browser.py tests/test_template_editor_browser.py tests/test_app_smoke.py
git commit -m "feat: edit six-page v57 carousels"
```

---

### Task 6: 六張 PNG、ZIP 與快取

**Files:**
- Modify: `daibu/cards/shoot.py`
- Modify: `daibu/cards/bundle.py`
- Modify: `daibu/cards/workbench.py`
- Modify: `pages/1_選題.py`
- Modify: `tests/test_cards_shoot.py`
- Modify: `tests/test_cards_bundle.py`
- Modify: `tests/test_cards_workbench.py`
- Modify: `tests/test_app_smoke.py`

**Interfaces:**
- Produces: `carousel_pngs(...) -> list[bytes]` 長度 6。
- Produces: `PAGE_FILENAMES` 六個檔名；`carousel_zip()` 只接受六張。

- [ ] **Step 1: 寫六檔 ZIP 紅燈**

```python
def test_zip_contains_six_numbered_pages_in_order():
    pngs = [f"png-{index}".encode() for index in range(6)]
    archive = bundle.carousel_zip(pngs)
    with ZipFile(BytesIO(archive)) as packaged:
        assert packaged.namelist() == [
            "01-cover.png", "02-who.png", "03-problem.png",
            "04-how-ai.png", "05-results.png", "06-cta.png",
        ]
```

Run: `.venv/bin/pytest -q tests/test_cards_bundle.py::test_zip_contains_six_numbered_pages_in_order`

Expected: FAIL，舊 bundle 要求七張。

- [ ] **Step 2: 更新 bundle 並轉綠**

錯誤文案改為「輪播圖必須剛好包含六張」。

Run: `.venv/bin/pytest -q tests/test_cards_bundle.py`

Expected: PASS。

- [ ] **Step 3: 寫六張真實 PNG 紅燈**

```python
def test_six_pngs_match_canvas_and_have_no_overflow(tmp_path):
    outputs = shoot.carousel_pngs(renderable_carousel_draft(), "SUN", asset(tmp_path))
    assert len(outputs) == 6
    assert all(_png_size(data) == (1080, 1350) for data in outputs)
```

Run: `.venv/bin/pytest -q tests/test_cards_shoot.py::test_six_pngs_match_canvas_and_have_no_overflow`

Expected: FAIL，Renderer／fixture／測試仍有七頁假設或版面溢出。

- [ ] **Step 4: 修正產圖／預覽迭代與快取長度並轉綠**

所有預覽迴圈從 `PAGE_TYPES` 動態取得 label；workbench cache 要求 PNG list 長度 6，舊七張 cache 回 None。

Run: `.venv/bin/pytest -q tests/test_cards_shoot.py tests/test_cards_bundle.py tests/test_cards_workbench.py tests/test_app_smoke.py -k 'carousel or png or bundle'`

Expected: 全綠。

- [ ] **Step 5: Commit**

```bash
git add daibu/cards/shoot.py daibu/cards/bundle.py daibu/cards/workbench.py pages/1_選題.py tests/test_cards_shoot.py tests/test_cards_bundle.py tests/test_cards_workbench.py tests/test_app_smoke.py
git commit -m "feat: export six-page v57 png bundles"
```

---

### Task 7: 壓力驗證、視覺 QA、正式清除與部署

**Files:**
- Modify: `daibu/cards/template_stress.py`
- Modify: `tests/test_cards_template_stress.py`
- Modify: `HANDOFF.md`
- Modify: `docs/superpowers/plans/2026-08-26-six-page-v57-production-integration.md`
- Delete: `.playwright-cli/railway-carousel-20260731/01-cover.png`
- Delete: `.playwright-cli/railway-carousel-20260731/02-who.png`
- Delete: `.playwright-cli/railway-carousel-20260731/03-problem.png`
- Delete: `.playwright-cli/railway-carousel-20260731/04-how-ai.png`
- Delete: `.playwright-cli/railway-carousel-20260731/05-results.png`
- Delete: `.playwright-cli/railway-carousel-20260731/06-why-care.png`
- Delete: `.playwright-cli/railway-carousel-20260731/07-cta.png`

**Interfaces:**
- Consumes: 六頁 schema v3 Renderer、editor、PNG bundle。
- Produces: 三家公司 × 長文字 × 寬／高 Logo 無溢出證據；正式 DB 備份與 migration 證據。

- [ ] **Step 1: 寫第五頁等寬高與跨公司壓力紅燈**

以 Playwright 實測三張 `.result-flow` 卡片 rect，要求 width spread／height spread `<= 1`；對 SUN、Billow AI Labs、Shiraz AI 與 wide/tall logo 跑六頁 `inspect_pages()`。

Run: `.venv/bin/pytest -q tests/test_cards_template_stress.py`

Expected: 初次 FAIL 會指出實際溢出或尺寸差。

- [ ] **Step 2: 只調整 v57 CSS/layout 直到壓力全綠**

不得降低正文可讀下限、關閉 overflow 檢查或縮小中間卡；修 layout 安全區與 CSS grid。

Run: `.venv/bin/pytest -q tests/test_cards_template_stress.py tests/test_cards_render.py tests/test_cards_shoot.py`

Expected: 全綠。

- [ ] **Step 3: 跑全套與兩輪截圖**

Run: `PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q`

啟動隔離 DB 的 Streamlit，依硬規則每輪只截：

```bash
playwright-cli resize 1280 800
playwright-cli screenshot --filename=.screenshots/v57-tool-round1-desktop.png
playwright-cli resize 375 812
playwright-cli screenshot --filename=.screenshots/v57-tool-round1-mobile.png
```

自評層次、留白、字體、三色、對齊、響應式、狀態與微動效；修正後再截 round2。375px 必須 `scrollWidth == clientWidth`，console 0 errors／0 warnings。

- [ ] **Step 4: 產品理解檢查點與 code review**

更新 HANDOFF：產品能力、使用者體驗、技術結構、資料流、設計理由、替代方案、安全與成本、測試證據、剩餘限制。執行 code review，Important 以上必須修正並重跑相關測試。

- [ ] **Step 5: 精確刪除舊 QA PNG**

先驗證資料夾檔名集合精確等於七個預期檔，再移除整個 `.playwright-cli/railway-carousel-20260731/`；確認路徑不存在。這些是可再生 QA 檔，不碰 `.screenshots/` 或 Logo。

- [ ] **Step 6: Commit、merge、main 全測與 push**

完成分支提交後 fast-forward 合併 main；main 重跑完整 pytest，push 並確認 `git rev-parse HEAD == git ls-remote origin refs/heads/main`。

- [ ] **Step 7: 正式 DB 備份、migration 與服務驗收**

1. 以 `sqlite3 daibu.db ".backup '<timestamped path>'"` 建立備份並用 `PRAGMA integrity_check` 驗證備份。
2. 記錄保留表列數與 canonical JSON 指紋；執行正式 migration。
3. 確認 carousel pages/sources/drafts 為 0，template versions 只含 schema 3，settings 指向 v3；保留表指紋不變。
4. 重啟既有 `io.daibu.content-brain`，沿用 `http://127.0.0.1:8501`。
5. 從首頁進入選題與設定，確認六頁內容 rail、六頁模板 rail、六張 PNG 與 ZIP；不按正式 LLM 產生按鈕。
6. 1280×800／375×812 正式站截圖，console 0 errors／0 warnings，服務 health `ok`。

- [ ] **Step 8: 更新計畫完成狀態與 HANDOFF**

記錄最終 commit、遠端 hash、全測數字、備份路徑、正式資料前後量測、服務 PID、核心流程與截圖路徑。
