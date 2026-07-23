# 呆一布 選題大腦（daibu-content-brain）

呆一布 AI 共學實驗室・社群組的**內容決策大腦**。

一個單人網頁儀表板：設定「大主題 × 星期幾」與「來源白名單」→ 一鍵讓 AI 從白名單抓最新內容、為每個主題挖出具體貼文題目（附切入角度、守門線分數、來源）→ 挑選/微調 → 推進流水線（候選→採用→草稿→已排程→已發）→ 回填成效 → 看板告訴你哪個主題有效、下週補哪個。

- **定位**：「不焦慮、會思考、陪你學」——文組視角的 AI 紀實。
- **v1 技術**：Python + Streamlit + SQLite，LLM 用免費的 Google AI Studio（備援 Groq）。

## 文件

- 設計：[`docs/spec.md`](docs/spec.md)
- 實作計畫（TDD 切片）：[`docs/plan.md`](docs/plan.md)
- 給 AI 開發者的守則：[`AGENTS.md`](AGENTS.md)

## 快速開始

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # 填入免費 API key（Gemini 或 Groq、Tavily）
streamlit run app.py
```

## 測試

```bash
pytest
```

## Roadmap（v1 之後的垂直切片）

製圖 → 自動發文/排程 → 留言協作（接機器人組 agent）→ 多人 + 雲端（搬到 Next.js + Supabase）。
