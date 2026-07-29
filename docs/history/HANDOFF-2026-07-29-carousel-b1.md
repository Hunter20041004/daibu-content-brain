# HANDOFF 歷史 — 輪播圖 B1（Task 6.5、7–11）

> 這一輪由 Codex 實作、Claude 於 2026-07-29 驗收通過。分支 `codex/ia-topic-first`。

## 這一輪交付了什麼

壞掉的來源修好，而且一則採用的候選能產出七格文字草稿並存進資料庫。
還沒有畫面、還沒有圖——那是 B2 與 B3 的事。

七個提交：`16410b4`、`64a4b60`、`d5370c8`、`2d83873`、`a9e57fb`、`7ce3f72`、
`963386b`（＋文件 `a4f26be`）。每個提交對應計畫上的一個 Task，程式與測試同進同出。

## Codex 回報的結果

- 全套：`.venv/bin/pytest -q` → **195 passed, 8 deselected**（實作前 174 passed, 3 deselected）
- 契約：五個指定 RSS 網址全部通過
- 既有的 `test_real_llm_returns_parsable_ideas` 仍紅：測資沒有具體公司名，
  新 prompt 依規格回 0 則。未改鬆測試。
- UI 自檢：桌機／手機兩輪，無橫向捲動、console 0 error。
  `.screenshots/task9-final-desktop.png`、`.screenshots/task9-final-mobile.png`

## Claude 的驗收證據（2026-07-29）

全部跑在 `/tmp/daibu-b1-verify.db`（真實 `daibu.db` 的複本），真實資料庫未被動到。

1. **全套測試**：`195 passed, 8 deselected in 5.79s`——數字與回報一致。
   deselected 由 3 → 8，正好是新增的 5 個 contract 標記測試。
2. **RSS 契約（真的打網路）**：`tests/test_rss.py -m contract` → `6 passed`。
   五個網址今天仍然全部活著，且契約測試打的網址與 `daibu/seeds.py` 綁的完全一致。
3. **真實資料庫複本的搬遷**：15 個綁定 → 5 個（INSIDE／Product Hunt AI／TechCrunch／
   VentureBeat AI／Y Combinator Blog），全部是 `rss`（不需要 `TAVILY_API_KEY`）；
   `a16z` 只解除綁定、仍留在來源庫；8 則既有題目一則沒少；`carousel_pages` 已建表。
4. **搬遷冪等**：手動把 `a16z` 加回綁定後再跑一次 `init_schema`，它沒有被再刪掉。
   Task 4 收斂與 Task 6.5 修正的先後順序正確（`VentureBeat AI` 沒被掃掉）。
5. **端對端（假 LLM、真資料庫）**：七格存進資料庫、頁序 1–7 正確；
   把 `grounding` 亂填成 `"亂寫的東西"` 會被打回 `model` 且 `source_quote` 清空；
   prompt 確實帶了公司名與引文；刪掉題目後 `carousel_pages` 殘留 0 列。
6. **紅線檔案**：`daibu/fetch/rss.py`、`daibu/fetch/search.py`、`daibu/theme.py`、
   `tests/test_theme.py` 這一輪都沒有被改（`git diff` 為空）。
7. **60 字門檻**：`MIN_EXCERPT_CHARS` 只在 `daibu/cards/draft.py` 出現一次，
   沒有在別處寫死。

### 順手量到的一件事：60 字門檻不會餓死管線

實測五個來源當天的 RSS 摘要長度（`snippet`），對照 `MIN_EXCERPT_CHARS = 60`：

| 來源 | 則數 | 摘要中位數 | ≥60 字 |
|---|---|---|---|
| Product Hunt AI | 10 | 69 | 8/10 |
| Y Combinator Blog | 10 | 232 | 10/10 |
| VentureBeat AI | 7 | 500 | 7/7 |
| TechCrunch | 10 | 140 | 10/10 |
| INSIDE | 10 | 101 | 10/10 |

47 則裡 45 則過門檻。Product Hunt 仍是最弱的一個，但不再是階段 A 看到的
「幾乎全是 47 字邊角料」。門檻設在 60 是合理的，暫不調整。

## 驗收時發現、但不擋 B1 的三件事

1. **使用者的 8 則既有題目全部產不出輪播草稿**（`company` 與 `source_excerpt` 都是空的）。
   這是預期內的——它們是 Task 3 改指令之前產的。要看到第一張圖，B3 驗收時得先按一次
   「產生候選」重產（會花 AI 額度）。
2. **Task 17 缺一段：provider 沒有公開的 `generate_text`。**
   `draft.generate(conn, idea, generate_text)` 要一個「餵字串、回字串」的函式，
   但 `GeminiProvider`／`GroqProvider` 只有私有的 `_generate_text`，
   `LLMProvider` 協定上也沒有。已在 `docs/plan-carousel.md` 的 Task 17 補上這一刀。
3. **`tests/test_seeds.py::test_load_seeds_themes_without_duplicates`** 原本斷言
   `len(sources) == 15`，改成 `== len(seeds.DEFAULT_SOURCES)`。仍擋得住重複插入，
   但不再釘死數量。可接受，記著就好。

## 待使用者決定（B1 留下來的唯一一題）

`tests/test_llm_contract.py::test_real_llm_returns_parsable_ideas` 的測資
（`Material("AI 實驗室發表新模型", ..., "公開資料摘要")`）在新指令下必然回 0 則，
因為裡面沒有任何公司名——**這正是 Task 3 要的行為，測試沒錯，是測資過時了**。

建議：把測資換成一則帶真實公司名、且摘要有具體事實的素材，讓它繼續守住
「真實 LLM 回得出可解析的 JSON」這條線。列進 B3 的收尾工單。
