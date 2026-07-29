# HANDOFF — 呆一布選題大腦（daibu-content-brain）

> 兩個貼上區塊：規劃找 🧠 Claude、實作找 🖐 Codex。由 Claude 於 2026-07-29 更新。
> 一句話現況：**階段 A 已驗收通過，這一輪做階段 B 的第一輪（B1）。**
> 專案全貌、設計決策、測試基線一律看 `STATUS.md`，這裡不重複。

---

## 這一輪要做什麼

**只做 B1 ＝ Task 6.5 與 Task 7–11，做完停下來，不要往 B2 衝。**

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

## ▼ 貼給 🖐 Codex（照計畫實作）

先讀 `STATUS.md`，再讀 `docs/plan-carousel.md`。

這一輪只做 **Task 6.5，接著 Task 7 到 Task 11**。嚴格 TDD、垂直切片，一次一個
失敗測試 → 綠 → 重構 → 下一個。紅→綠循環只跑當前那一個測試檔，收尾才跑全套。
每個 Task 做完就 commit。

收尾請做三件事，然後**停下來**：跑一次全套；跑一次
`.venv/bin/pytest -m contract -q` 確認五個來源的網址真的活著；把結果寫進下面的
「本輪狀態」。B2（Task 12–14）等使用者驗收過再開新對話做。

設計層有疑問寫進 `docs/open-questions.md`，不要自行更動產品方向。

---

## ▼ 貼給 🧠 Claude（討論／規劃／決策）

我要繼續呆一布選題大腦。先讀 `STATUS.md` 與 `docs/open-questions.md`。

要談的：

1. B1 的驗收結果
2. B2（Task 12–14，出圖）開工前要不要調整
3. `codex/ia-topic-first` 要不要現在就合併回 `main`（領先 58 個 commit、
   0 衝突、是 fast-forward；`refactor/ia-topic-first` 只剩一個標明作廢的
   探路 commit 可刪。**這個 repo 沒有遠端，推不上 GitHub 也沒有正式站**）

我完全沒有程式背景，專有名詞第一次出現請先用白話解釋。
**我負責產品決策，實作交給 Codex；請不要直接動程式碼。**

---

## 本輪狀態

- 尚未開工。

---

## 歷史

每一輪的完整實作紀錄與驗收證據放在 `docs/history/`，這份交接單只留當前這一輪
（上限 4 KB，由 `~/.claude/hooks/handoff-size-gate.mjs` 把關）。
