# TDD 實作計畫：操作驗收後的修正（Task 1–24）

回饋依據：`docs/2026-07-25-操作驗收回饋.html`（Claude 於 2026-07-25 實際操作
`codex/ia-topic-first` 分支，跑完整條流程後寫的 24 條回饋）。

## 給 Codex 的作業規則

- **嚴格 TDD、垂直切片**：一次只寫**一個**失敗測試 → 讓它綠 → 重構 → 下一個。
  禁止「先寫完 t1,t2,t3 再寫 i1,i2,i3」的水平切法。
- 每個 Task 做完就 `commit`，訊息寫清楚做了哪一刀。
- 用專案自己的環境：`.venv/bin/python`、`.venv/bin/pytest`。
- 頁面層的測試用 `streamlit.testing.v1.AppTest`（`tests/test_app_smoke.py`
  已經有完整範例：`monkeypatch.setenv("DAIBU_DB_PATH", ...)` 建臨時資料庫、
  `AppTest.from_file(...)`、再對 `app.markdown` / `app.button` 斷言）。
- 顏色與字級只能來自 `daibu/theme.py`，`pages/` 裡不得出現寫死色碼。
- 設計層疑點寫進 `docs/open-questions.md`，**不要自行更動產品方向**。

### ⚠️ 紅線變更（跟上一輪不同，請看清楚）

上一輪寫「**不准動 `daibu/theme.py`、`tests/test_theme.py`**」。

**這一輪 Task 1 必須動 `daibu/theme.py`**，因為深色模式的錯誤就在裡面
（`_adaptive_css_variables()` 用的 `light-dark()`）。解除這條限制，但下面兩件事
**仍然是紅線、一個字都不准改**：

- `LIGHT` / `DARK` 兩組色票的**數值**
- `tests/test_theme.py` 裡所有既有的對比度斷言（白字不可放在 `#6FC1CC` 上、
  主要按鈕一律深色字 `#0E0E2C`、深色模式文字不可用 `#32738F`）

Task 1 只改「這些顏色怎麼送進 CSS」，不改「顏色是什麼」。

`daibu/performance.py` 這一輪 **Task 13 會動**（`suggest()` 的門檻）。
`daibu/fetch/rss.py`、`daibu/fetch/search.py` 仍然不要動。

### 已經拍板的產品決策（不要自己改）

1. **刪除主題＝連底下的題目一起刪**，但按下去之前要明確告訴使用者會刪掉幾則。
2. **預設的 3 主題／15 來源只在資料庫全新時灌一次**，之後使用者刪掉就是刪掉了。
3. **採用與淘汰都改成一步完成、都可以復原**，另外補上「退回候選」。

### 時間戳記的處理（Task 2 的前提）

一律改存**本機時間**。使用者真實的 `daibu.db` 裡 `published_at` 全部是 `NULL`，
`created_at` 只有舊資料，**沒有需要搬遷的既有資料**，不必寫轉換程式。

基線：目前 `codex/ia-topic-first` 上 `.venv/bin/pytest -q` 為
`99 passed, 3 deselected`。每個 Task 完成後這個數字只能往上加，不能有紅燈。

---

# 階段 A — 會弄壞資料的問題（Task 1–6）

> 這六個 Task 是驗收能不能過的門檻。做完這段就先讓使用者看一次。

## Task 1 — 深色模式下彈出視窗的文字不再隱形

**問題**：`theme.py` 的色票用 `light-dark(淺, 深)` 送進 CSS 變數。
`light-dark()` 是看**元素自己的 `color-scheme`** 決定回傳哪個值，而 Streamlit 的
彈出視窗（`st.popover`）掛在 `<body>` 底下的 `#portal`，**不在 `.stApp` 裡面**。
`.stApp` 是 `color-scheme: dark`，但 `body` 是 `normal`，所以彈出視窗裡的
`var(--ink)` 回傳的是**淺色模式**的深藍 `#0E0E2C`，寫在深色底上等於隱形。

實測影響：新增主題、微調、淘汰、編輯來源這四個彈出視窗的所有欄位標籤與按鈕文字。

**紅**：`tests/test_theme.py` 新增
- `test_css_does_not_depend_on_light_dark_function`：
  `theme.css()` 產出的字串**不含** `light-dark(`。
- `test_css_defines_dark_palette_in_media_query`：
  產出的字串含 `@media (prefers-color-scheme: dark)`，且該段落內出現
  `--ink: #FAFCFE`（深色模式的 INK）。
- `test_palette_variables_are_defined_on_root_not_app`：
  `--ink` 的定義出現在 `:root {` 區塊內（讓 `#portal` 也繼承得到）。

**綠**：`daibu/theme.py`
- `_adaptive_css_variables()` 改成：`:root` 先無條件輸出 `LIGHT` 的值，
  再用 `@media (prefers-color-scheme: dark)` 覆寫成 `DARK` 的值。
- 為了讓使用者在 Streamlit 選單手動切換主題時也正確，額外加一段
  `.stApp[data-theme="dark"]`（或當下 Streamlit 實際使用的屬性——**先用瀏覽器
  檢查真實的屬性名稱再寫**，不要憑印象）的覆寫。
- `LIGHT` / `DARK` 的**數值一個都不准改**。

**驗收**
1. `.venv/bin/pytest tests/test_theme.py -q` 全綠，且既有的對比度測試沒有被改動。
2. **必做截圖驗證**：深色模式下打開「新增主題」「微調」「淘汰」「編輯來源」
   四個彈出視窗，截圖確認每一個欄位標籤都看得見。淺色模式也各截一張確認沒壞。

---

## Task 2 — 時間戳記改存本機時間

**問題**：`pipeline.set_status()` 用 SQLite 的 `CURRENT_TIMESTAMP`，那是
**世界標準時間**。實測：台灣時間 `2026-07-25 20:09` 按下「標記已發」，
資料庫存成 `2026-07-26 03:09`。台灣是 +8，所以下午 4 點以後標記的貼文都會跨到隔天。

**紅**：`tests/test_pipeline.py` 新增
- `test_publishing_records_local_time`：凍結／注入一個已知的本機時間
  （用 `monkeypatch` 換掉 `pipeline` 裡取得現在時間的函式），把一則題目標記已發，
  斷言 `published_at` 等於**本機**時間字串，而不是世界標準時間。

**綠**：`daibu/pipeline.py`
- 新增一個可被測試替換的取時間函式（例如 `def _now() -> str`，回傳
  `datetime.now().isoformat(sep=" ", timespec="seconds")`）。
- `set_status()` 標記已發時改成把 `_now()` 的結果當參數寫進去，不再用
  `CURRENT_TIMESTAMP`。

**同時**：`daibu/db.py` 的 `add_idea` 也把 `created_at` 改成同一個來源，
讓候選的建立時間不會顯示成「明天」。`tests/test_db.py` 補一個對應的斷言。

**驗收**：`tests/test_pipeline.py`、`tests/test_db.py` 全綠。

---

## Task 3 — 「本週已發」算得出剛剛發的那篇

**問題**：`overview.py` 的 `_published_this_week()` 把資料庫的值當日期，
拿去跟本機的 `date.today()` 比。Task 2 修好之後這裡應該自然會對，但要有測試
把行為釘住，避免以後又漂掉。

**紅**：`tests/test_app_smoke.py` 新增
- `test_home_counts_a_post_published_today`：建一則題目，用 `pipeline.set_status`
  標記已發（時間注入成「今天晚上 20:09」），跑 `AppTest`，
  斷言「本週已發」的數字是 `1`。
- `test_home_excludes_post_published_last_week`：同樣的做法，時間設成上週，
  斷言不被計入。

**綠**：確認 `_published_this_week()` 在 Task 2 之後就正確；若還有偏差再修它。
不要為了讓測試過而改測試。

**驗收**：`tests/test_app_smoke.py` 全綠。

---

## Task 4 — 刪除主題時連題目一起刪，並在刪之前講清楚

**問題**：`db.delete_theme()` 只清掉 `themes` 與 `theme_sources`，
**完全沒動 `ideas`**。實測刪掉一個主題後產生了 9 則孤兒題目，
它們在選題頁永遠找不到，卻還被概覽的「待你決策」算進去——
造成同一個畫面上「待你決策 8」和表格「候選 0」互相矛盾。

**紅（切片 1）**：`tests/test_db.py` 新增
- `test_delete_theme_also_deletes_its_ideas`：建一個主題、掛三則題目，
  刪掉主題後斷言 `ideas` 表裡不再有指向它的資料。
- `test_delete_theme_leaves_other_themes_ideas_untouched`：另一個主題的題目不受影響。

**綠（切片 1）**：`daibu/db.py` 的 `delete_theme()` 加上刪除 `ideas` 的敘述。
注意 `performance` 有外鍵指向 `ideas`，**要先刪 `performance` 再刪 `ideas`**，
否則會留下第二種孤兒。

**紅（切片 2）**：`tests/test_db.py` 新增
- `test_count_theme_content_reports_what_will_be_deleted`：
  一個新函式 `db.count_theme_content(conn, theme_id)` 回傳
  `{"候選": 8, "採用": 0, "已發": 1}` 這種形狀。

**綠（切片 2）**：在 `daibu/db.py` 實作它。

**紅（切片 3）**：`tests/test_app_smoke.py` 新增
- `test_delete_theme_warns_how_many_ideas_will_go`：主題底下有題目時，
  展開「主題設定」後畫面上要出現會刪掉幾則的文字。

**綠（切片 3）**：`pages/1_選題.py` 的刪除區塊改成：先呼叫 `count_theme_content`，
把「這會一併刪掉 8 則候選、1 則已發，且無法復原」用 `st.warning` 顯示出來，
再讓使用者勾確認框。

**驗收**：三個測試檔全綠；手動刪一個有題目的主題，確認概覽的數字跟著一起降。

---

## Task 5 — 預設資料只在資料庫全新時灌一次

**問題**：`seeds.load()` 在每一次 `connect_app_db()`（也就是每次頁面重跑）都會執行，
只要名字不在就補回去。實測：刪掉「AI 新創介紹」，重新整理它就用新編號復活；
刪掉「TechCrunch」來源，重新整理它也回來了（而且綁定關係沒回來，變成沒人用的孤兒）。
等於 15 個預設來源使用者一個都刪不掉。

**紅**：`tests/test_seeds.py` 新增
- `test_load_seeds_only_when_database_is_brand_new`：對一個全新資料庫呼叫
  `seeds.load()`，斷言灌入 3 主題 15 來源；**再刪掉其中一個主題與一個來源、
  再呼叫一次 `seeds.load()`**，斷言它們**沒有**被補回來。
- `test_load_is_still_idempotent_on_fresh_database`：對全新資料庫連續呼叫兩次，
  不會產生重複資料。

**綠**：`daibu/seeds.py`
- 在 `config` 表寫一個旗標（例如 `seeds_loaded` = `"1"`），`load()` 開頭先檢查，
  已經灌過就直接返回。
- **搬遷考量**：使用者現有的 `daibu.db` 已經有資料但還沒有這個旗標。
  `db.init_schema()` 要加一段：如果 `themes` 表已經有資料但旗標不存在，
  就直接把旗標補上（視為已灌過），避免升級後又被灌一次。
  `tests/test_db_migration.py` 補一個對應的測試。

**驗收**：`tests/test_seeds.py`、`tests/test_db_migration.py` 全綠；
拿使用者真實 `daibu.db` 的**複本**跑一次升級，確認 3 主題 15 來源都還在、沒有變成 6 個。

---

## Task 6 — 正文草稿不會因為切換主題就消失

**問題**：在正文框打字後切到別的主題再切回來，內容全部消失。
實測寫了 134 字，切一次就沒了，沒有警告也沒有自動儲存。
對一個把「寫正文」當核心流程的工具，這是最痛的資料遺失。

**紅**：`tests/test_app_smoke.py` 新增
- `test_body_draft_survives_switching_themes`：建兩個主題，
  在主題 A 的已採用題目正文框輸入文字（`AppTest` 的 `text_area` 可以設值），
  切換到主題 B 再切回 A，斷言正文框裡的文字還在。

**綠**：`pages/1_選題.py`
- 正文 `text_area` 加上 `on_change` 回呼，直接把內容寫進資料庫
  （沿用 `pipeline.update_body`）。這比只存在畫面狀態更可靠——重新整理頁面、
  甚至關掉重開都還在。
- 「儲存正文」按鈕保留（明確存檔的心理安全感），但下方加一行
  「已自動儲存於 HH:MM」的說明。

**驗收**：測試全綠；手動打字後切主題、重新整理頁面，兩種情況內容都還在。

---

# 階段 B — 卡住操作的地方（Task 7–14）

## Task 7 — 左欄看得出來現在選的是哪個主題

**問題**：三顆主題按鈕的背景色與邊框色完全一樣（都是 `rgb(17,17,54)` /
`rgb(42,42,74)`）。點下去那一瞬間的變化只是瀏覽器的鍵盤焦點外框，
滑鼠移開就沒了。這是主從式介面最基本的一件事。

**紅**：`tests/test_app_smoke.py` 新增
- `test_selected_theme_is_visually_marked`：選了第二個主題之後，
  畫面上只有那一個主題帶有選中標記（例如 button 的 `type="primary"`，
  或一個 `data-selected` 的標記文字）。

**綠**：`pages/1_選題.py`
- 主題按鈕依 `st.session_state.selected_theme_id` 決定 `type`：
  選中的用 `"primary"`、其餘 `"secondary"`。
- 若 `primary` 的藍綠底太搶眼，改成在 `daibu/theme.py` 加一個
  `.theme-item--selected` 的樣式（左側 3px 品牌色條 + 淡底），
  顏色只能取自既有色票。

**驗收**：測試全綠；截圖確認選中狀態明顯，且點到其他地方之後仍然看得出來。

---

## Task 8 — 主題底下的說明文字貼回自己的按鈕

**問題**：實測間距——按鈕到自己的說明文字是 **16px**，
說明文字到下一顆按鈕是 **0px**。視覺分組是相反的，
「週一 · 13 來源 · 0 候選」讀起來像在描述下面那顆主題。這會讓人讀錯資料。

**紅**：`tests/test_theme.py` 新增
- `test_theme_list_caption_hugs_its_button`：`theme.css()` 內含一條把
  主題清單說明文字上緣間距歸零、下緣間距加大的規則
  （例如 `.theme-item__meta { margin-top: 0.25rem; margin-bottom: 0.9rem; }`）。

**綠**：`daibu/theme.py` 加樣式；`pages/1_選題.py` 把每個主題的按鈕與說明文字
包在一個帶 class 的容器內。

**驗收**：測試全綠；**截圖量測**確認「按鈕→自己的說明」小於「說明→下一顆按鈕」。

---

## Task 9 — 每個動作都看得到成功回饋

**問題**：儲存正文、儲存微調、儲存來源綁定、標記已發、儲存成效——
程式裡都寫了 `st.success(...)`，但緊接著就 `st.rerun()`，
訊息在畫面上還來不及出現就被清掉。實測按「儲存正文」畫面完全沒反應
（其實存好了），按「採用」卡片無聲消失。

**紅**：`tests/test_app_smoke.py` 新增
- `test_adopting_shows_a_toast`：按下「採用」之後，`AppTest` 的 toast 集合
  裡出現對應訊息。

**綠**：把 `pages/` 與 `daibu/overview.py` 裡所有「`st.success` 後面接
`st.rerun()`」的地方改用 `st.toast(...)`（它能撐過重跑）。
沒有跟著 `st.rerun()` 的 `st.success` 可以留著。

**驗收**：測試全綠；手動走一次採用 → 儲存正文 → 標記已發 → 儲存成效，
每一步都要看得到提示。

---

## Task 10 — 概覽的行動按鈕直接帶到有候選的主題

**問題**：概覽說「你有 8 則候選等你決定」，按下「前往選題工作台」，
落點卻是第一個主題（候選 0），要自己一個一個點過去找。
這顆按鈕的價值就是省下找東西的時間。

另外選題頁的空狀態文案寫「按**左邊**的按鈕讓 AI 先整理一輪」，
但「產生候選」在**上方**，左邊是主題清單。

**紅（切片 1）**：`tests/test_app_smoke.py` 新增
- `test_home_cta_targets_the_theme_with_candidates`：兩個主題、候選只在第二個，
  按下概覽的行動按鈕後，選題頁顯示的是第二個主題的工作區。

**綠（切片 1）**：`daibu/overview.py` 在切頁前先設好
`st.session_state.selected_theme_id`，指向候選數最多的主題。
按鈕文字也一併改成指名道姓，例如「去看『AI 新創介紹』的 8 則」。

**紅（切片 2）**：`tests/test_app_smoke.py` 新增
- `test_empty_candidate_state_points_at_the_right_button`：
  空狀態文字不含「左邊」，改成指向上方的「產生候選」。

**綠（切片 2）**：改 `pages/1_選題.py` 的文案。

**驗收**：兩個測試全綠。

---

## Task 11 — 採用與淘汰都一步完成、都可以復原

**問題**：採用按一下就完成、無法反悔；淘汰要先展開彈出視窗、勾確認框、
再按確認淘汰。但 AI 一次產 3–8 則、通常只採用 1–2 則，
**淘汰的次數是採用的好幾倍**。頻繁又低風險的動作被設成最麻煩，
罕見又不可逆的動作被設成最容易，方向剛好相反。

**紅（切片 1）**：`tests/test_app_smoke.py` 新增
- `test_rejecting_takes_a_single_click`：候選卡片上的「淘汰」是一顆直接執行的
  按鈕（不是彈出視窗），按一下該則就從候選清單消失。

**綠（切片 1）**：`pages/1_選題.py` 把淘汰的 `st.popover` ＋ 勾選框拆掉，
改成一顆普通按鈕直接呼叫 `pipeline.set_status(..., pipeline.REJECTED)`。

**紅（切片 2）**：`tests/test_pipeline.py` 新增
- `test_restore_rejected_idea_back_to_candidate`：一個新函式
  `pipeline.restore(conn, idea_id)` 把「已淘汰」改回「候選」。

**綠（切片 2）**：在 `daibu/pipeline.py` 實作。

**紅（切片 3）**：`tests/test_app_smoke.py` 新增
- `test_rejecting_offers_an_undo`：淘汰之後畫面上出現可以復原的入口。

**綠（切片 3）**：`pages/1_選題.py` 淘汰後用 `st.toast` 提示，
並在候選區上方顯示一顆「復原剛剛淘汰的『標題』」按鈕
（把最後一次淘汰的題目編號記在 `st.session_state`）。

**驗收**：三個測試全綠；手動淘汰一則再復原，確認回到候選清單。

---

## Task 12 — 採用錯了可以退回候選

**問題**：採用是一步完成且沒有確認。點錯之後**完全無解**——
已採用的題目沒有退回候選的入口，也沒有刪除的入口，會永遠卡在那裡。
而已發之後同樣沒有任何辦法退回。

**紅**：`tests/test_app_smoke.py` 新增
- `test_adopted_idea_can_go_back_to_candidate`：已採用的題目展開後有
  「退回候選」，按下去之後它回到候選區。

**綠**
- `pages/1_選題.py` 在每則已採用題目的展開區加一顆「退回候選」。
- 已發區也加一顆「退回已採用」（放在展開區內、樣式低調）。
- 注意 `pipeline.set_status()` 目前在非「已發」狀態時會把 `published_at`
  清成 `NULL`，退回時這是對的行為，不用改。

**驗收**：測試全綠。

---

## Task 13 — 成效表單存完會清空，建議的門檻改看貼文數

**問題一**：存完成效之後欄位數字原封不動留著（讚 248、觸及 5120），
下一筆很容易誤帶上一篇的數字。而且成效紀錄目前只能新增、無法修改或刪除。

**問題二**：`performance.suggest()` 的門檻是 `len(ranked) == 1`，也就是看**主題數**。
實測兩個主題各只有 **1 篇**貼文，它就下結論「表現最好的是 AI 新創介紹，
下週優先補強 AI 近期大事」。單一樣本不該推出決策級的結論。

**紅（切片 1）**：`tests/test_performance.py` 新增
- `test_suggest_stays_cautious_when_each_theme_has_one_post`：
  兩個主題、每個 `posts` 都是 1，回傳的句子要包含「資料還太少」之類的但書，
  不可以出現「優先補強」。
- `test_suggest_compares_when_there_is_enough_data`：每個主題 `posts` 都 ≥ 3 時，
  才給出比較型的建議。

**綠**：`daibu/performance.py` 的 `suggest()` 改成看 `posts` 總數
（建議門檻：至少要有一個主題累積 3 篇以上才給比較型結論），
不足時回傳保守版本並註明目前各有幾篇。

**紅（切片 2）**：`tests/test_app_smoke.py` 新增
- `test_performance_form_clears_after_submit`：送出後三個數字欄位回到 0。

**綠（切片 2）**：`pages/2_成效.py` 送出後清掉 `st.session_state` 裡對應的鍵。

**驗收**：兩個測試檔全綠。

---

## Task 14 — 來源庫改成一列一個，並看得出誰在用

**問題**：每個來源佔三行（名稱、完整網址、「編輯 ○○○」按鈕），
15 個來源要捲約 2500px。網址還會在中間硬斷成兩行
（`…ithome.com.tw/tags/a` 換行 `i`），按鈕又把名字重複一次。
最關鍵的是**看不出這個來源被哪些主題使用**，所以按刪除時不知道會影響什麼。

**紅（切片 1）**：`tests/test_db.py` 新增
- `test_count_themes_using_source`：新函式 `db.count_themes_using_source(conn, source_id)`
  回傳使用中的主題數。

**綠（切片 1）**：在 `daibu/db.py` 實作。

**紅（切片 2）**：`tests/test_app_smoke.py` 新增
- `test_source_library_shows_usage_count`：來源庫展開後，
  每個來源旁邊出現「N 個主題在用」。

**綠（切片 2）**：`pages/1_選題.py` 的來源庫改版：
- 一列一個來源：名稱 ＋ 抓取方式標籤 ＋「N 個主題在用」＋ 一顆小的編輯入口。
- 網址只顯示網域（去掉通訊協定與路徑），完整網址放在編輯區裡。
- 刪除來源前顯示「這個來源正被 N 個主題使用」。

**驗收**：兩個測試全綠；截圖確認單一來源的高度從約 165px 降到 60px 以內。

---

# 階段 C — 視覺呈現（Task 15–22）

> 這一段大多是 CSS。純樣式的 Task 用 `tests/test_theme.py` 既有的
> 「斷言 `theme.css()` 產出的字串包含某條規則」寫法當紅燈，
> **並且每一個 Task 都要跑桌機 1280×800 與手機 375×812 的截圖自檢**。

## Task 15 — 左欄改成固定跟隨，不再留下大片空白

**問題**：左欄內容約 700px 就結束，右欄候選卡片可以延伸到 2200px 以上。
中間那一大段左邊完全是空的，而且主題清單會跟著捲出畫面外，
想換主題得整個捲回最上面。

**紅**：`tests/test_theme.py` 新增
- `test_context_column_sticks_on_desktop`：`theme.css()` 含
  `.context-column { position: sticky; top: ...; }`，
  且該規則被包在只對寬螢幕生效的媒體查詢內（手機不要 sticky）。

**綠**：`daibu/theme.py` 加樣式；`pages/1_選題.py` 的左欄容器掛上該 class。
`max-height` 要設好並允許內部捲動，避免左欄比視窗還高時卡住。

**驗收**：測試全綠；桌機截圖確認捲到底時主題清單仍在畫面上；
手機截圖確認沒有變成卡住的浮動區塊。

---

## Task 16 — 行事曆七格高度一致

**問題**：實測七張卡片高度是 `135 / 109 / **212** / 109 / 135 / 135 / 109`。
週三因為主題名長（「本週熱門 Claude/Codex Skill」）被擠成五行，整排歪掉。
「週六 · 今天」也因為多了「今天」兩個字被折行。

**紅（切片 1）**：`tests/test_app_smoke.py` 或新的 `tests/test_overview.py` 新增
- `test_calendar_truncates_long_theme_names`：新函式（放在 `daibu/overview.py`）
  把超過 N 個字的主題名截成「本週熱門 Cl…」，短的維持原樣。

**綠（切片 1）**：實作截斷函式並在行事曆使用，完整名稱放 `title` 屬性。

**紅（切片 2）**：`tests/test_theme.py` 新增
- `test_calendar_cards_have_fixed_height`：`theme.css()` 的 `.daibu-card`
  （或行事曆專用 class）含固定高度規則。

**綠（切片 2）**：`daibu/theme.py` 加樣式。順帶把「空檔」淡化、
把「今天」改成用色條標示而不是靠多印兩個字。

**驗收**：兩個測試全綠；截圖確認七格齊平。

---

## Task 17 — 「下一步」與「下週建議」卡片建立層次

**問題**：實測「下一步」三個字是 `16px / 字重 600`，
真正的內容「你有 8 則候選等你決定」是 `16px / 字重 400`——**只差字重、字級相同**。
這張橘色大卡（820×109）視覺很搶眼，但裡面最重要的那句話一點都不突出。
而且「前往選題工作台」按鈕掉在卡片外面，看起來不像是這張卡的行動按鈕。

**紅**：`tests/test_theme.py` 新增
- `test_suggestion_card_label_is_smaller_than_its_message`：
  `theme.css()` 內 `.suggestion-card__label` 的字級明顯小於
  `.suggestion-card__message`（至少差兩級，可直接斷言兩個具體數值）。

**綠**
- `daibu/theme.py` 加這兩個 class。標籤改小、加字距、降低不透明度；
  訊息放大加粗。
- `daibu/overview.py` 與 `pages/2_成效.py` 的卡片標記改用新 class，
  並把行動按鈕**放進卡片內**（用 `st.container` 包起來，或直接把按鈕
  移到卡片下緣、去掉中間的縫隙）。

**驗收**：測試全綠；截圖確認一眼就能讀到重點句。

---

## Task 18 — 成效圖表改中文軸、橫向標籤，資料少時只顯示表格

**問題**：縱軸寫 `avg_engagement`、橫軸寫 `theme`，是資料庫欄位名直接跑到畫面上。
中文主題名被旋轉 90 度變成直排，明明橫向空間很夠。
只有一筆資料時一根柱子橫跨 440px 幾乎填滿圖表區。
而且下面緊接著就是一張欄位名正確的中文表格——同一份資料講了兩次，圖還比表難讀。

**紅**：`tests/test_app_smoke.py` 新增
- `test_performance_hides_chart_when_data_is_thin`：只有一個主題有成效時，
  畫面上不出現圖表，只有表格。
- `test_performance_chart_axes_are_chinese`：資料足夠時圖表的軸標題是
  「平均互動」與「主題」，不是英文欄位名。

**綠**：`pages/2_成效.py`
- 主題數少於 2 時不畫圖，只留表格（表格的中文欄位名已經是對的）。
- 畫圖時把資料的欄位改名成中文再餵給圖表，或改用
  `st.bar_chart(..., x_label=..., y_label=...)`（**先確認目前 Streamlit 版本
  支援哪些參數再寫**）。
- 標籤方向：若 `st.bar_chart` 無法控制，改用 `st.altair_chart` 明確設定
  `labelAngle=0`。

**驗收**：測試全綠；截圖確認軸是中文、主題名橫排。

---

## Task 19 — 正文編輯區加高、加字數、空白時不能標記已發

**問題**：正文編輯框只有 **495×92**（約三行）。打了 134 字就開始在框裡上下捲。
「Ctrl+Enter to apply」的提示直接壓在最後一行文字上，而且整個介面只有這句是英文。
欄位標籤是「正文｜別再煩惱企劃案！AI新創如何幫你從「發呆」到「發光」的點子加速器」，
把整個標題重複貼上來（標題在展開區的標頭已經出現過一次）。
另外「標記已發」在正文完全空白時也照樣可以按，而且它是視覺上最搶眼的按鈕。

**紅（切片 1）**：`tests/test_app_smoke.py` 新增
- `test_publish_is_disabled_when_body_is_empty`：正文空白時「標記已發」是停用狀態。

**綠（切片 1）**：`pages/1_選題.py` 依正文內容決定 `disabled`；
把主要按鈕從「標記已發」換成「儲存正文」（`type="primary"` 給儲存）。

**紅（切片 2）**：新增
- `test_body_editor_shows_character_count`：畫面上出現字數，
  例如「128 字 · Threads 還可寫 372」。

**綠（切片 2）**：加字數顯示（Threads 上限 500、Instagram 2200，
上限值放在一個具名常數裡）。

**同時**：`text_area` 的 `label` 改成「正文」（不再重複標題）、
`height` 加大到約 240px。

**驗收**：兩個測試全綠；截圖確認寫 130 字時不需要在框內捲動、提示不壓字。

---

## Task 20 — 關掉 Deploy 按鈕，內容不再穿過頂部橫幅

**問題**：頂部橫幅設成透明背景但固定不動，內容往上捲會直接穿過去，
候選標題和右上角的「Deploy」「⋮」重疊。對一個只在自己電腦上跑的工具，
Deploy 按鈕也沒有意義。

**紅**：`tests/test_ui.py` 新增
- `test_toolbar_mode_is_minimal`：`.streamlit/config.toml` 的
  `[client] toolbarMode` 是 `"minimal"`。
- `tests/test_theme.py` 新增 `test_header_is_not_transparent`：
  `theme.css()` 裡 `[data-testid="stHeader"]` 的背景不是 `transparent`
  （改成 canvas 色或加毛玻璃）。

**綠**：改 `.streamlit/config.toml` 與 `daibu/theme.py`。

**驗收**：兩個測試全綠；截圖確認捲動時標題不再和任何東西重疊。

---

## Task 21 — 設定頁限寬、標籤全中文、看得出金鑰有沒有設定

**問題**：「模型」欄位橫跨整個內容區（約 1000px）只為了裝 `gemini-2.5-flash`。
標籤是半中半英（「LLM provider」「搜尋 provider」）。三個金鑰欄位不管選哪個
服務商都全部顯示。**最重要的是看不出金鑰目前到底有沒有設定**——
實測是有的（產生候選成功了），但畫面上只寫「已設環境變數時可留空」。
另外「搜尋 provider」只有一個選項卻做成下拉選單。

**紅（切片 1）**：`tests/test_app_smoke.py` 新增
- `test_settings_reports_key_status`：環境變數有金鑰時畫面顯示「已設定」，
  沒有時顯示「尚未設定」。

**綠（切片 1）**：`pages/3_設定.py` 加狀態顯示（**只顯示有沒有設定，
絕對不要把金鑰內容印出來**）。

**紅（切片 2）**：新增
- `test_settings_only_shows_the_active_provider_key`：選 gemini 時畫面上
  沒有 Groq 的金鑰欄位。

**綠（切片 2）**：依所選服務商決定顯示哪個金鑰欄位。

**同時**
- 標籤改成中文：「AI 服務商」「模型」「搜尋服務」「Gemini 金鑰」…
- 表單限寬約 560px（用 `st.columns` 或在 `theme.py` 加一個 `.settings-form` 限寬）。
- 「搜尋服務」只有一個選項時改成純文字顯示，不用下拉選單。

**驗收**：兩個測試全綠；截圖確認欄位寬度合理。

---

## Task 22 — 候選卡片標題降一級，新產生的排在前面並標示

**問題**：卡片標題用 `1.375rem / 字重 700`，兩行就佔掉半張卡，
八則連著看視覺重量幾乎一樣，很難快速掃過去挑。
另外新產生的候選排在清單**最下面**，按完「產生候選」還要捲到底才看得到，
而且沒有任何「這三則是新的」的標示。

**紅（切片 1）**：`tests/test_theme.py` 新增
- `test_candidate_title_is_one_level_below_section_heading`：
  `.candidate-card__title` 的字級小於區段標題。

**綠（切片 1）**：`daibu/theme.py` 把標題降到 `TYPE_SCALE[3]`，
並把切入角度那行的對比稍微提高（它才是判斷依據）。

**紅（切片 2）**：`tests/test_db.py` 新增
- `test_get_ideas_returns_newest_first`：`db.get_ideas` 依建立時間新到舊排序。

**綠（切片 2）**：改排序；`pages/1_選題.py` 對最近一次產生的那批加上
「新」的標記（把剛產生的編號記在 `st.session_state`）。

**驗收**：兩個測試全綠；截圖確認八則候選可以快速掃讀。

---

# 階段 D — 手機（Task 23）

## Task 23 — 手機版的三個調整

**問題**：375×812 沒有破版也沒有橫向捲動（這點是好的），但：
1. 點主題按鈕之後畫面不會跳到工作區，看起來像什麼都沒發生，要自己往下捲。
2. 三個待辦數字疊成直排、各佔約 190px 高，一屏只看得到一個半。
   這三個數字的價值就在於互相對照，拆開來看就沒意義了。
3. 「前往選題工作台」只有內容寬度、貼在左邊。

**紅**：`tests/test_theme.py` 新增
- `test_metrics_stay_in_one_row_on_mobile`：`theme.css()` 內有針對
  `max-width: 700px` 的規則讓待辦數字維持三欄（縮小字級），
  而不是讓 Streamlit 自動堆疊。

**綠**
- `daibu/theme.py` 加手機版規則：待辦數字三欄並排、數字字級縮小、
  主要行動按鈕滿寬。
- `pages/1_選題.py` 選完主題後捲到工作區
  （Streamlit 沒有內建捲動 API，用一個帶 `id` 的錨點 ＋ `st.markdown`
  注入一小段捲動指令；**若做不到就寫進 `docs/open-questions.md` 回報，
  不要硬幹**）。
- 手機版把頁面說明那一行收掉。

**驗收**：測試全綠；375×812 截圖確認三個數字在同一排、
選主題後畫面有跳到工作區。

---

# 階段 E — 清理（Task 24）

## Task 24 — 清掉移除功能留下的殘留物

> **這個 Task 一定要放到最後做**，等前面全部穩定、測試全綠之後再動，
> 免得清理跟修正混在一起難以定位問題。

**問題**
- `daibu/theme.py` 有八組樣式在四個頁面裡一次都沒被用到：
  `score-badge`（守門線分數）、`pipeline-bar`、`pipeline-legend`（流水線頁）、
  `hero-lockup`、`today-stat`（舊的吉祥物首頁）、`kanban-card-title`、
  `status-chip`、`attention-chip`。
- `daibu/ui.py` 有一個 `DEFAULT_GATE_LINE` 常數，定義了但沒有任何地方使用。
- 使用者的 `daibu.db` 的 `config` 表還留著一筆 `gate_line`，程式已經不讀它了。

**紅**：`tests/test_theme.py` 新增
- `test_css_has_no_unused_classes`：讀取 `pages/*.py`、`daibu/overview.py`、
  `daibu/ui.py` 的原始碼，斷言 `theme.css()` 定義的每一個 class 名稱
  至少出現在其中一個檔案裡。（先寫這個測試會紅，正好證明有八組沒用到。）

**綠**
- 刪掉那八組樣式（**Task 15–23 新加的 class 要記得算進去，別誤刪**）。
- 刪掉 `ui.py` 的 `DEFAULT_GATE_LINE`。
- `db.init_schema()` 加一段搬遷：把 `config` 表的 `gate_line` 刪掉，
  `tests/test_db_migration.py` 補測試。

**驗收**：`.venv/bin/pytest -q` 全綠；用使用者 `daibu.db` 的**複本**跑一次升級，
確認資料完好、`gate_line` 已消失。

---

# 最後的整體驗收

全部 24 個 Task 做完之後：

1. `.venv/bin/pytest -q` 全綠，且測試數明顯多於基線的 99。
2. **完整的截圖自檢兩輪**，四個頁面 × 兩種配色模式 × 兩個尺寸
   （桌機 1280×800、手機 375×812），共 16 張。
   **每一個彈出視窗都要打開來截**——上一輪就是漏了這一步才讓 Task 1 的錯誤過關。
3. 拿使用者真實 `daibu.db` 的**複本**（不要動原檔）跑一次完整流程：
   挑主題 → 產候選 → 採用 → 寫正文 → 標記已發 → 回填成效 → 刪一個主題，
   確認每一步的數字都對得起來。
4. 把結果整理進 `HANDOFF.md` 回報。
