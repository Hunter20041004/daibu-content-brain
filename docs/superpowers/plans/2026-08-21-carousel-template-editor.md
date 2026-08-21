# 系列模板畫布與版本管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Frontend tasks must also apply `frontend-design`, `emil-design-eng`, `ui-ux-pro-max`, and `playwright-cli` as required by project rules.

**Goal:** 在「設定 → 系列模板管理」加入受限制的 PPT 式畫布，讓使用者能移動、縮放已登錄元素並調整文字框，儲存時建立不可變新版本；舊草稿不被暗中改版，只能經使用者明確升級。

**Architecture:** 設定頁把已選系列、已選版本、七頁 Renderer HTML 與安全 `LayoutDocument` 傳給本機 `st.components.v2` 元件。元件只在 `data-layout-id` 元素上疊選取框、拖曳與縮放控制點，以 sessionStorage 維護未存 working copy 與 undo/redo；Python 收到完整 layout mapping 後重跑 schema、壓力內容與 Chromium 驗證，然後新增版本。新版本不隱式啟用，啟用與舊草稿升級都是另外的明確操作。

**Tech Stack:** Python 3.11+、Streamlit Components v2（Streamlit 1.60+）、原生 HTML/CSS/ES modules、sessionStorage、SQLite、Playwright／Chromium、pytest、Streamlit AppTest。

## Global Constraints

- 前置條件：`2026-08-21-carousel-layout-foundation.md` 與 `2026-08-21-carousel-content-editor.md` 全部完成、全套測試綠燈。
- 嚴格 Red → Green → Refactor；一次只新增一個失敗測試。
- 畫布只能改已登錄元素的 `x/y/w/h`；文字元素另可改 `font_size/text_align`。
- 不能新增、刪除、旋轉或改變 z-order、字型、色票、素材路徑、元素 ID 與資料綁定。
- 元件送回的 layout 一律當作不可信輸入；不接受 HTML、CSS、JavaScript、URL 或檔案路徑。
- 儲存模板永遠建新版本，不得 update 現有 `layout_json`；儲存本身不切換 active version。
- 設為 active 只影響之後新建草稿；既有草稿只有手動升級才改變綁定。
- 手動升級前先用舊草稿內容＋新模板做七頁 Chromium 驗證；失敗時 DB 與 PNG 指紋維持不變。
- 手機 375px 只提供版本檢視與啟用；精確拖曳編輯顯示「請改用桌面寬度」，不做難以操作的假手機畫布。
- 不增加 LLM 呼叫、付費服務、CDN 或 npm build。

## File Map

- Create `daibu/cards/template_editor_payload.py`: 畫布 payload、可調屬性白名單、未存 layout 重建與本頁 reset。
- Create `daibu/cards/template_editor_component.py`: Components v2 畫布 HTML/CSS/JS 與 Python wrapper。
- Create `daibu/cards/template_editor_service.py`: 存新版本、壓力驗證、啟用與草稿升級服務。
- Create `daibu/cards/template_stress.py`: 建立實際草稿＋近上限文字／長短公司名／橫直 Logo 的固定驗證案例。
- Create `daibu/cards/stress_assets/logo-wide.svg`、`daibu/cards/stress_assets/logo-tall.svg`: 只用於本機模板驗證的透明橫／直比例測試標記。
- Create `daibu/cards/template_editor_ui.py`: 設定頁的系列／版本／頁面協調層。
- Modify `daibu/cards/render.py`: 提供單頁畫布編輯 HTML，保持 `data-layout-id` 與正式輸出同源。
- Modify `daibu/cards/editor_service.py`: 新增舊草稿手動升級呼叫點。
- Modify `daibu/cards/editor_ui.py`: 顯示已綁定版本／active version 差異與手動升級按鈕。
- Modify `pages/3_設定.py`: 在系統設定之後新增獨立的「系列模板管理」。
- Modify `pages/1_選題.py`: 只接入手動升級狀態，不把畫布控制放進日常內容工作區。
- Create tests `tests/test_cards_template_editor_payload.py`、`tests/test_cards_template_editor_component.py`、`tests/test_cards_template_editor_service.py`、`tests/test_cards_template_stress.py`、`tests/test_template_editor_browser.py`。
- Modify tests `tests/test_cards_render.py`、`tests/test_cards_editor_service.py`、`tests/test_cards_editor_ui.py`、`tests/test_cards_layout_repository.py`、`tests/test_app_smoke.py`。

---

### Task 1: 安全的模板工作副本與屬性修改

**Files:**
- Create: `daibu/cards/template_editor_payload.py`
- Create: `tests/test_cards_template_editor_payload.py`

**Interfaces:**
- Produces: `TemplateField(element_id, label, kind, editable_properties, min_values, max_values)`
- Produces: `template_editor_payload(theme, versions, selected_version, page_type, preview_html) -> dict[str, object]`
- Produces: `apply_template_values(base: LayoutDocument, page_type: str, values: Mapping[str, Mapping[str, object]]) -> LayoutDocument`
- Produces: `reset_layout_page(working: LayoutDocument, base: LayoutDocument, page_type: str) -> LayoutDocument`
- Produces: `summarize_layout_diff(base: LayoutDocument, working: LayoutDocument) -> tuple[str, ...]`
- Consumes: `ELEMENT_REGISTRY`、`replace_element()`、`layout_to_mapping()`

- [ ] **Step 1: 寫第一個紅燈，正常更新已登錄元素**

```python
from daibu.cards.layout_schema import load_builtin_layout
from daibu.cards.template_editor_payload import apply_template_values


def test_template_values_update_registered_geometry_and_text_style():
    original = load_builtin_layout()
    edited = apply_template_values(original, "cover", {
        "heading": {
            "x": 104, "y": 372, "w": 620, "h": 260,
            "font_size": 78, "text_align": "left",
        },
    })
    heading = edited.pages["cover"].elements["heading"]
    assert heading.rect.x == 104
    assert heading.rect.w == 620
    assert heading.text_style.font_size == 78
    assert original.pages["cover"].elements["heading"] != heading
```

- [ ] **Step 2: 跑紅燈**

Run: `.venv/bin/pytest -q tests/test_cards_template_editor_payload.py::test_template_values_update_registered_geometry_and_text_style`

Expected: FAIL，因 module 尚不存在。

- [ ] **Step 3: 實作最小 mapping 重建**

`apply_template_values()` 先要求 `set(values) == set(base.pages[page_type].elements)`，每個元素只讀 registry 允許屬性，用 `replace_element()` 逐項重建，最後再 `parse_layout(layout_to_mapping(result))`。

- [ ] **Step 4: 依序加三個垂直紅燈再轉綠**

1. 未知元素或屬性被拒絕，不改 original。
2. 圖像元素送 `font_size` 被拒絕。
3. `reset_layout_page()` 只回復所選頁，其他頁的 working changes 保留。

- [ ] **Step 5: 實作 editor payload**

payload 必須包含 `themeId`、`themeName`、`versionId`、`versionNo`、`pageType`、`pages`、`elements`、`layout`、`previewHtml`、`canvas`；不包含 DB path、SQL、Logo 本機路徑或任意 CSS。

- [ ] **Step 6: 寫版本差異摘要紅燈再轉綠**

移動第 5 頁 3 個元素，另改 2 個文字框尺寸，要求摘要含「第 5 頁：移動 3 個元素、調整 2 個文字框」。座標差異算移動，w/h/font_size/text_align 差異算調整；同一元素可同時計入兩類。完全相同時回空 tuple。

- [ ] **Step 7: Commit**

```bash
git add daibu/cards/template_editor_payload.py tests/test_cards_template_editor_payload.py
git commit -m "feat: define safe template editor payloads"
```

### Task 2: 畫布元件骨架、選取框與屬性面板

**Files:**
- Create: `daibu/cards/template_editor_component.py`
- Modify: `daibu/cards/render.py`
- Create: `tests/test_cards_template_editor_component.py`
- Modify: `tests/test_cards_render.py`

**Interfaces:**
- Produces: `TemplateEditorEvent(dirty: bool, save_payload: Mapping[str, object] | None)`
- Produces: `mount_template_editor(payload, *, key) -> TemplateEditorEvent`
- Produces: `render.template_editor_page_html(page, company, asset, layout) -> str`
- Component state: `dirty`; trigger: `saveLayout`

- [ ] **Step 1: 寫 Renderer 紅燈，每個登錄元素都有唯一 hook**

```python
def test_template_editor_html_has_one_hook_for_every_registered_element(asset):
    layout = load_builtin_layout()
    output = render.template_editor_page_html(
        carousel_draft().pages[0], "SUN", asset, layout
    )
    found = re.findall(r'data-layout-id="([^"]+)"', output)
    assert set(found) == set(ELEMENT_REGISTRY["cover"])
    assert len(found) == len(ELEMENT_REGISTRY["cover"])
```

- [ ] **Step 2: 跑紅燈後以正式 Renderer 轉綠**

`template_editor_page_html()` 呼叫正式 `page_html()`，只在最外層加 editor mode marker；不得複製另一份頁面 HTML／CSS。

- [ ] **Step 3: 寫 component 契約紅燈**

```python
def test_template_component_exposes_canvas_and_eight_resize_handles():
    assert 'data-role="template-canvas"' in TEMPLATE_HTML
    assert TEMPLATE_JS.count('data-handle') >= 1
    assert 'HANDLE_DIRECTIONS = ["n","ne","e","se","s","sw","w","nw"]' in TEMPLATE_JS
    assert 'setTriggerValue("saveLayout"' in TEMPLATE_JS
```

- [ ] **Step 4: 建立元件四區結構**

HTML root 只有：頂部版本資訊、左側七頁 rail、中央畫布／操作列、右側屬性面板。CSS 沿用正式品牌代幣 `--ink:#102f3d`、`--teal:#2f7c87`、`--cyan:#86ccd4`、`--peach:#ec9870`、`--paper:#fafbf8`；畫布容器以 `aspect-ratio:4/5`等比顯示，不改 1080×1350 邏輯座標。

- [ ] **Step 5: 實作點選與屬性同步**

JS 把 Renderer HTML 放進 trusted preview root；在畫布上方另放 overlay layer。點 `[data-layout-id]` 後，從 working layout 換算選取框位置，建立八個 `button[data-handle]`；右側數字欄位只用 `valueAsNumber`寫回 working layout。文字屬性只在 registry `text=true` 時顯示。

- [ ] **Step 6: 加入鍵盤可用性紅燈**

Tab 可聚焦元素；Enter 選取；方向鍵移動 1px，Shift＋方向鍵移動 10px；所有圖示按鈕有 `aria-label`，focus ring 不可被切掉。

- [ ] **Step 7: 聚焦測試與 Commit**

Run: `.venv/bin/pytest -q tests/test_cards_template_editor_component.py tests/test_cards_render.py`

```bash
git add daibu/cards/template_editor_component.py daibu/cards/render.py tests/test_cards_template_editor_component.py tests/test_cards_render.py
git commit -m "feat: add constrained template canvas shell"
```

### Task 3: 拖曳、縮放、吸附、undo／redo 與 reset

**Files:**
- Modify: `daibu/cards/template_editor_component.py`
- Modify: `tests/test_cards_template_editor_component.py`

**Interfaces:**
- Component working history: `{past: LayoutMapping[], present: LayoutMapping, future: LayoutMapping[]}`
- Constants: `GRID_PX=8`、`SNAP_PX=6`、`SAFE_MARGIN=48`、`HISTORY_LIMIT=50`

- [ ] **Step 1: 寫拖曳座標換算紅燈**

匯出可純測試的 `clientDeltaToCanvas(delta, renderedWidth)`；畫布顯示寬 540px 時，滑鼠移動 10px 必須等於邏輯座標 20px。

- [ ] **Step 2: 以 Pointer Events 實作 drag／resize**

`pointerdown` 快照 present，`pointermove` 只更新 working layout 與 DOM，`pointerup` 才 push 一筆 history。縮放必須保留對側 anchor，並先在前端套 registry min/max；伺服器仍會重驗。

- [ ] **Step 3: 寫吸附紅燈再轉綠**

對畫布 48px 安全線、中心線、其他元素的 left/center/right 與 top/middle/bottom 進行 6px 容差吸附；只在命中時顯示青色 guide，pointerup 或 Escape 後移除。

- [ ] **Step 4: 寫即時碰撞訊號紅燈再轉綠**

前端只用幾何提示：兩個 `avoid` 元素邊緣距離 12px 內時選取框變橘，已交疊時變紅；`allow/background` 不顯示假警報。這不取代 Chromium，只是拖曳時的方向提示。

- [ ] **Step 5: 寫 history 紅燈再轉綠**

undo 把 present 移入 future 並還原上一份完整 layout；redo 相反；新 edit 清空 future；最多 50 筆。`Ctrl/Cmd+Z`、`Ctrl/Cmd+Shift+Z` 與按鈕皆走同一 helper。

- [ ] **Step 6: 本頁 reset 與 sessionStorage**

本頁 reset 使用 Task 1 `reset_layout_page()` 的等價前端操作，放進一筆 history；storage key 必須含 `themeId-versionId`，切版本不可混用 working copy。只有實際幾何改變才標 dirty。

- [ ] **Step 7: 取消與儲存 trigger**

Escape 取消本次 pointer 操作，恢復 pointerdown 快照；「儲存為新版本」回傳 `{baseVersionId, layout}`，不傳 preview HTML。

- [ ] **Step 8: 聚焦測試與 Commit**

Run: `.venv/bin/pytest -q tests/test_cards_template_editor_component.py`

```bash
git add daibu/cards/template_editor_component.py tests/test_cards_template_editor_component.py
git commit -m "feat: support precise template canvas editing"
```

### Task 4: 伺服器端模板驗證與不可變新版本

**Files:**
- Create: `daibu/cards/template_editor_service.py`
- Create: `daibu/cards/template_stress.py`
- Create: `daibu/cards/stress_assets/logo-wide.svg`
- Create: `daibu/cards/stress_assets/logo-tall.svg`
- Create: `tests/test_cards_template_editor_service.py`
- Create: `tests/test_cards_template_stress.py`
- Modify: `tests/test_cards_layout_repository.py`

**Interfaces:**
- Produces: `TemplateIssue(page_type, element_id, message)`
- Produces: `TemplateSaveResult(version: TemplateVersion | None, issues: tuple[TemplateIssue, ...])`
- Produces: `save_template_version(conn, theme_id, base_version_id, raw_layout, stress_cases) -> TemplateSaveResult`
- Produces: `set_active_template_version(conn, theme_id, version_id) -> TemplateVersion`
- Produces: `TemplateStressCase(draft, company, asset, label)`
- Produces: `build_template_stress_cases(actual_case: TemplateStressCase | None) -> tuple[TemplateStressCase, ...]`
- Consumes: `parse_layout()`、`render.draft_html_pages()`、`layout_validation.inspect_pages()`、`layout_repository.create_version()`

- [ ] **Step 1: 寫固定壓力案例紅燈**

`build_template_stress_cases(actual_case)` 必須保留 actual，再加 SUN／Billow AI Labs／Shiraz AI 三組；另一個 fixture 把每個可編輯欄位填到 `hard_chars - 2`，且保持七頁 section／diagram roles 合法。兩個 SVG 分別為 320×100 與 100×320 viewBox，只含安全 path/rect/title，先用既有 `logo.validate_upload()` 測試通過。沒有 actual draft 時仍回三組固定案例。

- [ ] **Step 2: 寫未知屬性 rollback 紅燈**

在合法 layout mapping 的 cover heading 放入 `rotate: 10`；呼叫 service 後要求回傳「標題含不允許的屬性」、versions 列數與 active pointer 全不變。

- [ ] **Step 3: 實作驗證順序**

```python
def save_template_version(conn, theme_id, base_version_id, raw_layout, stress_cases):
    base = layout_repository.get_version(conn, base_version_id)
    if base.theme_id != theme_id:
        return TemplateSaveResult(None, (
            TemplateIssue(None, None, "基礎版本不屬於這個內容系列。"),
        ))
    try:
        layout = parse_layout(raw_layout)
    except LayoutValidationError as error:
        return TemplateSaveResult(None, (map_schema_issue(error),))
    issues = validate_stress_cases(layout, stress_cases)
    if issues:
        return TemplateSaveResult(None, issues)
    version = layout_repository.create_version(conn, theme_id, layout)
    return TemplateSaveResult(version, ())
```

`validate_stress_cases()` 每個七頁 fixture 都用正式 Renderer 後呼叫 `inspect_pages()`；不只看座標 schema。

- [ ] **Step 4: 寫壓力內容紅燈**

把第 5 頁 `after-title` 縮到合法最小寬度，讓 SUN 正常內容通過、最長合法標題 fixture 溢出；要求不建版本，錯誤指到第 5 頁／改變後標題。

- [ ] **Step 5: 寫成功儲存紅燈**

三家公司與最長合法內容全通過後，新版本 `version_no + 1`，舊版 layout 逐欄相同，active pointer 仍指舊版。

- [ ] **Step 6: 啟用版本服務紅燈**

`set_active_template_version()` 只能啟用同系列且已存在的版本；成功後既有 `carousel_drafts.template_version_id` 全不變。

- [ ] **Step 7: 聚焦測試與 Commit**

Run: `.venv/bin/pytest -q tests/test_cards_template_stress.py tests/test_cards_template_editor_service.py tests/test_cards_layout_repository.py`

```bash
git add daibu/cards/template_stress.py daibu/cards/stress_assets/logo-wide.svg daibu/cards/stress_assets/logo-tall.svg daibu/cards/template_editor_service.py tests/test_cards_template_stress.py tests/test_cards_template_editor_service.py tests/test_cards_layout_repository.py
git commit -m "feat: validate and version carousel templates"
```

### Task 5: 接入設定頁的「系列模板管理」

**Files:**
- Create: `daibu/cards/template_editor_ui.py`
- Modify: `pages/3_設定.py`
- Modify: `tests/test_app_smoke.py`

**Interfaces:**
- Produces: `render_template_management(conn) -> TemplateManagementState`
- Consumes: `db.get_themes()`、layout repository、template component、template service

- [ ] **Step 1: 改 AppTest 先紅**

`test_settings_exposes_series_template_management` monkeypatch `mount_template_editor()` 捕捉 payload，要求：「系統設定」與「系列模板管理」是兩個獨立區；可選系列／版本／頁面；payload 有七頁與單頁 preview。

- [ ] **Step 2: 建立 UI 協調層**

1. 讀系列，沒有模板時用 `ensure_default_version()` 建 v1。
2. 版本 selectbox 顯示 `vN · YYYY-MM-DD HH:mm`，active 加「目前啟用」。
3. 從該系列最新一份有 Logo 的草稿組 actual stress case；沒有時就使用固定三組案例，不阻擋新系列建 v1。
4. 頁面狀態與 `summarize_layout_diff()` 的版本差異摘要由 component 呈現；Streamlit 只處理新版儲存結果與錯誤摘要。
5. 儲存成功後選中新版，顯示「已建立 vN，尚未設為啟用版」，不隱式啟用。

- [ ] **Step 3: 新版儲存 AppTest**

component 回傳合法 save trigger，monkeypatch Chromium validator 成功；要求新版列出、active badge 仍在舊版。validator 失敗時要求錯誤指向頁面／元素且不新增版本。

- [ ] **Step 4: 啟用確認 AppTest**

按「設為之後新貼文的啟用版」先顯示明確說明：新草稿會用 vN，現有草稿不變。二次確認後才切 pointer；取消時不寫 DB。

- [ ] **Step 5: 手機只讀狀態**

CSS media query 在 `max-width:767px` 隱藏畫布交互層、顯示已選版本的單頁預覽與「請改用桌面寬度調整模板」；版本檢視與啟用按鈕維持可用。

- [ ] **Step 6: Commit**

```bash
git add daibu/cards/template_editor_ui.py pages/3_設定.py tests/test_app_smoke.py
git commit -m "feat: add series template management settings"
```

### Task 6: 舊草稿手動升級與失敗保護

**Files:**
- Modify: `daibu/cards/template_editor_service.py`
- Modify: `daibu/cards/editor_service.py`
- Modify: `daibu/cards/editor_ui.py`
- Modify: `pages/1_選題.py`
- Modify: `tests/test_cards_template_editor_service.py`
- Modify: `tests/test_cards_editor_service.py`
- Create: `tests/test_cards_editor_ui.py`

**Interfaces:**
- Produces: `TemplateUpgradeResult(meta: CarouselDraftMeta | None, issues: tuple[TemplateIssue, ...])`
- Produces: `upgrade_draft_template(conn, idea_id, theme_id, draft, company, asset, target_version_id) -> TemplateUpgradeResult`

- [ ] **Step 1: 寫升級失敗 rollback 紅燈**

草稿綁 v1，active 是會讓第 3 頁標題 overflow 的 v2；升級後要求回傳第 3 頁 heading 錯誤，`template_version_id`、`content_revision`、PNG fingerprint 全不變。

- [ ] **Step 2: 實作先驗證再交易更新**

```python
def upgrade_draft_template(conn, idea_id, theme_id, draft, company, asset, target_version_id):
    current = db.get_carousel_draft_meta(conn, idea_id)
    target = layout_repository.get_version(conn, target_version_id)
    if current is None or target.theme_id != theme_id:
        return TemplateUpgradeResult(current, (
            TemplateIssue(None, None, "目標模板不屬於這篇貼文的內容系列。"),
        ))
    pages = render.draft_html_pages(draft, company, asset, target.layout)
    issues = layout_validation.inspect_pages(pages)
    if issues:
        return TemplateUpgradeResult(current, map_layout_issues(issues))
    meta = db.upgrade_carousel_template(conn, idea_id, target.id)
    return TemplateUpgradeResult(meta, ())
```

`db.upgrade_carousel_template()` 在同一 transaction 更新 version binding 並 `content_revision + 1`；不改 `carousel_pages`、`carousel_sources`、idea body 與 Logo。

- [ ] **Step 3: 寫成功升級紅燈**

新版七頁通過後，只有 meta version/revision 改變，內容全欄指紋不變，PNG fingerprint 改變。

- [ ] **Step 4: 內容編輯器 UI 紅燈**

已綁定 v1、active v3 時，顯示「這篇使用 v1；目前啟用 v3」與「檢查並改用 v3」；同版本時不顯示升級按鈕。按下後先二次確認，dirty content 時停用並要求先儲存。

- [ ] **Step 5: 錯誤定位與 Commit**

升級失敗的 issues 沿用內容編輯器頁碼／欄位錯誤列表，不顯示 DOM selector 或檔名。

```bash
.venv/bin/pytest -q tests/test_cards_template_editor_service.py tests/test_cards_editor_service.py tests/test_cards_editor_ui.py
git add daibu/cards/template_editor_service.py daibu/cards/editor_service.py daibu/cards/editor_ui.py pages/1_選題.py tests/test_cards_template_editor_service.py tests/test_cards_editor_service.py tests/test_cards_editor_ui.py
git commit -m "feat: safely upgrade carousel draft templates"
```

### Task 7: 真實瀏覽器畫布契約

**Files:**
- Create: `tests/test_template_editor_browser.py`
- Modify: `tests/browser_support.py`
- Modify: `daibu/cards/template_editor_component.py`

**Interfaces:**
- Consumes: Phase B `running_streamlit(tmp_path, seed_fn)`

- [ ] **Step 1: 寫第一個 E2E 紅燈：拖曳後預覽與屬性面板同步**

1. 開啟 tmp DB 的設定頁。
2. 點封面 heading，記錄 x 欄位與 bounding box。
3. 用 Playwright mouse 向右拖邏輯 32px。
4. 要求 x 欄位，preview 與 selection box 同步，DB version 列數仍不變。

- [ ] **Step 2: 修元件直到轉綠，才新增 resize 切片**

拖 southeast handle，要求 w/h 增加、對側 anchor 不變；undo 回原值，redo 再恢復。

- [ ] **Step 3: 新增儲存／啟用切片**

儲存建 v2 且 badge 顯示「尚未啟用」；二次確認設 active 後，舊 idea 仍綁 v1，新建 draft 綁 v2。

- [ ] **Step 4: 新增草稿升級切片**

到內容頁點「檢查並改用 v2」，成功後版本說明更新，內容沒有變，再產圖時 fingerprint 改變。

- [ ] **Step 5: 錯誤與手機切片**

1. 輸入小於 registry 的寬度，儲存被拒絕且 working copy 保留。
2. 375×812 可看版本／預覽，看到桌面編輯說明，無橫向捲軸。

- [ ] **Step 6: Commit**

```bash
git add tests/test_template_editor_browser.py tests/browser_support.py daibu/cards/template_editor_component.py
git commit -m "test: cover template canvas browser boundary"
```

### Task 8: 兩輪視覺 QA、完整資料安全與 Phase C 收尾

**Files:**
- Modify: `HANDOFF.md`
- Modify: `.gitignore`
- Verify: `.screenshots/template-editor-round1-desktop.png`
- Verify: `.screenshots/template-editor-round1-mobile.png`
- Verify: `.screenshots/template-editor-round2-desktop.png`
- Verify: `.screenshots/template-editor-round2-mobile.png`

**Interfaces:**
- Consumes: SUN、Billow AI Labs、Shiraz AI 三家公司與最長合法文字 fixture
- Produces: 可在設定統一管理的系列模板畫布與安全版本生命週期

- [ ] **Step 1: 用 `ui-ux-pro-max` 給第一輪的具體查表基準**

回顧已核可 v15.1 的科技編輯紙語言：LINE Seed、深藍／青／珊瑚橘、非對稱編輯留白、非 bento 卡片。模板工具的選取框、guide 與屬性面板應服務內容，不改變貼文本身視覺。

- [ ] **Step 2: 第一輪兩張截圖**

Run:

```bash
playwright-cli open http://127.0.0.1:8502
playwright-cli resize 1280 800
playwright-cli screenshot --filename=.screenshots/template-editor-round1-desktop.png
playwright-cli resize 375 812
playwright-cli screenshot --filename=.screenshots/template-editor-round1-mobile.png
```

逐項明寫不合格：層次、留白、字體、三色限制、對齊、375px overflow、hover/focus/loading/error/empty、微動效。

- [ ] **Step 3: 每個不合格項先加可重現測試再修**

桌面必須看得出「版本狀態 → 選頁 → 選元素 → 調整 → 儲存新版」的層次；屬性欄位不做等寬格子牆。手機不顯示無法使用的縮小控制點。

- [ ] **Step 4: 第二輪兩張截圖**

八項全數合格；375px `scrollWidth == clientWidth`；console 0 errors／0 warnings。回歸再檢查內容編輯器的 1280×800 與 375×812，確認設定頁 CSS 沒有洩漏。

- [ ] **Step 5: 正式 DB 的 SQLite `.backup` 副本完整流程**

先用既知 fixture 校準指紋量法，再量 ideas、carousel_pages、carousel_sources、brand_assets 與新三張模板表。在副本做：移動封面標題 → 儲存 v2 → 設 active v2 → 確認舊草稿仍 v1 → 升級單篇 → 產七圖。要求貼文內容與證據指紋不變，只有版本表、active pointer、指定草稿 meta 與 PNG fingerprint 改變。

- [ ] **Step 6: 三公司七頁驗證**

在 v1 與 v2 各跑 SUN、Billow AI Labs、Shiraz AI：42 張頁面無 overflow／非法碰撞，PNG 均 1080×1350，無 page number、source、date。

- [ ] **Step 7: 全套驗證**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q
.venv/bin/python -m compileall -q daibu pages
git diff --check
```

Expected: 0 failures；既有 deselected 外部契約維持略過。

- [ ] **Step 8: 更新 HANDOFF 產品理解檢查點**

寫明產品能力、使用者結果、系統區塊、資料流、設計理由／備援、安全成本、TDD／Chromium／資料副本證據、截圖路徑、剩餘限制。

- [ ] **Step 9: Commit Phase C**

```bash
git add .gitignore daibu/cards/template_editor_payload.py daibu/cards/template_editor_component.py daibu/cards/template_editor_service.py daibu/cards/template_editor_ui.py daibu/cards/template_stress.py daibu/cards/stress_assets/logo-wide.svg daibu/cards/stress_assets/logo-tall.svg daibu/cards/render.py daibu/cards/editor_service.py daibu/cards/editor_ui.py pages/1_選題.py pages/3_設定.py tests/browser_support.py tests/test_cards_template_editor_payload.py tests/test_cards_template_editor_component.py tests/test_cards_template_editor_service.py tests/test_cards_template_stress.py tests/test_template_editor_browser.py tests/test_cards_render.py tests/test_cards_editor_service.py tests/test_cards_editor_ui.py tests/test_cards_layout_repository.py tests/test_app_smoke.py HANDOFF.md
git commit -m "feat: deliver versioned carousel template editor"
```
