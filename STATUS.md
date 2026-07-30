# 專案現況 — 呆一布選題大腦（Daibu Content Brain）

> 由 Claude 建立、於 2026-07-30 更新。**新對話請先讀這份**。

## 這是什麼

**社群組的「內容決策大腦」** — 幫忙決定「這次要寫什麼主題」的工具。
以**主題**為核心：設定每個主題去哪些來源抓資料 → 讓 AI 產題目候選 → 你審核採用 →
寫正文、標記已發 → 回填成效 → 看哪個主題值得延續。

## 技術棧與怎麼跑

- **Streamlit**（四頁 UI）+ **SQLite**（`daibu.db`）
- Python 3.11．**用專案自己的虛擬環境**：`.venv/bin/python`
- `daibu/` — 核心邏輯；`pages/` — Streamlit 各頁；`app.py` — 進入點
- 測試：`.venv/bin/pytest`（`pytest.ini` 已設 `pythonpath = .`）
- LLM：**免費層可切換**（gemini／groq，不綁單一供應商）

## 工作分工（重要）

**Claude 是大腦 🧠**：發想、設計決策、寫 `docs/` 的 spec 與 TDD 計畫、更新
`HANDOFF.md`。**不直接寫實作程式碼。**
**Codex 是手 🖐**：照 `HANDOFF.md` 與 `docs/` 的計畫實作（紅→綠→重構）。

## 已定案的設計決策

- **不採用「四支柱」框架**（討論後捨棄）
- **守門線品管已廢除**（2026-07-24）：分數與評分標準對使用者沒有帶來判斷價值
- **L1–L5 來源分層已廢除**（2026-07-24）：主題直接綁具體來源
- **常青／時效分類已廢除**（2026-07-24）：有勾來源就抓、沒勾就靠主題名發想
- 成本策略：只用免費額度
- **刪除主題＝連底下的題目一起刪**（2026-07-25）：刪之前要先告知會刪掉幾則
- **預設的 3 主題／15 來源只在資料庫全新時灌一次**（2026-07-25）：
  使用者刪掉就是刪掉了，不再自動補回
- **採用與淘汰都是一步完成、都可復原**（2026-07-25）：
  實際使用時淘汰的次數遠多於採用，不該把它設計得比較麻煩
- **Logo 上限**（2026-07-30）：檔案 ≤ 2 MB；PNG 單邊 ≤ 4096 px、總像素 ≤ 800 萬、
  單邊 ≥ 64 px；SVG 必須有 `viewBox` 或寬高。檔案大小與解碼後像素分開限制，
  防的是「壓縮後很小、解開很大」的圖
- **來源包與來源快照分兩張表**（2026-07-30）：`idea_sources` 可隨時編輯，
  `carousel_sources` 是產草稿當下的快照，事後改筆記不會弄壞已存草稿
- **缺 Logo 只擋產圖、不擋產草稿**（2026-07-30）：草稿是純文字，不需要 Logo

## 目前進度

- **v1 功能**：已完成（訊號蒐集 → 選題 → 狀態流轉 → 成效回填）
- **前端品牌重構**：已完成，位於 `codex/frontend-brand-refactor` 分支。
  淺／深雙模式、桌機與手機版面、鍵盤 focus、減少動態偏好都已驗收。
- **資訊架構重整**：**Task 1–16 已由 Codex 實作完成**，位於 `codex/ia-topic-first`。
  - 設計規格：`docs/specs/2026-07-24-選題為核心的資訊架構重整-design.md`
  - TDD 計畫：`docs/plan-ia-refactor.md`（Task 1–16）

  主要改動：首頁改行動導向的情況概覽、設定頁只剩系統設定、選題頁改主從式工作台
  （左主題／右工作區）、流水線頁刪除、守門線與分層與常青分類全部移除。

- **操作驗收**：**已完成（2026-07-25）**，方向獲得肯定，但找出 **24 條要修的問題**，
  其中 **4 條會弄壞資料**（深色模式彈出視窗文字隱形、刪主題產生孤兒題目、
  時間戳記時區導致「本週已發」算錯、正文草稿會靜默消失）。
  - 驗收回饋（給人看，含截圖）：`docs/2026-07-25-操作驗收回饋.html`
  - TDD 計畫：`docs/plan-qa-fixes.md`（Task 1–24，五個階段）
  - **狀態：階段 A–E（Task 1–24）與最後整體驗收全部完成。**

- **貼文輪播圖產生器**：出圖引擎與選題工作台接線皆已在 `main` 完成。
  - 設計規格：`docs/specs/2026-07-28-貼文輪播圖產生器-design.md`
  - TDD 計畫：`docs/plan-carousel.md`（Task 1–17，分階段 A ＋ B1／B2／B3）
  - **階段 A（Task 1–6）已驗收**（2026-07-29）：選題產得出具體公司名與來源引文。
  - **B1（Task 6.5、7–11）已驗收**（2026-07-29）：五個來源全部修成免 key 的 RSS；
    七格結構、`carousel_pages` 資料表、輪播 prompt 與解析、草稿生成與 60 字引文門檻。
    驗收證據：`docs/history/HANDOFF-2026-07-29-carousel-b1.md`
  - **B2 Task 12–14 已完成（2026-07-29）**：字型與吉祥物就位，七格草稿可渲染成
    固定 1080×1350 品牌 HTML，再由 Playwright 輸出為 7 張 PNG。
- **資訊與視覺重設 Phase A–C 已完成（2026-07-30）**：
    `docs/plan-carousel-redesign.md` 的 Task 1–8 已完成。七頁來源草稿、官方 Logo
    驗證、固定圖解、滿版 HTML、七張 PNG 與兩輪視覺驗收均通過；免費 LLM 已改用
    `gemini-3.1-flash-lite`，Idea 與輪播真實契約均通過。
- **來源蒐集與出圖接線 Phase A–D 已完成（2026-07-30）**：
    `docs/plan-cards-wiring.md` 的 Task 1–11 已完成。每題來源包、網址建議值、
    Logo 上傳／重用、七頁編輯、出圖預覽與 ZIP 下載已接進已採用題目的工作台。

## 測試基線

重整前 `main` 的基線為 **68 passed、3 deselected**。重整後為
**99 passed、3 deselected**；操作驗收修正完成階段 B 後為
**136 passed、3 deselected**；操作驗收修正完成階段 C 後為
**157 passed、3 deselected**；操作驗收修正完成階段 D 後為
**164 passed、3 deselected**；操作驗收修正全部完成後為
**167 passed、3 deselected**。新增資料搬遷、主題工作台、行動概覽等回歸測試；
3 個需真實 API key 的契約測試仍維持 deselected。

輪播圖階段 A 完成後為 **174 passed、3 deselected**；**B1 完成後為
195 passed、8 deselected**（2026-07-29 驗收實測相符）。deselected 多出的 5 個
是新增的 RSS 契約測試，跑 `-m contract` 時會真的打網路——五個網址當天全綠。
**B2 Task 13 完成後為 216 passed、8 deselected**；**Task 14 完成後為
220 passed、8 deselected**，新增的瀏覽器與像素契約測試預設會執行。

**免費 LLM 契約修正與換模後為 312 passed、9 deselected**。真實 Idea 契約與
輪播契約均以 `gemini-3.1-flash-lite` 通過；輪播為 `1 passed in 29.57s`。
**來源蒐集與出圖接線完成後為 349 passed、10 deselected**；合併到 `main` 後
複驗同樣為 `349 passed, 10 deselected in 28.53s`。文章網址的真實契約另以
TechCrunch 公開頁面驗證通過。

（2026-07-23 的舊修正：`pytest` 原本有 12 個 collection 錯誤，已在 `pytest.ini`
加入 `pythonpath = .` 解決。）

⚠️ **2026-07-25 的觀察**：99 個測試全綠，但驗收找出的 4 個會弄壞資料的問題
**沒有任何一條被涵蓋**。它們的共同點是跨越了單一函式的邊界——瀏覽器實際算出來的
顏色、多張資料表的一致性、資料庫與本機時間的落差、頁面重跑的生命週期。
`docs/plan-qa-fixes.md` 的每個 Task 都要求先補一個會失敗的測試再修。

## 怎麼安全地實際操作測試

驗收或手動測試時，**不要直接跑在真實的 `daibu.db` 上**：

```
cp daibu.db /tmp/daibu-test.db
DAIBU_DB_PATH=/tmp/daibu-test.db .venv/bin/streamlit run app.py --server.port 8502
```

使用者自己常開著一個 Streamlit 在 8501，測試時挑別的 port。
另外「產生候選」是真的會呼叫 AI 與 15 個外部來源的（會花配額、要等幾秒）。

## 下一步

1. 依新的產品優先順序開下一個 Task；本輪 Phase A–D 已結束。
2. 如需真人內容驗收，使用 `/tmp` 的資料庫複本操作來源、Logo、產圖與 ZIP 全流程。
3. 更遠的一輪：分平台產文字（Threads／IG／LinkedIn）——本輪明確不做，
   見 `docs/open-questions.md`

## 分支現況

- `main` — 目前的可用版本，含來源蒐集與出圖接線 Phase A–D
- `codex/frontend-brand-refactor` — 前端品牌重構，待整合
- `codex/ia-topic-first` — 資訊架構重整與操作驗收修正 Task 1–24
  已實作並完成整體驗收
- `refactor/ia-topic-first` — ⚠️ Claude 越權寫的探路稿（commit `b6b66bc`），
  大致等價於新計畫的 Task 1–3，**可參考、不要直接 merge**
