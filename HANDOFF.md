# HANDOFF — 呆一布選題大腦（daibu-content-brain）

> 兩個貼上區塊：規劃找 🧠 Claude、實作找 🖐 Codex。由 Claude 於 2026-07-29 更新。
> 一句話現況：**B1 已實作完成；五個 RSS 來源全活，等待使用者驗收。**
> 專案全貌、設計決策、測試基線一律看 `STATUS.md`，這裡不重複。

---

## 這一輪要做什麼

**B1 ＝ Task 6.5 與 Task 7–11 已完成，尚未進入 B2。**

階段 B 有 11 個 Task，一場對話塞不下，切成三輪（見 `docs/plan-carousel.md`
「階段 B 分三輪做」）。B1 交付的是：**壞掉的來源修好，而且一則採用的候選能產出
七格文字草稿並存進資料庫**。這一輪還沒有畫面、還沒有圖，那是 B2 和 B3 的事。

- 設計規格：`docs/specs/2026-07-28-貼文輪播圖產生器-design.md`
- TDD 計畫：`docs/plan-carousel.md`
- 上一輪的驗收證據：`docs/history/HANDOFF-2026-07-29-carousel-phase-a.md`

實作前基線：`.venv/bin/pytest -q` → `174 passed, 3 deselected`。

---

## ⚠️ 這一輪最容易踩的坑

1. **Task 6.5 的搬遷必須排在 Task 4 的收斂之後。** 順序反了的話，新綁上去的
   `VentureBeat AI` 會被 Task 4 那段 DELETE 直接掃掉，而且因為兩段都只跑一次，
   之後不會自己修好。
2. **契約測試（打真實網路那五個網址）不可以跳過，紅了也不准改測試讓它過。**
   上一輪三個來源壞掉沒被發現，就是因為既有測試全是假資料。有網址掛掉就寫進
   `docs/open-questions.md`，其餘照常做完，回報時講清楚哪一個掛了。
3. **`grounding` 的預設值必須是 `model`**（需查證），不是 `source`。AI 沒標或
   亂標時當成「有依據」，會讓使用者誤以為那一格查證過了。
4. **引文門檻 `MIN_EXCERPT_CHARS = 60` 是 `daibu/cards/draft.py` 的常數**，
   別在別處再寫死一次 60。
5. **不要碰真實 `daibu.db`。** 驗收用複本：
   ```
   cp daibu.db /tmp/daibu-b1.db
   DAIBU_DB_PATH=/tmp/daibu-b1.db .venv/bin/streamlit run app.py --server.port 8502
   ```
   使用者自己常開著一個 Streamlit 在 8501，請挑別的 port。

---

## 下一步

使用者先驗收 B1。通過後另開新對話做 B2（Task 12–14）；不要提前做 Task 12。
驗收時一併決定下方真實 LLM 契約測試的測資要如何調整。

---

## 本輪狀態

- **已完成** Task 6.5、7–11；提交：
  `16410b4`、`64a4b60`、`d5370c8`、`2d83873`、`a9e57fb`、
  `7ce3f72`、`963386b`。
- 交付：5 個免 key RSS 來源；七格資料契約；`carousel_pages` CRUD 與刪除一致性；
  輪播 prompt／安全解析；草稿生成、保存與 60 字引文門檻。
- 全套：`.venv/bin/pytest -q` → **195 passed, 8 deselected**。
- 契約：五個指定 RSS 網址**全部通過**。整條
  `.venv/bin/pytest -m contract -q` 為 **1 failed, 6 passed, 1 skipped**；
  失敗的是既有 `test_real_llm_returns_parsable_ideas`：測資沒有具體公司名，
  新 prompt 依規格回 0 則。不是來源網址失效，未改鬆測試。
- UI 自檢：桌機／手機兩輪，無橫向捲動、console 0 error。
  最終圖：`.screenshots/task9-final-desktop.png`、
  `.screenshots/task9-final-mobile.png`。
- **停止點**：等待使用者驗收，不做 B2。

---

## 歷史

每一輪的完整實作紀錄與驗收證據放在 `docs/history/`，這份交接單只留當前這一輪
（上限 4 KB，由 `~/.claude/hooks/handoff-size-gate.mjs` 把關）。
