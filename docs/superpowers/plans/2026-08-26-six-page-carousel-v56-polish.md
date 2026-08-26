# Six-Page Carousel v56 Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立不覆蓋 v55 的 v56，完成九個瀏覽器標註所要求的文案、標題、頁面比例、重疊與對齊修正。

**Architecture:** 以 v55 為不可變基準複製 v56，先用內容契約鎖定指定文案，再以獨立幾何契約量測第 2–5 頁標題、第 2 頁定位圖、第 3 頁軸線與內容群組、第 4 頁內容占用率。視覺修正集中在 v56 尾端範圍化 CSS，既有內容鍵與 hidden 相容欄位維持不變。

**Tech Stack:** 單檔 HTML／CSS／內嵌 SVG、Python 3.11、Playwright、Node.js、既有視覺伴隨伺服器。

## Global Constraints

- v48、v50、v53、v54、v55 必須保留；只能新增 v56。
- 第 4 頁標題固定為「AI 扮演什麼樣的角色？」。
- 第 5 頁標題固定為「它怎麼實際改善現有流程？」。
- 第 5 頁不可顯示「購買關係」；右下摘要改為「帶來的價值」。
- 第 6 頁可見 CTA 只能是「追蹤呆一布 AI 共學實驗室」與「帶你看更多最新 AI 資訊」。
- 第 2–5 頁標題全部放大並稍微下移，長標題最多兩行且不可裁切。
- 第 2 頁定位圖與 Logo 不重疊；第 3 頁內容上移、右欄字放大且軸線右移；第 4 頁內容群組放大上移。
- 所有 `data-content-key`、hidden 相容欄位、六頁角色與 `01 / 06` 至 `06 / 06` 頁碼保持完整。
- 不修改正式 Renderer、AI 提示詞、SQLite、正式站或外部服務。
- 前端完成前至少跑兩輪 1280×800 與 375×812 截圖自檢。

---

### Task 1: v56 文案與不可變版本

**Files:**
- Create: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-56.html`
- Create: `.superpowers/brainstorm/3440-1787701682/content/v56-copy-contract.py`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/concise-narrative-contract.py`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/social-cta-contract.py`

**Interfaces:**
- Consumes: v55 完整 HTML 與全部內容鍵。
- Produces: v56 指定標題、`data-result-summary="delivered-value"` 與 `data-cta-copy="daibu-lab"`。

- [x] **Step 1: 寫 v56 文案失敗契約**

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
          headings: ['04', '05'].map((number) =>
            document.querySelector(`[data-page="${number}"] .page-title`).textContent.trim()),
          resultLabel: document.querySelector('[data-page="05"] .result-summary p:last-child b').textContent.trim(),
          resultMarker: document.querySelector('[data-page="05"] .result-summary p:last-child').dataset.resultSummary,
          ctaMarker: document.querySelector('[data-page="06"] .cta-center').dataset.ctaCopy,
          ctaLines: [...document.querySelectorAll('[data-page="06"] .cta-center > p')]
            .map((element) => element.textContent.trim()),
          visibleText: [...document.querySelectorAll('.carousel-page')]
            .map((element) => element.innerText).join(' '),
        })
        """
    )
    browser.close()

assert result["headings"] == ["AI 扮演什麼樣的角色？", "它怎麼實際改善現有流程？"], json.dumps(result, ensure_ascii=False)
assert result["resultLabel"] == "帶來的價值"
assert result["resultMarker"] == "delivered-value"
assert result["ctaMarker"] == "daibu-lab"
assert result["ctaLines"] == ["追蹤呆一布 AI 共學實驗室", "帶你看更多最新 AI 資訊"]
for forbidden in ["購買關係", "喜歡這類內容嗎？", "下一間想看哪家公司？", "@社群帳號"]:
    assert forbidden not in result["visibleText"], forbidden
print("v56 copy contract passed")
```

- [x] **Step 2: 在 v55 驗證紅燈**

Run:

```bash
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/v56-copy-contract.py \
  .superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-55.html
```

Expected: FAIL，標題仍是 v55 文字，CTA 仍有三段。

- [x] **Step 3: 複製 v55 並實作最小文案變更**

```html
<h3 class="page-title" data-content-key="page.how-ai.heading">AI 扮演什麼樣的角色？</h3>
<h3 class="page-title" data-content-key="page.results.heading">它怎麼實際改善現有流程？</h3>

<p data-result-summary="delivered-value">
  <b>帶來的價值</b>
  <span data-content-key="page.results.section.2.text">流程改善後，使用者少做重複整理，主管更容易看見導入成效，團隊也能把時間投入更需要判斷的工作。</span>
</p>

<div class="cta-center" data-cta-copy="daibu-lab">
  <p class="cta-line follow">追蹤呆一布 AI 共學實驗室</p>
  <p class="cta-line prompt">帶你看更多最新 AI 資訊</p>
</div>
```

舊 CTA 生成欄位繼續保留 `hidden`，但可見 `.cta-center` 只允許上述兩個 `<p>`。

- [x] **Step 4: 更新既有固定文案契約並驗證綠燈**

`concise-narrative-contract.py` 的第 4、5 頁標題預期值改為新文字；`social-cta-contract.py` 改為檢查兩句 CTA、`data-cta-copy="daibu-lab"` 與零舊 CTA 可見文字。

Run:

```bash
candidate=.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-56.html
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/v56-copy-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/concise-narrative-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/social-cta-contract.py "$candidate"
```

Expected: 三項契約通過。

---

### Task 2: 內頁標題、第 2 頁分離與第 3 頁幾何

**Files:**
- Create: `.superpowers/brainstorm/3440-1787701682/content/v56-layout-contract.py`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-56.html`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/page-polish-contract.py`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/problem-story-layout-contract.py`

**Interfaces:**
- Consumes: Task 1 的 v56 DOM。
- Produces: `data-v56-layout="expanded-interiors"` 與可量測的標題／第 2、3 頁幾何。

- [x] **Step 1: 寫標題與第 2 頁失敗契約**

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
          const rect = (element) => element.getBoundingClientRect();
          const titleMetrics = ['02', '03', '04', '05'].map((number) => {
            const card = document.querySelector(`[data-page="${number}"]`);
            const title = card.querySelector('.page-title');
            const range = document.createRange();
            range.selectNodeContents(title);
            const lines = [...range.getClientRects()];
            return {
              page: number,
              sizeRatio: parseFloat(getComputedStyle(title).fontSize) / rect(card).width,
              topRatio: (rect(title).top - rect(card.querySelector('.shared-sheet,.profile-sheet')).top) / rect(card).height,
              lines: lines.length,
              clipped: (lines.at(-1)?.bottom ?? 0) > rect(title).bottom + 1,
              mascotOverlap: Math.max(0, Math.min(rect(title).right, rect(card.querySelector('.mascot')).right)
                - Math.max(rect(title).left, rect(card.querySelector('.mascot')).left))
                * Math.max(0, Math.min(rect(title).bottom, rect(card.querySelector('.mascot')).bottom)
                - Math.max(rect(title).top, rect(card.querySelector('.mascot')).top)),
            };
          });
          const profile = document.querySelector('[data-page="02"]');
          return {
            marker: document.querySelector('[data-v56-layout]')?.dataset.v56Layout,
            titleMetrics,
            profileGap: rect(profile.querySelector('.logo-slot')).top - rect(profile.querySelector('.identity-map')).bottom,
          };
        }
        """
    )
    browser.close()

assert result["marker"] == "expanded-interiors"
assert all(item["sizeRatio"] >= 0.078 for item in result["titleMetrics"]), json.dumps(result, ensure_ascii=False)
assert all(item["topRatio"] >= 0.09 for item in result["titleMetrics"]), json.dumps(result, ensure_ascii=False)
assert all(item["lines"] <= 2 and not item["clipped"] for item in result["titleMetrics"]), json.dumps(result, ensure_ascii=False)
assert all(item["mascotOverlap"] <= 1 for item in result["titleMetrics"]), json.dumps(result, ensure_ascii=False)
assert result["profileGap"] >= 6, json.dumps(result, ensure_ascii=False)
print("v56 interior title and profile layout contract passed")
```

- [x] **Step 2: 在只改文案的 v56 驗證紅燈**

Expected: FAIL，缺少 `expanded-interiors` 標記，且第 2 頁定位圖仍與 Logo 區相交。

- [x] **Step 3: 實作標題與第 2 頁最小幾何修正**

在 v56 尾端加入：

```css
.carousel-showcase[data-v56-layout="expanded-interiors"] [data-page="02"] .page-title,
.carousel-showcase[data-v56-layout="expanded-interiors"] [data-page="03"] .page-title,
.carousel-showcase[data-v56-layout="expanded-interiors"] [data-page="04"] .page-title,
.carousel-showcase[data-v56-layout="expanded-interiors"] [data-page="05"] .page-title{
  margin-top:1.6cqw;
  font-size:8cqw;
  line-height:1.04;
}
.carousel-showcase[data-v56-layout="expanded-interiors"] .page-profile .identity-map{top:27%}
.carousel-showcase[data-v56-layout="expanded-interiors"] .page-profile .schema-profile{margin-top:18cqw}
```

若 `8cqw` 讓兩個長標題超過兩行，只能在第 4、5 頁個別降至仍大於 v55 的 `7.8cqw`；不得縮正文。

- [x] **Step 4: 擴充同一契約鎖定第 3 頁**

在 `v56-layout-contract.py` 同一次 Playwright evaluate 加入：

```javascript
const opportunity = document.querySelector('[data-page="03"]');
const context = rect(opportunity.querySelector('.problem-context'));
const notes = [...opportunity.querySelectorAll('.problem-note')].map(rect);
const spine = rect(opportunity.querySelector('.causal-spine'));
const bodyRatios = [...opportunity.querySelectorAll('.problem-note span')]
  .map((element) => parseFloat(getComputedStyle(element).fontSize) / rect(opportunity).width);
const gapCenter = (context.right + notes[0].left) / 2;
return {
  opportunityGapRatio: (Math.min(context.top, notes[0].top) - rect(opportunity.querySelector('.page-title')).bottom) / rect(opportunity).height,
  spineCenterDelta: Math.abs((spine.left + spine.width / 2) - gapCenter),
  minimumOpportunityBodyRatio: Math.min(...bodyRatios),
};
```

新增斷言：

```python
assert result["opportunityGapRatio"] <= 0.14
assert result["spineCenterDelta"] <= 4
assert result["minimumOpportunityBodyRatio"] >= 0.017
```

在尚未修改第 3 頁時執行，Expected: FAIL，至少軸線中心或正文比例不符。

- [x] **Step 5: 實作第 3 頁上移、放大與軸線右移**

```css
.carousel-showcase[data-v56-layout="expanded-interiors"] .page-problem .problem-context{top:29%}
.carousel-showcase[data-v56-layout="expanded-interiors"] .page-problem .schema-notes{top:29%}
.carousel-showcase[data-v56-layout="expanded-interiors"] .page-problem .causal-spine{left:41.5%}
.carousel-showcase[data-v56-layout="expanded-interiors"] .page-problem .problem-note{font-size:1.7cqw}
.carousel-showcase[data-v56-layout="expanded-interiors"] .page-problem .problem-note b{font-size:1.55cqw}
```

依實際量測微調 `top` 與 `left`，但契約門檻不得放寬。更新 `problem-story-layout-contract.py` 使用 v56 marker，並保留等寬、順序、零重疊與圓點對齊斷言。

- [x] **Step 6: 跑 Task 2 契約轉綠**

```bash
candidate=.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-56.html
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/v56-layout-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/page-polish-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/problem-story-layout-contract.py "$candidate"
```

Expected: 三項契約通過。

---

### Task 3: 第 4 頁內容群組放大與完整驗收

**Files:**
- Modify: `.superpowers/brainstorm/3440-1787701682/content/v56-layout-contract.py`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-56.html`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/page-three-four-density-contract.py`
- Modify: `HANDOFF.md`

**Interfaces:**
- Consumes: Task 2 的 `expanded-interiors` 幾何。
- Produces: 第 4 頁高占用內容群組、完整原型契約與視覺證據。

- [x] **Step 1: 在 v56 幾何契約新增第 4 頁失敗案例**

在 evaluate 加入：

```javascript
const mechanism = document.querySelector('[data-page="04"]');
const mechanismTitle = rect(mechanism.querySelector('.page-title'));
const route = rect(mechanism.querySelector('.schema-route'));
const contextCards = [...mechanism.querySelectorAll('.how-context p')].map(rect);
const contextBottom = Math.max(...contextCards.map((item) => item.bottom));
const sheet = rect(mechanism.querySelector('.shared-sheet'));
return {
  mechanismTopGapRatio: (route.top - mechanismTitle.bottom) / rect(mechanism).height,
  mechanismBottomUse: (contextBottom - sheet.top) / sheet.height,
  mechanismStepSpread: Math.max(...[...mechanism.querySelectorAll('.step')].map((element) => rect(element).width))
    - Math.min(...[...mechanism.querySelectorAll('.step')].map((element) => rect(element).width)),
};
```

新增斷言：

```python
assert result["mechanismTopGapRatio"] <= 0.12
assert result["mechanismBottomUse"] >= 0.88
assert result["mechanismStepSpread"] <= 2
```

Run v56 before geometry change. Expected: FAIL，標題至流程間距過大或內容群組占用不足。

- [x] **Step 2: 最小實作第 4 頁群組上移與放大**

```css
.carousel-showcase[data-v56-layout="expanded-interiors"] .page-solution .schema-route{
  top:27%;
  height:31%;
}
.carousel-showcase[data-v56-layout="expanded-interiors"] .page-solution .step{
  min-height:27cqw;
  padding:4.5cqw 3cqw 3cqw;
}
.carousel-showcase[data-v56-layout="expanded-interiors"] .page-solution .how-context{
  top:61%;
  bottom:8%;
}
.carousel-showcase[data-v56-layout="expanded-interiors"] .page-solution .how-context p{
  padding:3.2cqw;
}
```

依實測微調，但維持三步等寬、下方 2×2、正文最小比例與頁碼安全區。

- [x] **Step 3: 跑全部原型契約**

```bash
candidate=.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-56.html
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/v56-copy-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/v56-layout-contract.py "$candidate"
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

Expected: 16 項原型契約全部通過。

- [x] **Step 4: 兩輪桌機／手機視覺 QA**

第一輪只截：

```bash
playwright-cli resize 1280 800
playwright-cli screenshot --filename=.screenshots/v56-polish-round1-desktop.png
playwright-cli resize 375 812
playwright-cli screenshot --filename=.screenshots/v56-polish-round1-mobile.png
```

逐項檢查：層次、留白、LINE Seed、三色限制、左右基線、標題兩行上限、第 2 頁零重疊、第 3 頁軸線與文字、第 4 頁占用率、CTA 兩句、375px 響應式與 hover 微動效。明確記錄不合格項後只修對應幾何。

第二輪只截：

```bash
playwright-cli resize 1280 800
playwright-cli screenshot --filename=.screenshots/v56-polish-final-desktop.png
playwright-cli resize 375 812
playwright-cli screenshot --filename=.screenshots/v56-polish-final-mobile.png
playwright-cli eval "({scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth,pages:[...document.querySelectorAll('.carousel-page')].map((el)=>({page:el.dataset.page,overflow:el.scrollWidth>el.clientWidth}))})"
playwright-cli console
```

Expected: `scrollWidth == clientWidth == 375`、六頁 `overflow:false`、console 0 errors／0 warnings。

- [x] **Step 5: 文件、全測、合併與推送**

在 `HANDOFF.md` 新增 v56 的產品能力、使用者體驗、技術結構、資料流程、設計理由與備援、安全與成本、TDD 證據、視覺 QA、完整測試與剩餘限制。執行：

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q
```

Expected: `739 passed, 16 deselected`，只允許既有 Starlette／httpx 棄用 warning。依專案規則合回 `main`、於 `main` 重跑全套、推送並確認 `git rev-parse HEAD` 與 `git rev-parse origin/main` 相同。正式程式未變，不重啟或部署正式站。
