# Demo video project memory

## Session 1 — 2026-08-01

**Strategy:** 以約兩分鐘的功能導覽展示真實的 AI 新創找題材流程，標題 3 秒，分段錄製並剪掉 API 等待，最後加上繁體中文字幕；不加配音。

**Decisions:** 1280×720、30fps；真實執行 Tavily 與 Gemini；產品資料只寫入 `/private/tmp/daibu-workstation-redesign.db`。新案例若缺少已確認的官方 Logo，後段改接既有完整案例並明示轉場。

**Reasoning log:** 分段錄製能保留真實操作，同時避免觀眾觀看冗長搜尋與生成等待。

**Results:** 真實搜尋產生 Warp；AI 初稿 478 字、查證來源 3 筆。Warp 的官方 Logo 候選未經人工確認，因此後段依核可備援接到已驗證的 BillionToOne，完成七頁、七張圖、預覽與 ZIP 下載。

**Edit decisions:** 原始 13 段共約 154 秒；剪掉啟停空白並加速 AI 等待後為 115.4 秒。字幕最後以逐幀方式燒入，避免無損 concat 的片段時間戳造成漂移。

**Verification:** H.264 1280×720@30、yuv420p、無音訊、完整解碼通過；12 個剪接點與抽樣畫面通過三輪自評；真實 `daibu.db` 修改時間未變；文字 secret scan clean；最終全套測試 449 passed、12 deselected。

**Outstanding:** 等使用者觀看 `final.mp4` 後提出內容或節奏調整。
