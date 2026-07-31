# HANDOFF — 呆一布選題大腦

> 2026-07-31 更新。輪播全流程原有 10 項問題已修正、重驗、合併 `main` 並完成推送收尾。

## 本輪目標與驗收

依 `docs/plan-acceptance-cards.md` 的 A–D 驗收後，修正回報中的 1 🔴、2 🟠、7 🟡：
草稿逐段來源證據、Logo 死鎖、單次 LLM 呼叫、乾淨文章擷取、手機順序、封面來源、
輔助字可讀性、各頁主詞、CTA 新資訊，以及直接重整 `/選題` 的 404。

## 本輪狀態

- **資料安全**：只用 `/tmp/daibu-test.db`、port 8502、`/tmp/daibu-test-logos/`。
  舊 DB 搬遷後仍為 3 主題／8 題／6 候選／1 採用／1 已發；新增兩欄與四張表，
  `integrity_check=ok`。真實 `daibu.db` mtime 前後均為 `1785433278`。
- **可信研究**：來源研究只保留公司官方與可信網域，檢查公司相關性後才進草稿；畫面
  區分官方／第三方。重新產生沿用來源快照，只有「重新搜尋」才更新。本輪 Railway
  快照為 Railway Docs、Railway Blog、TechCrunch。
- **草稿信任**：每個事實段落都要有有效 source ID 與逐字存在於來源的 exact quote；
  來源、七頁草稿以單一交易儲存。Gemini 正常流程只呼叫一次，App 端做嚴格驗證。
- **完整操作**：官方 Railway SVG 經使用者看圖確認；七頁草稿、七張圖、ZIP 下載均
  成功。ZIP 恰為 `01-cover.png`–`07-cta.png` 七檔，抽查 1080×1350。
- **瀏覽器**：`/選題` 直接開啟與 reload 都正常，console 0 errors；375px 沒有水平
  捲動，預覽順序 01→07。唯二截圖為 `.screenshots/desktop.png`、
  `.screenshots/mobile.png`。
- **B 段十題**：已逐題更新於
  `docs/2026-07-30-輪播全流程驗收回饋.md`。不評內容值不值得發；只檢查可讀性、
  通順度與規格。十項原問題均通過重驗。
- **目前未解**：側欄首頁仍顯示 `app`，列為 🟡、不影響流程；本機未設定 Tavily key，
  因此其真實契約 skip，Gemini 與 TechCrunch 真實契約已通過。
- **驗證**：工作分支 `366 passed, 11 deselected, 1 warning in 18.59s`；合併後的
  `main` 為 `366 passed, 11 deselected, 1 warning in 18.43s`；`git diff --check` 通過。

## 下一步

本輪開發收尾已完成。之後若要處理側欄 `app`，請另開新 Task；不要在本輪擴大範圍。

## 依據

- 驗收腳本：`docs/plan-acceptance-cards.md`
- 完整回饋：`docs/2026-07-30-輪播全流程驗收回饋.md`
