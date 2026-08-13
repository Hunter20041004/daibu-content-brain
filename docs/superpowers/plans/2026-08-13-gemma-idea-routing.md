# Gemma 選題與 Gemini 備援實作計畫

> Design: `docs/superpowers/specs/2026-08-13-gemma-idea-routing-design.md`

**Architecture:** 在既有 LLM adapter 上新增任務路由 provider。Google 模式由 Gemma 處理選題與一般文字，Gemini 3.5 Flash-Lite 處理備援與輪播；Groq 模式維持原狀。

**Tech Stack:** Python 3.11、Google GenAI SDK、Streamlit、SQLite、pytest、Playwright CLI。

## TDD 垂直切片

### Task 1：Google 預設路由

1. 在 `tests/test_llm.py` 寫一個失敗測試：Google 設定回傳路由器，主要模型為 Gemma、備援／輪播為 Gemini 3.5 Flash-Lite。
2. 執行單一測試看紅。
3. 在 `daibu/llm/base.py` 新增最小路由器與 factory 接線。
4. 執行單一測試看綠並重構命名。

### Task 2：候選失敗備援

逐一垂直完成：

1. 主要候選成功時不呼叫備援。
2. 主要候選遇 503／額度／逾時時呼叫備援。
3. 主要候選連續無法解析時呼叫備援。
4. 備援錯誤保留給前台，且不吞掉不可恢復錯誤。

每一條都先寫一個紅測試，再做最小實作轉綠。

### Task 3：一般文字與輪播分工

1. 紅測試：`generate_text` 的可恢復 API 錯誤切 Gemini。
2. 最小實作轉綠。
3. 紅測試：`generate_carousel_text` 永遠只呼叫 Gemini。
4. 最小實作轉綠。

### Task 4：設定資料流

1. 紅測試：設定頁顯示「選題主要模型」與「備援與輪播模型」，預設值分別為 Gemma 4 26B 與 Gemini 3.5 Flash-Lite。
2. 最小修改 `pages/3_設定.py`、`pages/1_選題.py`，保存／傳遞 `llm_idea_model`。
3. 紅測試：既有 Groq 設定仍建立 Groq provider。
4. 綠後重構設定常數，避免模型名稱散落。

### Task 5：真實邊界與資料安全

1. 在真實契約測試加入 Gemma 候選案例，先執行確認現況失敗或缺口。
2. 只修實際契約差異，不調整 mock 假裝通過。
3. 用 SQLite Backup API 建立 QA 副本，記錄 ideas 與資格資料指紋。
4. 在副本跑一次完整候選流程，確認候選能解析、失敗不留半成品、正式資料不變。

### Task 6：前端與整體驗收

1. 跑聚焦測試與全套 pytest。
2. 啟動副本服務；依前端規範完成兩輪桌機／手機截圖、自評與 console 檢查。
3. 更新 `HANDOFF.md`，附最終截圖路徑與測試證據。
4. 合併 main，在 main 重跑全套測試。
5. 備份正式資料後只更新模型設定；推送、重啟正式服務。
6. 從首頁進入正式選題頁，確認健康、console、響應式與資料筆數／指紋。
