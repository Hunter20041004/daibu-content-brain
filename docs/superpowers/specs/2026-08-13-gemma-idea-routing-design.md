# Gemma 選題與 Gemini 備援設計

## 目標

降低免費模型單一額度或暫時容量不足造成的候選產生失敗，同時保留輪播草稿的結構化輸出穩定度。

## 已核可的產品行為

- AI 新創選題與一般候選產生，主要使用 `gemma-4-26b-a4b-it`。
- Gemma 遇到額度、逾時、503，或連續兩次仍無法產出可解析候選時，自動改用 `gemini-3.5-flash-lite`。
- 公司資格需要 LLM 時先用 Gemma；若 Gemma 遇到可恢復的 API 錯誤，改用 Gemini。
- 七頁輪播草稿固定使用 `gemini-3.5-flash-lite`，不交給 Gemma。
- 若使用者明確選擇 Groq，維持現有 Groq 單一 provider 行為，不暗中改回 Google。

## 架構與資料流

```text
設定／環境變數
      |
      v
GoogleFreeRouter
  |-- generate_ideas ------> Gemma 4 26B --可恢復失敗--> Gemini 3.5 Flash-Lite
  |-- research_text -------> Gemma 4 26B --API 失敗----> Gemini 3.5 Flash-Lite
  |-- generate_text -------> Gemini 3.5 Flash-Lite（正文）
  `-- generate_carousel ---> Gemini 3.5 Flash-Lite
```

路由器只負責選模型，不改 prompt、來源蒐集、公司資格規則或資料庫寫入順序。既有 selection 流程仍在完整結果驗證後才寫入 idea，因此主要模型與備援都失敗時不會留下半成品。

## 設定

- `llm_provider`：既有 `gemini`／`groq` 選擇。
- `llm_idea_model`：新增，Google 路由時預設 `gemma-4-26b-a4b-it`。
- `llm_model`：保留，Google 路由時代表 Gemini 備援與輪播模型，預設改為 `gemini-3.5-flash-lite`。
- 對應環境變數為 `LLM_IDEA_MODEL` 與既有 `LLM_MODEL`。

設定頁會把兩個 Google 模型分開標示，避免使用者誤以為單一模型負責全部任務。API key 仍只存在 `.env`／執行環境，不寫入 SQLite。

## 失敗邊界

自動備援只處理可恢復問題：`LLMQuotaError`、`LLMTimeoutError`、`LLMUnavailableError`、以及候選的 `LLMResponseError`。驗證、金鑰或程式錯誤不會被靜默吃掉。

Gemma 與 Gemini 雖有模型別額度，但共用 Google Gemini API；因此這能分散模型配額與容量，不能取代跨供應商備援。Groq 仍是未來可選的跨平台方案。

## 測試與驗收

- 單元測試逐片證明：預設模型、成功不呼叫備援、各種可恢復錯誤切換、輪播只走 Gemini、Groq 相容。
- 真實契約：用現有 Google key 呼叫 Gemma，確認繁體中文候選可被 `Idea` parser 接受；Gemini 輪播契約維持通過。
- 使用資料庫副本跑一次候選流程，不修改正式 ideas。
- 設定頁完成兩輪 1280×800 與 375×812 截圖 QA。
- 全套測試後才更新正式設定、合併、推送與重啟服務。

## 非目標

- 不新增付費模型。
- 不要求使用者本輪申請 Groq key。
- 不修改候選資格、來源策略、prompt 內容或輪播 schema。
- 不以多帳號或多 key 規避服務限制。
