# HANDOFF — 呆一布內容工作站

> 2026-08-01 更新。正文可見性、官方 Logo 候選確認與 BillionToOne 七頁草稿已完成 feature branch 驗證。

## 本輪目標與驗收

依以下文件完成兩項修正；正式 `daibu.db` 不得被驗收修改：

- `docs/superpowers/specs/2026-08-01-官方-logo-候選與正文可見性-design.md`
- `docs/superpowers/plans/2026-08-01-官方-logo-候選與正文可見性.md`

正文在深／淺色都必須可讀；公司正文完成後自動從一般網頁搜尋定位官網，只解析官網或官網品牌頁直接引用的 Logo。候選先預覽，使用者確認後才能存檔。Logo 不阻擋七頁文字草稿。

## 本輪狀態

- **正文**：Streamlit textarea 的容器、文字與游標已改用品牌語意 token，修正切換主題時「有 478 字但看起來全白」的狀況。
- **官方 Logo 候選**：新增 `search_web()` 與 `logo_discovery`。排除社群、媒體與不相關搜尋結果；最多讀 3 個官方頁，只下載頁面直接引用的 HTTPS SVG／PNG，沿用 2 MB、尺寸與 SVG 腳本安全驗證。白色版與一般版並存時優先一般深色版。
- **人工確認**：候選只放 Streamlit session；畫面提供官方頁、原檔連結、確認、拒絕與重試。只有確認會呼叫既有 `store_logo()` 寫入；拒絕不落盤並排除舊候選。手動上傳保留為收合備援。
- **BillionToOne 草稿**：`/tmp/daibu-workstation-redesign.db` 的 idea 15 已由免費 Gemini 依既有 S1（Y Combinator）原子產生 1–7 頁。標題依序為「1/11 的美國新生兒都在用…」、「認識 BillionToOne」、「解決了什麼問題？」、「AI 角色」、「成果」、「為什麼重要？」、「給我們的啟示」。
- **真實官網驗證**：由 `https://www.billiontoone.com/` 實際解析並驗證官方 CDN 的 `bto_logo_new.svg`；尚未存入資料庫，需使用者看圖確認。本機沒有 `TAVILY_API_KEY`，UI 會顯示可恢復錯誤與手動備援；真實 Tavily contract 因此 skip。
- **視覺驗收**：完成兩輪 1280×800 與 375×812；第一輪將過高的手動 Logo 表單改為收合，第二輪層次、留白、字體、三色內配色、對齊、375px 無溢位、狀態與微動效全數通過。最終圖：`.screenshots/desktop.png`、`.screenshots/mobile.png`。
- **測試與交付**：相關回歸 `28 passed, 110 deselected`；安全審查再補冒牌官網案例後，feature branch 全套 `442 passed, 12 deselected, 1 warning in 50.26s`，合併後 `main` 全套 `442 passed, 12 deselected, 1 warning in 50.90s`。已推送 `origin/main`；唯一警告是既有 Starlette/httpx 棄用提示。專案沒有正式部署流程，8502 為本機預覽。
- **資料安全**：只操作 `/tmp/daibu-workstation-redesign.db` 與 `/tmp/daibu-workstation-redesign-logos`。真實 `daibu.db` mtime 仍為 `1785433278`（2026-07-30 10:41:18 -0700）。

## 最容易踩的坑

- 不得把 Logo 候選自動視為正式資產；必須等使用者確認。
- 沒有 Tavily key 時不要改用圖片搜尋；顯示重試與官網手動上傳即可。
- 七頁草稿目前只有 S1 證據，文字與引文必須維持可追溯，不可自行補無來源主張。
- 本機入口為 `http://localhost:8502/選題`；專案沒有正式部署流程。
