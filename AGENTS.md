# AGENTS.md — 呆一布 選題大腦（給接手的 AI 開發者）

你（Codex）負責「動手實作」。設計已定案，**先讀 `docs/spec.md`（要做什麼）與 `docs/plan.md`（照什麼順序做、每步的測試）**，再開工。

## 最高原則：TDD（不可違反）

嚴格 **Red → Green → Refactor**，**垂直切片、一次一個失敗測試**：
- 先寫**一個**失敗測試 → 寫最少程式讓它綠 → 在測試保護下重構 → 全綠 → 才進下一個。
- **禁止水平切片**（不可一次寫完多個測試、再一次寫完多段實作）。
- 順序照 `plan.md` 的切片，每片做完都要能 demo。

## 契約 / 邊界測試（重要）

凡是打外部系統（LLM API、搜尋 API、RSS 來源）的 client，除了 mock 版單元測試外，**必須另外補一個對「真實邊界」的測試**，驗證我們實際用到的回傳格式/欄位真的如假設（例如真的打一次免費 LLM，確認能解析出 `Idea` 結構）。
- 若 mock 與真實系統對不起來，**修實作，不要調 mock 讓它假通過**。

## 硬性技術約束（不可自作主張改）

- Python 3.11+ / **Streamlit** / **SQLite** / **pytest**。
- LLM：**免費 provider，做成可切換的 adapter**。預設 **Google AI Studio（Gemini Flash）**，備援 **Groq（Llama）**。**⛔ 不要用 Claude 或任何付費模型。**
- 取材：`feedparser`（RSS）＋ 搜尋 API 限白名單網域（Tavily 預設）。
- **秘鑰走環境變數（`.env` + `python-dotenv`），絕不 hardcode、不 commit。** 附 `.env.example`。
- **不要實作 pillar / 四支柱**（已移除）。品管只有「守門線分數」。

## v1 Non-goals（不要提前做）

自動製圖、自動發文、自動回留言、多人登入、雲端部署 — 都是**之後**的切片，v1 不碰。

## 完成一片的定義（Definition of Done）

失敗測試 → 最小實作 → 綠 → 重構 → `pytest` 全綠 → 該片能在 `streamlit run app.py` 展示對應功能。

## 執行指令

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填入免費 API key
pytest                 # 測試
streamlit run app.py   # 跑起來
```

## 有疑慮時

規格不清或與現實衝突（例如某來源沒有 RSS、免費模型輸出格式不穩）→ **在該處留 `# TODO(需澄清): ...` 並選一個合理預設繼續**，不要卡住；把這些疑點集中記在 `docs/open-questions.md` 供人類回來裁決。
