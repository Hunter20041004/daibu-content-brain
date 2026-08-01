# HANDOFF — 呆一布內容工作站

> 2026-08-01 更新。AI 新創公司候選、自動文案與品牌主題切換已完成實作及 feature branch 驗證。

## 本輪目標與驗收

依以下文件完成兩項能力，維持 Streamlit／SQLite 與免費 LLM 技術棧：

- `docs/superpowers/specs/2026-07-31-ai-新創公司候選與自動文案-design.md`
- `docs/superpowers/plans/2026-07-31-ai-新創公司候選與自動文案.md`
- `docs/superpowers/specs/2026-08-01-品牌主題切換-design.md`
- `docs/superpowers/plans/2026-08-01-品牌主題切換.md`

AI 新創介紹只產具體公司候選，採用後可產 350–500 字繁中初稿；側邊欄可切換深／淺色並跨頁保存。正式 `daibu.db` 不得被驗收修改。

## 本輪狀態

- **公司候選**：`Theme.content_kind` 支援 `general/company_profile`；AI 新創介紹固定為公司模式。候選必須有公司、HTTPS 素材 URL 與可逐字回查的引文；畫面只呈現「公司｜在做什麼」。
- **自動文案**：採用且正文空白時顯示「AI 幫我寫初稿」；先研究可信來源，再由免費 LLM 產稿，正文與來源同一筆 SQLite transaction 保存。沒有 Tavily key 時可先用候選已驗證來源啟動，失敗保留舊資料。
- **主題切換**：保留 `toolbarMode = "minimal"`，在側邊品牌區加入「目前：淺／深色模式」與切換按鈕。沿用 Streamlit 原生主題鍵並保存跨頁偏好；SVG 以 CSS mask 呈現，支援鍵盤、45px 觸控、focus、disabled、切換中與 localStorage 失敗狀態。
- **瀏覽驗收**：8502 實走淺→深→內容製作→reload→淺；四頁偏好同步，鍵盤第 5 次 Tab 可達，全新根網址 session 為 `0 errors / 0 warnings`。直接 reload `/選題` 仍有 Streamlit 既有相對 health URL 404，但頁面可用。
- **視覺驗收**：完成兩輪 1280×800 與 375×812；最終深色圖為 `.screenshots/desktop.png`、`.screenshots/mobile.png`。層次、留白、字體、配色、對齊、響應式、狀態與動效均通過。
- **測試與交付**：主題／UI／導覽回歸 `68 passed, 77 deselected`；合併後 `main` 全套 `430 passed, 11 deselected, 1 warning in 37.42s`，已推送 `origin/main`。唯一警告是既有 Starlette/httpx 棄用提示；`git diff --check` 通過。
- **資料安全**：舊候選與本輪 QA 資料只從 `/tmp/daibu-workstation-redesign.db` 移除；最後備份為 `/tmp/daibu-company-qa-cleanup-final.7ORTUk/daibu-workstation-redesign.before-final-qa-cleanup.db`。真實 `daibu.db` mtime 前後均為 `1785433278`。

## 最容易踩的坑

- 勿把缺少 Tavily key 當成零來源；候選來源可先啟動初稿，Tavily 只負責擴充。
- `stActiveTheme-<pathname>-v2` 是逐路徑儲存；新增頁面時仍需保留 `daibuColorMode-v1` 的首次同步。
- 不要打開 Streamlit 工具列取代品牌按鈕，也不要把使用者／資料庫／LLM 內容插入可執行 HTML。
- 人工流程只使用 `/tmp` DB；專案沒有正式部署流程，本機入口為 `http://localhost:8502/`。
