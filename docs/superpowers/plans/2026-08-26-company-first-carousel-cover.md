# Company-First Carousel Cover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將粉彩手帳輪播封面改為公司 Logo 與公司名稱優先，一句話介紹作副標，同時保留現有 `CarouselDraft` 欄位相容性。

**Architecture:** 以 v53 為不可變基準建立 v54，只重排第 1 頁 DOM 與封面專屬 CSS。公司名稱由公司資料語意槽承載，Logo 使用固定安全框；既有 `page.cover.heading` 留在 DOM 但隱藏，`page.cover.section.0.text` 繼續作可見副標，其他六頁完全不變。

**Tech Stack:** 單檔 HTML／CSS／內嵌 SVG、Python 3.11、Playwright、既有視覺伴隨伺服器。

## Global Constraints

- v48、v50、v53 必須保留；新版本只能建立 v54，不得覆寫既有候選。
- Logo 維持原始比例，不裁切、不拉伸；缺少素材時顯示中性「企業 Logo」佔位。
- 公司名稱最多兩行；副標最多三行；公司名稱計算字級至少為副標的兩倍。
- `page.cover.heading` 必須保留供舊草稿相容，但在封面不可見。
- `page.cover.section.0.text` 是可見副標，`page.cover.section.1.text` 是小型產業標籤。
- 呆一布只能位於右下裝飾層，不得與 Logo、公司名稱或副標重疊。
- 不新增外部套件、AI 圖片、資料庫欄位、付費服務或正式站變更。
- 前端完成前必須做兩輪 1280×800 與 375×812 截圖自檢。

---

### Task 1: 建立封面公司主體契約與 v54

**Files:**
- Create: `.superpowers/brainstorm/3440-1787701682/content/cover-company-first-contract.py`
- Create: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-54.html`
- Test: `.superpowers/brainstorm/3440-1787701682/content/cover-company-first-contract.py`

**Interfaces:**
- Consumes: v53 的七頁 DOM、`page.cover.heading`、`page.cover.section.0.text`、`page.cover.section.1.text`。
- Produces: `data-cover-hierarchy="company-first"`、`.cover-logo`、`.cover-company-name`、`.cover-subtitle` 與隱藏的 `.legacy-cover-heading`。

- [x] **Step 1: 寫封面層級失敗契約**

建立契約並以 Chromium 量測實際畫面：

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
          const cover = document.querySelector('[data-page="01"]');
          const rect = (selector) => cover.querySelector(selector).getBoundingClientRect();
          const overlap = (a, b) => Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left))
            * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
          const logo = rect('.cover-logo');
          const name = rect('.cover-company-name');
          const subtitle = rect('.cover-subtitle');
          const mascot = rect('.mascot');
          const nameStyle = getComputedStyle(cover.querySelector('.cover-company-name'));
          const subtitleStyle = getComputedStyle(cover.querySelector('.cover-subtitle'));
          cover.querySelector('.cover-company-name').textContent = 'Billow Artificial Intelligence Laboratories';
          return {
            marker: cover.dataset.coverHierarchy,
            legacyHidden: cover.querySelector('[data-content-key="page.cover.heading"]').hidden,
            logoBeforeName: logo.bottom <= name.top,
            nameBeforeSubtitle: name.bottom <= subtitle.top,
            typeRatio: parseFloat(nameStyle.fontSize) / parseFloat(subtitleStyle.fontSize),
            lineClamp: nameStyle.webkitLineClamp,
            subtitleClamp: subtitleStyle.webkitLineClamp,
            overlaps: [logo, name, subtitle].map((item) => overlap(item, mascot)),
            nameFits: cover.querySelector('.cover-company-name').scrollHeight
              <= cover.querySelector('.cover-company-name').clientHeight + 1,
          };
        }
        """
    )
    browser.close()

assert result["marker"] == "company-first", "missing company-first cover marker"
assert result["legacyHidden"], "legacy cover heading remains visible"
assert result["logoBeforeName"] and result["nameBeforeSubtitle"], "cover reading order is wrong"
assert result["typeRatio"] >= 2, "company name is not dominant enough"
assert result["lineClamp"] == "2" and result["subtitleClamp"] == "3", "line limits are missing"
assert max(result["overlaps"]) <= 1, "mascot overlaps primary cover content"
assert result["nameFits"], "long company name does not fit"
print("company-first cover contract passed")
```

- [x] **Step 2: 在 v53 執行契約並確認紅燈**

Run:

```bash
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/cover-company-first-contract.py \
  .superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-53.html
```

Expected: FAIL with `missing company-first cover marker` or missing `.cover-logo`.

- [x] **Step 3: 建立 v54 並只重排封面**

複製 v53 為 v54，將封面文章改為以下結構；舊 heading 保留但隱藏：

```html
<article class="carousel-page page-cover" data-page="01" data-story-role="hook"
  data-cover-hierarchy="company-first" aria-label="第 1 頁：封面">
  <div class="sheet yellow-back"></div>
  <div class="tape-mark tape-left"></div>
  <div class="tape-mark tape-right"></div>
  <div class="sheet main-sheet">
    <div class="cover-meta">
      <span>一布懂 AI 新創</span>
      <small class="series" data-content-key="page.cover.section.1.text">產業分類</small>
    </div>
    <div class="cover-logo" role="img" aria-label="企業 Logo">企業 Logo</div>
    <h3 class="cover-company-name" data-company-field="company">公司名稱</h3>
    <div class="cover-rule" aria-hidden="true"></div>
    <p class="cover-subtitle" data-content-key="page.cover.section.0.text">一句話定位：它用什麼方法，替誰解決什麼問題？</p>
    <p class="legacy-cover-heading" data-content-key="page.cover.heading" hidden>封面標題：一句話抓住這家公司最重要的改變</p>
  </div>
  <svg class="mascot" viewBox="0 0 300 340" role="img" aria-label="角色招手開場"><use href="#pose-wave"/></svg>
</article>
```

在 v54 最後加入封面專屬覆寫，避免改動第 2–7 頁：

```css
.page-cover .main-sheet{padding:8% 9% 9%}
.page-cover .cover-meta{display:flex;align-items:center;justify-content:space-between;gap:3cqw;padding-bottom:2.4cqw;border-bottom:.28cqw solid var(--line);font-size:1.55cqw;font-weight:900;letter-spacing:.12em}
.page-cover .cover-logo{display:grid;width:32cqw;height:17cqw;margin:8cqw auto 0;place-items:center;overflow:hidden;color:#6e7f99;background:#eef8f7;font-size:2cqw;font-weight:900;line-height:1.2;text-align:center}
.page-cover .cover-logo img{display:block;width:100%;height:100%;object-fit:contain}
.page-cover .cover-company-name{display:-webkit-box;max-height:20cqw;margin:5cqw 0 0;overflow:hidden;-webkit-box-orient:vertical;-webkit-line-clamp:2;color:var(--ink);font-size:8.2cqw;font-weight:900;line-height:1.02;letter-spacing:-.055em;text-align:center}
.page-cover .cover-rule{width:42%;height:1.1cqw;margin:2.2cqw auto 0;border-radius:99px;background:var(--coral)}
.page-cover .cover-subtitle{display:-webkit-box;width:72%;max-height:13cqw;margin:5cqw auto 0;overflow:hidden;-webkit-box-orient:vertical;-webkit-line-clamp:3;font-size:3.1cqw;font-weight:800;line-height:1.38;text-align:center}
.page-cover .mascot{right:1%;bottom:2%;width:25%}
```

- [x] **Step 4: 執行封面契約並修到綠燈**

Run:

```bash
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/cover-company-first-contract.py \
  .superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-54.html
```

Expected: `company-first cover contract passed`.

- [x] **Step 5: 執行全部既有原型契約**

Run:

```bash
candidate=.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-54.html
base=.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-48.html
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/cover-company-first-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/page-polish-contract.py "$candidate"
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/visual-storytelling-contract.py "$base" "$candidate"
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

Expected: 12 項契約全部通過；`schema-aligned-contract.js` 證明隱藏 heading 仍存在。

---

### Task 2: 視覺壓力測試、文件與收尾

**Files:**
- Modify: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-54.html`
- Modify: `HANDOFF.md`
- Modify: `docs/superpowers/plans/2026-08-26-company-first-carousel-cover.md`

**Interfaces:**
- Consumes: Task 1 的 v54 與封面契約。
- Produces: 經兩輪桌機／手機驗證的封面候選與可追溯測試證據。

- [x] **Step 1: 第一輪桌機與手機截圖**

將 v54 同步到目前視覺伴隨內容目錄，重新開啟既有 `localhost:65302`，只截：

```bash
playwright-cli resize 1280 800
playwright-cli screenshot --filename=.screenshots/company-first-cover-round1-desktop.png
playwright-cli resize 375 812
playwright-cli screenshot --filename=.screenshots/company-first-cover-round1-mobile.png
```

逐項檢查層次、留白、LINE Seed 字體、三色限制、左右基線、375px overflow、素材缺失狀態與既有 hover 微動效，明確記錄不合格項。

- [x] **Step 2: 依第一輪證據做最小修正並重跑契約**

只修改 `.page-cover` 範圍；若長名稱或副標不合格，優先調整安全框、間距與字級，不放寬兩行／三行限制，也不移動第 2–7 頁。

Run:

```bash
.venv/bin/python .superpowers/brainstorm/3440-1787701682/content/cover-company-first-contract.py \
  .superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-54.html
```

Expected: PASS.

- [x] **Step 3: 第二輪桌機與手機截圖及瀏覽器量測**

```bash
playwright-cli resize 1280 800
playwright-cli screenshot --filename=.screenshots/company-first-cover-final-desktop.png
playwright-cli resize 375 812
playwright-cli screenshot --filename=.screenshots/company-first-cover-final-mobile.png
playwright-cli eval "({scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth,pages:[...document.querySelectorAll('.carousel-page')].map((el,i)=>({page:i+1,overflow:el.scrollWidth>el.clientWidth}))})"
playwright-cli console
```

Expected: `scrollWidth == clientWidth == 375`、七頁 `overflow:false`、console 0 errors／0 warnings。

- [x] **Step 4: 產品理解檢查點與文件更新**

在 `HANDOFF.md` 記錄產品能力、使用者體驗、技術結構、資料流、設計理由、備援、安全與成本、契約與截圖證據、正式 Renderer 尚未接線的限制；將本計畫全部 checkbox 勾選。

- [x] **Step 5: 完整測試**

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q
```

Expected: `739 passed, 16 deselected`；只允許既有 Starlette／httpx 棄用 warning。

- [ ] **Step 6: 提交、推送與驗證**

```bash
git add HANDOFF.md docs/superpowers/plans/2026-08-26-company-first-carousel-cover.md
git commit -m "docs: validate company-first carousel cover"
git push origin main
git ls-remote origin refs/heads/main
```

Expected: 本機 `HEAD` 與遠端 `main` hash 相同；被 `.gitignore` 排除的 v54 與截圖不加入提交。正式程式未變，不重啟或部署正式站。
