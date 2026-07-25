# HANDOFF — 呆一布選題大腦（daibu-content-brain）

> 兩個貼上區塊：規劃找 🧠 Claude、實作找 🖐 Codex。由 Claude 於 2026-07-24 更新。
> 一句話現況：**資訊架構 Task 1–16 已實作並驗證，位於 `codex/ia-topic-first`，待使用者產品驗收與整合。**

---

## 這一輪要做什麼

**選題為核心的資訊架構重整。** 使用者的原話：

> 「app 那頁應該要是情況概覽。設定方面有關什麼守門線的都幫我拿掉。選題的部分這頁
> 最嚴重，應該要是我現在既有的主題可以讓我設定跟編輯選要每個主題要去哪裡抓資料，
> 然後可以選主題產內容。內容流水線那一個分頁很多餘，可以拿掉。」

文件：

- 設計規格：`docs/specs/2026-07-24-選題為核心的資訊架構重整-design.md`
- TDD 實作計畫：`docs/plan-ia-refactor.md`（Task 1–16，逐一垂直切片）

經 brainstorm ＋ grill-me 定案的 **15 項決定**，摘要：

1. 首頁 → 行動導向的情況概覽（第一句話直接講下一步該做什麼）
2. 設定頁只剩系統設定（LLM／模型／API key／搜尋服務）
3. **守門線概念整個移除**（分數、理由、prompt 段落、設定欄位）
4. 選題頁改**主從式工作台**（左主題清單、右該主題工作區）
5. 主題**直接綁具體來源**，L1–L5 分層廢除
6. **常青／時效分類移除**（勾了來源就抓，沒勾就讓 AI 靠主題名發想）
7. 星期只當提醒，產候選由使用者點主題觸發
8. 來源庫收在選題頁的可展開區
9. 已採用的題目放選題頁下方（可寫正文、可標已發）
10. 流水線頁刪除，狀態收成 候選／採用／已發
11. 淘汰＝存成「已淘汰」＋**下次產候選時餵回 AI 叫它避開**
12. 新增 `published_at`
13. 現有主題的來源忠實換算，使用者自行修剪
14. 刪掉 3 個 manual 來源，抓取方式只留 rss／search
15. 沿用 DIVE 品牌視覺，只把資訊密度調緊

⚠️ **本輪明確不做**：分平台文字（Threads／IG／LinkedIn）與圖片生成。使用者已確認
那是下一輪的功能區。

⚠️ **三個最容易踩的坑**：

1. **舊資料庫要能就地升級**。使用者的 `daibu.db` 有 3 主題／18 來源／8 題目／
   1 筆成效，全部都要保住。升級程式要**可重複執行不出錯**（Task 8）。
2. **選題頁不能再依賴「今天星期幾」**。舊版按鈕只產今天排定的主題，新版是使用者
   點哪個主題就產哪個（Task 14 切片 3 專門擋這件事）。
3. **視覺紅線沿用上一輪**：白字不可放在品牌藍綠 `#6FC1CC` 上（對比只有 2.06:1），
   主要按鈕一律深色字 `#0E0E2C`；深色模式文字不可用 `#32738F`。
   `daibu/theme.py` 與 `tests/test_theme.py` 一行都不要動。

---

## ▼ 貼給 🖐 Codex（照計畫實作）

我要實作呆一布選題大腦的資訊架構重整。請依序讀：`STATUS.md`、`AGENTS.md`、
`docs/specs/2026-07-24-選題為核心的資訊架構重整-design.md`、`docs/plan-ia-refactor.md`。

- Streamlit ＋ SQLite；Python 用 `.venv/bin/python`，測試 `.venv/bin/pytest`
- 從 `docs/plan-ia-refactor.md` 的 Task 1 開始，**嚴格 TDD、一次一個失敗測試、
  垂直切片**，每個 Task 做完就 commit
- **不准動**：`daibu/theme.py`、`tests/test_theme.py`、`daibu/performance.py`、
  `daibu/fetch/rss.py`、`daibu/fetch/search.py`
- 顏色與字級只能來自 `daibu/theme.py`，`pages/` 裡不得出現寫死色碼
- **Task 8（資料搬遷）必須用使用者真實的 `daibu.db` 副本實測**，不能只靠
  mock，這是計畫裡唯一碰真實資料的關卡
- **Task 16（截圖自檢）不可跳過**，沒跑完兩輪截圖不得宣稱完成
- 設計層疑點寫進 `docs/open-questions.md`，不要自行更動產品方向

分支 `refactor/ia-topic-first` 的 commit `b6b66bc` 是 Claude 越權寫的探路稿
（大致等價於 Task 1–3），**可參考、可無視，不要直接 merge**。

基線：`main` 上 `.venv/bin/pytest -q` 為 `68 passed, 3 deselected`。

---

## ▼ 貼給 🧠 Claude（討論／規劃／決策）

我要繼續呆一布選題大腦。先讀 `STATUS.md`、
`docs/specs/2026-07-24-選題為核心的資訊架構重整-design.md` 與
`docs/open-questions.md`。

資訊架構重整的規格與計畫已寫好、交給 Codex 實作中。可能要談的：

1. Codex 做完後的產品驗收（主從式選題頁好不好用、概覽的「下一步提示」準不準）
2. **下一輪的大功能：分平台產文字（Threads／IG／LinkedIn）＋由文字產貼圖**
   —— 需要獨立一輪設計，且要先解決「圖片生成服務多數付費」與既定的
   「只用免費額度」成本策略的衝突
3. `docs/open-questions.md` 裡剩下的待裁決項目

我完全沒有程式背景，專有名詞第一次出現請先用白話解釋。
**我負責產品決策，實作交給 Codex；請不要直接動程式碼。**

---

## 已知的技術債

- 尚未設定 git 遠端；Tavily 契約測試因無 API key 持續跳過。
- 「AI 近期大事」原本靠 L3 的兩份電子報（TLDR AI、Ben's Bites），本輪刪掉 manual
  來源後**該層變成 0 個來源**，這個主題實際能抓的來源比原本少。若使用者在意，
  需另尋可自動抓取的替代來源。

---

## 本輪狀態（Claude，2026-07-24）

**狀態：設計已定案，等 Codex 實作。**

### 已完成（Claude 這一輪的產出）

- 用 AskUserQuestion 跑完 brainstorm 的四個大方向決策
- 用 `grill-me` 逐題盤問 11 個細節分岔，全部收斂
- 寫出設計規格與 16 個 Task 的 TDD 計畫
- 更新 `HANDOFF.md`、`STATUS.md`、`docs/open-questions.md`

### 過程中的一次違規（留紀錄避免重蹈）

Claude 一度**直接動手改程式碼**（`daibu/db.py`、`daibu/llm/`、多個測試檔），
違反「Claude 大腦／Codex 手」的分工。使用者當場指正後，該批改動已封存於分支
`refactor/ia-topic-first` 的 commit `b6b66bc`，`main` 已回復乾淨。

---

## 本輪狀態（Codex，2026-07-24）

**狀態：Task 1–16 已完成，待使用者產品驗收。**

### 使用者現在得到的產品能力

- 首頁是行動導向的「情況概覽」：下一步、待辦數字、七日排程、主題近況與提醒。
- 選題頁是主從式工作台：左側選主題，右側管理來源、產候選、採用／微調／淘汰、
  寫正文與標記已發。
- 設定頁只保留 provider、模型、搜尋服務與 API key；流水線頁已移除。
- 主題直接綁來源；淘汰標題會回饋給下一次生成；`published_at` 可誠實計算本週已發。

### 資料搬遷證據

- 使用者真實 `daibu.db` 的**副本**已執行就地升級；原檔未修改。
- 搬遷後保留 3 主題／8 題目／1 成效，來源由 18 變為 15。
- 三主題綁定來源數為 13／10／15；只剩 `rss`／`search`，外鍵檢查無錯。
- 注意：「AI 近期大事」原本 L3 的兩份 manual 電子報已移除，該層現在沒有來源。

### 測試與視覺證據

- `.venv/bin/pytest -q` → **99 passed、3 deselected**；3 個真實 API 契約測試未執行。
- Task 16 已跑兩輪桌機 1280×800、手機 375×812，並走過淺色與深色模式。
- 兩個 375px 畫面實測 `scrollWidth == innerWidth == 375`，無橫向捲軸。
- 最終淺色概覽：
  - `.screenshots/ia-refactor/round2/home-light-desktop.png`
  - `.screenshots/ia-refactor/round2/home-light-mobile.png`
- 最終深色選題：
  - `.screenshots/ia-refactor/round2/selection-dark-desktop.png`
  - `.screenshots/ia-refactor/round2/selection-dark-mobile.png`

### 剩餘限制

- 3 個外部服務契約測試沒有 API key，因此未呼叫外部服務。
- 成效頁只有一個主題數據點時，Vega 會在瀏覽器 console 留下尺度 warning；
  畫面可用，且本輪規格明訂不更動成效版面與 `daibu/performance.py`。
- 驗收清單的全 repo 禁詞 grep 與舊 schema 搬遷程式互相衝突，已記錄於
  `docs/open-questions.md`；沒有用字串混淆規避。
