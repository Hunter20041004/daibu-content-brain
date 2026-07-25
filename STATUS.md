# 專案現況 — 呆一布選題大腦（Daibu Content Brain）

> 由 Claude 建立、Codex 於 2026-07-24 更新。**新對話請先讀這份**。

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

## 目前進度

- **v1 功能**：已完成（訊號蒐集 → 選題 → 狀態流轉 → 成效回填）
- **前端品牌重構**：已完成，位於 `codex/frontend-brand-refactor` 分支。
  淺／深雙模式、桌機與手機版面、鍵盤 focus、減少動態偏好都已驗收。
- **資訊架構重整**：**Task 1–16 已由 Codex 實作完成，待使用者產品驗收**。
  實作位於 `codex/ia-topic-first`，每個 Task 都有獨立 commit。
  - 設計規格：`docs/specs/2026-07-24-選題為核心的資訊架構重整-design.md`
  - TDD 計畫：`docs/plan-ia-refactor.md`（Task 1–16）

主要改動：首頁改行動導向的情況概覽、設定頁只剩系統設定、選題頁改主從式工作台
（左主題／右工作區）、流水線頁刪除、守門線與分層與常青分類全部移除。

## 測試基線

重整前 `main` 的基線為 **68 passed、3 deselected**。重整後為
**99 passed、3 deselected**，新增資料搬遷、主題工作台、行動概覽等回歸測試；
3 個需真實 API key 的契約測試仍維持 deselected。

（2026-07-23 的舊修正：`pytest` 原本有 12 個 collection 錯誤，已在 `pytest.ini`
加入 `pythonpath = .` 解決。）

## 下一步

1. 使用者驗收新的資訊架構
2. 決定 `codex/ia-topic-first` 如何整合回 `main`
3. 驗收後再設計**下一輪大功能**：分平台產文字（Threads／IG／LinkedIn）＋由文字產貼圖
   —— 需先解決「圖片生成多數付費」與「只用免費額度」的衝突，見
   `docs/open-questions.md`

## 分支現況

- `main` — 目前的可用版本
- `codex/frontend-brand-refactor` — 前端品牌重構，待整合
- `codex/ia-topic-first` — 本輪資訊架構重整，Task 1–16 已實作並驗證
- `refactor/ia-topic-first` — ⚠️ Claude 越權寫的探路稿（commit `b6b66bc`），
  大致等價於新計畫的 Task 1–3，**可參考、不要直接 merge**
