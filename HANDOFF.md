# HANDOFF — 呆一布內容工作站

> 2026-07-31 更新。多系列內容工作站前端重構已完成、合併 `main` 並推送。

## 本輪目標與驗收

依以下文件實作，不更換 Streamlit／SQLite 技術棧、不做資料庫 migration：

- `docs/superpowers/specs/2026-07-31-多系列內容工作站重構-design.md`
- `docs/superpowers/plans/2026-07-31-多系列內容工作站重構.md`

五項範圍：四步驟資訊架構、候選比較與採用後接續、輪播線性檢查、統一命名與按鈕層級、呆一布狀態角色。

## 本輪狀態

- **資訊架構**：主導覽統一為「工作台／內容製作／成效／系統設定」；UI 將資料層的 `Theme` 統稱「內容系列」，保留既有 schema 以支援未來多系列。
- **今日任務與四步驟**：新增純狀態核心 `daibu/workspace.py`，依資料自動判斷「找題材 → 選一則 → 寫內容 → 做輪播」。工作台先顯示今日下一步與各系列進度，排程／成效降為次要資訊。
- **單一焦點流程**：候選與已採用內容一次只展開一則；「採用並繼續寫內容」會打開同一則正文；寫作階段隱藏較早的找題材／候選工具，正文直接展開；「儲存並繼續做輪播」接到輪播流程。
- **輪播檢查**：前置條件固定為「公司名稱／這篇內容的查證證據／官方 Logo／七頁草稿／七張圖片」，只強調第一個未完成項；移除原本兩條裝飾性側邊色條。
- **按鈕與名稱**：日常畫面只保留當前步驟的主要 CTA；素材管理收進「素材來源庫／系列素材來源／管理內容系列」。
- **角色狀態**：沿用 `assets/mascot/`，point 提示下一步、think 表示等待／判斷、confused 表示可恢復錯誤、happy 表示完成；都有文字狀態與 `aria-label`。
- **視覺自檢**：桌機 `1280×800` 與手機 `375×812` 最終圖為 `.screenshots/desktop.png`、`.screenshots/mobile.png`。層次、留白、字體、配色、對齊、響應式、狀態、動效皆通過；新瀏覽器 session 的首頁→內容製作 console 為 `0 errors / 0 warnings`。
- **測試**：AppTest `82 passed`；feature branch 全套 `403 passed, 11 deselected, 1 warning in 40.64s`；合併後 `main` 全套 `403 passed, 11 deselected, 1 warning in 44.18s`。唯一警告為既有 Starlette/httpx 棄用提示；`git diff --check` 通過。
- **資料安全**：瀏覽驗收使用 `/tmp/daibu-workstation-redesign.db` 與 port 8502；真實 `daibu.db` mtime 驗收前後均為 `1785433278`。

## 下一步

- `main` 已推送至既有 `origin`，遠端已包含本輪提交。
- 專案沒有 production 部署流程；本機預覽為 <http://localhost:8502/>。
- 下一階段請另開 task，從本交接單繼續。

## 最容易踩的坑

- `Theme` 是資料層舊名稱；不要只為改 UI 文案做 migration。
- 直接開舊 `/選題` 深連結時 Streamlit 可能先顯示自動頁名；從 `/` 的「內容製作」進入會使用統一導覽。
- 角色是狀態溝通元件，不要在每個區塊重複當裝飾。
