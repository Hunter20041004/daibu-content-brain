# HANDOFF — 呆一布選題大腦（daibu-content-brain）

> 於 2026-07-30 更新。
> 一句話現況：**新版輪播 Phase B（Task 4–5）完成；下一輪從 Phase C Task 6
>「新版滿版垂直敘事 HTML」開始。**

## 本輪目標與驗收

依 `docs/plan-carousel-redesign.md` 完成 Phase B：

- 沒有已確認的官方 Logo 就阻擋產圖；
- Logo 公司、官方 HTTPS 來源、確認日期與本機檔案都可驗證；
- 只接受可解碼的透明 PNG 或不含危險／外部內容的 SVG；
- 八種圖解使用固定品牌 layout，AI 角色採 A1 直式步驟＋M1 無框 Q 版頭像。

## 本輪狀態

- 工作分支：`codex/carousel-redesign-phase-b`。
- Task 4 提交 `c4eb2e1`：Logo metadata、PNG／SVG 驗證與 data URI。
- Task 5 提交 `e99376c`：固定圖解 layout 與四種 M1 表情。
- 審查修正 `f8365c0`：
  - PNG 改為 Pillow 真實解碼，並要求 alpha／透明資訊；
  - SVG 阻擋 protocol-relative、data URI、CSS `@import`、style 與外部 `url()`，
    仍允許本機 `#fragment` gradient／symbol；
  - 補八種 layout 路由、箭頭數與 HTML 跳脫測試。
- 安全複審修正 `fd0fb61`：SVG 改採靜態元素／屬性允許清單，阻擋 XML stylesheet、
  SMIL 動畫、DOCTYPE 與未知可執行元素。
- 最終安全修正 `c13f7ea`：資源型屬性採值級允許清單，阻擋 CSS escape／comment
  偽裝的外部 `url()`，只接受本機 `url(#id)`。
- 最新全套：`303 passed, 9 deselected`。
- `9 deselected` 是既有真實 LLM／RSS 契約測試；Phase B 沒有新增網路邊界。
- 本輪只做底層視覺零件，尚無完整畫面，因此未進前端截圖迴圈；Phase C 接成
  1080×1350 畫布後必須做兩輪視覺自檢。
- Logo 檔案大小／解碼像素上限尚未定義，已記錄於 `docs/open-questions.md`。

## 下一步

另開新對話執行 Phase C Task 6：把結構化七頁、Logo 與圖解接進新版滿版 HTML。
依 TDD 一次完成一個垂直切片；Phase C 完成前不得宣稱 PNG 視覺已驗收。

## 最容易踩的坑

1. 不可因缺 Logo 降級成公司名稱純文字，也不可刪掉已存草稿。
2. 不可重新開放 SVG 的外部網址、`style` 或非 `#fragment` 引用。
3. 第 4 頁維持 A1／M1：無虛線、無頭像背景框。
4. 不可讓 LLM 輸出任意 SVG；它只能選既有 `DiagramSpec`。
5. 不要碰真實 `daibu.db`；資料庫與出圖驗收使用暫存副本。
