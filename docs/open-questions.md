# 待人類裁決

## 已裁決（2026-07-24，資訊架構重整）

以下項目在本輪 grill-me 中已由使用者拍板，保留紀錄以免日後重複討論：

- **「淘汰」的資料語意** → 決定改為 `已淘汰` 狀態（不刪除），**且下次產候選時把
  該主題的淘汰標題餵回 prompt 叫 AI 避開**。詳見設計規格第 5、6.2 節。
- **首頁「本週已發」的時間定義** → 決定新增 `ideas.published_at`，標記已發時自動
  記時間。舊資料沒有這個時間，顯示為未知、不計入本週。
- **TLDR AI／Ben's Bites 沒有穩定公開 RSS** → 決定連同 Awesome Claude Code 一起
  **刪除這 3 個 `manual` 來源**，`fetch_type` 只留 `rss`／`search`。工具不再假裝
  在抓它們。
- **「常青／時效」分類** → 整個移除。有勾來源就抓、沒勾就讓 AI 靠主題名發想。

---

## 尚待裁決

### 「AI 近期大事」失去了 L3 那一層

刪掉兩份電子報來源後，這個主題原本涵蓋的 L3（電子報摘要）變成 0 個來源，實際能抓
的素材比重整前少。需要決定：另尋可自動抓取的電子報替代來源、還是接受這個主題就靠
L1／L2／L4 的來源即可。

### 「本週熱門 Claude/Codex Skill」沒有穩定排行榜

v1 以 GitHub 搜尋與官方 releases 並用。未來若要真的做「熱門」排序，需決定排名公式
（新建時間、增星速度或人工策展）。本輪不處理。

### 契約測試覆蓋範圍

真實 RSS 契約目前只固定驗證 TechCrunch；其他來源在實際使用後再逐一確認並補契約
測試。Tavily 搜尋因無 API key 持續跳過。

### Streamlit 雙模式圖表色盤

2026-07-24 實測 Streamlit 1.60：`chartCategoricalColors` 只能放在共用 `[theme]`，
放在 `[theme.light]`／`[theme.dark]` 會出現「not a valid config option」警告。因此
先共用品牌藍綠、次級藍、Highlight 三色；若未來需要各自最佳化深色圖表，再改由圖表
層依模式指定。

### Streamlit 手動配色模式沒有穩定的 DOM 屬性

2026-07-25 實測 Streamlit 1.60：從右上選單手動切換 Light／Dark 時，`.stApp` 的
`color-scheme` 計算值與 Emotion 產生的 class 會改變，但 `html`、`body`、`.stApp`
都沒有 `data-theme` 或其他可供自訂 CSS 穩定判斷的屬性；`#portal` 仍是
`color-scheme: normal`。`st.context.theme.type` 是正式介面，但官方文件也警告它在
使用者切換主題時可能慢一個重跑才更新。

本輪以三層方式處理：`prefers-color-scheme` 當系統預設備援、`st.context.theme.type`
當伺服器端覆寫，並用瀏覽器實測的 Streamlit 1.60 Light／Dark Emotion class 讓
`body:has(...)` 在切換當下同步 `.stApp` 與 `#portal`。最後一層會受 Streamlit
版本影響；未來升級 Streamlit 時，必須重跑深淺模式的全部彈窗截圖，若 class 改名就
更新對應值。若 Streamlit 日後提供穩定的 `data-theme`，應改用正式屬性並移除
Emotion class 相依。

### 舊 schema 欄位名稱的驗收規則

完工清單要求全 repo 搜尋 `gate_score`、`source_layers` 等舊名稱時只能剩 `docs/`，
但就地升級程式必須用這些名稱辨認使用者的舊 SQLite 結構，搬遷測試也必須建立舊欄位
才能證明資料能升級。兩者無法同時成立。

本輪選擇保留可讀、可測的搬遷程式，不用拆字串等方式規避 grep。建議把驗收例外明訂為
`daibu/db.py` 與 `tests/test_db_migration.py`，其他產品程式與頁面不得再引用舊概念。

### 下一輪的大功能：分平台產文字＋產貼圖

使用者的方向：內容要分平台（Threads／IG／LinkedIn 各寫各的）、先產文字再由文字產
圖。**本輪明確不做**。開始設計前要先解決的衝突：主流圖片生成服務多數付費，與專案
既定的「只用免費額度」成本策略牴觸。需要使用者裁決是否為此破例、或改用本地／免費
方案。
