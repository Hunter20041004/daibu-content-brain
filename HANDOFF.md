# HANDOFF — 呆一布選題大腦（daibu-content-brain）

> 兩個貼上區塊：規劃找 🧠 Claude、實作找 🖐 Codex。於 2026-07-29 更新。
> 一句話現況：**B2 已完成；先驗收七張 PNG，通過後另開對話做 B3。**
> 專案全貌、設計決策、測試基線一律看 `STATUS.md`，這裡不重複。

---

## 下一輪要做什麼

**B3 ＝ Task 15–17。使用者核可 B2 的七張圖後才開始。**

下一輪交付的是：**超長文字不爆版、七張圖可打包 zip、選題頁接上「產貼圖」按鈕**。

- 設計規格：`docs/specs/2026-07-28-貼文輪播圖產生器-design.md`
- TDD 計畫：`docs/plan-carousel.md`（Task 15–17）
- B1 驗收證據：`docs/history/HANDOFF-2026-07-29-carousel-b1.md`

實作前基線：`.venv/bin/pytest -q` → `220 passed, 8 deselected`。

---

## ⚠️ 下一輪最容易踩的坑

1. Task 15 要用超長字串真的出圖看底部像素，不可只測 CSS 字串。
2. Task 16 的 zip 檔名固定 `01-cover.png` 到 `07-cta.png`，七張順序不可漂移。
3. Task 17 要補 provider 公開的 `generate_text`；真實 LLM 契約測資也要換掉，
   詳見 B1 歷史交接單。
4. **不要碰真實 `daibu.db`。** 要實際跑就用複本：
   ```
    cp daibu.db /tmp/daibu-b3.db
    DAIBU_DB_PATH=/tmp/daibu-b3.db .venv/bin/streamlit run app.py --server.port 8502
   ```
   使用者自己常開著一個 Streamlit 在 8501，請挑別的 port。

---

## 本輪狀態

- 2026-07-29：Task 12–14 完成；尚未碰 Task 15–17。
- 新增 `shoot.png_bytes(html_text)`：以臨時本機 HTML 載入三個 LINE Seed TW 字重，
  再用 Chromium 輸出固定 1080×1350 PNG；字型失敗會明確報錯，不會靜默 fallback。
- 四個瀏覽器／像素測試預設執行：PNG 簽名與尺寸、外框／白卡色、文字像素、缺字型
  錯誤；Task 14 局部 `4 passed`，全套 `220 passed, 8 deselected`。
- 七張輸出與兩輪視覺自檢完成，最終瀏覽器 console `0 errors, 0 warnings`。
  七張圖：`.screenshots/task14-final/01-cover.png` 至 `07-cta.png`；
  檢視表：`.screenshots/task14-round1-contact-sheet.png`；
  最終封面：`.screenshots/task14-final-cover.png`。
- 下一步：先讓使用者目視驗收七張圖；通過後另開新對話做 B3。

---

## 歷史

每一輪的完整實作紀錄與驗收證據放在 `docs/history/`，這份交接單只留當前這一輪
（上限 4 KB，由 `~/.claude/hooks/handoff-size-gate.mjs` 把關）。
