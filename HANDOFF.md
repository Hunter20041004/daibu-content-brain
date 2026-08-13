# HANDOFF — Gemma 選題與 Gemini 備援

> 2026-08-13 14:00 更新。正式系統原本使用 `gemini-3.1-flash-lite`；12:45 的失敗是 Gemini 503 暫時繁忙，不是 429 額度耗盡。本輪依使用者核可，拆分高頻選題與格式敏感任務。

## 本輪目標與驗收

- 選題與必要公司資格查核優先使用 `gemma-4-26b-a4b-it`。
- Gemma 遇額度、逾時、503，或選題連續兩次格式失敗時，自動改用 `gemini-3.5-flash-lite`。
- 350–500 字正文與七頁輪播固定使用 Gemini 3.5 Flash-Lite。
- 不新增付費服務或 Groq key；不修改正式 ideas 做 QA。

## 本輪狀態

- **模型可用性**：Google Models API 實查目前 key 可呼叫 `gemma-4-26b-a4b-it`、`gemma-4-31b-it`、`gemini-3.1-flash-lite` 與 `gemini-3.5-flash-lite`；採用較適合高頻的 Gemma 4 26B。
- **任務路由**：新增 `GoogleTaskRouter`。`generate_ideas` 走 Gemma 並在可恢復失敗時切 Gemini；資格查核使用獨立 `generate_research_text`；一般 `generate_text` 與 `generate_carousel_text` 直接走 Gemini，避免正文被意外換模。
- **設定資料流**：新增 `llm_idea_model`／`LLM_IDEA_MODEL`，既有 `llm_model`／`LLM_MODEL` 改代表正文、備援與輪播模型。Groq 明確選擇仍維持原本行為。
- **TDD**：逐一看見缺少路由器、503 未切換、資格仍走一般文字、Gemini 預設仍為 3.1、設定頁未拆欄位與標籤不精確的紅燈，再做最小修正轉綠。
- **真實 Gemma 契約**：直接指定 Gemma、不允許備援，產出一則可解析、公司名為 Feldy 且標題含繁體中文的候選，`1 passed in 20.79s`。
- **真實雙模型契約**：Gemma 候選與 Gemini 3.5 七頁輪播同跑，`2 passed in 43.36s`；輪播七頁皆有 sections 並成功存回 SQLite 測試庫。
- **副本資料安全**：以 SQLite `.backup` 從正式絕對路徑建立 `/private/tmp/daibu-gemma-routing-qa.iG2HzU/daibu.db`；來源與副本起始均為 12 ideas、`integrity_check=ok`，ideas JSON SHA-256 均為 `405c705c707590ce3a9802392864ba7f9a87697b0b5a5e9fee5bc55a8595c9da`。
- **一次完整產生**：8502 僅點擊一次，候選由 4 增為 7，副本 ideas 由 12 增為 15；新增 Parasma、Billow AI Labs、Almanac。正式庫仍為 12，指紋仍為 `405c…9da`；副本 `integrity_check=ok`，browser console 0 errors／0 warnings。
- **視覺 QA**：設定頁完成多輪 1280×800 與 375×812。第一輪抓到任務說明不完整後補上正文／資格分工；直接重新整理中文子路徑會產生既有 `_stcore` 相對路徑 404，最終改由首頁正常導覽。最終兩尺寸模型值正確、手機 `scrollWidth=clientWidth=375`、console 0 errors／0 warnings。截圖：`.screenshots/gemma-routing-final-desktop.png`、`.screenshots/gemma-routing-final-mobile.png`。
- **全套測試**：功能分支為 `560 passed, 14 deselected, 1 warning in 66.83s`；14 個略過項目需真實外部服務，唯一 warning 是既有 Starlette/httpx 提醒。
- **安全與自審**：compileall、`git diff --check` 通過；秘密掃描先以合成 AIza key 校準後掃 production diff，沒有 Google、Groq 或 Tavily key。因本輪禁止子代理，依 review checklist 自審，未發現 Critical／Important 問題。
- **剩餘限制**：Gemma 與 Gemini 共用 Google API，只能分散模型別配額／容量，不能處理 Google 整體故障；跨平台備援仍需日後設定 Groq key。
- **狀態**：程式、真實模型契約、資料副本、完整候選流程、全套測試與最終畫面均已驗收；待合併 main 後複驗、更新正式模型設定、推送與重啟正式服務。

---

# 前一輪 — YC 公司身分資格修正

> 2026-08-13 12:50 更新。11:56 的「沒有符合資格」不是來源或 API 失效，而是裸公司名搜尋把 YC Almanac 認成 Almanac Realty Investors，並遺失 YC 已知的官方網域、成立年與 batch。

## 本輪目標與驗收

- 資格查核必須接收完整 `CompanyLead`，不可只傳公司名稱。
- 成立、上市與收購證據若無法對上官方網域或 YC 公司身分，不得淘汰公司；證據不足仍為 unknown，不自動放行。
- 依使用者核可，YC 官方頁的 `Active`＋官方網站＋十年內成立年／batch 可直接判定 eligible；`Public`／`Acquired` 直接判定 ineligible。
- Almanac、Feldy、Marengo 的受污染資格紀錄要在備份後精確修正；不得修改任何既有 idea。

## 本輪狀態

- **根因證據**：11:55:59 新增 Almanac=`ineligible/acquired`、Feldy／Marengo=`unknown`。Almanac 唯一證據是 LinkedIn 的 Almanac Realty Investors 收購紀錄；實際 YC Almanac 為 Summer 2026、Active，官方網站 `usealmanac.com`。
- **身分資料流**：selection 現在把 discovery 的 YC profile、官方網址、成立年、batch、狀態與來源名稱完整交給資格查核；legacy backfill 仍相容純字串。
- **同名防護**：有已知官方身分時，外部成立／上市／收購證據必須對上官方網域、YC profile 或 launch 身分；否則捨棄該證據並保持 unknown。官方網域上的真實 public 證據仍會判 ineligible。
- **YC 專屬規則**：只有 `source_name=YC Launches`、profile 為 `ycombinator.com`、狀態 `active`、有官方網站，而且成立年或 batch 年在十年內才直接 eligible。batch 年只保存成 `recent_batch` 證據，不冒充成立年。YC `public/acquired` 直接保存不合格紀錄。
- **成本**：符合上述條件的 YC 公司資格查核為 Tavily 0 次、資格 Gemini 0 次；非 YC 或身分不足者仍沿用每家公司一次 Tavily＋整批一次免費 LLM。
- **TDD**：逐一看見完整身分輸入、YC 年份證據、同名收購、同名年份、selection 身分傳遞、YC Active 直通與 YC public/acquired 直擋的紅燈，再做最小修正。聚焦資格／selection 為 `42 passed`。
- **副本資料安全**：用 SQLite Backup API 建立 `/private/tmp/daibu-company-identity-qa-019ffbe2-v2.db`。清除副本三筆前後均為 12 ideas，ideas JSON SHA-256 都是 `f75cfde255d25b6917fb6020d39fff2792ddfa8cb40baa41c0184d113a1bbf33`；其餘十筆資格 JSON SHA-256 都是 `2144bc6ccd918ea930cb170731c089b1a727b2f8c920a899fc2599b465a824d6`。
- **副本真實身分**：直接讀當下 YC Launches＋YC Companies 後，Almanac、Feldy、Marengo 都是 eligible/private_independent；Almanac 用 Summer 2026 batch，Feldy=2024、Marengo=2026，每家兩筆 YC profile 證據，且測試替身保證未呼叫 Tavily／Gemini。
- **一次真實產生**：8502 只點擊一次。資格已通過，但題目 Gemini 回 `LLMUnavailableError/ServerError`；畫面精確顯示「Gemini 暫時繁忙」，ideas 仍為 12，未重試。
- **視覺 QA**：兩輪各一張 1280×800 與 375×812。第一輪錯誤狀態層次、留白、字體、配色、對齊、響應式、狀態與動效合格，但直接開中文子路徑留下兩個既有 Streamlit 初始化 404；第二輪從首頁正常導覽後，兩尺寸 `scrollWidth=clientWidth`、候選（4）存在、console 0 errors／0 warnings。最終：`.screenshots/company-identity-round2-desktop.png`、`.screenshots/company-identity-round2-mobile.png`。
- **功能分支全套**：`551 passed, 13 deselected, 1 warning in 70.64s`；13 個略過項目需要真實外部服務，唯一 warning 是既有 Starlette／httpx 提醒。
- **合併 main 後全套**：`551 passed, 13 deselected, 1 warning in 64.84s`，exit code 0；唯一 warning 仍是既有 Starlette／httpx 提醒。
- **安全與自審**：compileall、`git diff --check` 通過；秘密掃描先用合成 AIza 字串校準，再掃 production diff，無 Gemini／Groq／Tavily key。依無子代理規則完成逐段自審，未發現 Critical／Important 問題。
- **正式備份**：`backups/daibu-before-company-identity-20260813-123742.db` 為 `integrity_check=ok`、12 ideas、13 筆資格，ideas JSON SHA-256=`f75cfde255d25b6917fb6020d39fff2792ddfa8cb40baa41c0184d113a1bbf33`。
- **正式 metadata 修正**：只覆寫 Almanac、Feldy、Marengo 三筆；現在三家都是 `eligible/private_independent`，Feldy=2024、Marengo=2026，Almanac 的成立年維持 null 並保存 Summer 2026 batch。修正過程 Tavily 0 次、Gemini 0 次。
- **正式資料複驗**：仍為 12 ideas、13 筆資格、`integrity_check=ok`；ideas 指紋仍為 `f75c…f33`，其餘十筆資格指紋仍為 `2144bc6ccd918ea930cb170731c089b1a727b2f8c920a899fc2599b465a824d6`。
- **正式服務**：管理命令再次遇到既有 `launchctl` 卸載後立即載入的時序問題；確認 plist `OK`、服務未載入與 8501 無占用後，只對 `io.daibu.content-brain` bootstrap＋kickstart。最終 `state=running`、健康檢查 `ok`，只監聽 `127.0.0.1:8501`。
- **正式使用者視角**：從首頁正常導覽到 `http://127.0.0.1:8501/選題`，顯示候選（4）與 Risklytics；1280px、375px 都無水平溢出，console 0 errors／0 warnings。正式截圖：`.screenshots/company-identity-production-desktop.png`、`.screenshots/company-identity-production-mobile.png`。
- **正式 log**：stderr 最後修改時間仍為 11:55:59，本輪重啟與唯讀畫面驗收沒有新增 server error。
- **狀態**：程式、資料副本、正式 metadata、main 全測、正式服務與正式畫面皆已驗收並推送。

## 前一輪：候選產生錯誤診斷

> 2026-08-13 11:34 更新。正式畫面再次出現泛用失敗訊息；根因不是資料遺失，而是多種已知外部錯誤沒有完整接到前台，且未知錯誤沒有留下安全診斷紀錄。

## 本輪目標與驗收

- Gemini 免費額度、超時、503 繁忙與回覆格式錯誤必須顯示不同的白話原因。
- 公司資格查核裡的 Gemini 錯誤不得被包成模糊的資格失敗；非 Gemini 的資格查核失敗仍需指出正確階段。
- 未知錯誤維持安全泛用文案，但 log 至少留下外層與根因的「類型」，不可記錄錯誤原文、API key、完整 prompt 或下載內容。
- 每種失敗都不得新增 idea 或不完整的資格快取；不得用重複點擊正式 API 來製造錯誤。

## 本輪狀態

- **QA 漏洞**：上一輪只驗證來源失敗、公司重複、資格不符與 Gemini 503；`LLMQuotaError`、`LLMTimeoutError`、`LLMResponseError` 與 `CompanyEligibilityVerificationError` 都會落入同一個泛用訊息。
- **11:34 證據邊界**：失敗後正式庫仍為 12 筆 ideas、10 筆資格紀錄，最新寫入仍是 11:29 的成功批次，證明 11:34 沒有半成品。但舊版 catch 沒寫 log，因此不能誠實斷言唯一根因是額度、超時、格式或 Tavily／資格服務。
- **錯誤保真**：資格查核現在會讓 Gemini 額度、超時與 503 原樣往前傳；其他資格查核錯誤才包成 `CompanyEligibilityVerificationError`。
- **前台文案**：已補 Gemini 額度、超時、模型格式與資格查核四個分支；原始錯誤文字不會顯示。
- **安全診斷**：所有候選產生錯誤會記錄 `error_type` 與 `cause_type`，不記 `str(error)` 或 traceback，避免第三方訊息意外含秘密或完整內容。
- **TDD**：八個回歸切片都逐一看見紅燈再做最小修正轉綠；模型、資格管線與選題頁整合為 `174 passed in 30.47s`。
- **功能分支全套**：`540 passed, 13 deselected, 1 warning in 59.38s`；13 個略過項目需真實外部服務，唯一 warning 是既有 Starlette／httpx 相依提醒。
- **合併 main 後全套**：`540 passed, 13 deselected, 1 warning in 54.55s`，exit code 0；唯一 warning 仍是既有 Starlette／httpx 相依提醒。
- **資料安全**：資格查核的三個 Gemini 錯誤測試都斷言 ideas 與資格快取為空；本輪沒有再次點擊正式產生按鈕。
- **真實邊界（零 API 呼叫）**：在正式資料的暫存副本把 provider 設成受控無效值，從 8502 真實點擊「再產生 3 則」。前台顯示安全泛用訊息，server 只記錄 `generation_failed error_type=ValueError cause_type=none`，沒有記錄錯誤原文或無效設定值；副本仍為 12 筆 ideas、10 筆資格紀錄，證明錯誤跨過 Streamlit 邊界後也不會半套寫入。
- **視覺驗收**：正式資料的 SQLite 副本在 8502 完成兩輪桌機／手機檢查。第一輪桌機抓到骨架載入未結束，判定狀態不合格；第二輪改以候選內容出現為條件，1280×800 與 375×812 都顯示 4 筆候選，手機 `scrollWidth=clientWidth=375`，console 0 errors／0 warnings。最終證據：`.screenshots/generation-errors-round2-desktop.png`、`.screenshots/generation-errors-round2-mobile.png`。
- **UI 檢視**：

  | Before | After | Why |
  |---|---|---|
  | 額度、超時、格式與資格錯誤都顯示泛用訊息 | 每類有自己的白話訊息 | 使用者不用猜來源或資格規則 |
  | 資格查核把 Gemini 錯誤包掉 | 額度／超時／繁忙保留到前台 | 不丟失真正失敗原因 |
  | 未知錯誤沒有 log | 只記錄外層與根因型別 | 可診斷，同時避免秘密外洩 |

- **正式服務**：管理命令再次遇到既有 `launchctl` 卸載後立即載入的時序問題；確認 plist 為 `OK`、舊服務確實未載入後，只對精確標籤 `io.daibu.content-brain` 執行 bootstrap＋kickstart。最終 `state=running`、健康檢查回 `ok`，且只監聽 `127.0.0.1:8501`。
- **正式資料複驗**：重啟前後都是 12 筆 ideas、10 筆資格紀錄；ideas 全 11 欄依 id 排序後的 SHA-256 都是 `86983e7be4f3f91b9eaca5f5f88e68bc385e78d56854ccc87efb7de82523a746`，本輪沒有修改正式內容。
- **正式使用者視角**：`http://127.0.0.1:8501/選題` 顯示 4 則候選與 Risklytics；1280px 與 375px 的 `scrollWidth` 都等於 viewport，browser console 0 errors／0 warnings。最終截圖：`.screenshots/generation-errors-production-desktop.png`、`.screenshots/generation-errors-production-mobile.png`。
- **狀態**：本輪程式、main 全測、受控錯誤邊界、正式服務、正式資料與正式畫面皆已驗收。

## 前一輪：AI 新創來源重整

> 2026-08-13 更新。「AI 新創介紹」已改用公司目錄找新公司、用新聞補時效性，最後才用公開證據查資格。

## 本輪目標與驗收

- 從 YC Launches 與 a16z Speedrun 發現當期 AI 新創，再用 YC Companies 補公司年份與狀態。
- TechCrunch Startups 只會補在已知公司上，不會因為一篇新聞就擅自創建公司候選。
- 歷史公司在查詳情與新聞前先排除；上市、被收購、超過十年或證據不足仍由現有 Tavily＋Gemini 資格守門擋下。
- 所有舊題目、正文、狀態、輪播圖與資格快取保留，移轉只改本系列今後的來源綁定。

## 本輪狀態

1. **產品能力**：一次點擊會從 YC Launches 與 Speedrun 找當期 AI 公司，用 YC Companies 補身分，再最多搭一則 TechCrunch 近期新聞。
2. **使用者體驗**：操作仍是「開始／再產生 3 則」；來源無法取得、公司都重複、資格不符與 Gemini 繁忙會顯示不同說明，不再全部誤報成資格失敗。
3. **技術區塊**：公司目錄 adapter 負責讀公開網頁；discovery 負責排重、初步狀態過濾與新聞配對；免費 LLM 負責整理候選；現有資格守門負責證據查核；SQLite 保存題目與快取。
4. **資料流**：公司目錄 → 歷史／狀態初濾 → 近期新聞 → 題目 LLM → Tavily 證據／整批資格 LLM → 只寫入合格候選。
5. **設計理由**：「這是哪家公司」、「現在為什麼值得寫」、「它是否符合系列資格」是三個不同問題，分開證據才不會把 API 繁忙誤當成資格過嚴。
6. **替代方案**：RSS-only 最省事，但容易只看到新聞熱度而非新公司；directory-only 公司身分比較穩，但缺少「為什麼是現在」。採用目錄＋新聞＋資格證據的三層組合。
7. **安全與成本**：只讀公開目錄，沒有新付費服務或新金鑰；每個未查公司最多一次 Tavily、每批最多一次資格 LLM，不重試湊滿三則。紀錄不含 API key、完整 prompt 或整頁下載內容。
8. **測試證據**：每個切片都先看見失敗測試再實作轉綠。最終聚焦套件 `209 passed, 5 deselected in 36.56s`；狀態修正後分支全套為 `532 passed, 13 deselected, 1 warning in 77.20s`，合併 main 後同套件為 `532 passed, 13 deselected, 1 warning in 108.00s`。YC Launches、YC Companies、Speedrun 與 TechCrunch 真實契約合計 `5 passed, 7 deselected in 2.51s`。
9. **剩餘限制**：公開網頁格式未來可能改版；目前沒有排程自動更新，也沒有處理公司別名；免費 Gemini 仍可能暂時繁忙。

- **舊來源處理**：Y Combinator Blog 保留、啟用，但不再綁在「AI 新創介紹」；舊 a16z RSS 保留成停用記錄且解除綁定；其他系列與來源不變。
- **副本真實流程**：以 SQLite Backup API 從正式庫建立 `/private/tmp/daibu-startup-source-acceptance-019ffbe2.db`。產生前後都是 10 筆 ideas，全欄位 SHA-256 同為 `b4908c2ec754419927b83bbe5a7efaebbcda4dcb9add57de9f5538f1fd31d9c8`。
- **這次實測結果**：四個來源綁定正確，又找不到新候選的根因是「Gemini 暂時繁忙」，不是資格過嚴或目錄來源無法使用。失敗後原候選與題目指紋不變。
- **狀態回歸**：視覺驗收發現失敗後仍殘留「呆一布正在讀資料」。回歸測試先紅後綠，現在等待中只用 spinner，失敗後只留復原說明與精確原因；選題頁 `103 passed in 31.49s`。
- **視覺驗收**：依規則完成三輪，每輪各一張 1280×800 與 375×812。最終四個新來源清楚勾選、舊 a16z 清楚停用，手機 `scrollWidth=clientWidth=375`，console 0 errors／0 warnings。最終證據：`.screenshots/startup-sources-round3-desktop.png`、`.screenshots/startup-sources-round3-mobile.png`。
- **UI 檢視**：

  | Before | After | Why |
  |---|---|---|
  | 失敗後同時顯示「正在讀資料」與失敗原因 | 等待時只有載入提示，結束後只顯示成功或實際失敗階段 | 避免互相矛盾的狀態讓人誤判根因 |
  | 公司目錄無專屬抓取類型 | 來源編輯器有「公司目錄」，且只接受核可的三個網址 | 不讓畫面假裝任意目錄都會解析 |

- **正式資料導入**：導入前用 SQLite Backup API 建立 `backups/daibu-before-startup-sources-20260813-1130.db`；備份與正式庫均為 `integrity_check=ok`、10 筆 ideas、7 筆資格紀錄，ideas 指紋同為 `b4908c2ec754419927b83bbe5a7efaebbcda4dcb9add57de9f5538f1fd31d9c8`。移轉後該指紋仍不變，`config.startup_source_strategy_v1=1`，四個新來源精確綁定，YC Blog 與舊 a16z 皆無綁定。
- **正式一次核心流程**：只點擊一次「再產生 3 則」，成功新增 Dipole Labs 與 Risklytics，兩家均為 2026 年成立、`eligible/private_independent`，來源都是 YC Launches 的可點擊 HTTPS 頁面。正式庫現為 12 筆 ideas、10 筆資格紀錄，舊 10 筆與備份逐欄指紋仍完全相同。
- **正式 localhost 驗收**：第一次服務 install 再次遇到既有 `launchctl` 時序問題；確認 plist 完整、舊服務已離開後，以精確標籤 `io.daibu.content-brain` bootstrap＋kickstart 恢復。最終 `state=running`、健康檢查成功、只監聽 `127.0.0.1:8501`；畫面顯示「候選（4）」與「候選整理好了」，1280px 與 375px 皆無水平溢出，browser console 0 errors／0 warnings。正式最終截圖：`.screenshots/startup-sources-production-desktop.png`、`.screenshots/startup-sources-production-mobile.png`。stderr 最後修改時間為 09:16，本次 11:27 重啟與真實流程未寫入新錯誤。

## 前一輪：新創公司資格查核

> 2026-08-10 更新。公司介紹候選現在必須以可追溯的公開證據確認成立不超過十年、未上市、未被收購，且仍為私人獨立公司。

## 本輪目標與驗收

- Cloudflare 等上市／已收購／超過十年的公司不得進入或留在可見候選。
- 每個沒查過的公司最多搜尋一次，整批公司只呼叫一次免費 LLM；已有資格快取的不重查。
- LLM 提供的網址與逐字引文必須實際出現在 Tavily 結果，否則判定 unknown 並排除。
- 舊候選只新增公司資格 metadata，不刪除或修改任何 `ideas` 欄位。

## 本輪狀態

- **根因**：舊流程只確認候選公司與素材網址／引文一致，沒有查成立年份、上市或收購狀態，因此 2009 年成立且 2019 年上市的 Cloudflare 仍可進入候選。
- **架構**：新增獨立 `company_eligibility` 表，保存 `eligible / ineligible / unknown`、成立年、所有權狀態、理由、原始證據 URL／逐字引文與查核時間；不與 `ideas` 做破壞性綁定。
- **資料流**：產生公司候選 → 排除歷史／同批重複 → 讀資格快取 → 每家未知公司 Tavily 一次 → 整批 Gemini 一次 → 程式核對 URL 與 quote → 先快取全部判定 → 只寫入 eligible 候選。
- **防誤判**：十年邊界可通過；十一年以上、已上市或已收購有證據即不合格；網址錯、引文不存在、缺少私人公司證據或證據矛盾一律 unknown，不讓模型自行放行。
- **舊資料回填**：`python -m daibu.company_eligibility backfill --db <path>` 只查尚未有快取的公司；重跑時不再呼叫 Tavily／LLM。
- **副本演練**：先用已知 10 筆 ideas 校準完整資料指紋。副本回填前後 SHA-256 均為 `bd13bc29e909606f08e315f86a87d5a2c64467258a409683dbe3011369fcb4d2`，10 筆與全部欄位不變。
- **真實邊界**：以實際 Tavily＋Gemini 查 Cloudflare、Moove、Railway；Cloudflare=`ineligible/public/2009`，Moove 與 Railway=`eligible/private_independent/2020`，三者各保存兩筆匹配證據。
- **API 成本**：每個新公司一次 Tavily、每批一次 Gemini。單家公司搜尋失敗只讓該公司 unknown，不重試湊滿三則，也不把原始錯誤或 API key 顯示給使用者。
- **TDD**：依垂直切片逐一看見 schema、證據驗證、上市／收購、矛盾、批次呼叫、快取、顯示過濾、回填與 idempotency 測試先失敗再通過；CLI 副本演練另抓到入口位置造成的 `NameError`，修正後同流程成功查核三家公司。
- **測試**：功能分支全套 `508 passed, 14 deselected, 1 warning in 94.16s`；14 個預設略過項目是需外部服務的契約測試，唯一 warning 是既有相依套件提示。
- **合併 main 後全套**：`508 passed, 14 deselected, 1 warning in 75.19s`，exit code 0；`origin/main` 與本機 `main` 均包含本輪提交。
- **視覺驗收**：副本在 1280×800 與 375×812 各跑兩輪；候選為 2、Moove／Railway 可見、Cloudflare 不可見，375px 水平 overflow 為 0。最終證據：`.screenshots/startup-eligibility-round2-desktop.png`、`.screenshots/startup-eligibility-round2-mobile.png`。
- **正式資料回填**：先用 SQLite `.backup` 建立 `backups/daibu-before-startup-eligibility-20260810-1330.db`；備份與正式庫均為 10 筆且 ideas 指紋同為 `bd13bc29e909606f08e315f86a87d5a2c64467258a409683dbe3011369fcb4d2`。回填後仍為同一指紋，只新增 Cloudflare／Moove／Railway 三筆資格紀錄。
- **正式 localhost 驗收**：重啟時再次遇到既有 `bootout`／`bootstrap` 時序問題；確認服務未載入後以精確標籤 `io.daibu.content-brain` 執行 bootstrap＋kickstart，最終 `loaded=yes`、`health=yes`、只監聽 `127.0.0.1:8501`。正式頁顯示「候選（2）」、Moove／Railway 可見、Cloudflare 不可見，1280px 無橫向溢出，browser console 0 errors／warnings。
- **限制**：公開網頁日後可能更新，目前快取沒有自動過期；公司後續上市或被收購時需重新查核。副本的第一次中文子路徑載入曾有既有 Streamlit `_stcore/health`／`host-config` 404，但正式 8501 最終驗收為 0 console errors／warnings。

## 前一輪：公司介紹候選排重與舊資料相容

> 2026-08-10 更新。修復公司介紹系列混入舊通用題目，以及「再產生」重複推薦已出現公司的問題。

## 本輪目標與驗收

- 公司介紹系列中，同一家公司整個系列只介紹一次，所有狀態都算已出現。
- 同一批 AI 結果也不能出現同公司或同題目。
- 舊的空白公司候選與後來的同公司重複項不顯示，但不刪除、不改狀態。
- 「比較」候選的介面語意改成「瀏覽／查看」。
- 找不到足夠的新公司時寧可少產，不重試免費 LLM 湊數。

## 本輪狀態

- **資料校準**：先用畫面已知的「候選（10）」校準 SQLite 查詢；`daibu.db` 同系列確實有 10 筆候選。其中 6 筆建立於公司限制上線前，`company` 為空白；4 筆有公司，但 Railway 有 2 筆。
- **根因一**：產生候選只排除同系列「已淘汰」標題，候選、採用、已發與同公司不同標題都不在排除名單。
- **根因二**：2026-07-31 才加入公司候選驗證；2026-07-25 的六筆舊通用題目仍留在資料庫，介面用「比較｜標題」替代空白公司，造成仍在產比較題的錯覺。
- **排重名冊**：SQLite 現在會提供同系列所有狀態的歷史題目與非空白公司，依 `created_at, id` 排序。
- **三層保護**：歷史公司／題目先交給 Gemini／Groq 避開；程式收到結果後再強制過濾歷史重複；同批較後出現的公司／題目也會被擋下，未通過者不寫入。
- **名稱規則**：公司與題目比對會去除頭尾空白並忽略英文大小寫，不做模糊比對，避免不同公司被誤傷。
- **舊資料相容**：公司介紹系列只顯示有公司名稱且第一次出現的資料；空白公司與後來重複項保留在 SQLite。一般系列維持原行為。
- **真實資料結果**：以 `daibu.db` 的暫存副本開啟選題頁，候選由 10 則變成 3 則，只顯示 Moove、第一次出現的 Railway、Cloudflare；六則通用題目與後來的 Railway 不顯示。
- **介面文案**：「一次比較／比較清單／逐則比較／先比較／比較｜」改成「一次查看／候選清單／逐則查看／先瀏覽／查看｜」。公司候選按鈕維持「公司｜在做什麼」。
- **TDD**：每個資料庫、prompt、歷史公司排重、歷史題目與同批排重、全重複錯誤、舊資料顯示、介面文案切片都先看見單一測試失敗，再做最小修正轉綠。
- **集中測試**：`PYTHON_DOTENV_DISABLED=1 ... pytest -q tests/test_db.py tests/test_llm.py tests/test_selection.py tests/test_app_smoke.py` 為 `192 passed in 26.24s`。停用 dotenv 是為了讓既有「金鑰尚未設定」測試不被本機真實 `.env` 影響。
- **真實 Gemini 契約**：`pytest -q -m contract tests/test_llm_contract.py::test_real_llm_returns_parsable_ideas` 為 `1 passed in 4.29s`；真實回應仍能解析為公司候選欄位。
- **功能分支全套**：`PYTHON_DOTENV_DISABLED=1 pytest -q` 為 `489 passed, 13 deselected, 1 warning in 54.05s`。13 個預設略過項目需要外部服務；唯一 warning 是既有 Starlette／httpx 棄用提示。
- **合併 main 後全套**：同一指令為 `489 passed, 13 deselected, 1 warning in 52.10s`，確認合併結果沒有引入差異。
- **視覺驗收第一輪**：桌機與手機的層次、留白、字體、配色、對齊、響應式、狀態與動效全數合格，沒有新增 CSS 修正。
- **視覺驗收第二輪**：重新載入後結果穩定。375px 與 1280px 的 `scrollWidth` 都等於 viewport；候選標題為 3，三家公司齊全，舊通用題不可見，`比較｜` 為 0，browser console 0 errors／warnings。最終截圖：`.screenshots/dedup-round2-desktop.png`、`.screenshots/dedup-round2-mobile.png`。
- **正式 localhost 驗收**：推送後重啟 `io.daibu.content-brain`。管理命令第一次在 `bootout` 後立刻 `bootstrap` 遇到 macOS 時序失敗；確認 plist 完整且服務未載入後，精確執行同一標籤的 `launchctl bootstrap` 與 `kickstart`，最終 `loaded=yes`、`health=yes`、只監聽 `127.0.0.1:8501`。
- **使用者畫面驗收**：實際開啟 `http://127.0.0.1:8501/選題`，頁面標題正確，顯示「候選（3）」與 Moove／Railway／Cloudflare；Railway 按鈕只有 1 個，`比較｜` 為 0，舊通用題不可見，1280px 無橫向溢出，browser console 0 errors／warnings。
- **資料保留複驗**：正式畫面驗收後直接查 SQLite，仍是 10 筆候選、6 筆空白公司，Cloudflare 1／Moove 1／Railway 2。數字來自 `ideas` 表按 `status` 與 `LOWER(TRIM(company))` 分組，證明本輪只改顯示與未來寫入規則，沒有刪除舊資料。
- **成本與限制**：沒有新依賴或付費服務，也不自動重試湊滿三則。精準比對無法自動合併 `Cloudflare` 與 `Cloudflare, Inc.` 這類別名；後續若要做別名需另有人工確認設計。

## 前一輪：macOS 登入後自動保持開啟

> 2026-08-10 更新。修復 `localhost:8501` 因手動 Streamlit 程序結束而拒絕連線，改由 macOS LaunchAgent 自動啟動與恢復。

## 本輪目標與驗收

- 使用者登入這台 Mac 後，工具自動在 `http://localhost:8501` 啟動，不需開 Terminal。
- Streamlit 程序意外停止後，由 macOS `launchd` 自動重開。
- 服務只綁 `127.0.0.1:8501`，不開放區域網路或公開網路。
- plist、啟動命令與紀錄不得含 API key；既有資料庫與使用者文件不得被修改。

## 本輪狀態

- **根因**：失敗時 `lsof` 確認 8501 沒有監聽程序；瀏覽器網址存在，但提供頁面的 Streamlit 已經結束。
- **服務**：已安裝使用者層級 LaunchAgent `io.daibu.content-brain`，設定在 `/Users/cengweiting/Library/LaunchAgents/io.daibu.content-brain.plist`。使用 `RunAtLoad=true`、`KeepAlive=true`、`ThrottleInterval=10`。
- **啟動鏈**：macOS `launchd` → 專案 `.venv/bin/streamlit` → `server.py` → `127.0.0.1:8501`。工作目錄固定為 `/Users/cengweiting/Developer/daibu-content-brain`。
- **管理命令**：新增 `.venv/bin/python -m daibu.local_service install|status|uninstall`。`uninstall` 只移除背景服務與 plist，保留 `.env`、資料庫、Logo 與紀錄。
- **秘密檔**：原本 `.env` 不存在；安裝時由 `.env.example` 建立空白 `.env`，權限實測為 `600`。沒有代填或顯示秘密，因此首頁目前會提醒尚未設定 Gemini key。
- **安全校準**：先用已知含 key 名稱的 `.env.example` 確認掃描方法有效，再掃 plist、stdout 與 stderr；三處都沒有 Gemini、Groq 或 Tavily API key 名稱。
- **第一次啟動**：安裝前健康檢查明確連線失敗；安裝後第 1 次輪詢即回應 `ok`。`launchctl` 顯示 `state=running`，`lsof` 顯示只監聽 `127.0.0.1:8501`。
- **自動恢復**：精確驗證 8501 舊 PID `14386` 的命令屬於本專案後送出 `TERM`；第 2 次輪詢出現新 PID `14439` 並恢復 `health=ok`，沒有用廣泛程序名稱終止其他程序。
- **瀏覽器驗收**：實際開啟首頁，標題為「呆一布 內容工作站」，既有「AI 新創介紹」系列與 9 則候選正常顯示；browser console 的 error／warning 均為 0。
- **TDD**：新增 10 個本機服務測試，逐一看見預期失敗後完成最小實作。涵蓋 plist、安全綁定位址、安裝前檢查、`.env` 建立與保護、launchctl 邊界、健康狀態、外來程序占用、無資料損失移除與白話錯誤訊息。
- **功能分支全套**：`481 passed, 13 deselected, 1 warning in 75.96s`。
- **合併 main 後全套**：`481 passed, 13 deselected, 1 warning in 85.44s`。13 個預設略過項目需外部服務；唯一 warning 是既有 Starlette／httpx 棄用提示。
- **紀錄**：`/Users/cengweiting/Library/Logs/DaibuContentBrain/stdout.log` 與 `stderr.log`。
- **成本與限制**：使用 macOS 內建服務，沒有訂閱費。Mac 關機、登出或睡眠時 localhost 仍不可用；若要 24 小時與他人共用，需另做雲端部署。

## 下一個使用者操作

在本機把 Gemini 與 Tavily key 填入 `.env`，再重啟背景服務。API key 不可貼進聊天；一次只引導一個本機操作。

## 前一輪：建造故事 HTML 改版

> 2026-08-06 更新。使用者回饋舊版「內容不對、看起來不好看」，經 grill-me 逐題對齊後重寫。未修改產品程式碼。

### 目標與驗收

依 `docs/superpowers/specs/2026-08-06-建造故事改版-design.md` 重寫建造故事 HTML：從八章的方法論教材，改成用一個真實功能貫穿全篇的四章教學；視覺從「只用品牌最淡幾階」改成編輯式雜誌骨架，把深色階拉回來當結構色。

### 交付狀態

- **十個拍板決策**：見設計文件第 3 節。關鍵三項是「不引用任何對話原文」、「主線用七張輪播圖產生器」、「工具定位寫成通用架構＋目前一個系列」。
- **章節**：八章砍到四章——做出來／系統／不寫歪／照著做。起點、分工、時間軸被主線吸收。
- **現場感素材**：嵌入七張 Railway 輪播成品（實測全部 1080×1350）與一組 `ia-refactor` 修前／修後對照。
- **素材驗證**：`carousel-redesign` 的 round1/round2 差異細到縮圖看不出來，不採用；`.screenshots/task10`–`task23` 共 13 個資料夾的 round1/round2 其實是明暗模式或裝置變體，不是修前／修後。判斷方法是比對兩個資料夾的檔名交集。
- **組裝方式**：改成 `docs/build-story/template.html` ＋ `build.py`。圖片以 base64 內嵌，分享後不會失效。產出檔開頭有註記，要改請動 template 後重跑 `python3 docs/build-story/build.py`。來源截圖在 `.screenshots/` 與 `.playwright-cli/`，兩者都被 gitignore，所以壓好的素材必須留在 `docs/build-story/assets/`。
- **測試**：新增 8 個、更新 2 個既有斷言（它們斷言的是被 spec 明確替換掉的舊八章結構）。建造故事測試 `13 passed`。
- **功能分支全測**：`466 passed, 13 deselected, 1 warning in 108.55s`。
- **合併 main 後全測**：`466 passed, 13 deselected, 1 warning in 102.70s`。13 個略過項是需要外部服務的契約測試；唯一 warning 是既有的 Starlette／httpx 棄用提示。
- **視覺驗收第一輪**：五項不合格——桌機右側大片死空間、窄文字欄與滿版元素對不齊、章節節奏不足、手機七張成品排 3 欄每張只剩 90px、主標把「呆一布」拆成兩行。
- **視覺驗收第二輪**：內容置中、圖片突出文字欄、章節間距 118px、手機成品改 2 欄、品牌名加 `.keep` 不換行。修完後八項檢查全過。過程中測試抓到 1280px 有 8px 橫向溢出，根因是 `.compare` 自己的 `margin` 簡寫寫在媒體查詢之後把負邊界蓋掉（媒體查詢不提高優先權）；已把突出規則移到基本規則之後。
- **產品程式與資料**：未修改 Streamlit、資料表、AI 指令或真實資料庫；本輪沒有呼叫 Tavily／Gemini。
- **抽 partial 的錯誤與修正**：從舊 HTML 抽評論工具時整個 `<script>` 都拿了，但裡面有兩個 IIFE，第一個是舊版的 journey／進度條／目次腳本。產出檔因此同時載入新舊兩套 journey 邏輯，載入與每次點擊都丟 TypeError（舊腳本找 `#reading-progress` 得到 null；舊鍵名 `sources`／`idea`／`cards` 與新版 `source`／`ideas`／`pages` 對不上）。既有測試沒抓到，因為新的 handler 先註冊先跑完。已只保留評論工具那一個 IIFE，並補上 `test_page_loads_and_interacts_without_console_errors`——先在未重建的產出檔上看到紅燈，重建後轉綠。
- **色彩 token 重整**：`--deep` 原本同時當標題文字色與實心區塊底色，深色主題下會變成淺字配淺底。已抽出 `--fill-strong`／`--on-fill-strong`／`--warn-*`／`--ok-*`。淺色模式的計算值不變，測試維持通過。
- **最終全套**：`467 passed, 13 deselected, 1 warning in 105.03s`。
- **已推送**：`origin/main` 已包含 `7e8f61f`。
- **舊正式站未更新**：`https://daibu-vibe-coding-story.workspace-249035.chatgpt.site` 仍服務舊的八章版本（已實際抓取確認，目次仍是八節）。該網域屬於 Codex 雲端工作區，這個 repo 沒有任何部署設定驅動它，本機無法重新部署。
- **新發佈位置**：`https://claude.ai/code/artifact/f9b4ff4f-1aee-4829-bde2-4ff04d9440d1`（Artifact，預設私人，要分享得從頁面的分享選單開啟）。由 `docs/build-story/build_artifact.py` 產生：拿掉 Tailwind CDN 與 Google Fonts（Artifact 沙箱擋外部連線），字型改成 Songti TC／PingFang TC 系統堆疊，並補上深色主題。實測 console 錯誤 0、外部請求 0、圖片全部載入、淺色與深色都無橫向捲動。

## 後續（同日）

- **文案人性化**（`afac739`）：依 humanizer-zh 清單過一遍正文。破折號 9 處減到 0、粗體 11 處減到 2、兩句對仗式格言的拉引句換成具體的話、拆掉 Red／Green／Refactor 的三段式排比。
- **修好內容系列的死路**（`aaf963e`）：選題頁可以刪系列，而 `seeds.load` 被 `seeds_loaded` 旗標擋住只跑一次。實測確認刪光後重開 App 系列不會回來，空狀態卻叫使用者去設定頁新增，而設定頁沒有這個功能。現在零個系列時才顯示「新增內容系列」表單當救援出口；有系列時維持隱藏，不牴觸 2026-08-01 單一系列收斂的決定。三處空狀態文案一併修正。

## 第二次改版（2026-08-07）

使用者回饋兩件事：「我作為一個完全不了解這個系統的人完全看不懂」、「我也不算是 vibe coding，比較偏 prompt engineer」。逐句讀過之後確認問題是**每一段都是結論，沒有前因後果**——例如「原本規劃的七個頁型裡有『文組生用途』和『多少錢』，在動工前被改掉」，讀者不知道七個頁型是什麼、為什麼那兩個不對。

- **範圍改成整個工具**，不再只講輪播圖那一個功能。
- **結構重排**：先看成品（七張圖移到最前面）→ 用起來是什麼樣子 → 開發方式 → 怎麼一步步做出來的 → 怎麼確認沒寫歪。
- **第三章改寫成七組「問題 → 解法」**，每組都交代當時的情況、發現什麼、怎麼解、結果。全部出自 `docs/specs/` 與 `docs/superpowers/specs/` 的背景段落。
- **新增第二章「開發方式：誰決定什麼」**：人說清楚要解決什麼 → Claude 追問並寫規格與計畫 → Codex 照計畫先寫測試再實作 → 人親手操作驗收。每輪留下規格、計畫、交接單三份檔案。
- **定位改掉**：不再用「Vibe Coding」。標題改成「我沒寫程式，怎麼做出呆一布內容工作站」，檔名一併改為 `docs/2026-08-07-呆一布內容工作站是怎麼做出來的.html`。
- **使用者刪掉兩條**：「圖片生成服務付費」與「系列太多要收斂」，理由是那不算問題。
- **補了三個名詞的白話定義**（內容系列、候選、採用），因為後面一直用到。
- 全套 `471 passed`。整頁 8598px。

## 舊建造故事交付的下一步

1. 舊網址的連結若已發給組員，等 Codex 額度恢復後重新部署原網址，兩個版本才不會並存。**刪除舊站需要在 Codex／ChatGPT 的介面上操作**，本機沒有任何憑證或設定可以碰到 `workspace-249035.chatgpt.site`。

## 前一輪：自動文案與官方 Logo 修復

> 2026-08-05 更新。這一輪修復「AI 文案產生後變空白」與「找不到新創公司官方 Logo」兩條真實使用流程。

### 目標與驗收

- 在現有 Streamlit 工作台中，AI 文案產生後要立刻顯示，且頁面重跑後不能被舊的空白編輯器內容蓋掉。
- 官方網站若把 Logo 寫成頁面內嵌 SVG，系統仍要能安全擷取、預覽，並維持「使用者確認後才保存」的產品規則。
- 搜尋備援不得把名稱只是部分相似的其他公司誤認為官方網域。
- 依 TDD 補回歸測試，完成真實 API／官網邊界驗證、兩輪桌機／手機視覺驗收與全套測試。

### 狀態

- **文案根因與修復**：Streamlit 的文字框會保留舊的瀏覽器 session 值；Gemini 已把新文案寫入 SQLite 後，舊空白值仍可能在下一次頁面重跑時覆蓋它。新增 `sync_body_editor`，資料庫正文比目前 session 更新時先同步編輯器；使用者正在打字時則保留使用者內容。
- **Logo 根因與修復**：Moove 官網的導覽 Logo 是頁面內嵌 `<svg>`，舊版只會找 `<img src>`。現在能解析安全的內嵌 SVG，移除非允許標籤／屬性並沿用既有 SVG 安全驗證，再以瀏覽器可顯示的 data URL 預覽。
- **搜尋備援**：第一次品牌搜尋沒有結果時才追加一次「公司名＋official website」查詢；網域判定改為完整 label 相符，因此 `moovecars.com` 不會再因包含 `moove` 字串而通過。
- **真實流程證據**：在實際 8501 工作台重新產生 Moove 文案，取得 492 字，來源重載後文字仍保留；Logo 候選來自 `https://www.moove.io`，頁面無應用程式錯誤或新增 console 錯誤。候選尚未保存，等待使用者肉眼確認。
- **安全與成本**：錯誤的 `moovecars.com` 候選沒有寫入資料庫；所有 Logo 仍須使用者確認才保存。只有第一次搜尋為空時才多用一次 Tavily 免費額度。
- **TDD／契約測試**：新增內嵌 SVG 擷取、空搜尋備援、相似網域拒絕、Moove 官網真實契約、正文 session 同步與 SVG data URL 預覽測試；均先看見失敗再以最小修正通過。
- **相關測試**：Logo 單元測試 `8 passed, 1 deselected`；Moove 真實官網契約 `1 passed`；相關頁面測試 `4 passed`；Python 編譯檢查通過。
- **全套測試**：最終乾淨環境 `458 passed, 13 deselected, 1 warning in 62.57s`。13 個預設略過項目是需外部服務的契約測試；唯一 warning 是既有 Starlette／httpx 棄用提示。
- **視覺驗收**：1280×800 與 375×812 各做兩輪；最終 Logo 候選卡、來源、確認／拒絕操作在桌機與手機都沒有破版，375px 的水平 overflow 為 0。最終證據：`.screenshots/logo-fix-round2-desktop.png`、`.screenshots/logo-fix-round2-mobile.png`；第一輪：`.screenshots/logo-fix-round1-desktop.png`、`.screenshots/logo-fix-round1-mobile.png`。
- **服務狀態**：本機工具維持在 `http://localhost:8501`。此專案目前沒有 production 部署流程，因此本輪不另建正式站。
- **剩餘限制**：設定頁輸入的 Tavily／Gemini key 只存在目前 Streamlit 程序；重啟工具後仍需重填。永久保存涉及秘密管理方式，未在本次功能修復中擅自改動。

### 下一步

1. 使用者在 Moove 候選卡上確認圖樣確實是官方 Logo 後，點「確認是官方 Logo」；確認前系統不會保存或拿去出圖。
2. 若要解決「重啟後 API key 消失」，另開一輪選擇安全的本機秘密保存方式，不把 key 寫進 Git。

## 前一輪：社團建造故事 HTML

> 同為 2026-08-05 交付。製作給幾乎不寫程式、主要使用 Vibe Coding 的社團組員閱讀的建造故事 HTML；未修改產品程式碼。

### 目標與驗收

依 `docs/superpowers/specs/2026-08-05-社團建造故事-html-design.md` 製作一份可獨立閱讀的繁體中文單頁 HTML，說明工具為什麼做、如何拆解、AI 與人的分工、系統資料流、TDD、真實迭代與可複製的 Vibe Coding 建造方式。

成品需沿用呆一布品牌，在 1280×800 與 375×812 各完成至少兩輪截圖自檢；不碰真實資料庫、不呼叫外部 API、不修改產品功能。

### 交付狀態

- **設計**：使用者已確認建造故事式互動網頁方向；正式規格位於 `docs/superpowers/specs/2026-08-05-社團建造故事-html-design.md`。
- **執行方式**：使用者選擇 inline；依 `docs/superpowers/plans/2026-08-05-社團建造故事-html.md` 以五個垂直 TDD 切片完成。
- **HTML 成品**：`docs/2026-08-07-呆一布內容工作站是怎麼做出來的.html`。包含八個主章節、一分鐘摘要、十個術語的漸進解釋、七步內容旅程、七階段時間軸、五張踩坑卡與八步建造公式。
- **閱讀互動**：桌機／手機章節導覽、閱讀進度、可鍵盤操作的七步內容旅程、原生技術補充、減少動態、列印版與全頁段落評論均完成。
- **內容現況**：守門線、來源分層、常青／時效分類只出現在「後來移除」的歷史脈絡；沒有寫成現有功能。
- **安全邊界**：HTML 不讀資料庫、不呼叫產品 API、不含 API key、本機絕對路徑或外連資產路徑；吉祥物與 favicon 都已內嵌。
- **HTML 測試**：`5 passed in 4.65s`。另以本機 HTTP 真實操作確認 AI 正文步驟切換成功、375px overflow 為 0、瀏覽器 console 為 0 errors；Tailwind CDN 有一則既有的 production 使用提醒。
- **功能分支全測**：`454 passed, 12 deselected, 1 warning in 69.48s`；唯一 warning 是既有 Starlette／httpx 棄用提示。
- **合併 main 後全測**：`454 passed, 12 deselected, 1 warning in 65.68s`；同一個既有棄用提示，無新增失敗。
- **視覺驗收第一輪**：主標字級被 Tailwind 基礎樣式覆蓋、桌機首屏留白過長、手機主標層級不足；已提高 selector specificity、重調字級與首屏高度並補 favicon。
- **視覺驗收第二輪**：層次、留白、字體、配色、對齊、響應式、狀態與動效全數通過。最終證據：`.screenshots/build-story-round2-desktop.png`、`.screenshots/build-story-round2-mobile.png`；第一輪證據：`.screenshots/build-story-round1-desktop.png`、`.screenshots/build-story-round1-mobile.png`。
- **產品程式與資料**：未修改 Streamlit、資料表、AI 指令或真實資料庫；本輪沒有呼叫 Tavily／Gemini。
- **公開分享網址**：`https://daibu-vibe-coding-story.workspace-249035.chatgpt.site`，只發佈這一份建造故事，不公開 private GitHub repo 的其他文件。
- **正式站驗證**：公開網址會進入 `/story`；在 375×812 實測主標正確、AI 正文步驟切換為選取狀態、內容同步更新、overflow 為 0、console 為 0 errors。唯一 warning 是 Tailwind CDN 的 production 提醒。

## 前一輪 Demo 影片交付紀錄

- **成片**：`artifacts/demo-video/edit/final.mp4`，115.4 秒、1280×720、30fps、H.264、yuv420p、無音訊、4.7 MB。SHA-256：`8c687b587baf5fea87ff79f7b7ddf9dab9fecbc736e9d7ba45415dbda15dc16c`。
- **正文畫面修正**：使用者發現第一個案例雖顯示 478 字，影片中的 textarea 卻是空白。資料庫正文完整，根因是錄製片段沒有拍到瀏覽器已繪製的文字。已只替換 36.2–45.2 秒，現在先顯示 Warp 正文開頭，再輕微捲動；沒有重跑 Tavily／Gemini。
- **真實流程**：搜尋新增 Warp idea 16；AI 初稿 478 字、查證來源 3 筆。系統找到 Warp 官網 Logo 候選，但未確認、未儲存、未拿去出圖。
- **透明備援**：影片以轉場明說 Warp Logo 等待確認，後段接已驗證的 BillionToOne idea 15，完成七頁草稿、七張圖、預覽與 ZIP 下載。
- **報告提綱**：`docs/2026-08-01-社團報告提綱.md`，可講 3–5 分鐘；另含只剩 3 分鐘與現場 API 失敗時的說法。
- **驗收證據**：`artifacts/demo-video/edit/verify/boundaries.png`、`samples.png`。正文可視回歸檢查由修正前 0.0000 升至 0.1481 並通過；3,462 幀可完整解碼、無黑格，總長與後半段時間軸未變。
- **技術驗證**：完整解碼成功；ZIP 內 7 張 PNG 均通過完整性檢查；文字產物沒有 Tavily／Gemini key；影片與字幕皆未經過設定頁。
- **資料安全**：8502 實際使用 `/private/tmp/daibu-workstation-redesign.db`。真實 `daibu.db` 錄製前後 mtime 都是 `1785650884`，未變。
- **測試**：正文修正後 `449 passed, 12 deselected, 1 warning in 43.78s`。產品程式碼未變；唯一 warning 是既有 Starlette/httpx 棄用提示。
- **已知非阻擋訊息**：Playwright console 有兩個 multipage-relative `_stcore/health`／`host-config` 404；錄影流程與畫面未受影響。

## 舊交付的分享方式

1. 把公開網址傳給社團組員，會後可直接用手機或桌機閱讀。
2. 若收到段落評論，整理後再決定是否改版；本輪成品與正式站已完成。

## 最容易踩的坑

- 現有規格與初版文件同時存在；描述現況時要以 `STATUS.md`、最新規格與實際程式為準，不能把已移除的守門線、來源分層或常青／時效分類寫成現有功能。
- 成品給非工程背景組員自讀。專有名詞第一次出現必須先講使用畫面與生活比喻，再放精準定義；主文不可變成檔案路徑導覽。
- 分享後不能依賴作者電腦的絕對路徑。吉祥物與必要 SVG 要內嵌，外部相依失效時仍須保留完整文字內容。
- 前端完成前要跑兩輪 1280×800 與 375×812 截圖自檢；只看 HTML 原始碼或指令 exit 0 不算視覺驗收。
