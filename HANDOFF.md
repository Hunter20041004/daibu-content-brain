# HANDOFF — 呆一布選題大腦（daibu-content-brain）

> 兩個貼上區塊：規劃找 🧠 Claude、實作找 🖐 Codex。由 Claude 於 2026-07-28 更新。
> 一句話現況：**貼文輪播圖產生器的設計與 TDD 計畫已完成，等 Codex 實作階段 A。**
> 專案全貌、設計決策、測試基線、分支現況一律看 `STATUS.md`，這裡不重複。

---

## 這一輪要做什麼

**只做階段 A（Task 1–6），做完停下來讓使用者驗收，不要往階段 B 衝。**

階段 A ＝ 讓「AI 新創介紹」的選題產得出**具體公司**。目前 AI 產的 6 則候選
全是沒有公司名的通用觀點文，而且 `source_url` 全空——階段 B 的產圖沒有公司名
根本無從開始，所以這段是前提。但它自己就有交付價值：候選從「不知道在講誰」
變成看四行就能決定採用與否。

- 設計規格：`docs/specs/2026-07-28-貼文輪播圖產生器-design.md`
- TDD 計畫：`docs/plan-carousel.md`（Task 1–17，兩階段）

實作前基線：`.venv/bin/pytest -q` → `167 passed, 3 deselected`。

---

## ⚠️ 這一輪最容易踩的坑

1. **Task 4 會動到使用者真實資料庫的 `theme_sources`。** 它用 `config` 的
   `startup_sources_pruned` 標記確保只跑一次，使用者事後自己加回來的來源不可再被刪。
   測試已經涵蓋這一點，不要簡化掉。
2. **`grounding` 的預設值必須是 `model`**（需查證），不是 `source`。
   AI 沒標或亂標時當成「有依據」，會讓使用者誤以為那格查證過了。
3. **不要碰真實 `daibu.db`。** 驗收用複本：
   ```
   cp daibu.db /tmp/daibu-carousel.db
   DAIBU_DB_PATH=/tmp/daibu-carousel.db .venv/bin/streamlit run app.py --server.port 8502
   ```
   使用者自己常開著一個 Streamlit 在 8501，請挑別的 port。
4. **「產生候選」是真的會呼叫 AI 與外部來源的**（會花配額、要等幾秒）。

---

## ▼ 貼給 🖐 Codex（照計畫實作）

先讀 `STATUS.md`，再讀 `docs/plan-carousel.md`。

這一輪只做**階段 A：Task 1 到 Task 6**。嚴格 TDD、垂直切片，一次一個失敗測試 →
綠 → 重構 → 下一個。紅→綠循環只跑當前那一個測試檔，Task 收尾才跑全套。
每個 Task 做完就 commit。

Task 6 是收尾：跑全套、用資料庫複本實際操作一次、把結果寫進 `HANDOFF.md` 的
「本輪狀態」，然後**停下來**。階段 B（Task 7–17）等使用者驗收過再開新對話做。

設計層有疑問寫進 `docs/open-questions.md`，不要自行更動產品方向。

---

## ▼ 貼給 🧠 Claude（討論／規劃／決策）

我要繼續呆一布選題大腦。先讀 `STATUS.md` 與 `docs/open-questions.md`。

要談的：

1. Codex 做完階段 A 之後的驗收結果
2. 階段 B（Task 7–17）開工前要不要調整
3. `codex/ia-topic-first` 與 `codex/frontend-brand-refactor` 兩個分支怎麼整合回
   `main`（**這件事拖很久了，還沒決定**）

我完全沒有程式背景，專有名詞第一次出現請先用白話解釋。
**我負責產品決策，實作交給 Codex；請不要直接動程式碼。**

---

## 本輪狀態

- 2026-07-29：Task 1–6 完成；全套 **174 passed、3 deselected、0 failed**。
- 複本實測：舊 6 則保留、5 來源綁定；真實產生 Hint、Pangram、Vela 後共 9 則，
  公司名、網址、引文齊全，console 0 errors。
- 限制：Y Combinator／INSIDE 缺 Tavily key、a16z 回 404；本次由另 2 個來源產題。
- 最終截圖：`.screenshots/desktop-round2.png`、`.screenshots/mobile-round2.png`。
- **已停在階段 A。下一步請開新對話做使用者驗收；不要直接開始階段 B。**

---

## 歷史

每一輪的完整實作紀錄與驗收證據放在 `docs/history/`，這份交接單只留當前這一輪
（上限 4 KB，由 `~/.claude/hooks/handoff-size-gate.mjs` 把關）。
