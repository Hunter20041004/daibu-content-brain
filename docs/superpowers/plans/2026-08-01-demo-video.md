# Demo 影片製作 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 產出約兩分鐘的呆一布內容工作站功能導覽 MP4，以及一份可講 3–5 分鐘的繁體中文報告提綱。

**Architecture:** 用 Playwright CLI 對 port 8502 的 Streamlit 工作站執行真實操作，分段錄成同規格 WebM；等待外部 API 時停止錄影，避免把冗長等待帶進成片。各片段先以 lossless concat 合併，再把步驟字幕放在最後一層並輸出 MP4；產品資料只寫入 `/tmp` SQLite 複本。

**Tech Stack:** Playwright CLI screencast、Streamlit、SQLite、Tavily、Gemini、ffmpeg／ffprobe、Markdown。

## Global Constraints

- 影片為 16:9，1280×720、30fps；總長 1:50–2:15，標題 3 秒。
- 無配音，字幕使用繁體中文；畫面不得顯示任何 API key。
- 真實 `daibu.db` 的修改時間在錄製前後必須一致。
- Logo 只能來自公司官網或官方品牌素材，未經使用者確認不得放進影片或出圖。
- 外部 API 失敗只重試一次；新案例無法完成 Logo 時，後段以明確字幕銜接既有完整案例。
- 不修改產品程式碼；錄影發現的產品 bug 只記錄。
- 所有影片工作檔放在 `artifacts/demo-video/edit/`。

---

### Task 1: 建立安全的影片工作區

**Files:**
- Create: `artifacts/demo-video/edit/project.md`
- Create: `artifacts/demo-video/edit/recording-manifest.md`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `daibu.db`、port 8502 的既有 Streamlit 服務
- Produces: 真實資料庫基準時間、錄影目錄、工具檢查結果

- [ ] **Step 1: 建立 `artifacts/demo-video/edit/`，並把影片二進位與中間檔加入 `.gitignore`**

保留 `project.md` 與 `recording-manifest.md` 可提交，忽略 `*.webm`、`*.mp4`、`*.ts`、`verify/*.png` 與 `segments.txt`。

- [ ] **Step 2: 記錄真實資料庫基準**

Run: `stat -f '%m %Sm' daibu.db`

Expected: 將 epoch 與可讀時間寫進 `recording-manifest.md`，錄影後用同一命令比較。

- [ ] **Step 3: 驗證執行環境**

Run: `lsof -nP -iTCP:8502 -sTCP:LISTEN`

Expected: 8502 有 Streamlit 服務監聽。

Run: `playwright-cli --version`

Expected: 命令成功。

Run: `ffmpeg -version` and `ffprobe -version`

Expected: 兩個命令成功；若 PATH 沒有，先使用 video-use 既有環境或安裝 ffmpeg，再繼續。

- [ ] **Step 4: 確認 8502 使用暫存資料庫**

以只讀程序資訊與 SQLite 路徑核對目前服務；若無法證明，停止現有 8502，先用 SQLite Backup API 建立新的 `/tmp/daibu-demo.db`，再以 `DAIBU_DB_PATH=/tmp/daibu-demo.db` 重啟 8502。不得用 `cp` 複製正在寫入的 SQLite。

- [ ] **Step 5: 建立工作記憶**

`project.md` 記錄本次已核可策略：功能導覽、約兩分鐘、3 秒標題、自動操作＋字幕、真實重新搜尋、無配音。

### Task 2: 探索並錄製真實操作片段

**Files:**
- Create: `artifacts/demo-video/edit/record-demo.js`
- Create: `artifacts/demo-video/edit/01-title.webm`
- Create: `artifacts/demo-video/edit/02-search.webm`
- Create: `artifacts/demo-video/edit/03-candidates.webm`
- Create: `artifacts/demo-video/edit/04-draft.webm`
- Create: `artifacts/demo-video/edit/05-sources-logo.webm`
- Create: `artifacts/demo-video/edit/06-carousel.webm`
- Create: `artifacts/demo-video/edit/07-download.webm`

**Interfaces:**
- Consumes: `http://localhost:8502/選題`、已設定的 Tavily 與 Gemini、Task 1 的安全環境
- Produces: 七段 1280×720 的無聲 WebM 與每段實際長度

- [ ] **Step 1: 用 Playwright CLI 做一次不錄影的定位巡覽**

以 accessible role／name 找出：AI 新創介紹、找題材、候選卡、採用、AI 幫我寫初稿、來源、官方 Logo、輪播七頁、預覽與下載按鈕。只讀 snapshot 優先，不使用脆弱的 CSS 位置選擇器。

- [ ] **Step 2: 寫 `record-demo.js`**

腳本使用 `page.screencast.start({ path, size: { width: 1280, height: 720 } })` 分段錄製；每個操作前後保留 0.7–2 秒。外部搜尋或生成開始後先錄下狀態，再停止該段，等待完成後才開始下一段，避免把 API 等待收進成片。

- [ ] **Step 3: 錄製 3 秒標題與搜尋片段**

標題文字固定為「呆一布內容工作站｜從找公司到七張輪播」，顯示 3000ms。接著錄製選系列、點擊找題材及載入狀態。

- [ ] **Step 4: 等待真實候選並錄製候選片段**

Tavily 或 Gemini 失敗時只重試一次。候選出現後，以平滑捲動展示公司名與一句話介紹，選擇資訊最完整且可繼續流程的一家。

- [ ] **Step 5: 錄製採用、正文與來源片段**

採用候選並點擊「AI 幫我寫初稿」；生成等待不錄入。完成後展示正文、查證來源與 Logo 狀態，畫面不得經過設定頁或任何 key 欄位。

- [ ] **Step 6: 錄製輪播與下載片段**

若新案例已有使用者確認過的官方 Logo，繼續展示七頁草稿、圖片預覽與下載。若沒有，停止新案例並以字幕轉場銜接既有完整案例；不得自行下載或確認 Logo。

- [ ] **Step 7: 以 ffprobe 盤點所有來源片段**

Run: `ffprobe -v error -show_entries stream=width,height,r_frame_rate -show_entries format=duration -of json artifacts/demo-video/edit/<segment>.webm`

Expected: 每段均為 1280×720、可解碼且 duration > 0。

### Task 3: 組裝、字幕與輸出影片

**Files:**
- Create: `artifacts/demo-video/edit/segments.txt`
- Create: `artifacts/demo-video/edit/raw-concat.webm`
- Create: `artifacts/demo-video/edit/master.srt`
- Create: `artifacts/demo-video/edit/preview.mp4`
- Create: `artifacts/demo-video/edit/final.mp4`

**Interfaces:**
- Consumes: Task 2 的 WebM 片段與 duration
- Produces: 1280×720 H.264 MP4、輸出時間軸字幕

- [ ] **Step 1: 依故事順序挑選並裁切片段**

順序固定為標題 → 找公司 → 候選 → 採用／正文 → 來源／Logo → 七張輪播 → 下載。只裁切無操作的頭尾停頓，不把閱讀所需畫面壓到少於 2 秒。

- [ ] **Step 2: 每段先標準化，再以 concat demuxer 無損合併**

若 Playwright 片段 codec／timebase 一致，直接 `ffmpeg -f concat -safe 0 -i segments.txt -c copy raw-concat.webm`；若不一致，各段只做一次 1280×720@30 的 VP9 標準化，再 `-c copy` concat。

- [ ] **Step 3: 建立輸出時間軸 `master.srt`**

字幕依片段累積時間定位，句子為：「從可信來源找具體 AI 公司」、「候選先說清楚公司在做什麼」、「由人決定採用哪一家」、「AI 協助完成正文初稿」、「保留查證來源與官方 Logo」、「整理成七張品牌輪播」、「完成後直接下載圖片」。每句 2–5 秒，不覆蓋主要按鈕。

- [ ] **Step 4: 字幕最後套用並輸出預覽**

用 H.264、`yuv420p`、1280×720、30fps 輸出 `preview.mp4`。字幕使用繁體中文可顯示的品牌字型、白字深色半透明底，放在下方安全區；字幕是最後一個影像 filter。

- [ ] **Step 5: 若總長短於 1:50，以閱讀停留補足；若超過 2:15，優先縮短等待與重複捲動**

Run: `ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 artifacts/demo-video/edit/preview.mp4`

Expected: 110–135 秒。

- [ ] **Step 6: 預覽通過後複製為 `final.mp4`**

最終檔不得再增加重新編碼；以檔案複製保留已驗證的 preview bytes。

### Task 4: 撰寫明天的口頭報告

**Files:**
- Create: `docs/2026-08-01-社團報告提綱.md`

**Interfaces:**
- Consumes: 最終影片段落與實際錄到的功能
- Produces: 3–5 分鐘繁體中文講稿提綱

- [ ] **Step 1: 依影片時間軸寫逐段說法**

每段包含「畫面看到什麼」與「建議說法」，不逐字朗讀 UI；整體以成果展示為主。

- [ ] **Step 2: 加入完成度與限制**

完成度只陳述已驗證內容：單一 AI 新創系列、可信來源候選、人工採用、AI 正文、來源／Logo、七張輪播、PNG／ZIP、桌機與手機介面、449 項測試。限制包括目前是本機版、Tavily key 只在本次服務有效、官方 Logo 仍需人工確認。

- [ ] **Step 3: 加入現場故障備援句**

若現場服務或網路不穩，直接播放 `final.mp4`，講稿仍能跟著影片完成。

### Task 5: 視覺、技術與資料安全驗收

**Files:**
- Create: `artifacts/demo-video/edit/verify/boundaries.png`
- Create: `artifacts/demo-video/edit/verify/samples.png`
- Modify: `artifacts/demo-video/edit/recording-manifest.md`
- Modify: `artifacts/demo-video/edit/project.md`
- Modify: `HANDOFF.md`

**Interfaces:**
- Consumes: `final.mp4`、真實 DB 基準、講稿
- Produces: 可重現的驗收證據與交接狀態

- [ ] **Step 1: 技術規格驗證**

Run: `ffprobe -v error -show_entries stream=codec_name,width,height,pix_fmt,r_frame_rate -show_entries format=duration,size -of json artifacts/demo-video/edit/final.mp4`

Expected: H.264、1280×720、yuv420p、30fps、110–135 秒。

- [ ] **Step 2: 建立兩張視覺接觸表並檢查**

`boundaries.png` 集中顯示所有片段邊界前後；`samples.png` 顯示前 2 秒、最後 2 秒與三個中段。檢查跳切、黑格、字幕遮擋、文字亂碼、Logo 規則與畫面可讀性。最多修正並重驗三輪。

- [ ] **Step 3: 掃描影片與文字產物是否含 key**

對字幕、腳本、manifest、講稿做 secret pattern 掃描；視覺接觸表確認設定頁與 key 欄位沒有入鏡。

- [ ] **Step 4: 驗證真實資料庫未變**

Run: `stat -f '%m %Sm' daibu.db`

Expected: epoch 與 Task 1 完全相同，寫入 `recording-manifest.md`。

- [ ] **Step 5: 更新交接並提交文字產物**

`HANDOFF.md` 記錄影片、講稿、驗收接觸表路徑與限制；提交 plan、講稿、manifest、project、HANDOFF 與 `.gitignore`，不提交 WebM／MP4／PNG 二進位。

- [ ] **Step 6: 推送 `main`**

確認本次只有影片製作文件與交接變更，push 到既有 `origin/main`；專案沒有正式站部署流程，因此不另建部署。
