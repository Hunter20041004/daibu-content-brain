# HANDOFF — 社團建造故事 HTML

> 2026-08-05 更新。這一輪製作給幾乎不寫程式、主要使用 Vibe Coding 的社團組員閱讀的建造故事 HTML；不修改產品程式碼。

## 本輪目標與驗收

依 `docs/superpowers/specs/2026-08-05-社團建造故事-html-design.md` 製作一份可獨立閱讀的繁體中文單頁 HTML，說明工具為什麼做、如何拆解、AI 與人的分工、系統資料流、TDD、真實迭代與可複製的 Vibe Coding 建造方式。

成品需沿用呆一布品牌，在 1280×800 與 375×812 各完成至少兩輪截圖自檢；不碰真實資料庫、不呼叫外部 API、不修改產品功能。

## 本輪狀態

- **設計**：使用者已確認建造故事式互動網頁方向；正式規格位於 `docs/superpowers/specs/2026-08-05-社團建造故事-html-design.md`。
- **執行方式**：使用者選擇 inline；依 `docs/superpowers/plans/2026-08-05-社團建造故事-html.md` 以五個垂直 TDD 切片完成。
- **HTML 成品**：`docs/2026-08-05-我怎麼用-vibe-coding-搭出呆一布內容工作站.html`。包含八個主章節、一分鐘摘要、十個術語的漸進解釋、七步內容旅程、七階段時間軸、五張踩坑卡與八步建造公式。
- **閱讀互動**：桌機／手機章節導覽、閱讀進度、可鍵盤操作的七步內容旅程、原生技術補充、減少動態、列印版與全頁段落評論均完成。
- **內容現況**：守門線、來源分層、常青／時效分類只出現在「後來移除」的歷史脈絡；沒有寫成現有功能。
- **安全邊界**：HTML 不讀資料庫、不呼叫產品 API、不含 API key、本機絕對路徑或外連資產路徑；吉祥物與 favicon 都已內嵌。
- **HTML 測試**：`5 passed in 4.65s`。另以本機 HTTP 真實操作確認 AI 正文步驟切換成功、375px overflow 為 0、瀏覽器 console 為 0 errors；Tailwind CDN 有一則既有的 production 使用提醒。
- **功能分支全測**：`454 passed, 12 deselected, 1 warning in 69.48s`；唯一 warning 是既有 Starlette／httpx 棄用提示。
- **合併 main 後全測**：`454 passed, 12 deselected, 1 warning in 65.68s`；同一個既有棄用提示，無新增失敗。
- **視覺驗收第一輪**：主標字級被 Tailwind 基礎樣式覆蓋、桌機首屏留白過長、手機主標層級不足；已提高 selector specificity、重調字級與首屏高度並補 favicon。
- **視覺驗收第二輪**：層次、留白、字體、配色、對齊、響應式、狀態與動效全數通過。最終證據：`.screenshots/build-story-round2-desktop.png`、`.screenshots/build-story-round2-mobile.png`；第一輪證據：`.screenshots/build-story-round1-desktop.png`、`.screenshots/build-story-round1-mobile.png`。
- **產品程式與資料**：未修改 Streamlit、資料表、AI 指令或真實資料庫；本輪沒有呼叫 Tavily／Gemini。
- **公開分享網址**：`https://daibu-vibe-coding-story.workspace-249035.chatgpt.site`，只發佈這一份建造故事，不公開 private GitHub repo 的其他文件。
- **正式站驗證**：公開網址會進入 `/story`；在 375×812 實測主標正確、AI 正文步驟切換為選取狀態、內容同步更新、overflow 為 0、console 為 0 errors。唯一 warning 是 Tailwind CDN 的 production 提醒。

## 前一輪 Demo 影片交付紀錄

- **成片**：`artifacts/demo-video/edit/final.mp4`，115.4 秒、1280×720、30fps、H.264、yuv420p、無音訊、4.7 MB。SHA-256：`8c687b587baf5fea87ff79f7b7ddf9dab9fecbc736e9d7ba45415dbda15dc16c`。
- **正文畫面修正**：使用者發現第一個案例雖顯示 478 字，影片中的 textarea 卻是空白。資料庫正文完整，根因是錄製片段沒有拍到瀏覽器已繪製的文字。已只替換 36.2–45.2 秒，現在先顯示 Warp 正文開頭，再輕微捲動；沒有重跑 Tavily／Gemini。
- **真實流程**：搜尋新增 Warp idea 16；AI 初稿 478 字、查證來源 3 筆。系統找到 Warp 官網 Logo 候選，但未確認、未儲存、未拿去出圖。
- **透明備援**：影片以轉場明說 Warp Logo 等待確認，後段接已驗證的 BillionToOne idea 15，完成七頁草稿、七張圖、預覽與 ZIP 下載。
- **報告提綱**：`docs/2026-08-01-社團報告提綱.md`，可講 3–5 分鐘；另含只剩 3 分鐘與現場 API 失敗時的說法。
- **驗收證據**：`artifacts/demo-video/edit/verify/boundaries.png`、`samples.png`。正文可視回歸檢查由修正前 0.0000 升至 0.1481 並通過；3,462 幀可完整解碼、無黑格，總長與後半段時間軸未變。
- **技術驗證**：完整解碼成功；ZIP 內 7 張 PNG 均通過完整性檢查；文字產物沒有 Tavily／Gemini key；影片與字幕皆未經過設定頁。
- **資料安全**：8502 實際使用 `/private/tmp/daibu-workstation-redesign.db`。真實 `daibu.db` 錄製前後 mtime 都是 `1785650884`，未變。
- **測試**：正文修正後 `449 passed, 12 deselected, 1 warning in 43.78s`。產品程式碼未變；唯一 warning 是既有 Starlette/httpx 棄用提示。
- **已知非阻擋訊息**：Playwright console 有兩個 multipage-relative `_stcore/health`／`host-config` 404；錄影流程與畫面未受影響。

## 下一步

1. 把公開網址傳給社團組員，會後可直接用手機或桌機閱讀。
2. 若收到段落評論，整理後再決定是否改版；本輪成品與正式站已完成。

## 最容易踩的坑

- 現有規格與初版文件同時存在；描述現況時要以 `STATUS.md`、最新規格與實際程式為準，不能把已移除的守門線、來源分層或常青／時效分類寫成現有功能。
- 成品給非工程背景組員自讀。專有名詞第一次出現必須先講使用畫面與生活比喻，再放精準定義；主文不可變成檔案路徑導覽。
- 分享後不能依賴作者電腦的絕對路徑。吉祥物與必要 SVG 要內嵌，外部相依失效時仍須保留完整文字內容。
- 前端完成前要跑兩輪 1280×800 與 375×812 截圖自檢；只看 HTML 原始碼或指令 exit 0 不算視覺驗收。
