# TDD 實作計畫：選題為核心的資訊架構重整

設計依據：`docs/specs/2026-07-24-選題為核心的資訊架構重整-design.md`

## 給 Codex 的作業規則

- **嚴格 TDD、垂直切片**：一次只寫**一個**失敗測試 → 讓它綠 → 重構 → 下一個。
  禁止「先寫完 t1,t2,t3 再寫 i1,i2,i3」的水平切法。
- 每個 Task 做完就 `commit`，訊息寫清楚做了哪一刀。
- 用專案自己的環境：`.venv/bin/python`、`.venv/bin/pytest`。
- **不准動**：`daibu/theme.py`、`tests/test_theme.py`、`daibu/performance.py`、
  `daibu/fetch/rss.py`、`daibu/fetch/search.py`。
- 顏色與字級只能來自 `daibu/theme.py`，`pages/` 裡不得出現寫死色碼。
- 設計層疑點寫進 `docs/open-questions.md`，**不要自行更動產品方向**。
- 分支 `refactor/ia-topic-first` 的 commit `b6b66bc` 是 Claude 越權寫的探路稿
  （Task 1–3 大致等價），**可參考、可無視，不要直接 merge**。

基線：目前 `main` 上 `.venv/bin/pytest -q` 為 `68 passed, 3 deselected`。

---

## Task 1 — `Idea` 拿掉守門線欄位

**紅**：`tests/test_llm.py`
- 改 `test_parse_ideas_tolerates_codefence`：JSON 不含 `gate_score`／`gate_reason`，
  斷言 `title`／`angle`／`source_url` 正確。
- 新增 `test_parse_ideas_ignores_leftover_gate_fields`：舊格式 JSON（仍含
  `gate_score`）餵進去也不會爆，且產出的 `Idea` 沒有 `gate_score` 屬性。

**綠**
- `daibu/llm/base.py`：`Idea` 只留 `title`／`angle`／`source_url`。
- `daibu/llm/prompt.py`：`parse_ideas` 不再讀 gate 欄位。

**驗收**：`.venv/bin/pytest tests/test_llm.py -q` 全綠。

---

## Task 2 — `prompt.build` 拿掉 `gate_line` 與 `kind`

**紅**：`tests/test_llm.py`
- 改 `test_build_prompt_contains_product_context`：呼叫時不傳 `gate_line`、不傳
  `kind`。
- 新增 `test_build_prompt_no_longer_mentions_gate_line`：產出的文字不含「守門線」
  也不含 `gate_score`。

**綠**
- `prompt.build(theme_name, materials, n)`：移除 `gate_line` 段落、移除
  「主題類型」行、移除「gate_score 必須是 0–100」與 evergreen/timely 那兩條要求。
- 要求清單改為：文組視角、有素材時必須填 `source_url`、只輸出 JSON 陣列、
  每個物件只含 `title`／`angle`／`source_url`。

**驗收**：`tests/test_llm.py` 全綠。

---

## Task 3 — 兩個 provider 的簽名同步

**紅**：`tests/test_llm.py` 四個 provider 測試改成
`provider.generate_ideas(theme_name, materials, n)`。

**綠**：`daibu/llm/gemini.py`、`daibu/llm/groq.py`、`base.LLMProvider` protocol
同步移除 `kind` 與 `gate_line`。

**同時**：`tests/test_llm_contract.py` 一併更新（它是 `contract` 標記，平常被
`pytest.ini` 排除，但不能留著壞掉的呼叫）。

**驗收**：`tests/test_llm.py` 全綠；
`.venv/bin/pytest -m contract --collect-only` 不報錯。

---

## Task 4 — `ideas` 表拿掉守門線欄位

**紅**：`tests/test_db.py`
- 改 `test_add_and_get_candidate_idea`：用新的 `Idea(...)` 三參數建構，斷言
  `source_url` 正確且 `not hasattr(ideas[0], "gate_score")`。
- 新增 `test_ideas_table_has_no_gate_columns`：`PRAGMA table_info(ideas)` 不含
  `gate_score`／`gate_reason`。

**綠**
- `daibu/db.py`：`init_schema` 的 `ideas` 建表移除兩欄；`add_idea` 的 INSERT 與
  `get_ideas` 的 SELECT 對應調整。
- `daibu/models.py`：`StoredIdea` 移除兩欄。

**驗收**：`tests/test_db.py` 全綠。

---

## Task 5 — `ideas` 新增 `published_at`

**紅**：`tests/test_pipeline.py`
- 新增 `test_marking_published_records_the_time`：`set_status(..., "已發")` 後
  該筆 `published_at` 不為 None。
- 新增 `test_moving_back_from_published_clears_the_time`：從已發改回採用後，
  `published_at` 變回 None。

**綠**
- `init_schema` 的 `ideas` 加 `published_at TEXT`。
- `StoredIdea` 加 `published_at: str | None`，`get_ideas` 一併讀出。
- `pipeline.set_status`：目標為 `已發` 時寫入 `CURRENT_TIMESTAMP`，否則寫 NULL。

**驗收**：`tests/test_pipeline.py` 全綠。

---

## Task 6 — 狀態收成三段＋「已淘汰」

**紅**：`tests/test_pipeline.py`
- 新增 `test_statuses_are_the_three_visible_stages`：
  `pipeline.STATUSES == ["候選", "採用", "已發"]`。
- 新增 `test_rejected_is_accepted_but_not_a_visible_stage`：
  `set_status(..., pipeline.REJECTED)` 不拋錯，且 `REJECTED not in STATUSES`。
- 既有的 `test_set_status_rejects_unknown_value` 保持綠。

**綠**：`daibu/pipeline.py` 定義 `STATUSES`／`REJECTED`／`ALL_STATUSES`，
`set_status` 改用 `ALL_STATUSES` 驗證。

**驗收**：`tests/test_pipeline.py` 全綠。

---

## Task 7 — 主題直接綁具體來源

**紅**：`tests/test_db.py`
- `test_add_and_get_theme_keeps_its_bound_sources`：建兩個來源，建主題時帶
  `source_ids=[a, b]`，讀回來 `source_ids == [a, b]`。
- `test_update_theme_replaces_its_bound_sources`：改綁後只剩新的。
- `test_deleting_a_source_unbinds_it_from_themes`：刪來源後，主題的
  `source_ids` 不再含它。
- `test_init_schema_creates_all_product_tables`：表清單加入 `theme_sources`。
- 其餘既有測試改成新的 `Theme(...)`／`Source(...)` 建構子。

**綠**
- `daibu/models.py`：`Theme` 的 `source_layers` → `source_ids: list[int]`、
  移除 `kind`；`Source` 移除 `layer`。
- `daibu/db.py`：建 `theme_sources` 表；`add_theme`／`update_theme` 寫入關聯、
  `get_themes` 一次查出關聯回填；`delete_theme`／`delete_source` 清掉關聯；
  `get_sources` 移除 `layer` 參數。

**驗收**：`tests/test_db.py` 全綠。

---

## Task 8 — 舊資料庫就地升級

**紅**：新檔 `tests/test_db_migration.py`。先在測試裡用原始 SQL 建一份**舊結構**
的資料庫（含 `source_layers`／`layer`／`gate_score`／五段狀態／manual 來源），
再呼叫 `db.init_schema(conn)`，逐一斷言：

1. `test_migration_drops_gate_columns_and_keeps_ideas`
2. `test_migration_folds_retired_statuses_into_adopted`（草稿／已排程 → 採用）
3. `test_migration_keeps_written_body`
4. `test_migration_deletes_manual_sources`
5. `test_migration_turns_layers_into_direct_source_bindings`
6. `test_migration_drops_layer_and_kind_columns`
7. `test_migration_adds_published_at_as_null`
8. `test_migration_is_idempotent`（連跑兩次不出錯、資料筆數不變）

**一次寫一個**，每個都先紅再綠。

**綠**：`db.init_schema` 開頭偵測舊欄位（`PRAGMA table_info`），存在就走升級路徑：
建新表 → 搬資料 → 刪舊表 → 改名。順序照 spec 第 8 節。

**驗收**：`tests/test_db_migration.py` 全綠；
用**使用者真實的 `daibu.db` 副本**跑一次升級，確認 3 主題／15 來源／8 題目／
1 筆成效都在，且三個主題的來源數為 13／10／15。**這一步是契約測試性質，必做**。

---

## Task 9 — `collector` 改用綁定的來源

**紅**：`tests/test_collector.py`
- 改既有三個測試為新的 `Theme(...)`／`Source(...)`。
- `test_collect_only_uses_sources_bound_to_the_theme`：兩個來源只綁一個，
  另一個不得被抓。
- `test_theme_without_sources_collects_nothing`：沒綁來源回傳 `[]`（不是錯誤）。
- 刪掉 `test_evergreen_returns_empty_without_fetching`（概念已不存在）。

**綠**：`collector.collect` 移除 evergreen 判斷，改成
`source.id in theme.source_ids and source.enabled`。

**驗收**：`tests/test_collector.py` 全綠。

---

## Task 10 — 淘汰記憶餵回 AI

**紅**
- `tests/test_llm.py`：`test_build_prompt_asks_ai_to_avoid_rejected_titles`
  （傳 `avoid_titles=["舊題"]`，產出的文字含該標題）；
  `test_build_prompt_omits_avoid_section_when_nothing_rejected`
  （傳空清單時不得出現空的「請避開」段落）。
- `tests/test_selection.py`：`test_generate_passes_rejected_titles_of_that_theme`
  —— 先塞一則該主題的 `已淘汰`、一則**別的主題**的 `已淘汰`，斷言只有前者被傳給
  provider。

**綠**
- `prompt.build(..., avoid_titles: list[str] | None = None)`。
- provider 的 `generate_ideas` 多接 `avoid_titles` 並往下傳。
- `selection.generate_for_theme` 移除 `gate_line`，改為查出該主題的
  `已淘汰` 標題後傳入。
- `db` 加一個查詢函式取某主題的已淘汰標題。

**驗收**：`tests/test_llm.py`、`tests/test_selection.py` 全綠。

---

## Task 11 — 種子資料改用新結構

**紅**：`tests/test_seeds.py`
- `test_seed_sources_have_no_manual_fetch_type`：種子來源的 `fetch_type` 全部
  是 `rss` 或 `search`。
- `test_seed_themes_are_bound_to_named_sources`：載入後每個種子主題的
  `source_ids` 不為空、且對得上來源名稱。
- 既有測試改用新建構子。

**綠**：`daibu/seeds.py` 的 `DEFAULT_SOURCES` 移除 `layer` 與 3 個 manual 來源；
`DEFAULT_THEMES` 移除 `kind`／`source_layers`，改帶要綁的來源名稱，`load()` 先建
來源、再依名稱查 id 綁定。

**驗收**：`tests/test_seeds.py` 全綠。

---

## Task 12 — 設定頁瘦身

**紅**：`tests/test_app_smoke.py`
- `test_settings_page_only_keeps_system_settings`：設定頁載入後，畫面文字不含
  「守門線」「大主題」「來源白名單」。
- 既有 `test_settings_page_loads_without_errors` 改指向新檔名。

**綠**：`git mv pages/0_設定.py pages/3_設定.py`，內容砍到只剩系統設定表單。

**驗收**：`tests/test_app_smoke.py` 該兩題綠。

---

## Task 13 — 刪流水線頁、成效頁改號

**紅**：`tests/test_app_smoke.py`
- 刪掉三個 `test_pipeline_*` 測試。
- `test_performance_page_loads_without_errors` 與
  `test_performance_shows_recommendation_before_chart` 改指向 `pages/2_成效.py`。
- 新增 `test_no_pipeline_page_exists`：`pages/` 底下沒有檔名含「流水線」的檔。

**綠**：`git rm pages/2_流水線.py`；`git mv pages/3_成效.py pages/2_成效.py`；
改掉那句指向流水線的空狀態文案。

**驗收**：`tests/test_app_smoke.py` 全綠。

---

## Task 14 — 選題頁改主從式工作台

分成五個垂直切片，**逐一紅→綠**，測試都放 `tests/test_app_smoke.py`：

1. `test_selection_lists_my_themes_in_the_left_column`
   —— 建三個主題，畫面上三個名稱都在。
2. `test_selection_shows_the_selected_theme_workspace`
   —— 預設選第一個主題，右欄出現它的名稱與來源勾選欄。
3. `test_selection_generates_for_the_selected_theme_only`
   —— monkeypatch `selection.generate_for_theme`，按產生後只收到被選中的主題，
   且**不再依賴今天星期幾**（這是舊版最容易踩的坑）。
4. `test_selection_only_shows_candidates_of_the_selected_theme`
   —— 兩個主題各有候選，只顯示選中那個的。
5. `test_selection_warns_when_theme_has_no_sources`
   —— 沒綁來源的主題，畫面出現「只靠主題名發想」的提示。
6. `test_selection_lists_adopted_ideas_with_body_editor`
   —— 已採用區能打開正文編輯。

**綠**：改寫 `pages/1_選題.py`，版面照 spec 第 7.2 節。選中的主題 id 存
`st.session_state`。

**驗收**：上述六題全綠，且整份 `tests/test_app_smoke.py` 全綠。

---

## Task 15 — 首頁改情況概覽

**紅**：`tests/test_app_smoke.py`，逐一切片：

1. `test_home_leads_with_the_next_action`
   —— 有候選時，畫面出現「N 則候選等你決定」。
2. `test_home_next_action_falls_back_when_nothing_pending`
   —— 沒有任何待辦時，出現「目前沒有待辦」。
3. `test_home_shows_the_week_schedule`
   —— 七天的主題排程都畫得出來。
4. `test_home_lists_each_theme_status`
   —— 各主題近況表含來源數與已發數。
5. `test_home_flags_themes_without_sources`
   —— 沒綁來源的主題出現在提醒區。

既有的 `test_home_shows_single_primary_action` 與
`test_home_renders_mascot_without_code_block` 依新版面調整或刪除（**若刪要在
commit 訊息說明理由**）。

**綠**：改寫 `app.py`，內容照 spec 第 7.1 節。

**驗收**：`tests/test_app_smoke.py` 全綠。

---

## Task 16 — 密度調整與截圖自檢

**這一步沒有自動測試能代替，必做，做完才算交件。**

1. `.venv/bin/streamlit run app.py`，用內建 Browser pane 開啟
2. 截兩張：桌機 **1280×800**、手機 **375×812**
3. 對照全域檢查清單逐項自評，**明確寫出哪幾項不合格**：
   層次／留白／字體／配色／對齊／響應式／狀態／動效
4. 修正（密度調整照 spec 第 10 節：移除大 hero、卡片內距與間距各縮一級、
   左欄主題改緊湊列表）
5. 回到第 2 步再截一次，直到全部通過
6. 淺色與深色模式都要走過一遍
7. 375px 寬**不得出現橫向捲軸**
8. 最終截圖存 `.screenshots/ia-refactor/`，並在 `HANDOFF.md` 附上路徑

---

## 完工驗收清單

- [ ] `.venv/bin/pytest -q` 全綠（3 個 contract 測試維持 deselected）
- [ ] 用真實 `daibu.db` 副本跑過升級，3 主題／15 來源／8 題目／1 成效都在
- [ ] 側欄只有四項：概覽／選題／成效／設定
- [ ] 全 repo `grep -r "守門線\|gate_score\|gate_reason\|source_layers\|evergreen"`
      只剩 `docs/` 裡的歷史紀錄
- [ ] 桌機與手機截圖各兩輪、淺深兩模式都驗過
- [ ] `docs/open-questions.md` 更新
- [ ] `STATUS.md`、`HANDOFF.md` 更新
