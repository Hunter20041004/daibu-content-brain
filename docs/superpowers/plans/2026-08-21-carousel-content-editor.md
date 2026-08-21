# 七頁內容編輯器與即時預覽 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. UI tasks 必須依專案規則同時套用 `frontend-design`、`emil-design-eng`、`ui-ux-pro-max` 與 `playwright-cli`。

**Goal:** 用左側七頁導覽、中間內容欄位與右側同頁即時預覽取代七份長表單，讓所有貼文內容含 diagram nodes 可修改，七頁只有通過真實版面檢查才一起保存與產圖。

**Architecture:** Python 將已存 `CarouselDraft`、鎖定證據、七頁 Renderer HTML 與 content revision 序列化給一個本機 `st.components.v2` 元件。元件在瀏覽器維護未存 working copy、用 `data-edit-key` 直接更新同源預覽 DOM，並只在「儲存全部」時把完整 payload 送回 Python；Python 重建 draft、保留鎖定資料、跑 Chromium validator 後原子保存。

**Tech Stack:** Python 3.11+、Streamlit Components v2（Streamlit 1.60+）、原生 HTML/CSS/ES modules、sessionStorage、SQLite、Playwright、pytest、Streamlit AppTest。

## Global Constraints

- 前置條件：`2026-08-21-carousel-layout-foundation.md` 全部完成且全套測試綠燈。
- 嚴格 Red → Green → Refactor，一次只寫一個失敗測試。
- 七頁切換保留未存內容；未按「儲存全部變更」前不寫 SQLite。
- 所有觀眾可見的內容文字可改：heading、section text、DiagramNode title/text/expression。
- page number/type、section label、diagram kind／node 數量、source IDs、evidence quotes、source label 鎖定。
- 即時預覽不可重做第二套模板；只更新 Python Renderer 已輸出的 `data-edit-key` 文字節點。
- 有未存修改、字數硬超限或 layout issue 時禁止產圖。
- 儲存失敗保留 working copy、目前頁與輸入；不自動縮字、不截字、不改寫。
- Component 不接受使用者 HTML/CSS；預覽 HTML只能來自已 escape 的 Python Renderer。
- 不載 CDN、不新增 npm build；使用 Streamlit 1.60 已提供的 Components v2。
- 桌面三欄；375px 變成橫向頁籤＋表單＋預覽，禁止水平捲動。

## File Map

- Create `daibu/cards/editor_payload.py`: draft ↔ 安全 editor payload、欄位 key 與 working copy 重建。
- Create `daibu/cards/editor_component.py`: Components v2 的 HTML/CSS/JS 與 Python wrapper。
- Create `daibu/cards/editor_service.py`: 保存管線、版面錯誤轉成頁／欄位錯誤。
- Create `daibu/cards/editor_ui.py`: 內容工作台與既有重新產生／來源查看／產圖操作的協調層。
- Modify `daibu/cards/render.py`: 為所有可編輯文字加入穩定 `data-edit-key`。
- Modify `pages/1_選題.py:1738-2023`: 以新工作台取代七份垂直表單，不動正文與 Logo 區。
- Modify `requirements.txt`: pin `streamlit>=1.60,<2`，保證 Components v2 API。
- Create tests `tests/test_cards_editor_payload.py`、`tests/test_cards_editor_service.py`、`tests/test_cards_editor_component.py`、`tests/test_carousel_editor_browser.py`。
- Modify `tests/test_app_smoke.py`、`tests/test_cards_render.py`、`tests/test_cards_workbench.py`。

---

### Task 1: 安全的 content field key 與 working copy 重建

**Files:**
- Create: `daibu/cards/editor_payload.py`
- Create: `tests/test_cards_editor_payload.py`

**Interfaces:**
- Produces: `EditableField(key, page_type, label, value, input_kind, recommended_chars, hard_chars, options)`
- Produces: `LockedEvidence(label, source_ids, quotes)`
- Produces: `draft_to_editor_payload(draft, preview_html, revision) -> dict[str, object]`
- Produces: `apply_editor_values(saved_draft, values: Mapping[str, str]) -> CarouselDraft`
- Produces key format: `page.<page_type>.heading`、`.section.<index>.text`、`.diagram.<index>.<title|text|expression>`

- [ ] **Step 1: 寫第一個紅燈，只驗證 diagram 可改、來源不可被 payload 覆寫**

```python
from daibu.cards.editor_payload import apply_editor_values
from tests.card_fixtures import carousel_draft


def test_editor_values_update_diagram_text_but_preserve_evidence():
    original = carousel_draft()
    values = {
        "page.problem.heading": "新的問題標題",
        "page.problem.diagram.0.title": "新的第一步",
        "page.problem.diagram.0.text": "新的節點說明",
        "page.problem.diagram.0.expression": "think",
    }
    edited = apply_editor_values(original, values)
    problem = edited.pages[2]
    assert problem.heading == "新的問題標題"
    assert problem.diagram.nodes[0].title == "新的第一步"
    assert problem.diagram.nodes[0].text == "新的節點說明"
    assert problem.sections[0].source_ids == original.pages[2].sections[0].source_ids
    assert problem.sections[0].evidence_quotes == original.pages[2].sections[0].evidence_quotes
```

- [ ] **Step 2: 跑紅燈**

Run: `.venv/bin/pytest -q tests/test_cards_editor_payload.py::test_editor_values_update_diagram_text_but_preserve_evidence`

- [ ] **Step 3: 實作 parser，只接受由原 draft 派生的合法 key**

```python
def editable_values(draft):
    values = {}
    for page in draft.pages:
        prefix = f"page.{page.page_type}"
        values[f"{prefix}.heading"] = page.heading
        for index, section in enumerate(page.sections):
            values[f"{prefix}.section.{index}.text"] = section.text
        if page.diagram:
            for index, node in enumerate(page.diagram.nodes):
                values[f"{prefix}.diagram.{index}.title"] = node.title
                values[f"{prefix}.diagram.{index}.text"] = node.text
                values[f"{prefix}.diagram.{index}.expression"] = node.expression
    return values
```

`apply_editor_values()` 先比較 `set(values) <= set(editable_values(saved_draft))`；未知 key 拋 `ValueError("內容欄位不存在：…")`，再用 `dataclasses.replace()` 重建 frozen dataclasses。

`DiagramNode.expression` 不是自由文字，只接受 `daibu.cards.mascot.EXPRESSIONS` 的 `listen|think|happy|concerned`；未知表情拋 `ValueError("圖解表情不存在")`，不使用 Renderer 的 fallback 默默改成 think。

- [ ] **Step 4: 轉綠後逐一新增兩個紅燈**

1. 未知 key 不能改 page type／source。
2. section 與 diagram node 數量完全不變。

- [ ] **Step 5: 實作 payload**

payload 每頁包含 `number`、`pageType`、人類頁名、fields、lockedEvidence、`previewHtml`；另有由 Python `q_head_svg()` 產生的固定 `expressionPreviews`。heading／section／node title/text 的 `inputKind="text"`，expression 的 `inputKind="expression"` 且 options 只有四個白名單值。quote 當純文字值，不能混入 HTML。

- [ ] **Step 6: Commit**

```bash
git add daibu/cards/editor_payload.py tests/test_cards_editor_payload.py
git commit -m "feat: serialize safe carousel editor payloads"
```

### Task 2: Renderer 提供穩定 `data-edit-key`

**Files:**
- Modify: `daibu/cards/render.py`
- Modify: `tests/test_cards_render.py`

**Interfaces:**
- Consumes: Task 1 key format
- Produces: 每個可編輯文字節點一個且只有一個 `data-edit-key`

- [ ] **Step 1: 寫紅燈，完整 draft 的 keys 必須與七頁 HTML hooks 完全相等**

```python
def test_renderer_exposes_every_editable_value_once(asset):
    draft = carousel_draft()
    expected = set(editable_values(draft))
    outputs = [render.page_html(page, "ElevenLabs", asset) for page in draft.pages]
    found = re.findall(r'data-edit-key="([^"]+)"', "".join(outputs))
    assert set(found) == expected
    assert len(found) == len(expected)
```

- [ ] **Step 2: 跑紅燈，再新增 `_editable_text()`**

```python
def _editable_text(key: str, value: str, *, tag: str = "span", classes: str = "") -> str:
    return (
        f'<{tag} class="{classes}" data-edit-key="{html.escape(key)}">'
        f'{html.escape(value)}</{tag}>'
    )


def _editable_expression(key: str, value: str) -> str:
    if value not in mascot.EXPRESSIONS:
        raise ValueError("圖解表情不存在")
    return (
        f'<span class="expression-hook" data-edit-key="{html.escape(key)}">'
        f'{mascot.q_head_svg(value)}</span>'
    )
```

所有 content 文字只經 `_editable_text()`；diagram expression 只經 `_editable_expression()` 將已知白名單 SVG 包進穩定 hook。結構 label 仍是普通 escaped text，不加 edit key。

- [ ] **Step 3: 跑綠並檢查 script injection 測試**

Run: `.venv/bin/pytest -q tests/test_cards_render.py`

- [ ] **Step 4: Commit**

```bash
git add daibu/cards/render.py tests/test_cards_render.py
git commit -m "feat: expose stable carousel edit hooks"
```

### Task 3: 本機 Components v2 內容模式骨架

**Files:**
- Modify: `requirements.txt`
- Create: `daibu/cards/editor_component.py`
- Create: `tests/test_cards_editor_component.py`

**Interfaces:**
- Produces: `ContentEditorEvent(dirty: bool, save_payload: Mapping[str, object] | None)`
- Produces: `mount_content_editor(payload, *, key) -> ContentEditorEvent`
- Component state: `dirty`; trigger: `save`

- [ ] **Step 1: 寫版本與元件契約紅燈**

```python
from daibu.cards import editor_component


def test_content_component_has_seven_page_navigation_and_save_trigger():
    assert 'data-role="page-rail"' in editor_component.CONTENT_HTML
    assert 'setTriggerValue("save"' in editor_component.CONTENT_JS
    assert 'sessionStorage' in editor_component.CONTENT_JS
    assert 'data-edit-key' in editor_component.CONTENT_JS
```

- [ ] **Step 2: 跑紅燈；pin Streamlit 並註冊 v2 component**

`requirements.txt` 將 `streamlit` 改成 `streamlit>=1.60,<2`。

```python
import streamlit as st

_content_component = st.components.v2.component(
    "daibu_carousel_content_editor",
    html=CONTENT_HTML,
    css=CONTENT_CSS,
    js=CONTENT_JS,
    isolate_styles=True,
)
```

- [ ] **Step 3: 實作 HTML 與設計代幣**

root 只能包含 page rail、field panel、preview、status/action bar 四區；CSS 變數固定 `--ink:#102f3d`、`--teal:#2f7c87`、`--cyan:#86ccd4`、`--peach:#ec9870`、`--paper:#fafbf8`。桌面 grid 為 `132px minmax(320px,1fr) minmax(360px,.9fr)`，不是等寬卡片牆。

- [ ] **Step 4: 實作 JS working copy**

```javascript
export default function(component) {
  const {data, parentElement, setStateValue, setTriggerValue} = component;
  const storageKey = `daibu-carousel-${data.ideaId}`;
  const saved = JSON.parse(sessionStorage.getItem(storageKey) || "null");
  const state = saved && saved.revision === data.revision
    ? saved
    : {revision: data.revision, pageType: data.pages[0].pageType, values: data.values, dirty: false};

  function persist() {
    sessionStorage.setItem(storageKey, JSON.stringify(state));
  }
  function markDirty(value = true) {
    if (value && !state.dirty) {
      state.dirty = true;
      setStateValue("dirty", true);
    }
    persist();
  }
  function updatePreview(key, value) {
    const field = data.fieldsByKey[key];
    parentElement.querySelectorAll(`[data-edit-key="${CSS.escape(key)}"]`)
      .forEach(node => {
        if (field.inputKind === "expression") {
          const template = document.createElement("template");
          template.innerHTML = data.expressionPreviews[value];
          node.replaceChildren(template.content.cloneNode(true));
        } else {
          node.textContent = value;
        }
      });
  }
  function saveAll() {
    setTriggerValue("save", {revision: data.revision, values: state.values});
  }
  renderEditor(parentElement, data, state, {markDirty, updatePreview, saveAll});
}
```

`renderEditor` 使用 `document.createElement` 與 `textContent` 建 inputs／labels／evidence；只有 `previewHtml` 與白名單固定 `expressionPreviews` 是 Python Renderer 產生的 trusted strings，可放入 preview root。不得對使用者文字 values 使用 `innerHTML`；expression value 只用來查白名單 map，不拼 HTML。

`renderEditor()` 必須在同一個 JS module 實作以下完整責任：

```javascript
function pageStatus(page, state, fieldsByKey) {
  let status = "saved";
  for (const item of page.fields) {
    const field = fieldsByKey[item.key];
    const value = state.values[item.key];
    if (field.inputKind === "text" && value.length > field.hardChars) return "error";
    if (field.inputKind === "text" && value.length > field.recommendedChars) status = "warning";
    else if (value !== item.value && status === "saved") status = "dirty";
  }
  return status;
}


function renderEditor(root, data, state, actions) {
  root.replaceChildren();
  const rail = document.createElement("nav");
  rail.dataset.role = "page-rail";
  const form = document.createElement("section");
  form.dataset.role = "field-panel";
  const preview = document.createElement("section");
  preview.dataset.role = "preview";
  const previewRoot = document.createElement("div");
  previewRoot.className = "carousel-preview";
  previewRoot.innerHTML = data.pages.find(page => page.pageType === state.pageType).previewHtml;
  preview.append(previewRoot);

  for (const page of data.pages) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `${page.number} ${page.label}`;
    button.dataset.pageType = page.pageType;
    button.dataset.status = pageStatus(page, state, data.fieldsByKey);
    button.setAttribute("aria-current", page.pageType === state.pageType ? "page" : "false");
    button.addEventListener("click", () => {
      state.pageType = page.pageType;
      actions.markDirty(false);
      renderEditor(root, data, state, actions);
    });
    rail.append(button);
  }

  const current = data.pages.find(page => page.pageType === state.pageType);
  for (const field of current.fields) {
    const label = document.createElement("label");
    label.textContent = field.label;
    const input = document.createElement(
      field.inputKind === "expression" ? "select" : "textarea"
    );
    input.name = field.key;
    if (field.inputKind === "expression") {
      for (const value of field.options) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = data.expressionLabels[value];
        input.append(option);
      }
    }
    input.value = state.values[field.key];
    input.addEventListener("input", event => {
      state.values[field.key] = event.currentTarget.value;
      actions.markDirty(true);
      actions.updatePreview(field.key, event.currentTarget.value);
      renderActionBar();
    });
    label.append(input);
    if (field.inputKind === "text") {
      const counter = document.createElement("small");
      counter.dataset.role = "character-count";
      const refreshLimit = () => {
        const count = input.value.length;
        counter.textContent = `${count} / ${field.recommendedChars}`;
        counter.dataset.limit = count > field.hardChars
          ? "hard"
          : count > field.recommendedChars ? "near" : "normal";
        input.setAttribute("aria-invalid", count > field.hardChars ? "true" : "false");
      };
      input.addEventListener("input", refreshLimit);
      refreshLimit();
      label.append(counter);
    }
    form.append(label);
  }

  const evidence = document.createElement("details");
  const evidenceLabel = document.createElement("summary");
  evidenceLabel.textContent = "查證來源（鎖定）";
  evidence.append(evidenceLabel);
  for (const item of current.lockedEvidence) {
    const line = document.createElement("p");
    line.textContent = `${item.label}：${item.quotes.join("／")}`;
    evidence.append(line);
  }
  form.append(evidence);

  const actionBar = document.createElement("aside");
  actionBar.dataset.role = "action-bar";
  const save = document.createElement("button");
  save.type = "button";
  save.textContent = "儲存全部變更";
  save.addEventListener("click", actions.saveAll);
  actionBar.append(save);
  function renderActionBar() {
    const hardIssue = Object.entries(state.values).some(([key, value]) => {
      const field = data.fieldsByKey[key];
      return field && field.inputKind === "text" && value.length > field.hardChars;
    });
    save.disabled = !state.dirty || hardIssue;
    actionBar.dataset.status = hardIssue ? "invalid" : state.dirty ? "dirty" : "saved";
  }
  renderActionBar();
  root.append(rail, form, preview, actionBar);
  for (const [key, value] of Object.entries(state.values)) {
    actions.updatePreview(key, value);
  }
}
```

切頁的 `actions.markDirty(false)` 只負責 `persist()`，不可把原本的 dirty 狀態改成 false；`markDirty(value)` 只在 `value === true` 時首次通知 Streamlit。重繪時先套用目前 working copy 的所有 `state.values` 到 preview hooks，因此切頁不會丟失未存預覽。

`pageStatus()` 以該頁欄位和已存 `data.values` 比較：超過 hard limit 是 `error`、超過 recommended 是 `warning`、值有變是 `dirty`、否則 `saved`；page rail 以文字＋圖示同時呈現，不只靠顏色。伺服器 Chromium issues 回傳後覆蓋成 `error`並自動回到第一個錯誤頁。

- [ ] **Step 5: Python wrapper**

mount 時傳 `default={"dirty": False}`、`on_dirty_change=lambda: None`、`on_save_change=lambda: None`；把 `result.save` 正規化成 dict，沒有 trigger 時為 `None`。

- [ ] **Step 6: 轉綠並 Commit**

```bash
git add requirements.txt daibu/cards/editor_component.py tests/test_cards_editor_component.py
git commit -m "feat: add local carousel content component"
```

### Task 4: 七頁精準保存服務

**Files:**
- Create: `daibu/cards/editor_service.py`
- Create: `tests/test_cards_editor_service.py`

**Interfaces:**
- Produces: `EditorIssue(page_type, field_key, message)`
- Produces: `SaveResult(draft, revision, issues)`
- Produces: `save_editor_payload(conn, idea_id, saved_draft, payload, company, asset) -> SaveResult`

- [ ] **Step 1: 寫 rollback 紅燈**

用 heading 高度 20px 的測試 template 讓 Chromium 回 overflow；呼叫服務後要求 DB draft/meta 完全不變、結果含 `page_type='cover'`、`field_key='page.cover.heading'`。

- [ ] **Step 2: 跑紅燈，再實作保存管線**

```python
def save_editor_payload(conn, idea_id, saved_draft, payload, company, asset):
    meta = db.get_carousel_draft_meta(conn, idea_id)
    if meta is None or payload["revision"] != meta.content_revision:
        return SaveResult(saved_draft, meta.content_revision if meta else 0, (
            EditorIssue(None, None, "草稿已在其他畫面更新，請重新載入後再修改。"),
        ))
    try:
        edited = apply_editor_values(saved_draft, payload["values"])
        validate_draft(edited)
    except (ValueError, DraftValidationError) as error:
        return SaveResult(saved_draft, meta.content_revision, map_content_issues(error))
    version = layout_repository.get_version(conn, meta.template_version_id)
    html_pages = render.draft_html_pages(edited, company, asset, version.layout)
    issues = layout_validation.inspect_pages(html_pages)
    if issues:
        return SaveResult(edited, meta.content_revision, map_layout_issues(issues))
    try:
        db.save_carousel_draft(
            conn, idea_id, edited, expected_revision=payload["revision"]
        )
    except RevisionConflict as error:
        return SaveResult(saved_draft, error.actual_revision, (
            EditorIssue(None, None, "草稿已在其他畫面更新，請重新載入後再修改。"),
        ))
    new_meta = db.get_carousel_draft_meta(conn, idea_id)
    return SaveResult(edited, new_meta.content_revision, ())
```

`map_layout_issues()` 用 element registry 與 renderer 的 element→field map 轉成可行動中文；不顯示 HTML 檔名。

- [ ] **Step 3: 轉綠後新增成功保存紅燈**

要求七頁所有更新一起寫入、revision +1、template_version_id 不變、舊 PNG fingerprint 失效。

- [ ] **Step 4: 聚焦測試與 Commit**

Run: `.venv/bin/pytest -q tests/test_cards_editor_service.py tests/test_db.py`

```bash
git add daibu/cards/editor_service.py tests/test_cards_editor_service.py
git commit -m "feat: save seven carousel pages atomically"
```

### Task 5: 接入選題工作台並移除七份長表單

**Files:**
- Create: `daibu/cards/editor_ui.py`
- Modify: `pages/1_選題.py:1738-2023`
- Modify: `tests/test_app_smoke.py`

**Interfaces:**
- Produces: `render_content_workbench(conn, idea, draft, asset) -> ContentWorkbenchState`
- Consumes: Task 3 component、Task 4 save service、現有重新產生／重新研究／PNG／ZIP 操作

- [ ] **Step 1: 改寫既有 smoke test 先紅**

`test_saved_carousel_draft_shows_seven_editable_pages` 不再找 7 個 `st.text_input`；改 monkeypatch `editor_ui.mount_content_editor` 捕捉 payload，要求七頁、每頁 preview、diagram fields 與 locked evidence 存在，頁面沒有舊「儲存草稿」按鈕。

- [ ] **Step 2: 跑單一紅燈**

Run: `.venv/bin/pytest -q tests/test_app_smoke.py::test_saved_carousel_draft_shows_seven_editable_pages`

- [ ] **Step 3: 實作 `editor_ui.py`**

1. 取得 draft meta 與綁定 TemplateVersion。
2. 用同一 Renderer 產七頁 HTML。
3. 建 payload、mount component。
4. 若 `save_payload` 存在，顯示 spinner、呼叫 service；issues 用頁碼／欄位顯示，成功 toast＋rerun。
5. 回傳 `dirty`，供產圖按鈕判斷。

- [ ] **Step 4: 在 `pages/1_選題.py` 精確替換舊 editor block**

保留重新產生、重新搜尋、Logo、PNG 預覽、ZIP、正文與發布流程；只刪除七個 container、text inputs、text areas 與舊 save button。

- [ ] **Step 5: smoke 轉綠後，新增保存 action AppTest**

monkeypatch component 回傳合法 save payload，要求 DB 更新與 toast；再回傳非法 payload，要求 DB 不變且錯誤存在。

- [ ] **Step 6: Commit**

```bash
git add daibu/cards/editor_ui.py pages/1_選題.py tests/test_app_smoke.py
git commit -m "feat: replace carousel forms with page editor"
```

### Task 6: 未存狀態阻擋產圖與離開提示

**Files:**
- Modify: `daibu/cards/editor_component.py`
- Modify: `daibu/cards/editor_ui.py`
- Modify: `pages/1_選題.py`
- Modify: `tests/test_app_smoke.py`
- Modify: `tests/test_cards_editor_component.py`

**Interfaces:**
- Produces: `ContentWorkbenchState(dirty, issues, revision)`

- [ ] **Step 1: 寫產圖阻擋紅燈**

component result `dirty=True` 時，「產生七張圖」disabled 且旁邊顯示「先儲存七頁變更，再產生圖片」；DB 與快取不變。

- [ ] **Step 2: 轉綠後寫離開提示紅燈**

Component JS 在 dirty 時註冊 `beforeunload`，clean 時移除；點重新產生／重新搜尋改由 component trigger `requestRegenerate`／`requestResearch`，Python 維持既有二次確認。

- [ ] **Step 3: 保存成功清理 sessionStorage**

revision 改變時 component 必須捨棄舊 storage；不得清除其他 idea 的 key。

- [ ] **Step 4: 聚焦測試與 Commit**

```bash
.venv/bin/pytest -q tests/test_cards_editor_component.py tests/test_app_smoke.py -k carousel
git add daibu/cards/editor_component.py daibu/cards/editor_ui.py pages/1_選題.py tests/test_cards_editor_component.py tests/test_app_smoke.py
git commit -m "feat: guard unsaved carousel changes"
```

### Task 7: 真實瀏覽器互動契約

**Files:**
- Create: `tests/test_carousel_editor_browser.py`
- Create: `tests/browser_support.py`

**Interfaces:**
- Produces fixture: `running_streamlit(tmp_path, seed_fn) -> base_url`

- [ ] **Step 1: 建立受控本機 server fixture**

用未占用 loopback port 啟動 `.venv/bin/streamlit run app.py --server.headless true`，環境只指向 tmp SQLite；輪詢 `/_stcore/health`，finally terminate 精確 PID。不得接正式 `daibu.db`。

- [ ] **Step 2: 寫第一個瀏覽器紅燈：切頁保留未存值**

1. 開啟 seeded 已採用 idea。
2. 在第 3 頁 diagram textarea 輸入「新的流程節點」。
3. 點第 5 頁，再回第 3 頁。
4. 要求值與 preview text 都是新字，SQLite 仍是舊字。

- [ ] **Step 3: 實作／修正 component 直到轉綠**

只跑此測試；不可先新增下一個。

- [ ] **Step 4: 依序新增兩個瀏覽器切片**

1. 超過 hard limit：欄位紅色、頁籤紅點、save disabled、generate disabled。
2. 合法 save：顯示檢查中、成功後 SQLite 更新、dirty 消失、preview 不跳頁。

- [ ] **Step 5: Commit**

```bash
git add tests/browser_support.py tests/test_carousel_editor_browser.py daibu/cards/editor_component.py
git commit -m "test: cover live carousel editing boundary"
```

### Task 8: 兩輪視覺 QA、完整流程與 Phase B 收尾

**Files:**
- Modify: `HANDOFF.md`
- Modify: `.gitignore`
- Verify: `.screenshots/carousel-editor-round1-desktop.png`
- Verify: `.screenshots/carousel-editor-round1-mobile.png`
- Verify: `.screenshots/carousel-editor-round2-desktop.png`
- Verify: `.screenshots/carousel-editor-round2-mobile.png`

**Interfaces:**
- Consumes: SUN、Billow AI Labs、Shiraz AI 三家公司 fixture
- Produces: 可日常使用的內容編輯器，模板畫布仍未接入

- [ ] **Step 1: 第一輪 1280×800 與 375×812 截圖**

依前端硬規則逐項寫明不合格：層次、留白、LINE Seed、三色限制、對齊、手機 overflow、hover/focus、loading/error/empty、微動效。舊截圖不要重讀。

- [ ] **Step 2: 每個不合格項先加可重現測試再修**

同時逐頁看七頁預覽，特別檢查長標題換行、企業 Logo、呆一布、安全範圍與錯誤定位。

- [ ] **Step 3: 第二輪兩尺寸截圖**

要求八項全部合格、375px `scrollWidth == clientWidth`、console 0 errors／0 warnings。

- [ ] **Step 4: 真實 tmp DB 完整流程**

修改 heading／section／diagram → 切七頁 → 儲存 → 產七圖 → ZIP；確認七張圖使用新文字、無 source/date/page number，原 evidence 仍存在。

- [ ] **Step 5: 全套測試**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q
.venv/bin/python -m compileall -q daibu pages
git diff --check
```

- [ ] **Step 6: 更新 HANDOFF 產品理解檢查點並 Commit**

```bash
git add requirements.txt .gitignore daibu/cards/editor_payload.py daibu/cards/editor_component.py daibu/cards/editor_service.py daibu/cards/editor_ui.py daibu/cards/render.py pages/1_選題.py tests/browser_support.py tests/test_cards_editor_payload.py tests/test_cards_editor_component.py tests/test_cards_editor_service.py tests/test_cards_render.py tests/test_cards_workbench.py tests/test_carousel_editor_browser.py tests/test_app_smoke.py HANDOFF.md
git commit -m "feat: deliver live seven-page carousel editor"
```
