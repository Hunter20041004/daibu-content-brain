# 六頁系列模板獨立文字層（schema v4）設計規格

日期：2026-08-27

狀態：已完成產品方案確認，待使用者審閱書面規格
適用模板：`sticky-notebook-v1` 六頁 v57 正式版

## 1. 問題與產品目標

目前「系列模板管理」有些文字可以選取並調整字級，有些看得到卻無法單獨調整。這不是權限問題，而是 layout schema v3 的資料粒度不一致：例如第 5 頁的「使用前」卡片在版面資料裡只有一個 `before` 元素，但 Renderer 在它裡面又放了 `BEFORE`、標題與說明三個文字節點。編輯器只認得外層 `before`，因此三段文字共用同一個選取框與一組字級；子層 CSS 又使用固定 px 或相對 `em`，使外層字級不一定能直接控制使用者看到的那一段文字。

本輪目標是把第 2–5 頁所有可見且有獨立語意的文字拆成獨立版面層。完成後，使用者點選「使用前｜英文標籤」、「使用前｜標題」或「使用前｜說明」時，右側面板只調整該段文字，不影響同卡片的其他文字。背景卡、圖示、箭頭與文字也分離，移動背景不會偷偷帶動文字。

封面與 CTA 目前沒有這個複合層問題，本輪維持既有結構與視覺行為。

## 2. 已拍板方案與替代方案

### 主方案：升級為 schema v4（採用）

建立正式的獨立圖層資料模型，讓編輯器、即時預覽與 PNG Renderer 共用同一份 v4 layout。每個邏輯文字角色有自己的 `data-layout-id`，背景與裝飾也有自己的非文字元素。

- 優點：畫面、控制項與輸出資料一致；可測試、可遷移、之後新增模板也能遵循同一規則。
- 成本：registry、內建 layout、Renderer、CSS、相容層與測試需同步修改；版面元素數量會增加。
- 產品理由：這是唯一能保證「點哪段、改哪段、輸出也一致」的長期解法。

### 備援 A：只在編輯器疊加子文字控制框（不採用）

不改 schema，只讓瀏覽器臨時辨識卡片內文字。

- 優點：表面改動較少。
- 缺點：儲存資料沒有正式欄位可承接，正式 PNG 容易與預覽分岔；復原、重做與版本相容也會變得模糊。

### 備援 B：保留 v3，為每一頁寫例外規則（不採用）

針對 `before`、`stage-1` 等元素逐一加特殊控制。

- 優點：短期可少改 schema parser。
- 缺點：例外會隨頁型增加，測試與維護成本持續上升，也無法建立一致的模板能力。

## 3. 使用者體驗

### 3.1 選取與屬性面板

- 點背景色塊：只顯示 X、Y、寬、高等幾何控制，不顯示字級與文字對齊。
- 點文字：顯示 X、Y、寬、高、字級與對齊。
- 圖層名稱採「區塊｜角色」格式，例如：
  - `使用前｜英文標籤`
  - `使用前｜標題`
  - `使用前｜說明`
  - `代表使用者｜背景`
- 拖曳、縮放、鍵盤移動、復原、重做、Escape 取消與重設，仍沿用現有操作模式。
- 手機維持唯讀；本輪不新增手機精準排版能力。
- 本輪不新增群組、多選、旋轉、z-order、任意新增／刪除元素或自訂字型／色票。

### 3.2 預覽文字

模板管理仍使用語意佔位文字，不帶入 SUN 或其他真實公司資料。拆層後，每個可編輯內容欄位的 `data-edit-key` 必須與對應的 `data-layout-id` 放在同一個實際文字 DOM 節點上，使即時內容替換、版面移動與字級調整都作用於同一物件。

固定設計文字（例如 `COMPANY FILE`、`THE OPPORTUNITY`、`BEFORE`）雖然不是草稿內容欄位，仍是可見文字角色，因此會有獨立文字 layout layer，可調位置、框尺寸、字級與對齊，但不會在內容編輯器中變成可改文案。

## 4. schema v4 圖層模型

schema v4 延續 1080×1350 固定畫布與既有白名單屬性：

- 所有元素：`x`、`y`、`w`、`h`
- 文字元素：另有 `font_size`、`text_align`
- 非文字元素：不得帶文字屬性
- 未登錄元素、未知欄位、非有限數字、越界或低於最小尺寸，仍由 parser 拒絕
- collision policy 延續 `avoid`、`allow`、`background`

核心不變式：

1. 一個 `data-layout-id` 只代表一個可獨立操作的視覺物件。
2. 承載使用者內容的文字節點，同時承載該內容的 `data-edit-key`。
3. `font-size` 與 `text-align` 直接套在實際文字節點；子層 CSS 不得再以固定 px、`em` 或更高 specificity 覆寫它。
4. 背景圖層使用 `background` collision policy，不與自己的前景文字互判碰撞。
5. 文字層仍需參與畫布越界、文字溢出與前景碰撞檢查。

## 5. 第 2–5 頁圖層清單

下列名稱描述 v4 的語意分層；實作時 ID 採穩定的 kebab-case。所有既有 `heading`、Logo 與 mascot 保留，但固定頁面眉標也納入文字層。

### 第 2 頁 `who`

- 頁面：`page-label`、`heading`、`logo`、`mascot`
- 身份流程：三個節點文字與兩個箭頭各自分離
- 白話定位：`positioning-bg`、`positioning-label`、`positioning-text`
- 基本資料：`facts-bg`、`facts-label`、`facts-text`
- 為什麼值得介紹：`reason-bg`、`reason-label`、`reason-text`

### 第 3 頁 `problem`

- 頁面：`page-label`、`heading`、`question-mark`、`spine`、`mascot`
- 現在怎麼做：`current-bg`、`current-label`、`current-text`
- 哪裡還能更好：`opportunity-bg`、`opportunity-label`、`opportunity-text`
- 三個流程節點各自拆為：`stage-N-bg`、`stage-N-icon`、`stage-N-index`、`stage-N-title`、`stage-N-text`

### 第 4 頁 `how-ai`

- 頁面：`page-label`、`heading`、兩個流程箭頭、`mascot`
- 三個流程步驟各自拆為：`step-N-bg`、`step-N-tag`、`step-N-title`、`step-N-text`
- 四張補充卡各自拆為：`<section>-bg`、`<section>-label`、`<section>-text`；section 為 `traditional`、`ai-role`、`human`、`difference`

### 第 5 頁 `results`

- 頁面：`page-label`、`heading`、`mascot`
- 代表使用者：`audience-bg`、`audience-label`、`audience-text`
- 使用前：`before-bg`、`before-tag`、`before-title`、`before-text`
- 產品介入：`intervention-bg`、`intervention-arrow`、`intervention-title`、`intervention-text`
- 使用後：`after-bg`、`after-tag`、`after-title`、`after-text`
- 核心差異：`core-difference-bg`、`core-difference-label`、`core-difference-text`
- 帶來的價值：`value-bg`、`value-label`、`value-text`

圖示、箭頭、問號與背景是非文字 graphic；`COMPANY FILE`、`BEFORE`、節點編號等以字型呈現且需調字級的內容則登錄為文字元素。若某一符號最終以 SVG 實作，就登錄為 graphic，不提供字級控制；分類以實際 Renderer 節點為準，不以畫面看起來像不像文字猜測。

## 6. v3 → v4 相容與版本生命週期

### 6.1 讀取

- parser 接受既有 schema v3 與新 schema v4。
- v3 只在記憶體中正規化成 v4，不回寫舊 `layout_json`。
- 每個舊 composite 的外框幾何成為對應 `*-bg`；其標籤、標題、正文與圖示位置，依內建 v57 的已校準相對比例投影到舊外框。
- 對本來已是獨立元素的 heading、Logo、mascot、spine，幾何值原樣帶入。
- 正規化結果必須完整通過 v4 registry、越界與碰撞前置驗證，否則模板不可進入可儲存狀態。

這個策略的白話意思是：舊版本像一個裝著三段文字的紙盒；打開時程式在記憶體裡把紙盒拆成背景與三張文字卡，但不改掉倉庫中的原始紙盒。

### 6.2 儲存與啟用

- 使用者第一次儲存正規化後的舊模板時，建立新的不可變 schema v4 template version。
- 所有 v3 歷史版本保持原始 JSON 與版本 ID，不做批次覆寫。
- SQLite 資料表結構不變；版本差異由既有 `schema_version` 與 `layout_json` 承接。
- 新建草稿綁定 active v4 版本；既有草稿仍維持原 template version，除非走既有的明確升級流程。
- 正式切換前先備份 SQLite，確認 template version 數量、草稿綁定、`integrity_check` 與 `foreign_key_check`；若要升級現有 SUN 草稿，只改模板綁定，不重寫正文、來源、Logo 或頁面內容。

### 6.3 快取

編輯器 sessionStorage key／payload fingerprint 必須包含 schema version 與 registry fingerprint。v3 composite 的暫存工作副本不得套到 v4 獨立層，避免舊座標覆蓋新圖層。

## 7. Renderer、CSS 與編輯器共用契約

資料流如下：

```text
v3/v4 layout_json
        │
        ▼
解析＋記憶體正規化為 v4
        │
        ├──► 模板編輯器 overlay／屬性面板
        │
        ├──► 即時預覽 DOM
        │
        └──► 正式 PNG Renderer
```

- Renderer 是唯一可見結構來源；模板編輯器不得維護另一套假 DOM。
- 每個 registry element 必須在對應頁的正式 DOM 中恰好出現一次。
- 每個需要即時替換的內容 key 必須落在對應文字 layout node；缺 hook、重複 hook 或 registry/DOM 不一致時，預覽顯示錯誤並禁止儲存。
- CSS 負責視覺外觀，但 layout CSS 對 X／Y／寬高／字級／對齊擁有最終控制權。
- 背景卡可保留色彩、陰影、折角與膠帶感；這些裝飾不能靠文字節點的 padding 或 pseudo-element 製造出不可分離的幾何。
- 第 5 頁三張主要背景卡維持相同尺寸；拆層不能破壞 v57 已核定的三卡平衡。

## 8. 驗證與錯誤處理

儲存前沿用 Chromium 精準檢查，並增加獨立層契約：

- registry 與 Renderer hook 一一對應
- 文字 computed font-size 等於 layout 值
- 調整一個文字層時，兄弟文字層的幾何與字級不變
- 移動背景時，前景文字位置不變
- 文字不得溢出自己的框、畫布或被裁切
- 前景元素依 collision policy 檢查碰撞；背景不與自己的前景誤判
- 桌面可操作、手機唯讀，兩者皆無頁面橫向捲動
- 驗證失敗時停留在 working copy，不建立 template version、不改 active version、不改草稿綁定

## 9. TDD 實作原則

實作計畫必須依垂直切片逐一執行 Red → Green → Refactor；一次只新增一個會失敗的行為測試，再寫最小實作讓它通過。預計切片順序：

1. v4 registry 與 parser 接受完整獨立層。
2. 一個 v3 composite 正規化為 v4 且不改原輸入，再逐頁擴充映射。
3. Renderer 先拆一張卡，驗證 `data-layout-id`／`data-edit-key` 同節點與 computed font-size，再逐頁擴充。
4. 編輯器選取背景不顯示字級；選取文字顯示並可修改。
5. 兄弟文字互不影響、背景與文字互不帶動，並覆蓋 undo／redo／Escape。
6. v4 儲存建立不可變新版本；v3 歷史 JSON 與舊草稿綁定不變。
7. 真實 Chromium 驗證第 2–5 頁每個文字層、正式 PNG 與預覽一致。

每個 Task 收尾才跑一次完整測試；合併回 `main` 後再跑一次。外部邊界方面，SQLite 版本寫入與真實 Chromium DOM／computed style 都要有 integration 或 browser test，不能只靠 mock。

## 10. 視覺 QA 與驗收標準

完成前至少做兩輪 Playwright 截圖自檢，每輪只截：

- 1280×800 桌面版：展示第 5 頁不同文字層的選取與屬性面板
- 375×812 手機版：確認唯讀狀態與無水平溢出

每輪逐項檢查層次、留白、LINE Seed 標題／內文字體差異、粉彩主色數量、左右對齊、375px 響應式、hover／focus／錯誤／已儲存狀態與低干擾微動效。第一輪發現的問題要先修正，再進行第二輪；最終截圖路徑記入 `HANDOFF.md`。

使用者可見的完成條件：

1. 第 2–5 頁每段可見邏輯文字都能單獨選取。
2. 選取任何文字都能單獨改字級與對齊，不改變同卡片其他文字。
3. 選取背景只改幾何，不顯示文字控制。
4. 儲存、重開、啟用後設定值仍在；預覽與 1080×1350 PNG 一致。
5. 舊 v3 版本仍可回看，資料庫原始歷史版本不被改寫。
6. 第 2–5 頁沒有文字裁切、非預期碰撞或破壞 v57 核定版面。

## 11. 安全、成本與剩餘限制

- 不新增外部套件、API、LLM 呼叫或付費服務。
- 不改 SQLite table schema；只在使用者儲存或正式切換時增加既有格式的不可變模板版本。
- 正式資料寫入前必須備份並用使用者視角重開模板與草稿驗證，不以 command exit 0 代替畫面驗收。
- 拆層後操作物件較多；本輪以清楚命名解決辨識問題，不加入圖層樹或群組功能。
- 固定設計文字可調版面與字級，但不在內容編輯器改文案；若未來需要改固定英文眉標，應另開模板文案能力，不在本輪偷偷擴張。

## 12. 與既有規格的關係

- 本規格以 `2026-08-26-six-page-v57-production-integration-design.md` 的六頁 v57、schema v3 正式成果為起點，升級為 schema v4。
- 本規格取代 `2026-08-23-template-editor-independent-text-layers-design.md` 對舊七頁／schema v2 架構的實作定義；舊檔保留作歷史紀錄，不再是目前程式的依據。
- 本規格延續 `2026-08-23-template-editor-live-preview-placeholders-design.md` 的「正式 Renderer 是唯一預覽 DOM」與語意佔位原則，但取代其中以單一主要角色代表 composite 的做法；v4 改為每個子角色各有獨立 layer 與 placeholder hook。
