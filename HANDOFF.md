# HANDOFF — 呆一布選題大腦（daibu-content-brain）

> 兩個貼上區塊：規劃找 🧠 Claude、實作找 🖐 Codex。由 Claude 於 2026-07-29 更新。
> 一句話現況：**B1 已驗收通過；這一輪做 B2，把七格草稿變成 7 張 PNG。**
> 專案全貌、設計決策、測試基線一律看 `STATUS.md`，這裡不重複。

---

## 這一輪要做什麼

**B2 ＝ Task 12、13、14。做完就停，不要碰 Task 15–17。**

這一輪交付的是：**字型與吉祥物就位，一則草稿能真的輸出 7 張 PNG**。
選題頁上還不會有按鈕、還不會打包 zip——那是 B3。

- 設計規格：`docs/specs/2026-07-28-貼文輪播圖產生器-design.md`
- TDD 計畫：`docs/plan-carousel.md`（Task 12–14）
- 上一輪的驗收證據：`docs/history/HANDOFF-2026-07-29-carousel-b1.md`

實作前基線：`.venv/bin/pytest -q` → `195 passed, 8 deselected`。

**開工前的擋路石**：LINE Seed TW 字型要**使用者自己去官網下載**
（<https://seed.line.me/index_tw.html>），把 Regular／Bold／ExtraBold 三個 `.otf`
與授權條款放進 `assets/fonts/`。檔案還沒到位就先做七個吉祥物 SVG，字型那條測試
會紅——**不要為了讓它綠就改測試，也不要改成抓網路字型**。

---

## ⚠️ 這一輪最容易踩的坑

1. **七個吉祥物 SVG 畫完要截圖給使用者挑**（Task 12 Step 5）。這是使用者明確
   要參與的一步，不滿意就退回重畫。**不要自己拍板往下做 Task 13。**
   這組素材網站也會共用，值得多花時間。
2. **貼文圖的顏色一律寫死**，禁止 CSS 變數與 `light-dark()`。它是要匯出的成品，
   不是介面，不能跟著深淺模式變。色票、字重（只有 400／700／800）、畫布
   1080×1350 全部見計畫的「Global Constraints」，一個字都不要自己改。
3. **Task 14 那三個像素契約測試預設就要跑**，不可以 deselect 掉。
   必須真的產出 PNG 去看像素，不是只測函式有沒有被呼叫——
   「字沒被畫出來」這種錯只有看像素才抓得到。
4. **`playwright install chromium` 首次約 150 MB**，先裝好再開始 Task 14，
   不要把下載時間算進紅→綠的循環裡。
5. **不要碰真實 `daibu.db`。** 要實際跑就用複本：
   ```
   cp daibu.db /tmp/daibu-b2.db
   DAIBU_DB_PATH=/tmp/daibu-b2.db .venv/bin/streamlit run app.py --server.port 8502
   ```
   使用者自己常開著一個 Streamlit 在 8501，請挑別的 port。

---

## 下一步

B2 做完停下來讓使用者驗收（重點是看那 7 張圖長什麼樣）。通過後另開新對話做
B3（Task 15–17）。

B3 開場前要先處理的兩件小事，已記在
`docs/history/HANDOFF-2026-07-29-carousel-b1.md`：provider 缺公開的
`generate_text`（已補進計畫的 Task 17）、真實 LLM 契約測試的測資要換掉。

---

## 本輪狀態

（Codex 實作時填：完成到哪個 Task、全套測試數字、契約測試結果、
截圖路徑、卡住的地方。）

---

## 歷史

每一輪的完整實作紀錄與驗收證據放在 `docs/history/`，這份交接單只留當前這一輪
（上限 4 KB，由 `~/.claude/hooks/handoff-size-gate.mjs` 把關）。
