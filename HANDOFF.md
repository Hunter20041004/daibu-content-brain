# HANDOFF — 呆一布選題大腦（daibu-content-brain）

> 於 2026-07-30 更新。
> 一句話現況：**出圖引擎已完成並在 `main`；這一輪開始把它接上人真正會操作的
> 四件事——蒐集來源、上傳 Logo、產圖、下載 ZIP。**

## 本輪目標與驗收（只做 Phase A）

依 `docs/plan-cards-wiring.md` 完成 **Phase A：來源包可蒐集、可編輯**，
共 Task 1–3。**做完就停，提醒使用者開新對話接 Phase B。**

- Task 1：新表 `idea_sources`，冪等搬遷、round-trip、刪題目連帶清乾淨。
- Task 2：`daibu/cards/sources.py` — 1–8 筆上限、`S1`–`S8` 編號、刪中間一筆
  不重新編號、必填欄位錯誤訊息。
- Task 3：`daibu/fetch/page.py` — 貼 https 網址抓出版方／日期／引文建議值，
  含一條真實網路的 `@pytest.mark.contract` 測試。

驗收：`.venv/bin/pytest -q` 全套綠燈且高於 312；新增測試都走過紅→綠。

## 設計依據

- 規格：`docs/specs/2026-07-30-來源蒐集與出圖接線-design.md`
- 計畫：`docs/plan-cards-wiring.md`（Phase A–D，Task 1–11）
- 上一輪歸檔：`docs/history/HANDOFF-2026-07-30-carousel-phase-c.md`

## 本輪已裁決（Claude，2026-07-30）

- **來源包與來源快照分兩張表**：`idea_sources` 可隨時編輯，
  `carousel_sources` 是產草稿當下的快照。理由：`source_label` 是產生當下寫死的
  字串且會被 `validate_draft` 回頭檢查，共用一張表會讓舊草稿突然驗證失敗。
- **Logo 上限**：檔案 ≤ 2 MB；PNG 單邊 ≤ 4096 px、總像素 ≤ 800 萬、單邊 ≥ 64 px；
  SVG 必須有 `viewBox` 或同時有 `width`／`height`。檔案大小與解碼後像素分開限制，
  因為壓縮後很小的圖解開可能吃掉數百 MB 記憶體。錯誤文案見規格 §5.3。
- **新檢查只放新的 `validate_upload()`**，不動 `logo_data_uri()`／`_validate_svg()`。
- **抓網址只產生「建議值」**，使用者逐欄確認後才存——那一按就是查證動作本身。

## 本輪狀態

- 目前分支：`main`，追蹤 `origin/main`，工作區乾淨（`.DS_Store`、`.claude/`
  維持未追蹤）。
- 基線：`312 passed, 9 deselected`。
- Claude 這一輪只寫了 `docs/` 與 `HANDOFF.md`，**未動任何原始碼**。
- Codex 尚未開工。

## 最容易踩的坑

1. **缺 Logo 只擋「產生七張圖」，不擋「產生輪播草稿」**——草稿是純文字。
   前一版規格寫「缺 Logo 阻擋產圖」，容易被讀成什麼都不能做。
2. 不可為了讓測試綠燈放寬既有規則：五欄必填、https、`YYYY-MM-DD`、
   140–220 字門檻、SVG 白名單、PNG 透明檢查，一條都不動。
3. 驗證失敗時**不清空使用者輸入、不寫回半套資料**——「正文草稿靜默消失」是
   這個專案真實發生過的事故。
4. viewBox 檢查別塞進 `_validate_svg()`，會弄紅既有的
   `test_logo_accepts_svg_with_local_gradient_and_symbol`。
5. 紅→綠只跑當前那一個測試檔，Task 收尾才跑全套。
6. 手動驗收用複本：`cp daibu.db /tmp/daibu-test.db` 並跑在 port 8502
   （使用者的 Streamlit 佔著 8501）。
