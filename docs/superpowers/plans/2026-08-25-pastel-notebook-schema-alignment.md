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
