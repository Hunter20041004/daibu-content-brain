# 編輯器定位與輪播草稿恢復設計

## 背景

正式內容製作頁有三個同時可見的問題：

1. 「編輯｜題目」按鈕只重設已經相同的 `selected_adopted_id`，頁面重跑後仍停在頂端；正文編輯器位於視窗下方，使用者看不到任何變化。
2. `gemini-3.5-flash-lite` 能回傳合法六頁 JSON，但 API Schema 沒有表達「每個事實區塊都要有查證引文」與「CTA 必須逐字固定」；應用程式最後驗證才拒絕，且目前沒有格式修正重試。
3. `st.status` 內拋錯時會留下不完整的 `error` 圖示文字，狀態標題看起來像 `rror正在查證公司資料…`。

## 已核可的使用者結果

- 被選中的文章按鈕顯示「正在編輯｜…」。按任何文章按鈕後，頁面平滑捲到該文章編輯器；偏好減少動效時改為立即定位。
- 六頁 CTA 永遠由程式套用 `pages.CTA_TEXT`，不依賴模型是否逐字遵守。
- 第一份輪播回覆若無法通過解析或 grounding 驗證，系統把精確錯誤訊息附到同一份 prompt，完整重生一次；第二次仍失敗才顯示錯誤。
- 失敗時不覆蓋既有來源、草稿或圖片，且狀態收合為「公司資料查證未完成」。
- 真實 LLM 契約以六頁為準，檢查頁序、固定 CTA、逐字引文與資料庫寫入。

## 技術設計

### 編輯器定位

沿用現有 `theme-workspace` 的 iframe scroll bridge，不引入新套件。點擊文章按鈕時同時寫入：

- `selected_adopted_id`
- `scroll_to_adopted_editor_id`

頁面在選定文章的 expander 前輸出唯一 anchor。只有 request id 與文章 id 相同時才建立一次性 iframe，呼叫 parent document 的 `scrollIntoView()`。按鈕選取狀態直接由 `selected_adopted_id` 計算，不另存重複狀態。

### 固定 CTA

`prompt.parse_carousel()` 仍只負責把模型 JSON 轉成 `CarouselDraft` 並執行結構驗證。`draft.create()` 在 grounded validation 前，把 CTA 頁唯一 section 的文字、來源與引文替換為程式常數。這是品牌固定文案，不是模型事實，因此不會創造未查證內容。

### 有限重試

`draft.create()` 最多呼叫 `generate_text` 兩次：

1. 第一次使用原始六頁 prompt。
2. 若解析、結構或 grounded validation 失敗，第二次在原 prompt 後附上第一輪的安全驗證錯誤，要求重新輸出完整六頁 JSON。

第二次仍失敗時，以第二次 raw response 建立 `LLMResponseError`，不保存任何草稿。timeout、quota 與 provider unavailable 不屬格式錯誤，不在此層重試。

### 狀態與錯誤

產生流程保留 `st.status`，但 catch 區塊會將 status 更新為 `state="error"`、label「公司資料查證未完成」、`expanded=False`，再顯示既有資料保護訊息。畫面不顯示 raw LLM response 或 API 細節。

## 安全與成本

- 無 schema migration、新依賴或付費服務。
- 只有第一份回覆不合格時才多用一次免費模型額度；最多一次，不做無限重試。
- 公司來源、舊草稿與圖片仍由既有「全部成功後才單一 transaction 保存」保護。
- 正式驗收使用 `daibu.db` 副本；除重啟服務外不寫正式內容。

## 驗收

- AppTest 能看見「正在編輯」、一次性 scroll marker 與乾淨錯誤狀態。
- 單元測試先分別重現 CTA 偏離與第一輪缺引文，再證明固定 CTA 與一次修正重試。
- 真實 Gemini 契約回傳六頁並通過 `validate_grounded_draft`。
- Playwright 兩輪各驗證 1280×800 與 375×812；點擊後編輯器進入 viewport，無水平溢出，console 0 errors／0 warnings。

