# 呆一布 選題大腦（daibu-content-brain）

呆一布 AI 共學實驗室・社群組的**內容決策大腦**。

一個單人網頁儀表板：建立主題並直接勾選資料來源 → 讓 AI 產生貼文題目與切入角度 →
採用、微調或淘汰候選 → 在同一個主題工作台寫正文、標記已發 → 回填成效 →
從情況概覽看見下一步與各主題近況。

- **定位**：「不焦慮、會思考、陪你學」——文組視角的 AI 紀實。
- **v1 技術**：Python + Streamlit + SQLite，LLM 用免費的 Google AI Studio（備援 Groq）。

## 文件

- 目前設計：[`docs/specs/2026-07-24-選題為核心的資訊架構重整-design.md`](docs/specs/2026-07-24-選題為核心的資訊架構重整-design.md)
- 實作計畫（TDD 切片）：[`docs/plan-ia-refactor.md`](docs/plan-ia-refactor.md)
- 給 AI 開發者的守則：[`AGENTS.md`](AGENTS.md)

## 快速開始

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
.venv/bin/playwright install chromium
cp .env.example .env    # 填入免費 API key（Gemini 或 Groq、Tavily）
.venv/bin/streamlit run app.py
```

## 測試

```bash
.venv/bin/pytest
```

## Roadmap（v1 之後的垂直切片）

下一輪預計獨立設計：依 Threads／Instagram／LinkedIn 產生不同文字，再由文字產貼圖。
圖片服務成本仍待裁決；自動發文、留言協作、多人與雲端部署不在 v1。
