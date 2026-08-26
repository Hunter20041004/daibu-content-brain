# Six-Page Carousel Narrative Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 v54 收斂成六張可見頁面，重寫第 2–5 頁標題與改善機會敘事，並把原第 6 頁的三個 SVG 圖示分配到第 2、3、5 頁。

**Architecture:** 以 v54 為不可變基準建立 v55。可見 DOM 只保留 `cover → who → opportunity → how-ai → results → cta` 六頁；舊 `why-care`、封面標題與產業分類欄位搬入隱藏相容區，讓現有 `CarouselDraft` 仍可載入。內容鍵不改名，正式資料遷移留到 Renderer 接線階段。

**Tech Stack:** 單檔 HTML／CSS／內嵌 SVG、Python 3.11、Node.js、Playwright、既有視覺伴隨伺服器。

## Global Constraints

- v48、v50、v53、v54 必須保留；只能新增 v55。
- 六張可見頁面頁碼固定為 `01 / 06` 至 `06 / 06`。
- `page.why-care.*`、`page.cover.heading`、`page.cover.section.1.text` 必須存在但不可見。
- 第 2–5 頁標題固定為「它在做什麼？」、「它想優化什麼？」、「AI 怎麼做到的？」、「用了，差在哪？」。
- 第 3 頁不得預設原流程失效或卡住；內容角色是改善機會。
- 原第 6 頁的循環、靶心與上升折線 SVG 只能分別出現在第 3、2、5 頁，且必須 `aria-hidden="true"`。
- 前五頁語意便利貼數量由 26 降為 22；CTA 不套用便利貼。
- 不修改正式 Renderer、AI 提示詞、SQLite、正式站或外部服務。
- 前端完成前必須做兩輪 1280×800 與 375×812 截圖自檢。

---

### Task 1: 六張可見頁面與舊欄位相容

**Files:**
- Create: `.superpowers/brainstorm/3440-1787701682/content/six-page-structure-contract.py`
- Create: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-55.html`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/social-cta-contract.py`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/unified-notebook-contract.js`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/cover-company-first-contract.py`

**Interfaces:**
- Consumes: v54 的七張文章與全部 `data-content-key`。
- Produces: 六張 `.carousel-page`、`data-page="01"` 至 `"06"`、`data-narrative="identity-opportunity-mechanism-outcome"`、隱藏 `.legacy-why-care-fields`。

- [ ] **Step 1: 寫六頁結構失敗契約**

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


html_path = Path(sys.argv[1]).resolve()
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.set_content(html_path.read_text(encoding="utf-8"), wait_until="domcontentloaded")
    result = page.evaluate(
        """
        () => {
          const cards = [...document.querySelectorAll('.carousel-page')];
          const hiddenKeys = [...document.querySelectorAll('[data-content-key][hidden]')]
            .map((element) => element.dataset.contentKey);
          const whyCareKeys = [...document.querySelectorAll('[data-content-key^="page.why-care."]')];
          return {
            pages: cards.map((card) => card.dataset.page),
            roles: cards.map((card) => card.dataset.storyRole),
            totals: cards.map((card) => getComputedStyle(card, '::after').content),
            marker: document.querySelector('[data-narrative]')?.dataset.narrative,
            ctaPage: document.querySelector('.page-close')?.dataset.page,
            whyCareCount: whyCareKeys.length,
            allWhyCareHidden: whyCareKeys.every((element) => element.hidden),
            coverHeadingHidden: hiddenKeys.includes('page.cover.heading'),
            industryHidden: hiddenKeys.includes('page.cover.section.1.text'),
          };
        }
        """
    )
    browser.close()

assert result["pages"] == ["01", "02", "03", "04", "05", "06"], json.dumps(result, ensure_ascii=False)
assert result["roles"] == ["hook", "identity", "opportunity", "mechanism", "outcome", "cta"], json.dumps(result, ensure_ascii=False)
assert result["marker"] == "identity-opportunity-mechanism-outcome"
assert result["ctaPage"] == "06"
assert result["whyCareCount"] == 14 and result["allWhyCareHidden"]
assert result["coverHeadingHidden"] and result["industryHidden"]
assert all("06" in value for value in result["totals"]), json.dumps(result["totals"], ensure_ascii=False)
print("six-page structure contract passed")
```

- [ ] **Step 2: 在 v54 驗證紅燈**

Run:

```bash
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/six-page-structure-contract.py \
  .superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-54.html
```

Expected: FAIL，`pages` 仍為 `01` 至 `07`。

- [ ] **Step 3: 建立 v55 的六頁骨架**

複製 v54 為 v55，做以下最小 DOM 變更：

```html
<main ... data-narrative="identity-opportunity-mechanism-outcome">
  <!-- cover: page 01，產業欄位移到 hidden compatibility fields -->
  <!-- who: page 02 -->
  <article class="carousel-page page-problem" data-page="03" data-story-role="opportunity" ...></article>
  <!-- how-ai: page 04 -->
  <!-- results: page 05 -->
  <article class="carousel-page page-close" data-page="06" data-story-role="cta" ...></article>
</main>
<div class="legacy-compatibility-fields" hidden>
  <span data-content-key="page.cover.section.1.text" hidden>產業分類</span>
  <!-- 將 v54 原第 6 頁的 14 個 why-care 元素原文逐一搬到這裡，每個元素都保留原 data-content-key 並加 hidden -->
</div>
```

將頁碼 CSS 改為：

```css
.carousel-page::after{content:attr(data-page) " / 06"}
```

刪除可見 `.page-evidence` article；CTA 從 `data-page="07"` 改為 `data-page="06"`。封面 `.cover-meta` 只保留系列名稱，產業分類鍵搬到相容區。

- [ ] **Step 4: 更新三個既有結構契約**

1. `social-cta-contract.py`：CTA selector 由 `[data-page="07"]` 改成 `[data-page="06"]`。
2. `unified-notebook-contract.js`：可見 page count 與頁碼總數由 7 改成 6。
3. `cover-company-first-contract.py`：`visibleCoverKeys` 只允許 `["page.cover.section.0.text"]`，並另斷言產業欄位 hidden。

- [ ] **Step 5: 驗證六頁骨架轉綠**

Run:

```bash
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/six-page-structure-contract.py \
  .superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-55.html
```

Expected: `six-page structure contract passed`。

---

### Task 2: 簡潔標題與改善機會敘事

**Files:**
- Create: `.superpowers/brainstorm/3440-1787701682/content/concise-narrative-contract.py`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-55.html`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/narrative-density-contract.py`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/problem-story-layout-contract.py`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/page-polish-contract.py`

**Interfaces:**
- Consumes: Task 1 的六頁 DOM 與既有正式內容鍵。
- Produces: 四個固定短標題、`data-opportunity-layout="current-improvement-value"`、第 2 頁固定提問、第 4 頁「關鍵差別」。

- [ ] **Step 1: 寫標題與語意失敗契約**

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


html_path = Path(sys.argv[1]).resolve()
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.set_content(html_path.read_text(encoding="utf-8"), wait_until="domcontentloaded")
    result = page.evaluate(
        """
        () => ({
          headings: ['02','03','04','05'].map((number) =>
            document.querySelector(`[data-page="${number}"] .page-title`).textContent.trim()),
          thesis: document.querySelector('[data-page="02"] .thesis').textContent.trim(),
          opportunityMarker: document.querySelector('[data-page="03"]').dataset.opportunityLayout,
          contextLabels: [...document.querySelectorAll('[data-page="03"] .problem-context b')]
            .map((element) => element.textContent.trim()),
          nodeLabels: [...document.querySelectorAll('[data-page="03"] .problem-note b')]
            .map((element) => element.textContent.trim()),
          howLabels: [...document.querySelectorAll('[data-page="04"] .how-context b')]
            .map((element) => element.textContent.trim()),
          visibleText: [...document.querySelectorAll('.carousel-page')]
            .map((element) => element.textContent).join(' '),
        })
        """
    )
    browser.close()

assert result["headings"] == ["它在做什麼？", "它想優化什麼？", "AI 怎麼做到的？", "用了，差在哪？"], json.dumps(result, ensure_ascii=False)
assert result["thesis"] == "為什麼這間 AI 公司值得出現？"
assert result["opportunityMarker"] == "current-improvement-value"
assert result["contextLabels"] == ["現在怎麼做", "哪裡還能更好"]
assert result["nodeLabels"] == ["現有流程", "優化空間", "釋放價值"]
assert result["howLabels"] == ["傳統做法", "AI 的角色", "人仍負責", "關鍵差別"]
for forbidden in ["原本的做法會卡住", "問題出現", "摩擦累積", "形成代價", "本頁要記住"]:
    assert forbidden not in result["visibleText"], forbidden
print("concise narrative contract passed")
```

- [ ] **Step 2: 在六頁骨架驗證紅燈**

Run:

```bash
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/concise-narrative-contract.py \
  .superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-55.html
```

Expected: FAIL，四個標題仍是 v54 長句。

- [ ] **Step 3: 實作固定標題與第 2／4 頁文案**

```html
<h3 class="page-title" data-content-key="page.who.heading">它在做什麼？</h3>
<div class="thesis">為什麼這間 AI 公司值得出現？</div>

<h3 class="page-title" data-content-key="page.how-ai.heading">AI 怎麼做到的？</h3>
<!-- 右下 how-context -->
<p class="remember"><b>關鍵差別</b><span data-content-key="page.how-ai.section.3.text">差別不只是加快單一步驟，而是讓資訊能沿著流程繼續被使用，人仍保留最後判斷。</span></p>

<h3 class="page-title" data-content-key="page.results.heading">用了，差在哪？</h3>
```

- [ ] **Step 4: 垂直重寫第 3 頁改善機會**

第 3 頁加入 `data-opportunity-layout="current-improvement-value"`，並使用以下原型 fixture；正式內容鍵保持不變：

```html
<h3 class="page-title" data-content-key="page.problem.heading">它想優化什麼？</h3>
<div class="problem-context">
  <p><b>現在怎麼做</b><span data-content-key="page.problem.section.0.text">使用者原本已有一套完成工作的方式，只是資料整理、判斷與交接分散在不同步驟裡。</span></p>
  <p><b>哪裡還能更好</b><span data-content-key="page.problem.section.1.text">機會不一定是修補壞掉的流程，而是減少重複整理、等待與資訊落差，讓原本可行的工作更順。</span></p>
</div>
<!-- 三張既有 problem-note 依序改成： -->
<b data-content-key="page.problem.diagram.0.title">現有流程</b>
<span data-content-key="page.problem.diagram.0.text">人依既有步驟蒐集資料、完成判斷，再把結果交給下一個人或工具。</span>
<b data-content-key="page.problem.diagram.1.title">優化空間</b>
<span data-content-key="page.problem.diagram.1.text">找出最耗時間、最常重複或最容易失去脈絡的環節，讓 AI 先處理其中一段。</span>
<b data-content-key="page.problem.diagram.2.title">釋放價值</b>
<span data-content-key="page.problem.diagram.2.text">流程少一點等待與重工，人便能把時間留給判斷、溝通與下一步行動。</span>
```

- [ ] **Step 5: 更新敘事與版面契約並驗證綠燈**

1. `narrative-density-contract.py`：marker 改為 `identity-opportunity-mechanism-outcome`；roles 改為六頁；最低字數只檢查 `02:110, 03:175, 04:190, 05:175`。
2. `problem-story-layout-contract.py`：marker 改成 `current-improvement-value`，保留左右欄、三節點等寬、順序與零重疊量測。
3. `page-polish-contract.py`：移除舊 proof page，CTA mascot selector 改為 page `06`。

Run:

```bash
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/concise-narrative-contract.py \
  .superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-55.html
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/narrative-density-contract.py \
  .superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-55.html
```

Expected: `concise narrative contract passed` 與 `narrative density contract passed`。

---

### Task 3: 圖示重新分配、材質契約與視覺驗收

**Files:**
- Create: `.superpowers/brainstorm/3440-1787701682/content/redistributed-icons-contract.py`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-55.html`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/sticky-note-system-contract.py`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/sticky-material-contract.py`
- Modify: `HANDOFF.md`

**Interfaces:**
- Consumes: v54 原第 6 頁三個 `.signal-icon` SVG path。
- Produces: page 02 的 `data-visual="target-icon"`、page 03 的 `data-visual="cycle-icon"`、page 05 的 `data-visual="growth-icon"`。

- [ ] **Step 1: 寫圖示分配失敗契約**

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


html_path = Path(sys.argv[1]).resolve()
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.set_content(html_path.read_text(encoding="utf-8"), wait_until="domcontentloaded")
    result = page.evaluate(
        """
        () => [...document.querySelectorAll('[data-visual$="-icon"]')].map((icon) => ({
          visual: icon.dataset.visual,
          page: icon.closest('.carousel-page')?.dataset.page,
          hidden: icon.getAttribute('aria-hidden'),
          inside: icon.closest('.carousel-page')?.contains(icon) ?? false,
        }))
        """
    )
    browser.close()

expected = [
    {"visual": "target-icon", "page": "02", "hidden": "true", "inside": True},
    {"visual": "cycle-icon", "page": "03", "hidden": "true", "inside": True},
    {"visual": "growth-icon", "page": "05", "hidden": "true", "inside": True},
]
assert result == expected, json.dumps(result, ensure_ascii=False)
print("redistributed icons contract passed")
```

- [ ] **Step 2: 在未搬圖示的 v55 驗證紅燈**

Expected: FAIL，找不到三個 `*-icon`。

- [ ] **Step 3: 搬移三個 SVG 並保持低對比**

1. 靶心 SVG 放入第 2 頁 `.identity-map` 的「目標使用者」節點。
2. 循環 SVG 放入第 3 頁第一張「現有流程」便利貼。
3. 上升折線 SVG 放入第 5 頁 `.after`「使用後」便利貼。

三者共用：

```css
.redistributed-icon{position:absolute;z-index:0;width:11cqw;height:11cqw;fill:none;stroke:var(--ink);stroke-width:3;stroke-linecap:round;stroke-linejoin:round;opacity:.16;pointer-events:none}
.identity-map [data-visual="target-icon"]{right:1cqw;top:50%;transform:translateY(-50%)}
.problem-note [data-visual="cycle-icon"],.result-flow [data-visual="growth-icon"]{right:1.5cqw;bottom:1.5cqw}
```

文字容器維持 `position:relative; z-index:1`，不得讓 SVG 壓低對比或擋字。

- [ ] **Step 4: 更新 22 張便利貼材質契約並跑全部原型契約**

`sticky-note-system-contract.py` 與 `sticky-material-contract.py` 移除 `.signal-stack section,.evidence-limit` selector，預期數量由 `26` 改為 `22`。

Run:

```bash
candidate=.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-55.html
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/six-page-structure-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/concise-narrative-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/redistributed-icons-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/cover-company-first-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/page-polish-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/narrative-density-contract.py "$candidate"
node .superpowers/brainstorm/3440-1787701682/content/schema-aligned-contract.js "$candidate"
node .superpowers/brainstorm/3440-1787701682/content/unified-notebook-contract.js "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/straight-density-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/sticky-note-system-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/sticky-material-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/page-three-four-density-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/problem-story-layout-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/social-cta-contract.py "$candidate"
```

Expected: 14 項原型契約全部通過。`visual-storytelling-contract.py` 不適用於 v55，因為它的唯一目的，是證明 v50 與 v48 在「文字完全不變」的前提下只增加圖解；v55 已由使用者明確要求改寫文字，內容鍵完整性改由 `schema-aligned-contract.js` 與 `six-page-structure-contract.py` 驗證。

- [ ] **Step 5: 兩輪桌機／手機視覺 QA**

第一輪只截：

```bash
playwright-cli resize 1280 800
playwright-cli screenshot --filename=.screenshots/six-page-narrative-round1-desktop.png
playwright-cli resize 375 812
playwright-cli screenshot --filename=.screenshots/six-page-narrative-round1-mobile.png
```

逐項檢查層次、留白、LINE Seed 字體、三色限制、左右基線、六頁頁碼、375px overflow、CTA 與 hover 微動效；明確記錄不合格項後只修改對應頁面。

第二輪只截：

```bash
playwright-cli resize 1280 800
playwright-cli screenshot --filename=.screenshots/six-page-narrative-final-desktop.png
playwright-cli resize 375 812
playwright-cli screenshot --filename=.screenshots/six-page-narrative-final-mobile.png
playwright-cli eval "({scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth,pages:[...document.querySelectorAll('.carousel-page')].map((el)=>({page:el.dataset.page,overflow:el.scrollWidth>el.clientWidth}))})"
playwright-cli console
```

Expected: `scrollWidth == clientWidth == 375`、六頁 `overflow:false`、console 0 errors／0 warnings。

- [ ] **Step 6: 文件、完整測試、合併與推送**

在 `HANDOFF.md` 記錄九欄產品理解、TDD 紅綠證據、14 項原型契約與兩輪截圖。執行：

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q
```

Expected: `739 passed, 16 deselected`，只允許既有 Starlette／httpx 棄用 warning。依專案預設合回 `main`，於 `main` 再跑相同完整測試，推送後確認本機與 `origin/main` hash 相同。正式程式未變，不重啟或部署正式站。
