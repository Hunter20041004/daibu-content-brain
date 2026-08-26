# Carousel v57 Icon Flow Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增不覆蓋 v56 的 v57，將三個半透明 SVG 集中到第三頁右側三張便利貼、把因果線移到欄間視覺中線，並讓第四頁只使用箭頭連接三張流程卡。

**Architecture:** 由 v56 複製出 v57，保持全部內容鍵與六頁 DOM 角色不變，只搬動三個既有 SVG 並加入 `data-v57-polish="icon-flow"` 範圍化 CSS。新增一份 Playwright 幾何契約，以元素實際邊界驗證圖標歸屬、線的位置與第四頁單一連接語言。

**Tech Stack:** 單檔 HTML／CSS／內嵌 SVG、Python 3.11、Playwright、既有本機視覺伴隨伺服器。

## Global Constraints

- v56 必須保持不變；只能新增 v57。
- 第三頁映射固定為：循環圖標→現有流程、靶心圖標→優化空間、成長圖標→釋放價值。
- 第 2、5 頁不再包含上述三個 `.redistributed-icon`。
- 第三頁因果線中心必須落在左右欄空隙由左往右 55%–65% 的範圍。
- 第四頁保留兩個箭頭，移除 `.schema-route::before` 的虛線。
- 所有 `data-content-key`、hidden 相容欄位、六頁角色與頁碼保持完整。
- 不修改正式 Renderer、AI 提示詞、SQLite、正式站或外部服務。
- 完成前至少跑兩輪 1280×800 與 375×812 截圖自檢。

---

### Task 1: v57 圖標重新分配

**Files:**
- Create: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-57.html`
- Create: `.superpowers/brainstorm/3440-1787701682/content/v57-icon-flow-contract.py`

**Interfaces:**
- Consumes: v56 的六頁 DOM、`cycle-icon`、`target-icon`、`growth-icon`。
- Produces: `data-v57-polish="icon-flow"` 與第三頁三張便利貼的一對一圖標映射。

- [ ] **Step 1: 寫圖標分配失敗契約**

建立 Playwright 契約，回傳三張右側便利貼各自的 `data-visual`，並確認三個 SVG 的最近頁面與最近便利貼：

```python
from pathlib import Path
import json
import sys
from playwright.sync_api import sync_playwright

html_path = Path(sys.argv[1]).resolve()
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.set_content(html_path.read_text(encoding="utf-8"), wait_until="domcontentloaded")
    result = page.evaluate("""
      () => ({
        marker: document.querySelector('[data-v57-polish]')?.dataset.v57Polish,
        noteIcons: [...document.querySelectorAll('[data-page="03"] .problem-note')]
          .map(note => [...note.querySelectorAll('.redistributed-icon')]
            .map(icon => icon.dataset.visual)),
        iconHomes: [...document.querySelectorAll('.redistributed-icon')]
          .map(icon => ({icon: icon.dataset.visual, page: icon.closest('.carousel-page')?.dataset.page,
            note: icon.closest('.problem-note')?.className ?? null})),
      })
    """)
    browser.close()

assert result["marker"] == "icon-flow", json.dumps(result, ensure_ascii=False)
assert result["noteIcons"] == [["cycle-icon"], ["target-icon"], ["growth-icon"]], json.dumps(result, ensure_ascii=False)
assert {item["page"] for item in result["iconHomes"]} == {"03"}, json.dumps(result, ensure_ascii=False)
print("v57 icon distribution contract passed")
```

- [ ] **Step 2: 在 v56 驗證紅燈**

Run:

```bash
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/v57-icon-flow-contract.py \
  .superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-56.html
```

Expected: FAIL，缺少 `icon-flow` marker，靶心與成長圖標仍位於第 2、5 頁。

- [ ] **Step 3: 複製 v56 並搬動三個 SVG**

在 v57 的 `<main>` 加上：

```html
data-v57-polish="icon-flow"
```

從第 2 頁移除 `target-icon`，從第 5 頁移除 `growth-icon`；保留第 3 頁第一張卡的 `cycle-icon`，並將兩個 SVG 分別放進 `.problem-note.n2` 與 `.problem-note.n3`。所有圖標保留 `aria-hidden="true"`。

- [ ] **Step 4: 驗證圖標分配綠燈**

Run:

```bash
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/v57-icon-flow-contract.py \
  .superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-57.html
```

Expected: `v57 icon distribution contract passed`。

---

### Task 2: 第三頁圖標安全區與因果線視覺中線

**Files:**
- Modify: `.superpowers/brainstorm/3440-1787701682/content/v57-icon-flow-contract.py`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-57.html`

**Interfaces:**
- Consumes: Task 1 的三張便利貼與三個圖標。
- Produces: 圖標完全位於所屬便利貼、零文字碰撞，以及因果線中心比例 `0.55–0.65`。

- [ ] **Step 1: 擴充契約並驗證紅燈**

在同一次 evaluate 加入圖標邊界、圖標與正文的交疊面積，以及欄間位置比例：

```javascript
const rect = element => element.getBoundingClientRect();
const overlap = (a, b) => Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left))
  * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
const problem = document.querySelector('[data-page="03"]');
const context = rect(problem.querySelector('.problem-context'));
const notesBox = rect(problem.querySelector('.schema-notes'));
const spine = rect(problem.querySelector('.causal-spine'));
const iconSafety = [...problem.querySelectorAll('.problem-note')].map(note => {
  const noteBox = rect(note);
  const iconBox = rect(note.querySelector('.redistributed-icon'));
  const copyBoxes = [...note.querySelectorAll('i,b,span')].map(rect);
  return {
    inside: iconBox.left >= noteBox.left && iconBox.right <= noteBox.right
      && iconBox.top >= noteBox.top && iconBox.bottom <= noteBox.bottom,
    textOverlap: Math.max(...copyBoxes.map(copy => overlap(iconBox, copy))),
  };
});
const gapStart = context.right;
const gapEnd = notesBox.left;
const spineCenter = spine.left + spine.width / 2;
const spineGapRatio = (spineCenter - gapStart) / (gapEnd - gapStart);
```

新增斷言：

```python
assert all(item["inside"] and item["textOverlap"] <= 1 for item in result["iconSafety"]), json.dumps(result, ensure_ascii=False)
assert 0.55 <= result["spineGapRatio"] <= 0.65, json.dumps(result, ensure_ascii=False)
```

Run v57 before CSS changes. Expected: FAIL，因果線仍在欄間中線偏左處，新增圖標亦尚未使用一致安全區。

- [ ] **Step 2: 實作最小幾何修正**

在 v57 尾端加入範圍化 CSS：

```css
.carousel-showcase[data-v57-polish="icon-flow"] [data-page="03"] .problem-note .redistributed-icon{
  right:1.5cqw;
  bottom:1.5cqw;
}
.carousel-showcase[data-v57-polish="icon-flow"] [data-page="03"] .causal-spine{
  left:-2.05cqw;
}
```

依契約實測只微調 `left`，不得放寬 `0.55–0.65` 門檻。

- [ ] **Step 3: 驗證第三頁綠燈**

Run:

```bash
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/v57-icon-flow-contract.py \
  .superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-57.html
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/problem-story-layout-contract.py \
  .superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-57.html
```

Expected: 兩項契約通過。

---

### Task 3: 第四頁單一流程連接語言與完整驗收

**Files:**
- Modify: `.superpowers/brainstorm/3440-1787701682/content/v57-icon-flow-contract.py`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-57.html`
- Modify: `HANDOFF.md`

**Interfaces:**
- Consumes: v57 的 `.schema-route`、兩個 `.flow-arrow`。
- Produces: 兩個可見箭頭、零 route 虛線，以及完整測試與視覺證據。

- [ ] **Step 1: 擴充第四頁失敗契約**

在 evaluate 加入：

```javascript
const route = document.querySelector('[data-page="04"] .schema-route');
const routeBefore = getComputedStyle(route, '::before');
const flowArrows = [...route.querySelectorAll('.flow-arrow')];
const arrowVisibility = flowArrows.map(arrow => {
  const before = getComputedStyle(arrow, '::before');
  const after = getComputedStyle(arrow, '::after');
  return before.content !== 'none' && after.content !== 'none';
});
```

新增斷言：

```python
assert len(result["arrowVisibility"]) == 2 and all(result["arrowVisibility"]), json.dumps(result, ensure_ascii=False)
assert result["routeBeforeBorderStyle"] == "none", json.dumps(result, ensure_ascii=False)
```

Run v57 before CSS change. Expected: FAIL，`.schema-route::before` 仍為 dashed。

- [ ] **Step 2: 移除虛線並保留箭頭**

在 v57 尾端加入：

```css
.carousel-showcase[data-v57-polish="icon-flow"] [data-page="04"] .schema-route::before{
  content:none;
  border:0;
}
```

- [ ] **Step 3: 跑完整原型契約**

Run v57 專屬契約，以及 v56 已使用的全部 Python／Node 原型契約。`visual-storytelling-contract.py` 以 v57 自身作 baseline 與 candidate，檢查視覺元素仍位於各頁內且可存取性標記完整。

Expected: 全部通過，沒有內容鍵或頁面結構回歸。

- [ ] **Step 4: 兩輪桌機／手機視覺 QA**

第一輪各截一張 1280×800 與 375×812，檢查層次、留白、字體、三色、左右基線、三圖標安全區、因果線位置、第四頁只剩箭頭、響應式與既有 hover 微動效。若有不合格項，只修對應的 v57 CSS。

第二輪各截最終桌機／手機圖，並執行：

```bash
playwright-cli eval "({scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth,pages:[...document.querySelectorAll('.carousel-page')].map(el=>({page:el.dataset.page,overflow:el.scrollWidth>el.clientWidth}))})"
playwright-cli console
```

Expected: `scrollWidth == clientWidth == 375`、六頁 `overflow:false`、console 0 errors／0 warnings。

- [ ] **Step 5: 產品理解檢查點、文件與完整測試**

在 `HANDOFF.md` 紀錄產品能力、使用者體驗、技術結構、資料流程、設計理由與備援、安全與成本、TDD 證據、視覺 QA 與剩餘限制。執行：

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q
```

Expected: `739 passed, 16 deselected`，只允許既有 Starlette／httpx warning。

- [ ] **Step 6: 合併、main 複驗與推送**

提交追蹤文件，將隔離分支 fast-forward 合回 `main`，於 `main` 重跑完整測試，推送並確認：

```bash
git rev-parse HEAD
git rev-parse origin/main
```

Expected: 兩個 commit hash 相同。正式程式未變，因此不部署正式站；將 v57 與最終截圖同步回被忽略的主工作區原型資料夾。
