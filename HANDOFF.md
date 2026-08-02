# HANDOFF — 呆一布內容工作站

> 2026-08-01 更新。永久收斂成「AI 新創介紹」單一預設系列，並移除儀表板手動新增入口。

## 本輪目標與驗收

依下列文件完成一次性清理與預設值調整：

- `docs/superpowers/specs/2026-08-01-單一內容系列清理-design.md`
- `docs/superpowers/plans/2026-08-01-單一內容系列清理.md`

既有資料庫永久刪除「AI 新創介紹」以外的系列及其完整依賴資料；新資料庫只預設 AI 新創介紹；前端不再允許手動新增系列，但仍泛用顯示日後由程式新增的系列。

## 本輪狀態

- **一次性資料遷移**：`db.init_schema()` 新增 `single_series_cleanup_v1` 標記。僅在「AI 新創介紹」恰好一筆時，以同一 SQLite savepoint 依序清除其他系列的 `performance`、`carousel_pages`、`carousel_sources`、`idea_sources`、`ideas`、`theme_sources`、`themes`；目標缺失或重複時完全不刪且不寫標記。標記存在後，未來透過 `db.add_theme()` 新增的系列不會再被清掉。
- **永久清理結果**：真實 `daibu.db` 從 3 系列／8 題變成 1 系列／6 題；保留的 6 題仍全為「候選」，id、系列關聯、標題、角度、來源網址、狀態、正文與建立時間逐欄相同。共享來源保留，資料庫 `PRAGMA integrity_check = ok`。
- **預覽庫結果**：`/tmp/daibu-workstation-redesign.db` 從 3 系列／6 題變成 1 系列／4 題（3 候選、1 採用）。BillionToOne idea 15 仍有正文 478 字、查證來源 1 筆、輪播 7 張；來源庫仍 16 筆。
- **可復原備份**：`/tmp/daibu-single-series-cleanup.ZmrTxe/daibu-before.db` 保留真實庫清理前 3 系列／8 題；`/tmp/daibu-single-series-cleanup.ZmrTxe/workstation-before.db` 保留預覽庫清理前 3 系列／6 題。兩份皆由 SQLite Backup API 建立且完整性為 `ok`。
- **預設值**：`seeds.DEFAULT_THEMES` 只保留 `AI 新創介紹`（`company_profile`，原五個指定來源）；`DEFAULT_SOURCES` 全部保留。
- **前端**：移除「＋ 新增內容系列」popover 與「建立內容系列」表單；既有系列的編輯、來源設定與確認刪除仍在。選題頁及首頁無系列時統一顯示「目前沒有內容系列；請透過專案設定新增。」
- **視覺驗收**：最終桌機 1280×800 與手機 375×812 均顯示單一系列和完整工作區，沒有新增入口；兩個寬度 `scrollWidth == clientWidth`，正常側欄導覽進入時 console 0 錯誤。最終圖：`.screenshots/desktop.png`、`.screenshots/mobile.png`。
- **測試與交付**：相關 121 項通過；feature branch 全套 `449 passed, 12 deselected, 1 warning in 45.43s`，合併後 `main` 全套 `449 passed, 12 deselected, 1 warning in 46.68s`；唯一警告是既有 Starlette/httpx 棄用提示。已推送 `origin/main`，本機 feature branch 已用小寫 `-d` 刪除；專案沒有正式部署流程，8502 為本機預覽。

## 最容易踩的坑

- `single_series_cleanup_v1` 是一次性安全閘門，不可刪除或重新命名，否則可能讓舊清理再次執行。
- 後續新增內容系列請改 `seeds.DEFAULT_THEMES` 或透過程式呼叫 `db.add_theme()`；不要把手動新增表單加回儀表板。
- 清理程式刻意保留共享 `sources`、全部 `brand_assets` 及沒有綁系列的題目；不可擴大刪除範圍。
- 本機入口為 `http://localhost:8502/選題`；專案沒有正式部署流程。
