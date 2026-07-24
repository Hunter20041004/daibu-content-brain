# 專案現況 — 呆一布選題大腦（Daibu Content Brain）

> 由 Claude 建立、Codex 於 2026-07-24 更新。**新對話請先讀這份**。

## 這是什麼

**社群組的「內容決策大腦」** v1 — 幫忙決定「這次要寫什麼主題」的工具。
從訊號蒐集 → 選題建議 → 流水線狀態追蹤 → 成效回填，形成一個閉環。

## 技術棧與怎麼跑

- **Streamlit**（四頁 UI）+ **SQLite**（`daibu.db`）
- Python 3.11．**用專案自己的虛擬環境**：`.venv/bin/python`
- `daibu/` — 核心邏輯；`pages/` — Streamlit 各頁；`app.py` — 進入點
- 測試：`.venv/bin/pytest`（`pytest.ini` 已設 `pythonpath = .`）
- LLM：**免費層可切換**（不綁單一供應商）

## 已定案的設計決策

- **不採用「四支柱」框架**（討論後捨棄）
- **守門線品管**：用明確門檻決定內容能不能過關，而不是靠感覺
- 成本策略：只用免費額度

## 目前進度

依 git，已完成：流水線狀態流轉 → 成效回填與彙總建議 → 種子白名單與範例主題 →
**Streamlit 四頁 UI 串接與 DIVE web 品牌重構**。

前端目前支援淺／深色模式、桌機與手機版面、鍵盤 focus 與減少動態偏好；
實作位於 `codex/frontend-brand-refactor` 分支。

## 2026-07-23 的修正

`pytest` 原本有 12 個 collection 錯誤（測試找不到 `daibu` 套件），
已在 `pytest.ini` 加入 `pythonpath = .` 修正。

2026-07-24 前端重構完成後，`.venv/bin/pytest -q` 為
**68 passed、3 deselected**；3 個是需要真實 API key 的契約測試。

## 下一步

進行人工產品驗收並決定如何整合 `codex/frontend-brand-refactor` 分支；
未決產品問題見 `docs/open-questions.md`。
