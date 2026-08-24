# 模板編輯器即時畫布與語意占位符 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修正模板編輯器「選取框有移動、真正元素沒有移動」的同步錯誤，並用語意占位符取代 SUN 等壓力測試公司的預覽內容。

**Architecture:** 新增一個只供模板設定畫面使用的占位內容組裝器，但仍經過正式 Renderer 產生 HTML。前端元件以同一份 working `LayoutDocument` 同時驅動真正的 `[data-layout-id]` DOM、選取框與屬性欄；Python 保存端與不可變版本生命週期維持不變。真實 Chromium 會直接測量實際元素與選取框，避免只驗證控制層而再次假通過。

**Tech Stack:** Python 3.11+、Streamlit Components v2、原生 HTML/CSS/ES modules、SQLite、pytest、Playwright／Chromium、`playwright-cli`。

## Global Constraints

- 嚴格 Red → Green → Refactor；一次只新增一個失敗測試，轉綠後才進下一個切片。
- 模板畫布不顯示 SUN、Billow AI Labs、Shiraz AI 或其 Logo；動態欄位顯示語意角色。
- 呆一布機器人、裝飾線、圓、底色與固定版面語法維持正式外觀。
- 正式內容預覽與 PNG 仍顯示真實公司、Logo 與貼文內容；占位符不得寫入 SQLite。
- 前端只套用登錄元素的 `x/y/w/h/font_size/text_align`；不接受任意 HTML、CSS、JavaScript、URL 或檔案路徑。
- 拖曳、縮放、數字欄位、復原、重做、Escape 與重設都必須同步真正 DOM 與選取框。
- 模板保存仍建立不可變新版本；編輯中不寫 DB，保存本身不切換 active version。
- 手機 375px 維持唯讀；不得新增 LLM 呼叫、外部套件、CDN、付費服務或資料庫 migration。
- 完成前至少做兩輪 1280×800 與 375×812 截圖自檢，並驗證正式站核心流程。

## File Map

- Create `daibu/cards/template_placeholders.py`: 建立七頁中性的模板預覽草稿與公司／系列占位常數。
- Modify `daibu/cards/render.py`: 讓模板預覽可指定系列名稱與 Logo 占位文案，不改正式輸出預設值。
- Modify `daibu/cards/template_editor_ui.py`: 模板畫布改用占位草稿；三家公司壓力案例只留在保存驗證。
- Modify `daibu/cards/template_editor_payload.py`: 檢查正式 Renderer 是否提供完整 `data-layout-id` hooks，回傳可理解的同步錯誤。
- Modify `daibu/cards/template_editor_component.py`: 將 working layout 套到真正 DOM，處理即時拖曳與同步錯誤狀態。
- Create `tests/test_cards_template_placeholders.py`: 驗證七頁占位內容及正式資料不受影響。
- Modify `tests/test_cards_template_editor_ui.py`: 驗證設定頁 payload 不再含測試公司內容。
- Modify `tests/test_cards_template_editor_payload.py`: 驗證缺少 Renderer hook 時回傳明確錯誤。
- Modify `tests/test_cards_template_editor_component.py`: 驗證同步 helper 與錯誤狀態契約。
- Modify `tests/test_template_editor_browser.py`: 真實測量真正元素、選取框、屬性欄與 DB。
- Modify `HANDOFF.md`: 紀錄產品結果、資料流、測試、視覺 QA 與部署證據。

---

### Task 1: 七頁語意占位內容

**Files:**
- Create: `daibu/cards/template_placeholders.py`
- Create: `tests/test_cards_template_placeholders.py`
- Modify: `daibu/cards/render.py`
- Modify: `daibu/cards/template_editor_ui.py`
- Modify: `tests/test_cards_template_editor_ui.py`

**Interfaces:**
- Produces: `COMPANY_PLACEHOLDER = "公司名稱"`
- Produces: `SERIES_PLACEHOLDER = "系列名稱"`
- Produces: `build_template_placeholder_draft() -> CarouselDraft`
- Extends: `render.template_editor_page_html(..., series_name: str = SERIES_NAME, logo_placeholder_text: str = "LOGO 待確認") -> str`
- Consumes: `ELEMENT_REGISTRY`、`pages.SECTION_LABEL_SEQUENCES`、正式 `page_html()`。

- [ ] **Step 1: 寫占位草稿的第一個紅燈**

Create `tests/test_cards_template_placeholders.py`:

```python
from daibu.cards import pages
from daibu.cards.template_placeholders import (
    COMPANY_PLACEHOLDER,
    SERIES_PLACEHOLDER,
    build_template_placeholder_draft,
)


def test_template_placeholder_draft_covers_all_seven_semantic_pages():
    draft = build_template_placeholder_draft()
    assert tuple(page.page_type for page in draft.pages) == pages.PAGE_TYPES
    assert draft.pages[0].heading == "封面標題"
    assert all(
        page.heading == "頁面標題"
        for page in draft.pages[1:]
    )
    assert COMPANY_PLACEHOLDER == "公司名稱"
    assert SERIES_PLACEHOLDER == "系列名稱"
```

- [ ] **Step 2: 跑紅燈並確認失敗原因正確**

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_template_placeholders.py::test_template_placeholder_draft_covers_all_seven_semantic_pages
```

Expected: FAIL with `ModuleNotFoundError: daibu.cards.template_placeholders`。

- [ ] **Step 3: 實作最小占位草稿組裝器**

Create `daibu/cards/template_placeholders.py`:

```python
from daibu.cards import pages
from daibu.cards.layout_registry import ELEMENT_REGISTRY
from daibu.cards.schema import (
    CarouselDraft,
    CarouselPage,
    ContentSection,
    DiagramNode,
    DiagramSpec,
)


COMPANY_PLACEHOLDER = "公司名稱"
SERIES_PLACEHOLDER = "系列名稱"

_DIAGRAM_KIND = {
    "problem": "problem-chain",
    "how-ai": "ai-generate",
    "results": "before-after",
    "why-care": "signals",
}
_DIAGRAM_ELEMENT_IDS = {
    "problem": ("stage-1", "stage-2", "stage-3"),
    "how-ai": ("step-1", "step-2", "step-3"),
    "results": ("before-title", "to", "after-title"),
    "why-care": ("signal-1", "signal-2", "signal-3"),
}


def build_template_placeholder_draft() -> CarouselDraft:
    built = []
    for page_no, page_type in enumerate(pages.PAGE_TYPES, start=1):
        sequence_index = 1 if page_type == "why-care" else 0
        labels = pages.SECTION_LABEL_SEQUENCES[page_type][sequence_index]
        sections = tuple(
            ContentSection(label, label, (), ())
            for label in labels
        )
        diagram = None
        if page_type in _DIAGRAM_KIND:
            diagram = DiagramSpec(
                _DIAGRAM_KIND[page_type],
                tuple(
                    DiagramNode(
                        ELEMENT_REGISTRY[page_type][element_id].label,
                        "圖解說明",
                        "think",
                    )
                    for element_id in _DIAGRAM_ELEMENT_IDS[page_type]
                ),
            )
        built.append(
            CarouselPage(
                page_no,
                page_type,
                "封面標題" if page_type == "cover" else "頁面標題",
                sections,
                diagram,
                "",
            )
        )
    return CarouselDraft((), tuple(built))
```

- [ ] **Step 4: 跑綠燈**

Run the Step 2 command.

Expected: `1 passed`。

- [ ] **Step 5: 寫 Renderer 占位文字紅燈**

Append to `tests/test_cards_template_placeholders.py`:

```python
import base64
import re

from daibu.cards import render
from daibu.cards.layout_schema import load_builtin_layout


def test_template_editor_html_uses_semantic_company_series_and_logo():
    draft = build_template_placeholder_draft()
    cover = render.template_editor_page_html(
        draft.pages[0],
        COMPANY_PLACEHOLDER,
        None,
        load_builtin_layout(),
        series_name=SERIES_PLACEHOLDER,
        logo_placeholder_text="企業 Logo",
    )
    assert "公司名稱" in cover
    assert "系列名稱" in cover
    assert "一布懂 AI 新創" not in cover
    match = re.search(
        r'<img src="data:image/svg\+xml;base64,([^"]+)" '
        r'alt="公司名稱 Logo">',
        cover,
    )
    assert match is not None
    assert "企業 Logo" in base64.b64decode(match.group(1)).decode("utf-8")
```

- [ ] **Step 6: 跑紅燈**

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_template_placeholders.py::test_template_editor_html_uses_semantic_company_series_and_logo
```

Expected: FAIL because `template_editor_page_html()` does not accept `series_name` or `logo_placeholder_text`。

- [ ] **Step 7: 最小擴充 Renderer，保留正式輸出預設**

Modify `daibu/cards/render.py`:

```python
def page_html(
    page: CarouselPage,
    company: str,
    brand_asset: BrandAsset | None,
    layout: LayoutDocument | None = None,
    *,
    allow_logo_placeholder: bool = False,
    browser_preview: bool = False,
    logo_placeholder_text: str = "LOGO 待確認",
) -> str:
```

Replace only the SVG text node construction with:

```python
f'font-family="sans-serif" font-size="22">'
f'{html.escape(logo_placeholder_text)}</text></svg>'
```

Change `template_editor_page_html()` to:

```python
def template_editor_page_html(
    page: CarouselPage,
    company: str,
    brand_asset: BrandAsset | None,
    layout: LayoutDocument,
    *,
    series_name: str = SERIES_NAME,
    logo_placeholder_text: str = "LOGO 待確認",
) -> str:
    output = page_html(
        page,
        company,
        brand_asset,
        layout,
        allow_logo_placeholder=True,
        browser_preview=True,
        logo_placeholder_text=logo_placeholder_text,
    )
    output = output.replace(
        html.escape(SERIES_NAME),
        html.escape(series_name),
    )
    return output.replace(
        'data-template="editorial-v15.1"',
        'data-template="editorial-v15.1" data-template-editor="true"',
        1,
    )
```

Run the Step 6 command. Expected: `1 passed`。

- [ ] **Step 8: 寫設定頁不再使用壓力案例內容的紅燈**

Extend `test_template_management_builds_seven_page_payload()` in `tests/test_cards_template_editor_ui.py`:

```python
    assert "公司名稱" in captured["previewHtml"]
    assert "系列名稱" in captured["previewHtml"]
    for test_company in ("SUN", "Billow AI Labs", "Shiraz AI"):
        assert test_company not in captured["previewHtml"]
```

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_template_editor_ui.py::test_template_management_builds_seven_page_payload
```

Expected: FAIL because current UI still renders `stress_cases[0]`。

- [ ] **Step 9: UI 改用占位草稿，保存仍用三家公司壓力案例**

Modify imports in `daibu/cards/template_editor_ui.py`:

```python
from daibu.cards.template_placeholders import (
    COMPANY_PLACEHOLDER,
    SERIES_PLACEHOLDER,
    build_template_placeholder_draft,
)
```

Replace the preview setup with:

```python
    stress_cases = build_template_stress_cases()
    placeholder_draft = build_template_placeholder_draft()
    page = next(
        item for item in placeholder_draft.pages
        if item.page_type == page_type
    )
    preview = render.template_editor_page_html(
        page,
        COMPANY_PLACEHOLDER,
        None,
        selected.layout,
        series_name=SERIES_PLACEHOLDER,
        logo_placeholder_text="企業 Logo",
    )
```

Do not change the `save_template_version(..., stress_cases)` call.

- [ ] **Step 10: 跑 Task 1 聚焦測試並提交**

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_template_placeholders.py \
  tests/test_cards_template_editor_ui.py \
  tests/test_cards_render.py
```

Expected: all pass。

```bash
git add daibu/cards/template_placeholders.py daibu/cards/render.py \
  daibu/cards/template_editor_ui.py tests/test_cards_template_placeholders.py \
  tests/test_cards_template_editor_ui.py
git commit -m "fix: use semantic template editor placeholders"
```

---

### Task 2: 屬性欄同步真正貼文元素

**Files:**
- Modify: `tests/test_template_editor_browser.py`
- Modify: `daibu/cards/template_editor_component.py`
- Modify: `tests/test_cards_template_editor_component.py`

**Interfaces:**
- Produces in component JS: `applyWorkingLayout() -> string[]`，回傳缺少的 element IDs。
- Consumes: `state.present.pages[data.pageType].elements` and `data.elements`。

- [ ] **Step 1: 寫數字欄位改變真正 DOM 的紅燈**

Add to `tests/test_template_editor_browser.py`:

```python
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
```

- [ ] **Step 2: 跑紅燈**

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_template_editor_browser.py::test_template_property_x_moves_actual_element_and_selection_together
```

Expected: FAIL because `box_dx > 0` but `actual_dx == 0`。

- [ ] **Step 3: 實作單一幾何同步 helper**

Add inside the component function in `TEMPLATE_JS`:

```javascript
  function applyWorkingLayout() {
    const missing = [];
    const items = elementMap(state, data.pageType);
    Object.entries(items).forEach(([elementId, item]) => {
      const element = root.querySelector(
        `.template-document [data-layout-id="${elementId}"]`
      );
      if (!element) {
        missing.push(elementId);
        return;
      }
      const descriptor = data.elements.find(
        entry => entry.elementId === elementId
      );
      const values = {
        left: `${item.x}px`,
        top: `${item.y}px`,
        width: `${item.w}px`,
        height: `${item.h}px`,
      };
      if (descriptor?.kind === "text") {
        values["font-size"] = `${item.font_size}px`;
        values["text-align"] = item.text_align;
      }
      Object.entries(values).forEach(([property, value]) => {
        element.style.setProperty(property, value, "important");
      });
    });
    return missing;
  }
```

Immediately after `doc.innerHTML=data.previewHtml;`, call:

```javascript
    const missing = applyWorkingLayout();
```

The inline declarations use `important` because the formal Renderer already emits some high-specificity positioning rules; the working copy must be the visible editing layer without changing the saved HTML.

- [ ] **Step 4: 跑綠燈**

Run the Step 2 command.

Expected: `1 passed` and rendered deltas differ by at most 1 CSS px。

- [ ] **Step 5: 補純契約測試，防止 helper 被移除**

Append to `tests/test_cards_template_editor_component.py`:

```python
def test_template_component_applies_working_geometry_to_renderer_dom():
    script = template_editor_component.TEMPLATE_JS
    assert "function applyWorkingLayout()" in script
    assert 'style.setProperty(property, value, "important")' in script
    assert "const missing = applyWorkingLayout();" in script
```

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_template_editor_component.py \
  tests/test_template_editor_browser.py::test_template_property_x_moves_actual_element_and_selection_together
```

Expected: all pass。

- [ ] **Step 6: Commit**

```bash
git add daibu/cards/template_editor_component.py \
  tests/test_cards_template_editor_component.py \
  tests/test_template_editor_browser.py
git commit -m "fix: synchronize template properties with preview elements"
```

---

### Task 3: 拖曳中即時同步與 Escape 恢復

**Files:**
- Modify: `tests/test_template_editor_browser.py`
- Modify: `daibu/cards/template_editor_component.py`

**Interfaces:**
- Consumes: Task 2 `applyWorkingLayout()`。
- Preserves: existing history, snapping, collision, resize and DB behavior。

- [ ] **Step 1: 把既有拖曳測試升級成「放開滑鼠前」的紅燈**

In `test_template_canvas_drag_syncs_property_without_saving()`, record `actual_before` and `box_before`, then replace the drag portion with:

```python
            actual = editor.locator(
                '.template-document [data-layout-id="heading"]'
            )
            actual_before = actual.bounding_box()
            box_before = box.bounding_box()
            page.mouse.move(
                box_before["x"] + box_before["width"] / 2,
                box_before["y"] + box_before["height"] / 2,
            )
            page.mouse.down()
            page.mouse.move(
                box_before["x"] + box_before["width"] / 2 + 16,
                box_before["y"] + box_before["height"] / 2,
            )
            actual_during = actual.bounding_box()
            box_during = box.bounding_box()
            actual_dx = actual_during["x"] - actual_before["x"]
            box_dx = box_during["x"] - box_before["x"]
            assert actual_dx > 0
            assert abs(actual_dx - box_dx) <= 1
            page.mouse.up()
```

- [ ] **Step 2: 跑紅燈**

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_template_editor_browser.py::test_template_canvas_drag_syncs_property_without_saving
```

Expected: FAIL before `mouse.up()` because the selection box moves during `pointermove` but actual DOM waits for the later full render。

- [ ] **Step 3: 在 pointermove 套用 working geometry**

In `startPointer()`'s `move` handler, immediately after `state.present=next;`, call:

```javascript
      applyWorkingLayout();
      renderSelection();
      renderProperties();
```

Do not call `setStateValue()` or write sessionStorage on every frame; existing `pointerup → mark(after)` remains the single history and component-state boundary.

- [ ] **Step 4: 跑綠燈並確認 DB 未偷存**

Run the Step 2 command.

Expected: `1 passed`; the existing assertion still shows exactly one template version before explicit save。

- [ ] **Step 5: 寫 Escape 必須恢復真正 DOM 的紅燈**

In `test_template_canvas_escape_cancels_active_drag()`, record the actual element rectangle before dragging and append after Escape:

```python
            actual_after = actual.bounding_box()
            assert abs(actual_after["x"] - actual_before["x"]) <= 1
            assert abs(actual_after["y"] - actual_before["y"]) <= 1
```

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_template_editor_browser.py::test_template_canvas_escape_cancels_active_drag
```

Expected: FAIL because `state.present` is restored but the actual DOM retains the live-drag style。

- [ ] **Step 6: Escape 同步恢復 DOM**

Change `cancel` in `startPointer()` to:

```javascript
    const cancel=()=>{
      cleanup();
      state.present=before;
      applyWorkingLayout();
      renderSelection();
      renderProperties();
    };
```

Run the Step 5 command. Expected: `1 passed`。

- [ ] **Step 7: 強化 resize／undo／redo 的實際 DOM 回歸證據**

In `test_template_canvas_resize_undo_and_redo_keep_opposite_anchor()`, record actual heading width before resize and assert:

```python
            actual = editor.locator(
                '.template-document [data-layout-id="heading"]'
            )
            actual_before = actual.bounding_box()
            # existing resize action
            actual_resized = actual.bounding_box()
            assert actual_resized["width"] > actual_before["width"]
            editor.get_by_role("button", name="復原").click()
            actual_undone = actual.bounding_box()
            assert abs(
                actual_undone["width"] - actual_before["width"]
            ) <= 1
            editor.get_by_role("button", name="重做").click()
            actual_redone = actual.bounding_box()
            assert abs(
                actual_redone["width"] - actual_resized["width"]
            ) <= 1
```

This is regression coverage for the shared Task 2 renderer path; it should pass without another production change. If it fails, fix only the common synchronization call site, not the test expectations.

- [ ] **Step 8: 跑模板瀏覽器測試並提交**

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_template_editor_browser.py
```

Expected: all pass。

```bash
git add daibu/cards/template_editor_component.py \
  tests/test_template_editor_browser.py
git commit -m "fix: keep template preview live during pointer edits"
```

---

### Task 4: Renderer hook 缺失時阻擋保存

**Files:**
- Modify: `tests/test_cards_template_editor_payload.py`
- Modify: `daibu/cards/template_editor_payload.py`
- Modify: `tests/test_cards_template_editor_component.py`
- Modify: `daibu/cards/template_editor_component.py`

**Interfaces:**
- Produces: `missing_preview_element_ids(preview_html: str, page_type: str) -> tuple[str, ...]`
- Adds payload field: `previewSyncError: str`，正常時為空字串。

- [ ] **Step 1: 寫缺少 hook 的紅燈**

Add to `tests/test_cards_template_editor_payload.py`:

```python
def test_template_payload_reports_missing_renderer_layout_hooks():
    layout = load_builtin_layout()
    version = SimpleNamespace(
        id=11,
        version_no=1,
        created_at="2026-08-23T10:00:00",
        layout=layout,
    )
    payload = template_editor_payload(
        SimpleNamespace(id=7, name="AI 新創介紹"),
        [version],
        version,
        "cover",
        '<main data-layout-id="heading"></main>',
    )
    assert payload["previewSyncError"].startswith("預覽缺少版面元素：")
    assert "company-name" in payload["previewSyncError"]
```

- [ ] **Step 2: 跑紅燈**

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_template_editor_payload.py::test_template_payload_reports_missing_renderer_layout_hooks
```

Expected: FAIL with missing `previewSyncError` key。

- [ ] **Step 3: 實作可信 Renderer hook 檢查**

Add imports and helper to `daibu/cards/template_editor_payload.py`:

```python
import re


_LAYOUT_ID = re.compile(r'data-layout-id=["\u0027]([^"\u0027]+)["\u0027]')


def missing_preview_element_ids(
    preview_html: str,
    page_type: str,
) -> tuple[str, ...]:
    found = set(_LAYOUT_ID.findall(preview_html))
    return tuple(sorted(set(ELEMENT_REGISTRY[page_type]) - found))
```

Before returning the payload:

```python
    missing = missing_preview_element_ids(preview_html, page_type)
    sync_error = (
        "預覽缺少版面元素：" + "、".join(missing)
        if missing
        else ""
    )
```

Add `"previewSyncError": sync_error` to the return mapping.

- [ ] **Step 4: 跑綠燈**

Run the Step 2 command. Expected: `1 passed`。

- [ ] **Step 5: 寫前端保存閘門契約紅燈**

Add to `tests/test_cards_template_editor_component.py`:

```python
def test_template_component_blocks_save_when_preview_hooks_are_missing():
    script = template_editor_component.TEMPLATE_JS
    assert "data.previewSyncError" in script
    assert "save.disabled=!state.dirty||Boolean(syncError)" in script
    assert "preview-sync-error" in script
```

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_template_editor_component.py::test_template_component_blocks_save_when_preview_hooks_are_missing
```

Expected: FAIL because the component ignores `previewSyncError`。

- [ ] **Step 6: 顯示白話錯誤並停用保存**

In `render()` after creating the save button:

```javascript
    const syncError = data.previewSyncError || (
      missing.length
        ? `預覽缺少版面元素：${missing.join("、")}`
        : ""
    );
    save.disabled=!state.dirty||Boolean(syncError);
    versionBar.append(title,save);
    if (syncError) {
      const alert = document.createElement("p");
      alert.className = "preview-sync-error";
      alert.setAttribute("role", "alert");
      alert.textContent = syncError;
      versionBar.append(alert);
    }
```

Move `applyWorkingLayout()` early enough in `render()` that `missing` is available before the save button is finalized. Add compact error styling without introducing another accent color:

```css
.preview-sync-error { margin:0 0 0 12px; color:var(--peach); font-size:12px; font-weight:800; }
```

- [ ] **Step 7: 跑 payload、component 與瀏覽器回歸並提交**

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_template_editor_payload.py \
  tests/test_cards_template_editor_component.py \
  tests/test_template_editor_browser.py
```

Expected: all pass。

```bash
git add daibu/cards/template_editor_payload.py \
  daibu/cards/template_editor_component.py \
  tests/test_cards_template_editor_payload.py \
  tests/test_cards_template_editor_component.py
git commit -m "fix: block saves when template preview hooks are incomplete"
```

---

### Task 5: 產品理解檢查點、完整 QA、合併與正式站驗收

**Files:**
- Modify: `HANDOFF.md`
- Verify only: all production and test files from Tasks 1–4。

**Interfaces:**
- Consumes: all previous task outputs。
- Produces: test evidence, final desktop/mobile screenshots, merged `main`, pushed `origin/main`, verified `http://127.0.0.1:8501`。

- [ ] **Step 1: 在全測與 commit 前交付九欄產品理解檢查點**

Record in commentary and later in `HANDOFF.md`:

1. 產品能力：模板畫布顯示角色占位符並真正移動內容。
2. 使用者體驗：不用猜 SUN 是否固定，也不再看到框與內容分離。
3. 技術結構：占位組裝器、正式 Renderer、前端同步層、保存驗證層。
4. 資料流程：占位草稿只進預覽；working layout 同時驅動 DOM 與 overlay；保存才進 DB。
5. 設計理由：保留一套 Renderer，避免預覽與正式 PNG 漂移。
6. 替代方案：每幀回 Python 重產 HTML 較單純但延遲高，因此只作備援。
7. 安全與成本：白名單屬性、無 schema／外部依賴／LLM／付費變更。
8. 測試證據：紅燈原因、聚焦綠燈、完整 pytest、真實 Chromium、兩輪截圖。
9. 剩餘限制：手機唯讀；仍不支援新增／刪除／旋轉／改圖層與品牌系統。

- [ ] **Step 2: 跑靜態檢查與完整測試**

Run:

```bash
git diff --check
PYTHON_DOTENV_DISABLED=1 .venv/bin/python -m compileall -q daibu pages app.py server.py
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q
```

Expected: `git diff --check` and `compileall` exit 0; full suite is at least the baseline `718 passed, 16 deselected` plus new tests, with only the known Starlette/httpx deprecation warning。

- [ ] **Step 3: 用隔離資料庫啟動視覺 QA 站**

Create a recoverable database copy; do not edit formal `daibu.db`:

```bash
qa_dir=$(mktemp -d /tmp/daibu-template-preview-qa.XXXXXX)
cp daibu.db "$qa_dir/daibu.db"
DAIBU_DB_PATH="$qa_dir/daibu.db" PYTHON_DOTENV_DISABLED=1 \
  .venv/bin/streamlit run app.py --server.headless=true \
  --server.port=8502 --server.address=127.0.0.1
```

Expected: `http://127.0.0.1:8502/_stcore/health` returns `ok`。Keep the exact process session so it can be terminated after QA; do not kill by broad process name.

- [ ] **Step 4: 第一輪桌機／手機截圖與八項自評**

Run from the project root:

```bash
mkdir -p .screenshots
playwright-cli open http://127.0.0.1:8502
playwright-cli goto http://127.0.0.1:8502/%E8%A8%AD%E5%AE%9A
playwright-cli resize 1280 800
playwright-cli screenshot --filename=.screenshots/template-live-preview-round1-desktop.png
playwright-cli resize 375 812
playwright-cli screenshot --filename=.screenshots/template-live-preview-round1-mobile.png
```

Read only these two new images. Explicitly score: hierarchy, whitespace rhythm, font distinction, maximum three main colors, shared alignment lines, 375px overflow, focus/error/read-only states, and subtle interaction feedback. Also verify visible copy includes semantic placeholders and excludes the three test company names.

If any item fails, add one focused failing test for the defect, make the minimum repair, rerun that file, and only then continue.

- [ ] **Step 5: 第二輪截圖與 interaction verification**

Run:

```bash
playwright-cli resize 1280 800
playwright-cli screenshot --filename=.screenshots/template-live-preview-round2-desktop.png
playwright-cli resize 375 812
playwright-cli screenshot --filename=.screenshots/template-live-preview-round2-mobile.png
playwright-cli console
```

Expected: all eight visual checks pass; desktop drag visibly moves content and selection together; mobile is read-only with `scrollWidth == clientWidth == 375`; console has 0 errors and 0 warnings. Close the browser and terminate only the QA Streamlit process.

- [ ] **Step 6: 正式內容回歸**

Run the existing Renderer and template service tests that use SUN／Billow／Shiraz as real stress inputs:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_render.py \
  tests/test_cards_template_stress.py \
  tests/test_cards_template_editor_service.py \
  tests/test_cards_layout_validation.py
```

Expected: all pass, proving real company names and Logo remain in production rendering while editor placeholders stay isolated。

- [ ] **Step 7: 更新 HANDOFF 並提交**

Add a new top section to `HANDOFF.md` containing the nine-field checkpoint, exact pass counts, red-light causes, final screenshot paths, DB non-write evidence, remaining limits and deployment result.

Run:

```bash
git diff --check
git status --short
git add HANDOFF.md
git commit -m "docs: record template preview synchronization QA"
```

Expected: only intended project files are committed; existing user files in the primary checkout remain untouched。

- [ ] **Step 8: 自審、合併 main、在 main 重跑全套**

Review the complete branch diff against the design spec. Verify no arbitrary style input, no placeholder leakage into formal output, no unrelated refactor and no uncommitted feature files.

Then from the primary checkout:

```bash
git merge --no-ff codex/template-editor-live-preview
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q
git diff --check
```

Expected: merge has no conflict; the same complete suite passes on `main`。If main contains overlapping uncommitted user changes or any test fails, stop and report exact evidence instead of pushing.

- [ ] **Step 9: Push and restart the existing local production service**

```bash
git push origin main
.venv/bin/python -m daibu.local_service status
.venv/bin/python -m daibu.local_service install
curl --fail --silent --show-error \
  http://127.0.0.1:8501/_stcore/health
```

Expected: `origin/main` contains the merge commit; the exact LaunchAgent `io.daibu.content-brain` is loaded and healthy; health returns `ok`; listener remains `127.0.0.1:8501`。If the known macOS bootout/bootstrap race occurs, inspect exact service state and recover only the exact label; never kill by broad process name.

- [ ] **Step 10: 正式站使用者視角驗收**

Open `http://127.0.0.1:8501` from the root page, navigate normally to 設定, and verify at 1280×800 and 375×812:

- semantic placeholders are visible and no test company is presented as the template default;
- dragging an element moves the actual content and selection together;
- editing without saving leaves the version count unchanged;
- mobile remains read-only with no horizontal overflow;
- console and current server log contain no new critical error.

Capture final evidence as:

```text
.screenshots/template-live-preview-production-desktop.png
.screenshots/template-live-preview-production-mobile.png
```

Update the top `HANDOFF.md` status with the final production evidence, amend only the documentation commit if needed, push the updated `main`, and re-check health.

---

## Completion Criteria

- Template editor uses semantic placeholders on all seven pages and never presents SUN／Billow／Shiraz as defaults.
- Actual DOM and selection box move within 1 CSS px of each other for property edits and live pointer edits.
- Escape, resize, undo and redo leave actual DOM, selection and property values consistent.
- Missing Renderer hooks produce a visible error and disable saving.
- Production Renderer still uses real company content and Logo.
- Focused tests, full suite, compileall, diff check, two visual QA rounds and production browser verification all pass.
- Work is merged to `main`, pushed to existing origin and served at the existing `http://127.0.0.1:8501` URL.
