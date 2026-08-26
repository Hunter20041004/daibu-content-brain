# 粉彩手帳模板內容契約對齊 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓已核可的粉彩手帳七頁原型完整容納現有自動產圖工具的正式內容欄位。

**Architecture:** 保留單檔視覺伴隨原型，使用 `data-content-key` 建立一對一內容契約；Node 靜態契約負責欄位與禁用假設，Playwright 負責兩種 viewport 的使用者畫面驗證。

**Tech Stack:** HTML、CSS、SVG、Node.js 靜態契約、Playwright CLI。

## Global Constraints

- 不修改正式 Renderer、SQLite、LLM prompt 或舊草稿。
- 不改粉彩手帳色票、紙張語言或四種已核可角色動作。
- 一次只新增一個失敗契約，再做最小版面修改轉綠。

---

### Task 1: 七頁內容鍵契約

**Files:**
- Create: `.superpowers/brainstorm/3440-1787701682/content/schema-aligned-contract.js`
- Create: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-schema-aligned-31.html`

**Interfaces:**
- Consumes: `daibu/cards/pages.py` 的頁型與欄位順序。
- Produces: 每個正式內容角色一個 `data-content-key` 的原型 DOM。

- [x] **Step 1: 寫欄位鍵與禁用假設契約。**
- [x] **Step 2: 對 v30 執行並確認因缺少正式鍵而失敗。**
- [x] **Step 3: 複製為新畫面並逐頁重綁內容槽。**
- [x] **Step 4: 執行契約並確認通過。**

### Task 2: 響應式視覺驗收

**Files:**
- Modify: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-schema-aligned-31.html`
- Modify: `HANDOFF.md`

**Interfaces:**
- Consumes: Task 1 的七頁原型。
- Produces: 無裁切、無水平溢出的桌機與手機畫面。

- [x] **Step 1: 以 Playwright 截 1280×800 與 375×812 第一輪畫面。**
- [x] **Step 2: 列出不合格項並做最小 CSS 修正。**
- [x] **Step 3: 重截第二輪，檢查 console、scrollWidth 與七頁內容鍵。**
- [x] **Step 4: 將證據與剩餘限制寫回 `HANDOFF.md`。**

### Task 3: 直角框線與內容密度

**Files:**
- Create: `.superpowers/brainstorm/3440-1787701682/content/straight-density-contract.py`
- Create: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-straight-dense-35.html`
- Modify: `HANDOFF.md`

**Interfaces:**
- Consumes: Task 2 的正式內容鍵與粉彩手帳外殼。
- Produces: 主要框全數回正、主要內容延伸至畫布至少 74% 的原型。

- [x] **Step 1: 寫主要框旋轉與內容模組高度的瀏覽器契約。**
- [x] **Step 2: 在 v31 重現 22 個旋轉框及低密度頁面。**
- [x] **Step 3: 回正紙框與資訊框，放大真實內容模組。**
- [x] **Step 4: 修正第 2 頁窄欄越界，完成桌機與手機視覺迭代。**
- [x] **Step 5: 驗證內容契約、手帳一致性、直角密度與瀏覽器 console。**

### Task 4: 全頁便利貼表面系統

**Files:**
- Create: `.superpowers/brainstorm/3440-1787701682/content/sticky-note-system-contract.py`
- Create: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-37.html`
- Modify: `HANDOFF.md`

**Interfaces:**
- Consumes: Task 3 的直角密集版面與正式內容鍵。
- Produces: 29 個語意內容面共用的便利貼紙面、色票與陰影。

- [x] **Step 1: 寫便利貼數量、無框線、有陰影、無旋轉的瀏覽器契約。**
- [x] **Step 2: 在 v35 確認缺少統一便利貼系統。**
- [x] **Step 3: 將定位、基本資料、AI 步驟、成果、訊號與結論統一成便利貼。**
- [x] **Step 4: 依第一輪截圖加強紙片陰影，維持直角與內容密度。**
- [x] **Step 5: 以桌機、手機與四項契約完成複驗。**

### Task 5: 便利貼實體材質細節

**Files:**
- Create: `.superpowers/brainstorm/3440-1787701682/content/sticky-material-contract.py`
- Create: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-39.html`
- Modify: `HANDOFF.md`

**Interfaces:**
- Consumes: Task 4 的 29 個直角便利貼面。
- Produces: 每張便利貼共用的上緣黏膠層、紙纖維與右下掀角。

- [x] **Step 1: 寫 29 個便利貼的黏膠、紙紋、折角瀏覽器契約。**
- [x] **Step 2: 在 v37 確認只有色面與陰影，材質契約失敗。**
- [x] **Step 3: 加入三個材質提示，保留 AI 步驟與 CTA 的定位方式。**
- [x] **Step 4: 依第一輪截圖加強上緣黏膠色差。**
- [x] **Step 5: 以兩輪截圖與五項原型契約完成複驗。**

### Task 6: 第 3／4 頁密度與社群 CTA

**Files:**
- Create: `.superpowers/brainstorm/3440-1787701682/content/page-three-four-density-contract.py`
- Create: `.superpowers/brainstorm/3440-1787701682/content/social-cta-contract.py`
- Create: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-43.html`
- Modify: `HANDOFF.md`

**Interfaces:**
- Consumes: Task 5 的便利貼材質與現有 `CarouselDraft` CTA 欄位。
- Produces: 第 3／4 頁緊密版面，以及不重複內容總結的系列社群 CTA。

- [x] **Step 1: 寫第 3／4 頁等寬節點與底部空隙契約，在 v39 確認失敗。**
- [x] **Step 2: 將問題節點與 AI 流程改成等寬列，保留下方四格敘事。**
- [x] **Step 3: 寫純社群 CTA 契約，在 v40 確認舊結論結構失敗。**
- [x] **Step 4: 改成帳號、內容承諾、讀者問題與三個行動；隱藏舊生成欄位維持相容。**
- [x] **Step 5: 依截圖量出 CTA 空洞，加入留言提示並完成桌機／手機複驗。**

### Task 7: 移除 CTA 區塊並改為置中短句

**Files:**
- Modify: `.superpowers/brainstorm/3440-1787701682/content/social-cta-contract.py`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/sticky-note-system-contract.py`
- Modify: `.superpowers/brainstorm/3440-1787701682/content/sticky-material-contract.py`
- Create: `.superpowers/brainstorm/3440-1787701682/content/company-neutral-seven-pages-sticky-45.html`
- Modify: `HANDOFF.md`

- [x] **Step 1: 將 CTA 契約改為 2–3 句置中文字、零舊區塊，並在 v43 確認失敗。**
- [x] **Step 2: 移除帳號卡、提問卡、提示膠囊與行動列，保留四個隱藏舊欄位。**
- [x] **Step 3: 將便利貼表面契約由 29 面更新為前六頁 26 面，以 v43 紅、v44 綠校準。**
- [x] **Step 4: 依第一輪截圖建立 CTA 最小字級比例契約，於 v45 放大三層文字。**
- [x] **Step 5: 完成桌機／手機第二輪截圖、console 與全套契約驗收。**
