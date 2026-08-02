# HANDOFF — 呆一布內容工作站 Demo 影片

> 2026-08-02 更新。這一輪只製作影片與報告提綱，沒有修改產品程式碼。

## 本輪目標與驗收

依下列文件製作一支約兩分鐘、無配音、有繁中字幕的功能導覽影片，並附 3–5 分鐘社團報告提綱：

- `docs/superpowers/specs/2026-08-01-demo-video-design.md`
- `docs/superpowers/plans/2026-08-01-demo-video.md`

錄影須真實重跑 Tavily＋Gemini，但只能寫入 `/tmp` 資料庫；新 Logo 未經使用者確認不得用於出圖。標題 3 秒，總長 1:50–2:15，輸出 1280×720 H.264 MP4。

## 本輪狀態

- **成片**：`artifacts/demo-video/edit/final.mp4`，115.4 秒、1280×720、30fps、H.264、yuv420p、無音訊、4.7 MB。SHA-256：`385c2abcb743b887819c766e1993a97971bfc7b79b29c36fd78ec767a686073f`。
- **真實流程**：搜尋新增 Warp idea 16；AI 初稿 478 字、查證來源 3 筆。系統找到 Warp 官網 Logo 候選，但未確認、未儲存、未拿去出圖。
- **透明備援**：影片以轉場明說 Warp Logo 等待確認，後段接已驗證的 BillionToOne idea 15，完成七頁草稿、七張圖、預覽與 ZIP 下載。
- **報告提綱**：`docs/2026-08-01-社團報告提綱.md`，可講 3–5 分鐘；另含只剩 3 分鐘與現場 API 失敗時的說法。
- **驗收證據**：`artifacts/demo-video/edit/verify/boundaries.png`、`samples.png`。三輪自評後，12 個剪接點無黑格；字幕不遮主要操作；3 秒標題、Logo 轉場與結尾卡正常。
- **技術驗證**：完整解碼成功；ZIP 內 7 張 PNG 均通過完整性檢查；文字產物沒有 Tavily／Gemini key；影片與字幕皆未經過設定頁。
- **資料安全**：8502 實際使用 `/private/tmp/daibu-workstation-redesign.db`。真實 `daibu.db` 錄製前後 mtime 都是 `1785650884`，未變。
- **測試**：隔離分支基線 `449 passed, 12 deselected, 1 warning in 58.20s`；分支最終 `449 passed, 12 deselected, 1 warning in 68.23s`；合併回 `main` 後 `449 passed, 12 deselected, 1 warning in 62.70s`。產品程式碼未變；唯一 warning 是既有 Starlette/httpx 棄用提示。
- **已知非阻擋訊息**：Playwright console 有兩個 multipage-relative `_stcore/health`／`host-config` 404；錄影流程與畫面未受影響。

## 下一步

1. 使用者觀看 `final.mp4`，若需要只調整節奏、字幕或刪減片段，不必重跑 API。
2. 明天現場直接播放影片並照提綱補充；不要現場重新搜尋，避免網路與免費額度不穩。

## 最容易踩的坑

- 影片二進位與驗收 PNG 已加入 `.gitignore`，不在 Git；工作區移除前要確認主專案路徑仍有檔案。
- `master.srt` 是成片輸出時間軸；字幕必須在所有剪輯後，以 `burn-captions.py` 最後燒入。
- Warp Logo 仍是待確認候選，不可從影片畫面推定已核可。
