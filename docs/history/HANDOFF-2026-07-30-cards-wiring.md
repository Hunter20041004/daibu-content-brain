# HANDOFF 歸檔 — 來源蒐集與出圖接線 Phase A–D（2026-07-30）

> 這是 `HANDOFF.md` 在轉入「全流程操作驗收」前的完整內容。
> 由 Codex 於本輪收尾時寫下，Claude 已獨立複驗（見文末）。

一句話現況：**來源蒐集、官方 Logo、七張圖與 ZIP 已全部接進選題工作台，
Phase A–D 已在 `main` 完成。**

## 本輪目標與結果

依 `docs/plan-cards-wiring.md` 完成 Phase A–D、Task 1–11。

- **Phase A｜來源包**：新增 `idea_sources`，每題可存 1–8 筆查證來源；
  `S1`–`S8` 取最小空號，刪題目會連帶清除。貼入公開 https 網址可抓出版方、
  日期與引文建議值，仍須由使用者確認後才存。
- **Phase B｜官方 Logo**：公司共用 Logo 可上傳、替換、重用並保留官方來源與
  確認日期。只收 SVG／透明 PNG；限制 2 MB、4096 px、800 萬總像素與 64 px
  最小邊，錯誤不會留下半套資料。
- **Phase C｜ZIP**：七張 1080×1350 PNG 依固定頁型編成
  `01-cover.png` 到 `07-cta.png`，下載檔名含公司與日期。
- **Phase D｜工作台**：已採用題目內可完成公司名、來源、Logo、七頁草稿編輯、
  重新產生確認、出圖預覽與 ZIP 下載。草稿改動後舊圖快取會失效。

## 產品與資料流

```text
採用題目
  → idea_sources（可編輯查證包）
  → carousel_sources（產稿當下快照）＋ carousel_pages（七頁草稿）
  → brand_assets（公司共用、附官方來源的 Logo）
  → Playwright 渲染七張 PNG → ZIP
```

來源包與快照分開，避免之後修改筆記時讓既有草稿的來源標籤失效。缺 Logo 只擋
「產生七張圖」，不擋純文字草稿；這是本輪刻意保留的產品行為。

## 驗收證據

- 分支 `codex/cards-wiring` 已快轉合併進 `main`。
- 功能分支收尾：`.venv/bin/pytest -q` → **349 passed, 10 deselected**。
- 合併後 `main` 複驗：`.venv/bin/pytest -q` →
  **349 passed, 10 deselected in 28.53s**。
- 真實文章頁契約：TechCrunch 網址抓取測試 **1 passed**。
- 最終 UI：console **0 errors**；375px 時
  `scrollWidth = clientWidth = 375`，無橫向破版。
- 截圖：`.screenshots/desktop.png`、`.screenshots/mobile.png`
  （目錄已忽略，不進 git）。
- 合併前差異審查：無 Critical／Important 問題。

## 剩餘限制與風險

1. 預設略過的 10 個 contract 測試會打真實 LLM／RSS／網頁，需網路或 API key；
   一般全套測試不會花免費額度。
2. 部分網站會擋自動抓取；介面會保留原輸入，使用者可改成手動填寫。
3. 這是本機 Streamlit 工具，專案沒有 production 部署流程；v1 的雲端部署仍是
   non-goal。
4. 手動驗收請用複本資料庫與 port 8502，不要動使用者正在用的 `daibu.db`。

## Claude 的獨立複驗（2026-07-30）

- Task 1–11 的 commit `2d4e911`…`aafe512` 全數存在，另加收尾 `57e147d`。
- `HEAD` 與 `origin/main` 同為 `57e147d`，確認已推送。
- 自行重跑全套：**349 passed, 10 deselected in 58.14s**，與回報一致。
- 四項設計裁決逐條核對通過。其中 viewBox 檢查確實位於
  `validate_upload()`（`daibu/cards/logo.py` 143–205 行），未污染
  `_validate_svg()`（210 行起）；既有綠燈測試
  `test_logo_accepts_svg_with_local_gradient_and_symbol` 未被更動，
  `tests/test_cards_logo.py` 的 diff 為 43 加 1 減，純加法。
- 缺 Logo 的分界正確：產草稿按鈕用 `missing_requirements`（不含 Logo），
  產圖按鈕用 `can_render`（含 Logo）。
