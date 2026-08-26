# 六頁 v57 正式產圖工具接線設計

## 目的

把已核可的粉彩手帳 v57 六頁原型接進正式貼文工具，讓 AI 產稿、內容編輯、模板預覽、PNG 產圖與 ZIP 下載都只處理同一套六頁結構。舊七頁草稿、舊七頁模板版本與舊 PNG 不保留。

## 已確認的產品決策

- 正式頁序固定為：`cover → who → problem → how-ai → results → cta`。
- `why-care` 頁型從正式內容契約、AI prompt、Renderer、編輯器、模板編輯器、PNG 與 ZIP 全面移除。
- 第五頁「使用前／產品介入／使用後」三張便利貼使用 `repeat(3, 1fr)`，寬高、內距與視覺重量一致。
- v57 粉彩手帳成為唯一正式模板；舊 `editorial-v15.1` HTML、CSS、layout 與資料庫模板版本移除。
- 現有七頁草稿、來源快照、草稿版本綁定與舊 PNG 全部刪除。
- 選題、題目狀態、公司名稱、來源包、正式 Logo 與其他非輪播資料保留。
- 不呼叫付費 API；遷移與壓力測試使用本機 fixture，不重新產生任何正式內容。

## 現況盤點

2026-08-26 以 `sqlite3 -readonly daibu.db` 盤點；先執行 `SELECT 1` 校準連線，`PRAGMA integrity_check` 為 `ok`。

- `carousel_pages`：0 列、0 個 idea。
- `carousel_sources`：0 列、0 個 idea。
- `carousel_drafts`：0 列、0 個 idea。
- `carousel_template_versions`：2 列、1 個 theme。
- `carousel_template_settings`：1 列、1 個 theme。
- 正式 PNG 不落磁碟或資料庫，只存在 Streamlit `session_state`；服務重啟即可清空。
- 磁碟另有 `.playwright-cli/railway-carousel-20260731/` 的七張舊 QA PNG，屬本輪可刪範圍。

## 產品架構

```text
已查證來源＋公司資料
          ↓
六頁 AI Prompt / JSON Schema
          ↓
CarouselDraft（六個 page_type）
          ↓
內容編輯器 ──儲存──> carousel_pages / carousel_sources
          ↓                         ↓
v57 Renderer <── 六頁模板版本／layout schema v3
          ↓
1080×1350 HTML × 6
          ↓
Playwright PNG × 6
          ↓
六張預覽＋六檔 ZIP
```

## 元件與責任

### 1. 六頁內容契約

`daibu/cards/pages.py` 的 `PAGE_TYPES` 改成六頁，移除 `why-care` 對應標籤、diagram、mascot 與 section 規則。`CarouselDraft` 資料類別不變，讓既有資料流仍使用同一個型別；只有合法頁序與各頁內容角色改為六頁。

六頁內容角色：

1. `cover`：公司名稱、Logo、一句話定位。
2. `who`：公司定位、基本資料、為什麼值得介紹。
3. `problem`：現有流程、優化空間、釋放價值。
4. `how-ai`：理解輸入、分析處理、交付結果，加上 AI 角色與人工責任。
5. `results`：使用前、產品介入、使用後，加上核心差異與帶來的價值。
6. `cta`：固定兩句社群 CTA；不再要求總結與提問卡。

### 2. AI Prompt 與回應 schema

`daibu/llm/prompt.py` 與 Gemini JSON schema 改成剛好六頁，刪除 why-care 任務。標題與 section label 使用目前核可文字，不要求第 4–6 頁標題重複公司名。來源 grounding 規則保留：事實型內容仍須綁來源與逐字引文；CTA 可使用固定品牌文案而不要求來源。

### 3. v57 正式 Renderer

新增正式 `sticky-notebook-v1.html`、`sticky-notebook-v1.css` 與 `sticky-notebook-v1.json`，結構取自核可的 `company-neutral-seven-pages-sticky-57.html`，但內容節點全部由正式 `CarouselDraft` 與 `BrandAsset` 注入，不複製原型 fixture 文字。

每頁維持 1080×1350，使用 LINE Seed TW、深藍／天藍／黃／珊瑚／薄荷色票、方格紙背景、白紙、膠帶、直角便利貼、右下折角與手繪呆一布。裝飾 SVG 皆 `aria-hidden="true"`；Logo 有獨立安全區；文字節點保留 `data-edit-key`，版面節點保留 `data-layout-id`。

第五頁三張流程便利貼固定三等分：

```css
.result-flow {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  align-items: stretch;
}
```

三卡使用相同高度、padding、標題字級與正文下限，不以縮小中卡換取箭頭空間；流程方向由卡片之間的箭頭呈現。

### 4. layout schema v3

舊 schema v1/v2 描述七頁 editorial 版型，無法安全承載六頁 v57。新增 schema v3 registry，頁型只含六頁，元素名稱與 v57 DOM 一致。正式執行只建立 v3；解析器不再接受建立新的 v1/v2 版本。

由於使用者明確要求刪除舊七頁內容，migration 會清除舊模板版本，因此不需要在正式 UI 保留 v1/v2 編輯能力。讀取舊格式只保留在 migration 測試 fixture，不保留產品入口。

### 5. 內容與模板編輯器

內容 rail、欄位 payload、儲存驗證與成功訊息全部改成六頁。模板編輯器亦只顯示六頁與 schema v3 元素。手機仍維持唯讀；桌機拖曳、縮放、字級、對齊、undo／redo 與不可變版本機制保留。

### 6. PNG 與 ZIP

`carousel_pngs()` 必須產生六張 1080×1350 PNG。ZIP 檔名固定為：

```text
01-cover.png
02-who.png
03-problem.png
04-how-ai.png
05-results.png
06-cta.png
```

快取 fingerprint 仍包含內容、模板版本與 revision；部署重啟會清除舊 session cache，新六頁內容亦會產生不同 fingerprint。

## 破壞性遷移

### 刪除目標

在單一 SQLite transaction 中依外鍵順序處理：

1. `carousel_pages`
2. `carousel_sources`
3. `carousel_drafts`
4. `carousel_template_settings`
5. `carousel_template_versions`
6. 建立每個現有 theme 的唯一 schema v3 六頁版本並設為 active

遷移不得刪除：`ideas`、`idea_sources`、`brand_assets`、themes、成效資料或使用者設定。

### 可恢復性

- 執行正式 migration 前，以 SQLite `.backup` 建立時間戳備份。
- migration 本身必須 idempotent；中途失敗由 transaction 全數 rollback。
- 備份只用於故障復原，不重新匯入七頁產品入口。
- 刪除 `.playwright-cli/railway-carousel-20260731/` 七張 QA PNG 前，先精確確認資料夾內只有預期的 `01-cover.png` 至 `07-cta.png`。
- 正式服務重啟清除 session 內舊 PNG；不嘗試存取或修改使用者瀏覽器其他資料。

## 錯誤處理

- 六頁順序、頁型、section 或 diagram 缺漏：拒絕儲存並指出頁面。
- 文字或 Logo 超出版面：不產圖、不覆蓋已存內容，回傳可讀的版面錯誤。
- migration 發現未知模板 schema、外鍵異常或備份失敗：停止部署，不清除資料。
- 正式資料清除完成但六頁模板初始化失敗：同一 transaction rollback。
- PNG 任一頁失敗：不建立 ZIP，UI 顯示失敗頁型。

## TDD 與驗收

### 垂直切片

1. 六頁 PAGE_TYPES／內容契約／fixture：先看七頁期待失敗，再改成六頁。
2. Prompt／Gemini schema：先看輸出仍要求七頁失敗，再改六頁。
3. 破壞性 migration：在隔離 DB 植入七頁草稿、來源、模板與保留資料；先看舊資料未清，再實作並驗證只清輪播資料。
4. v57 Renderer：逐頁以正式 fixture 建立失敗契約，再逐頁接入 DOM／CSS／layout。
5. 編輯器：先讓 rail／payload 的七頁斷言失敗，再改六頁並跑真實 Chromium 儲存流程。
6. PNG／ZIP：先看七張期待失敗，再改為六張與新檔名。
7. 視覺與壓力：SUN、Billow AI Labs、Shiraz AI；短／長公司名；橫式／直式 Logo；每個欄位接近 hard limit。

### 必須通過

- 每次只跑當前測試檔完成 Red→Green→Refactor。
- 每個 Task 收尾跑相關測試；合併前與 main 各跑完整 pytest。
- 1280×800 與 375×812 至少兩輪截圖自檢。
- 六頁 HTML 與 PNG 均無文字裁切、元素越界、非法碰撞或橫向捲動。
- 第五頁三張卡寬高差各不超過 1 CSS px。
- 正式 migration 前後以已校準查詢量測資料：輪播舊資料與舊模板版本歸零並建立 v3；保留表的列數與 canonical 指紋不變。
- 正式服務沿用既有 localhost 網址，console 0 errors／0 warnings，六頁編輯、產圖與 ZIP 核心流程實際通過。

## 替代方案與取捨

- **保留舊草稿並手動升級**：資料風險最低，但使用者已明確拒絕保留七頁內容，因此不採用。
- **維持七頁 schema、只隱藏 why-care**：改動較小，但 AI、編輯器與輸出會長期不一致，因此不採用。
- **直接覆寫 v1/v2 layout**：會破壞不可變版本與舊資料辨識，且無法表達頁型減少，因此不採用。

## 成本、安全與限制

- 不新增付費服務或前端套件。
- 不在實作或驗收中呼叫正式 LLM；真實 API 契約維持 deselected，除非使用者另行授權。
- 正式草稿目前為 0，因此本次刪除沒有內容損失；仍按可恢復遷移流程執行，避免不同環境有資料時誤刪。
- Git 歷史仍可看到舊 Renderer；「刪除」指產品程式、正式資料與 runtime 入口不再保留，不改寫 Git 歷史。
