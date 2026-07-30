# HANDOFF — 呆一布選題大腦（daibu-content-brain）

> 於 2026-07-29 更新。
> 一句話現況：**新版輪播 Phase A（Task 1–3）完成；下一輪從 Phase B Task 4
>「官方 Logo 是產圖硬門檻」開始。**

## 本輪目標與驗收

依 `docs/plan-carousel-redesign.md` 完成 Phase A（Task 1–3）：

- 七頁結構、必要 section、140–220 字、圖解與來源 ID 可驗證；
- 結構化草稿與來源能安全寫入／讀回 SQLite；
- 免費 LLM 真實回覆能通過同一份嚴格契約。

## 本輪狀態

- 工作分支：`codex/carousel-redesign-phase-a`。
- Task 1 提交 `9b6618c`：七頁 schema、必要 section、140–220 字、圖解與來源契約。
- Task 2 提交 `0f03782`：SQLite 結構化頁面／來源 round-trip 與舊資料庫 migration。
- Task 3（本次提交）：Gemini／Groq 共用 prompt/parser、一次帶完整錯誤的定向修稿、
  僅合併失敗頁、第二次失敗不保存；來源先驗證、標示由程式產生並保留來源順序。
- Code review 的第八頁覆寫、malformed JSON、固定 label 順序、空內容／圖解節點等
  邊界已補回歸測試；最終 reviewer 回報無阻擋問題。
- 驗收：
  - 相關測試：`113 passed`。
  - 全套：`271 passed, 9 deselected`。
  - 真實免費 Gemini 契約曾通過：`1 passed in 70.28s`，涵蓋產生、定向修稿、驗證、
    SQLite 寫入與讀回；提示文字澄清後再跑時碰到免費每日 20 次的 `429` 額度上限，
    並非 parser／validator 失敗。
- `docs/open-questions.md` 已記錄採用「一次帶錯誤修稿」的裁決。

## 下一步

另開新對話執行 Phase B Task 4：官方 Logo 是產圖硬門檻。先讀計畫第 1384 行起的
Logo 驗證／快取切片；依 TDD 一次完成一個垂直切片。Phase B 仍不做 HTML 排版或 PNG
出圖，那是 Phase C。

## 最容易踩的坑

1. 不可把空 `source_ids` 自動補成某個來源；程式不知道哪一筆真的支持該主張。
2. 不可把 140 字下限或必要 label 放寬來讓真實測試假綠。
3. 第二次 LLM 回覆只可替換第一次失敗／錯位的頁；已合格頁不可覆寫。
4. 不要碰真實 `daibu.db`；資料庫測試只用 `tmp_path`。
5. Gemini 免費額度可能在同日觸發 `429`；不要因此切到付費模型。
