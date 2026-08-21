# 輪播模板版本與共用排版基礎 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Renderer 與視覺驗收 tasks 必須依專案規則同時套用 `frontend-design`、`emil-design-eng`、`ui-ux-pro-max` 與 `playwright-cli`。

**Goal:** 把已核可 v15.1 視覺搬入正式 Renderer，建立安全的 Layout Document、模板版本、草稿綁定與真實 Chromium 版面驗證，且不改壞任何既有內容。

**Architecture:** 用固定 1080×1350 座標的 `LayoutDocument` 描述七頁已登錄元素；不可變的 v15.1 HTML/CSS 是基準模板，Layout CSS 只套用伺服器驗證過的幾何與文字屬性。SQLite 保存每系列的模板版本與 active pointer，每份草稿固定綁一版；預覽、驗證與 PNG 共用同一個 Renderer。

**Tech Stack:** Python 3.11+、Streamlit 1.60+、SQLite、dataclasses、JSON、Playwright／Chromium、pytest。

## Global Constraints

- 嚴格 Red → Green → Refactor；一次只新增一個失敗測試，轉綠後才進下一個。
- 正式畫布固定 `1080×1350`；PNG 輸出尺寸不得改變。
- v15.1 參考檔只讀：`/Users/cengweiting/Developer/daibu-content-brain/.superpowers/brainstorm/31101-1787251453/content/multi-company-template-stress-v13.html`。
- 初始模板保留正式 Logo 安全區、右側大型企業名稱與呆一布機器人；圖片不顯示頁碼、來源或日期。
- `carousel_pages`、`carousel_sources`、ideas、正文、Logo 與狀態的既有內容在 migration 前後必須逐欄相同。
- Layout JSON 不接受任意 HTML、CSS、JavaScript、URL、檔案路徑、未知元素或未知屬性。
- 模板版本不可單獨覆寫或刪除；只有使用者確認刪除整個內容系列時才連同刪除其版本。切換 active version 不得改寫既有草稿。
- 不增加 LLM 呼叫、付費服務或外部 CDN。
- 本計畫完成後才可執行 `2026-08-21-carousel-content-editor.md`；模板畫布計畫也依賴本計畫。

## File Map

- Create `daibu/cards/layout_schema.py`: Layout dataclass、JSON parser、白名單與數值驗證。
- Create `daibu/cards/layout_registry.py`: 七頁元素 ID、可調屬性、碰撞政策與使用者名稱。
- Create `daibu/cards/layout_repository.py`: 模板版本、active pointer、版本查詢與切換。
- Create `daibu/cards/layout_validation.py`: Chromium bounding-box、文字溢出與碰撞報告。
- Create `daibu/cards/layouts/editorial-v15-1.json`: 由核可原型量出的正式 v1 幾何。
- Create `daibu/cards/templates/editorial-v15-1.html`: 固定 1080×1350 外殼。
- Create `daibu/cards/templates/editorial-v15-1.css`: 不再任意修改的 v15.1 基準視覺。
- Create `scripts/extract_carousel_layout.py`: 從核可原型量測並輸出初始 Layout JSON。
- Modify `daibu/db.py`: 新表、backfill、草稿 metadata 與刪除一致性。
- Modify `daibu/cards/render.py`: 以 `CarouselDraft／CarouselPage + TemplateVersion` 產生同源 HTML。
- Modify `daibu/cards/shoot.py`: 接受模板版本並共用 Layout Validator。
- Modify `daibu/cards/workbench.py`: 圖片快取指紋包含模板版本與內容 revision。
- Test `tests/test_cards_layout_schema.py`、`tests/test_cards_layout_repository.py`、`tests/test_cards_layout_validation.py`。
- Modify tests `tests/test_db_migration.py`、`tests/test_db.py`、`tests/test_cards_render.py`、`tests/test_cards_shoot.py`。

---

### Task 1: Layout schema 與元素白名單

**Files:**
- Create: `daibu/cards/layout_schema.py`
- Create: `daibu/cards/layout_registry.py`
- Create: `tests/test_cards_layout_schema.py`

**Interfaces:**
- Produces: `LayoutRect`、`TextStyle`、`LayoutElement`、`LayoutPage`、`LayoutDocument`
- Produces: `parse_layout(value: Mapping[str, object]) -> LayoutDocument`
- Produces: `layout_to_mapping(document: LayoutDocument) -> dict[str, object]`
- Produces: `replace_element(document: LayoutDocument, page_type: str, element_id: str, **changes: object) -> LayoutDocument`
- Produces: `LayoutValidationError(element_id: str | None, message: str)`
- Consumes later: repository、Renderer、模板元件送回的 JSON

- [ ] **Step 1: 寫第一個失敗測試，只要求未知元素被拒絕**

```python
import pytest

from daibu.cards.layout_schema import LayoutValidationError, parse_layout


def test_layout_rejects_unknown_element():
    value = {
        "schema_version": 1,
        "canvas": {"width": 1080, "height": 1350},
        "pages": {
            "cover": {
                "elements": {
                    "unknown-widget": {
                        "x": 0, "y": 0, "w": 100, "h": 100
                    }
                }
            }
        },
    }

    with pytest.raises(LayoutValidationError, match="unknown-widget"):
        parse_layout(value)
```

- [ ] **Step 2: 執行紅燈**

Run: `.venv/bin/pytest -q tests/test_cards_layout_schema.py::test_layout_rejects_unknown_element`

Expected: FAIL，因 `daibu.cards.layout_schema` 尚不存在。

- [ ] **Step 3: 建立七頁 registry 與最小 parser**

```python
# daibu/cards/layout_registry.py
from dataclasses import dataclass


@dataclass(frozen=True)
class ElementRule:
    label: str
    text: bool = False
    collision: str = "avoid"
    min_w: float = 24
    min_h: float = 24
    min_font_size: float = 22
    max_font_size: float = 132


ELEMENT_REGISTRY = {
    "cover": {
        "series": ElementRule("系列名稱", True),
        "company-logo": ElementRule("企業 Logo"),
        "company-name": ElementRule("企業名稱", True, "allow"),
        "heading": ElementRule("封面標題", True),
        "rule": ElementRule("標題分隔線", False, "background", 24, 2),
        "positioning": ElementRule("一句話定位", True),
        "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
    },
    "who": {
        "header": ElementRule("頁首"),
        "heading": ElementRule("頁面標題", True),
        "positioning": ElementRule("白話定位", True),
        "facts": ElementRule("基本資料", True),
        "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
    },
    "problem": {
        "header": ElementRule("頁首"), "heading": ElementRule("頁面標題", True),
        "spine": ElementRule("問題脈絡線", False, "background", 2, 24),
        "stage-1": ElementRule("問題階段一", True),
        "stage-2": ElementRule("問題階段二", True),
        "stage-3": ElementRule("問題階段三", True),
        "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
    },
    "how-ai": {
        "header": ElementRule("頁首"), "heading": ElementRule("頁面標題", True),
        "spine": ElementRule("AI 流程線", False, "background", 2, 24),
        "step-1": ElementRule("流程一", True), "step-2": ElementRule("流程二", True),
        "step-3": ElementRule("流程三", True), "caution": ElementRule("要注意的點", True),
        "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
    },
    "results": {
        "header": ElementRule("頁首"), "before-title": ElementRule("改變前標題", True),
        "before-copy": ElementRule("改變前內容", True),
        "axis": ElementRule("對比軸線", False, "background", 2, 24),
        "to": ElementRule("到", True, "allow"), "after-title": ElementRule("改變後標題", True),
        "after-copy": ElementRule("改變後內容", True),
        "summary": ElementRule("結果摘要", True),
        "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
    },
    "why-care": {
        "header": ElementRule("頁首"), "heading": ElementRule("頁面標題", True),
        "signal-1": ElementRule("觀察訊號一", True),
        "signal-2": ElementRule("觀察訊號二", True),
        "signal-3": ElementRule("觀察訊號三", True),
        "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
    },
    "cta": {
        "header": ElementRule("頁首"), "heading": ElementRule("頁面標題", True),
        "thesis": ElementRule("收束結論", True), "question": ElementRule("讀者問題", True),
        "invitation": ElementRule("互動邀請", True),
        "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
    },
}
```

在 `layout_schema.py` 使用 frozen dataclass；parser 先檢查 canvas 必須恰為 1080×1350、page type 與 element ID 必須出現在 registry，再建立物件。`replace_element()` 只能修改該元素 registry 允許的 `x/y/w/h/font_size/text_align`，以 `dataclasses.replace()` 回傳新的 frozen document；未知屬性仍走同一個 `LayoutValidationError`。

- [ ] **Step 4: 重跑測試轉綠**

Run: `.venv/bin/pytest -q tests/test_cards_layout_schema.py`

Expected: `1 passed`。

- [ ] **Step 5: 逐一新增並轉綠三個垂直測試**

依序新增：負數尺寸、元素超出畫布、文字元素非法 `text_align`。每新增一個先跑紅，再補對應檢查；合法對齊只接受 `left|center|right`。

- [ ] **Step 6: Commit**

```bash
git add daibu/cards/layout_schema.py daibu/cards/layout_registry.py tests/test_cards_layout_schema.py
git commit -m "feat: define safe carousel layout schema"
```

### Task 2: 從核可 v15.1 產生可追蹤的初始 Layout JSON

**Files:**
- Create: `scripts/extract_carousel_layout.py`
- Create: `daibu/cards/layouts/editorial-v15-1.json`
- Modify: `tests/test_cards_layout_schema.py`

**Interfaces:**
- Consumes: 核可原型與 `ELEMENT_REGISTRY`
- Produces: `load_builtin_layout() -> LayoutDocument`

- [ ] **Step 1: 寫失敗測試，要求 built-in layout 完整涵蓋 registry**

```python
from daibu.cards.layout_registry import ELEMENT_REGISTRY
from daibu.cards.layout_schema import load_builtin_layout


def test_builtin_layout_covers_every_registered_element():
    document = load_builtin_layout()
    assert set(document.pages) == set(ELEMENT_REGISTRY)
    for page_type, rules in ELEMENT_REGISTRY.items():
        assert set(document.pages[page_type].elements) == set(rules)
```

- [ ] **Step 2: 跑紅燈**

Run: `.venv/bin/pytest -q tests/test_cards_layout_schema.py::test_builtin_layout_covers_every_registered_element`

Expected: FAIL，因 JSON 與 loader 尚不存在。

- [ ] **Step 3: 建立量測腳本**

腳本用 Python Playwright 讀原型，將三個字型與 mascot URL 換成專案內 `file://` URI，呼叫 `renderCompany('sun')`，再依下列完整 selector map 量測相對於 `.post` 的矩形並縮放到 1080×1350：

```python
SELECTORS = {
    "cover": {"series": ".series", "company-logo": ".cover-logo-v151", "company-name": ".cover-word", "heading": "h2", "rule": ".cover-line", "positioning": ".cover-copy", "mascot": ".mascot"},
    "who": {"header": ".post-head", "heading": ".post-title", "positioning": ".profile-main-v15", "facts": ".profile-detail-v15", "mascot": ".mascot"},
    "problem": {"header": ".post-head", "heading": ".post-title", "spine": ".problem-spine-v15", "stage-1": ".problem-stage-v15:nth-of-type(1)", "stage-2": ".problem-stage-v15:nth-of-type(2)", "stage-3": ".problem-stage-v15:nth-of-type(3)", "mascot": ".mascot"},
    "how-ai": {"header": ".post-head", "heading": ".post-title", "spine": ".how-spine-v15", "step-1": ".how-step-v15:nth-of-type(1)", "step-2": ".how-step-v15:nth-of-type(2)", "step-3": ".how-step-v15:nth-of-type(3)", "caution": ".how-caution-v15", "mascot": ".mascot"},
    "results": {"header": ".post-head", "before-title": ".results-before-v15 .result-title-v15", "before-copy": ".results-before-v15 .result-copy-v15", "axis": ".result-axis-v15", "to": ".result-to-v15", "after-title": ".results-after-v15 .result-title-v15", "after-copy": ".results-after-v15 .result-copy-v15", "summary": ".result-summary-v15", "mascot": ".mascot"},
    "why-care": {"header": ".post-head", "heading": ".post-title", "signal-1": ".signal-primary-v15", "signal-2": ".signal-secondary-v15:nth-child(1)", "signal-3": ".signal-secondary-v15:nth-child(2)", "mascot": ".mascot"},
    "cta": {"header": ".post-head", "heading": ".post-title", "thesis": ".closing-lead-v15", "question": ".closing-question-v15", "invitation": ".closing-cta-v15", "mascot": ".mascot"},
}
```

每個文字元素另存 `font_size` 與 computed `text-align`；JSON 以 `sort_keys=True, indent=2, ensure_ascii=False` 輸出，禁止手改生成結果。

- [ ] **Step 4: 執行 extractor**

Run:

```bash
.venv/bin/python scripts/extract_carousel_layout.py \
  --source /Users/cengweiting/Developer/daibu-content-brain/.superpowers/brainstorm/31101-1787251453/content/multi-company-template-stress-v13.html \
  --output daibu/cards/layouts/editorial-v15-1.json
```

Expected: 輸出七頁 JSON；所有 x/y/w/h 為有限數字且在 1080×1350 內。

- [ ] **Step 5: 實作 `load_builtin_layout()` 並轉綠**

Run: `.venv/bin/pytest -q tests/test_cards_layout_schema.py`

Expected: 全綠。

- [ ] **Step 6: Commit**

```bash
git add scripts/extract_carousel_layout.py daibu/cards/layouts/editorial-v15-1.json daibu/cards/layout_schema.py tests/test_cards_layout_schema.py
git commit -m "feat: freeze approved carousel layout"
```

### Task 3: 新增模板版本與草稿 metadata 資料表

**Files:**
- Modify: `daibu/db.py:355-540`
- Modify: `tests/test_db_migration.py`

**Interfaces:**
- Produces tables: `carousel_template_versions`、`carousel_template_settings`、`carousel_drafts`

- [ ] **Step 1: 寫 migration 紅燈，先只要求三張表與唯一鍵存在**

```python
def test_migration_adds_carousel_template_tables_idempotently(tmp_path):
    conn = db.connect(str(tmp_path / "layout.db"))
    db.init_schema(conn)
    db.init_schema(conn)
    names = {row["name"] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    assert {"carousel_template_versions", "carousel_template_settings", "carousel_drafts"} <= names
    indexes = conn.execute("PRAGMA index_list(carousel_template_versions)").fetchall()
    indexed_columns = {
        tuple(
            item["name"]
            for item in conn.execute(f"PRAGMA index_info({row['name']})")
        )
        for row in indexes
    }
    assert ("theme_id", "version_no") in indexed_columns
```

- [ ] **Step 2: 跑紅燈**

Run: `.venv/bin/pytest -q tests/test_db_migration.py::test_migration_adds_carousel_template_tables_idempotently`

- [ ] **Step 3: 在 `init_schema()` executescript 加入 SQL**

```sql
CREATE TABLE IF NOT EXISTS carousel_template_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    theme_id INTEGER NOT NULL,
    version_no INTEGER NOT NULL,
    schema_version INTEGER NOT NULL,
    layout_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(theme_id, version_no),
    FOREIGN KEY(theme_id) REFERENCES themes(id)
);
CREATE TABLE IF NOT EXISTS carousel_template_settings (
    theme_id INTEGER PRIMARY KEY,
    active_version_id INTEGER NOT NULL,
    FOREIGN KEY(theme_id) REFERENCES themes(id),
    FOREIGN KEY(active_version_id) REFERENCES carousel_template_versions(id)
);
CREATE TABLE IF NOT EXISTS carousel_drafts (
    idea_id INTEGER PRIMARY KEY,
    template_version_id INTEGER NOT NULL,
    content_revision INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(idea_id) REFERENCES ideas(id),
    FOREIGN KEY(template_version_id) REFERENCES carousel_template_versions(id)
);
```

- [ ] **Step 4: 重跑 migration 測試**

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add daibu/db.py tests/test_db_migration.py
git commit -m "feat: add carousel template version tables"
```

### Task 4: 模板 repository 與 active version 不變量

**Files:**
- Create: `daibu/cards/layout_repository.py`
- Create: `tests/test_cards_layout_repository.py`

**Interfaces:**
- Produces: `TemplateVersion(id, theme_id, version_no, layout, created_at)`
- Produces: `ensure_default_version(conn, theme_id) -> TemplateVersion`
- Produces: `get_version(conn, version_id) -> TemplateVersion`
- Produces: `get_active_version(conn, theme_id) -> TemplateVersion`
- Produces: `create_version(conn, theme_id, layout) -> TemplateVersion`
- Produces: `set_active_version(conn, theme_id, version_id) -> None`

- [ ] **Step 1: 寫紅燈，要求新版本遞增但不自動切換 active**

```python
from daibu.models import Theme


def test_new_template_version_is_immutable_and_not_activated_implicitly(tmp_path):
    conn = db.connect(str(tmp_path / "test.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "一布懂 AI 新創", 4, [], 5))
    first = layout_repository.ensure_default_version(conn, theme_id)
    changed = replace_element(first.layout, "cover", "heading", x=120)
    second = layout_repository.create_version(conn, theme_id, changed)
    assert second.version_no == 2
    assert layout_repository.get_active_version(conn, theme_id).id == first.id
    assert layout_repository.get_version(conn, first.id).layout != second.layout
```

- [ ] **Step 2: 跑紅燈，再實作 repository**

版本建立使用 `with conn:`，`MAX(version_no)+1` 與 insert 在同一交易；`layout_json` 必須先 `parse_layout()` 再以 `layout_to_mapping()` canonicalize。

- [ ] **Step 3: 重跑轉綠**

Run: `.venv/bin/pytest -q tests/test_cards_layout_repository.py`

- [ ] **Step 4: 再寫一個紅燈，要求不能把其他系列版本設成 active**

`set_active_version()` 查到 `version.theme_id != theme_id` 時拋 `ValueError("模板版本不屬於這個內容系列")`；確認舊 pointer 不變後轉綠。

- [ ] **Step 5: Commit**

```bash
git add daibu/cards/layout_repository.py tests/test_cards_layout_repository.py
git commit -m "feat: manage immutable carousel template versions"
```

### Task 5: 既有草稿 backfill 與固定版本綁定

**Files:**
- Modify: `daibu/db.py:1129-1134,1311-1395`
- Modify: `tests/test_db_migration.py`
- Modify: `tests/test_db.py`

**Interfaces:**
- Produces: `CarouselDraftMeta(idea_id, template_version_id, content_revision, updated_at)`
- Produces: `RevisionConflict(expected_revision, actual_revision)`
- Produces: `get_carousel_draft_meta(conn, idea_id) -> CarouselDraftMeta | None`
- Produces: `upgrade_carousel_template(conn, idea_id, template_version_id) -> CarouselDraftMeta`
- Changes: `save_carousel_draft(conn, idea_id, draft, expected_revision=None) -> CarouselDraftMeta` preserves existing binding and increments revision

- [ ] **Step 1: 寫 migration 紅燈，校準內容快照後再量**

測試先建立既有七頁草稿，將 `carousel_pages`、`carousel_sources`、ideas 的完整排序 tuple 存成 `before`，刪掉三張新表模擬舊庫，再跑 `init_schema()`；要求 `after == before`，且新增一列 meta 綁 theme 的 v1。第二次 `init_schema()` 不增加任何列。

- [ ] **Step 2: 跑紅燈**

Run: `.venv/bin/pytest -q tests/test_db_migration.py::test_template_backfill_preserves_existing_carousel_content`

- [ ] **Step 3: 實作 `_backfill_carousel_template_metadata()`**

```python
def _backfill_carousel_template_metadata(conn):
    from daibu.cards import layout_repository

    rows = conn.execute(
        "SELECT DISTINCT ideas.id, ideas.theme_id FROM ideas "
        "JOIN carousel_pages ON carousel_pages.idea_id = ideas.id "
        "WHERE ideas.theme_id IS NOT NULL"
    ).fetchall()
    for row in rows:
        version = layout_repository.ensure_default_version(conn, row["theme_id"])
        conn.execute(
            "INSERT OR IGNORE INTO carousel_drafts "
            "(idea_id, template_version_id, content_revision, updated_at) "
            "VALUES (?, ?, 1, ?)",
            (row["id"], version.id, _now()),
        )
```

在 `init_schema()` 建表後呼叫；不得 update 既有 page/source 列。

- [ ] **Step 4: 轉綠後，新增保存 revision 紅燈**

保存既有 draft 後要求 `template_version_id` 不變、`content_revision + 1`；新 draft 則綁當下 active。再加一個過期 revision 紅燈：傳入 `expected_revision=1`但 DB 已是 2 時拋 `RevisionConflict(1, 2)`，pages/sources/meta 皆不變。比對 revision、`_replace_carousel_draft()` 與 meta insert/update 必須包在同一 `with conn:`。

- [ ] **Step 5: 修正刪除路徑**

`delete_idea()` 在刪 idea 前先刪 `carousel_drafts`。`delete_theme()` 的確認計數要包含輪播草稿與模板版本，實際順序為：草稿 metadata → pages/sources/ideas → active settings → template versions → theme；單一系列 cleanup 用同一順序。依序新增「刪單篇」與「刪整個系列」兩個紅燈，要求沒有孤兒列且其他系列不變。

- [ ] **Step 6: 聚焦測試**

Run: `.venv/bin/pytest -q tests/test_db.py tests/test_db_migration.py`

Expected: 全綠。

- [ ] **Step 7: Commit**

```bash
git add daibu/db.py tests/test_db.py tests/test_db_migration.py
git commit -m "feat: bind carousel drafts to template versions"
```

### Task 6: 正式 v15.1 Renderer — 封面與公司定位頁

**Files:**
- Create: `daibu/cards/templates/editorial-v15-1.html`
- Create: `daibu/cards/templates/editorial-v15-1.css`
- Modify: `daibu/cards/render.py`
- Modify: `tests/test_cards_render.py`

**Interfaces:**
- Produces: `render.page_html(page, company, brand_asset, layout=None) -> str`
- Produces HTML hooks: `data-template="editorial-v15.1"`、`data-page-type`、`data-layout-id`

- [ ] **Step 1: 先寫封面紅燈**

要求 HTML 含正式 Logo、右側 `company-name`、heading、positioning、mascot；禁止 `.page-tag`、`.page-source` 與 `來源：`。

- [ ] **Step 2: 跑紅燈**

Run: `.venv/bin/pytest -q tests/test_cards_render.py::test_cover_uses_editorial_v15_1_without_page_number_or_source`

- [ ] **Step 3: 建立固定模板外殼與封面 markup**

```python
def _layout_box(element_id: str, content: str, *, tag: str = "div", classes: str = "") -> str:
    return f'<{tag} class="{classes}" data-layout-id="{element_id}">{content}</{tag}>'


def _cover(page, company, logo_uri):
    positioning = next(item.text for item in page.sections if item.label == "一句話定位")
    return (
        '<article class="card cover-v151" data-page-type="cover">'
        + _layout_box("series", html.escape(SERIES_NAME), classes="series")
        + _layout_box("company-logo", f'<img src="{logo_uri}" alt="{html.escape(company)} Logo">')
        + _layout_box("company-name", html.escape(company), classes="company-name")
        + _layout_box("heading", html.escape(page.heading), tag="h1", classes="cover-heading")
        + _layout_box("rule", "", classes="cover-rule")
        + _layout_box("positioning", html.escape(positioning), tag="p", classes="cover-copy")
        + _layout_box("mascot", _mascot_img("point"), classes="mascot-box")
        + '</article>'
    )
```

CSS 色票固定為深藍 `#102f3d`、青 `#86ccd4`、珊瑚 `#ec9870`、紙白 `#fafbf8`；使用 bundled LINE Seed。所有標題使用 `white-space:pre-wrap`、`word-break:keep-all`、`overflow-wrap:normal`，保留使用者明確換行且不從英文／數字／公司名中間硬切；放不下由 Task 9 報 overflow，不自動縮字。Layout CSS 由 Task 8 套座標。

- [ ] **Step 4: 封面轉綠後，再寫 who 頁紅燈並實作**

who 僅使用現有兩個 sections：`白話定位` → `positioning`、`基本資料` → `facts`；不虛構第三段。視覺使用青色主區＋深藍結論區填滿下半頁，保留 mascot。

- [ ] **Step 5: Chromium 聚焦檢查**

Run: `.venv/bin/pytest -q tests/test_cards_render.py -k 'v15_1 or cover or who'`

- [ ] **Step 6: Commit**

```bash
git add daibu/cards/templates/editorial-v15-1.html daibu/cards/templates/editorial-v15-1.css daibu/cards/render.py tests/test_cards_render.py
git commit -m "feat: render approved carousel cover and profile"
```

### Task 7: 正式 v15.1 Renderer — 第 3 至 7 頁

**Files:**
- Modify: `daibu/cards/render.py`
- Modify: `daibu/cards/templates/editorial-v15-1.css`
- Modify: `tests/test_cards_render.py`

**Interfaces:**
- Consumes: section roles 與 `DiagramSpec.nodes`
- Produces: registry 所列的五頁 `data-layout-id`

- [ ] **Step 1: 逐頁做五個垂直切片，不可一次全寫**

每頁順序都是：新增一個紅燈 → 跑單一 test → 實作 markup/CSS → 跑綠 → 才進下一頁。

1. `problem`: 三個 `DiagramNode` 對應 `stage-1..3`，兩個 sections 做段落補充；無 diagram 時明確拋 `ValueError("第 3 頁缺少問題流程圖解")`。
2. `how-ai`: 三個 nodes 對應 `step-1..3`，`人仍負責` 對應 caution；禁止靠固定索引猜 section。
3. `results`: before-after 三 nodes 對應兩側與「到」，sections 放進 copy／summary；兩色各佔 50%。
4. `why-care`: signals 三 nodes 對應三訊號；`證據限制` 只在編輯器顯示，不在圖上另做小腳註方格。
5. `cta`: `收束結論`、`給讀者的問題`、`互動邀請` 對應 thesis/question/invitation。

- [ ] **Step 2: 每頁 HTML escaping 測試**

在既有 unsafe 內容 fixture 放 `<script>`，要求輸出只有 `&lt;script&gt;`；不得把 LLM／使用者字串放進 class、style 或 script。

- [ ] **Step 3: 聚焦測試**

Run: `.venv/bin/pytest -q tests/test_cards_render.py tests/test_cards_diagrams.py`

- [ ] **Step 4: Commit**

```bash
git add daibu/cards/render.py daibu/cards/templates/editorial-v15-1.css tests/test_cards_render.py
git commit -m "feat: render seven editorial carousel pages"
```

### Task 8: 將 Layout Document 套成唯一座標來源

**Files:**
- Modify: `daibu/cards/render.py`
- Modify: `tests/test_cards_render.py`

**Interfaces:**
- Produces: `layout_css(document: LayoutDocument, page_type: str) -> str`

- [ ] **Step 1: 寫紅燈，移動 heading 後 HTML CSS 必須精確改變**

```python
def test_layout_css_uses_saved_geometry(carousel_page, asset):
    layout = replace_element(load_builtin_layout(), "cover", "heading", x=123, y=234, w=500, h=190)
    output = render.page_html(carousel_page, "ElevenLabs", asset, layout)
    assert '[data-layout-id="heading"]' in output
    assert "left:123px" in output
    assert "top:234px" in output
    assert "width:500px" in output
    assert "height:190px" in output
```

- [ ] **Step 2: 實作只輸出白名單 CSS**

```python
def _element_css(element_id, element):
    declarations = [
        "position:absolute!important",
        f"left:{element.rect.x:g}px", f"top:{element.rect.y:g}px",
        f"width:{element.rect.w:g}px", f"height:{element.rect.h:g}px",
    ]
    if element.text_style is not None:
        declarations += [
            f"font-size:{element.text_style.font_size:g}px",
            f"text-align:{element.text_style.text_align}",
        ]
    return f'[data-layout-id="{element_id}"]{{{";".join(declarations)}}}'
```

`page_html()` 首先 `parse_layout()`；不得把原始 JSON 拼進 style。

- [ ] **Step 3: 跑 Renderer 全檔**

Run: `.venv/bin/pytest -q tests/test_cards_render.py`

- [ ] **Step 4: Commit**

```bash
git add daibu/cards/render.py tests/test_cards_render.py
git commit -m "feat: render carousel from saved layout geometry"
```

### Task 9: 真實 Chromium Layout Validator

**Files:**
- Create: `daibu/cards/layout_validation.py`
- Create: `tests/test_cards_layout_validation.py`
- Modify: `daibu/cards/shoot.py`

**Interfaces:**
- Produces: `LayoutIssue(page_type, element_id, code, message)`
- Produces: `inspect_layout(html_text, page_type, registry=ELEMENT_REGISTRY) -> tuple[LayoutIssue, ...]`
- Produces: `validate_rendered_pages(pages: Mapping[str, str]) -> None`

- [ ] **Step 1: 寫真實瀏覽器紅燈，壓扁標題框會回傳可行動錯誤**

```python
def test_layout_validator_reports_text_overflow_with_page_and_element(asset):
    layout = replace_element(load_builtin_layout(), "cover", "heading", h=20)
    html_text = render.page_html(carousel_draft().pages[0], "ElevenLabs", asset, layout)
    issues = layout_validation.inspect_layout(html_text, "cover")
    assert [(item.element_id, item.code) for item in issues] == [("heading", "text-overflow")]
    assert "第 1 頁" in issues[0].message
    assert "封面標題" in issues[0].message
```

- [ ] **Step 2: 跑紅燈，實作 browser measurement**

JS 對每個 `[data-layout-id]` 回傳 rect、`scrollWidth/clientWidth`、`scrollHeight/clientHeight`；Python 依 registry 判斷 canvas bounds、必要元素最小尺寸與 `avoid` 元素交集。`allow/background` 不報假碰撞。

- [ ] **Step 3: 逐一新增真實邊界測試**

依序加入 mascot 越界、Logo 不可見、兩個 `avoid` 元素碰撞、允許 mascot 重疊四個測試；每個先紅後綠。

- [ ] **Step 4: 新增標題一／兩行契約**

以真實 LINE Seed 逐一驗證：短標題實測只有一行；剛好需要兩行的標題不被提前強制斷行；明確 `\n` 保留詞組；第三行或 `scrollHeight > clientHeight` 回 `text-overflow`。JS 回傳標題的 `Range.getClientRects()` 視覺行數，不以字數猜行數。

- [ ] **Step 5: 讓 `carousel_pngs()` 先驗證再截圖**

任一 issue 時拋 `RuntimeError("第 N 頁…")`，outputs 必須仍為空；合法七頁維持七張 PNG。

- [ ] **Step 6: 聚焦測試**

Run: `.venv/bin/pytest -q tests/test_cards_layout_validation.py tests/test_cards_shoot.py`

- [ ] **Step 7: Commit**

```bash
git add daibu/cards/layout_validation.py daibu/cards/shoot.py tests/test_cards_layout_validation.py tests/test_cards_shoot.py
git commit -m "feat: validate carousel layout in chromium"
```

### Task 10: 版本感知產圖、資料副本驗證與 Phase A 收尾

**Files:**
- Modify: `daibu/cards/shoot.py`
- Modify: `daibu/cards/workbench.py`
- Modify: `tests/test_cards_shoot.py`
- Modify: `tests/test_cards_workbench.py`
- Modify: `.gitignore`
- Modify: `HANDOFF.md`

**Interfaces:**
- Produces: `carousel_pngs(draft, company, brand_asset, layout) -> list[bytes]`
- Produces: `render_fingerprint(draft, template_version_id, content_revision) -> str`

- [ ] **Step 1: 寫快取紅燈**

同內容、不同 `template_version_id` 的 fingerprint 必須不同；同版本 revision 增加也不同。轉綠後更新所有呼叫者，但不要接新 UI。

- [ ] **Step 2: 建立正式 DB 的 SQLite `.backup` 副本**

先量正式庫已知基線：ideas、carousel_pages、carousel_sources、brand_assets 數量與逐欄排序 SHA-256；用同一量法量副本，確認完全相同後才在副本跑 `init_schema()`。

- [ ] **Step 3: 副本 migration 驗證**

migration 後重新量原四組資料，要求內容指紋完全相同；只允許三張新表與 backfill rows 增加。重跑 migration，模板／meta 數量不得增加。

- [ ] **Step 4: 三家公司七頁 Chromium 壓力測試**

使用 SUN、Billow AI Labs、Shiraz AI 內容 fixture 與橫／直 Logo；要求 21 張 HTML 無 overflow／非法碰撞，PNG 都是 1080×1350，圖上 DOM 不含 page number、source 或 date。

- [ ] **Step 5: 兩輪正式 Renderer 視覺 QA**

從 tmp DB 啟動 Streamlit 並進入 SUN 七頁預覽，第一輪只截 `.screenshots/layout-foundation-round1-desktop.png`（1280×800）與 `.screenshots/layout-foundation-round1-mobile.png`（375×812）。明寫八項不合格項後，每項先加可重現測試再修。第二輪只截 `layout-foundation-round2-*`，要求層次、留白、LINE Seed、三色限制、對齊、375px 無 overflow、狀態、微動效全合格；console 0 errors／0 warnings。`.screenshots/` 加入 `.gitignore`，最終路徑寫入 HANDOFF，不將截圖納入 Git。

- [ ] **Step 6: 全套驗證**

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q
.venv/bin/python -m compileall -q daibu pages
git diff --check
```

Expected: 0 failures；既有 deselected contract tests 維持略過。

- [ ] **Step 7: 產品理解檢查點**

更新 `HANDOFF.md`：產品能力、使用者體驗、技術結構、資料流、設計理由／備援、安全成本、Red→Green 證據、真實資料副本、測試結果、剩餘限制。此時明確寫「內容編輯器與模板畫布尚未接入」。

- [ ] **Step 8: Commit Phase A**

```bash
git add .gitignore daibu/cards/layout_schema.py daibu/cards/layout_registry.py daibu/cards/layout_repository.py daibu/cards/layout_validation.py daibu/cards/layouts/editorial-v15-1.json daibu/cards/templates/editorial-v15-1.html daibu/cards/templates/editorial-v15-1.css daibu/cards/render.py daibu/cards/shoot.py daibu/cards/workbench.py daibu/db.py scripts/extract_carousel_layout.py tests/test_cards_layout_schema.py tests/test_cards_layout_repository.py tests/test_cards_layout_validation.py tests/test_cards_render.py tests/test_cards_shoot.py tests/test_cards_workbench.py tests/test_db.py tests/test_db_migration.py HANDOFF.md
git commit -m "feat: establish versioned carousel layout foundation"
```
