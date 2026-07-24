# HANDOFF — 呆一布選題大腦（daibu-content-brain）

> 兩個貼上區塊：規劃找 🧠 Claude、實作找 🖐 Codex。由 Claude 於 2026-07-24 更新。
> 一句話現況：**v1 與前端品牌重構均已完成；四頁已換成 DIVE web 品牌視覺、支援淺／深色，並完成桌機與手機驗收。**

---
## 這一輪要做什麼

依 Figma「DIVE web」的品牌視覺重構前端。文件：

- 設計規格：`docs/specs/2026-07-24-前端品牌重構-design.md`
- TDD 實作計畫：`docs/plan-frontend.md`（Task 1–11，逐一垂直切片）
- 品牌資產：`assets/mascot.svg`（吉祥物，Claude 依設計稿重繪的近似版）

已與使用者確認的四個決定：**① 字型改用免費替代字（Figtree + Noto Sans TC）② 淺色／深色雙模式都做
③ 換皮 + 版面重排（資訊架構不動）④ 吉祥物由 Claude 重繪**。

⚠️ 兩件最容易踩的坑，已寫成測試擋住：

1. **白字放在品牌藍綠 `#6FC1CC` 上只有 2.06:1 對比**，遠低於無障礙標準。主要按鈕一律用 `#0E0E2C` 深色字。
2. **深色模式不可沿用 `#32738F` 當文字色**（對比 3.56:1），要改用 `#6FC1CC`。

---
## ▼ 貼給 🖐 Codex（照計畫實作）

我要實作呆一布選題大腦的前端品牌重構。請依序讀：`STATUS.md`、`AGENTS.md`、
`docs/specs/2026-07-24-前端品牌重構-design.md`、`docs/plan-frontend.md`。

- Streamlit（四頁）＋ SQLite；Python 用 `.venv/bin/python`，測試 `.venv/bin/pytest`
- 照 `docs/plan-frontend.md` 的 Task 1 開始，**嚴格 TDD、一次一個失敗測試、垂直切片**
- 只准動 `app.py`、`pages/`、`daibu/ui.py`、`.streamlit/config.toml`，並新增 `daibu/theme.py`、`tests/test_theme.py`
- **後端邏輯（db / selection / pipeline / performance / seeds / llm / fetch）一行都不要動**
- 顏色與字級只能來自 `daibu/theme.py`，`pages/` 裡不得出現寫死的色碼
- 每個 Task 做完就 commit，設計層疑點寫進 `docs/open-questions.md`，不要自行更動產品方向

---
## ▼ 貼給 🧠 Claude（討論／規劃／決策）

我要繼續呆一布選題大腦。先讀 `STATUS.md`、`docs/specs/2026-07-24-前端品牌重構-design.md` 與 `docs/open-questions.md`。

前端品牌重構的規格與計畫已經寫好、交給 Codex 實作中。可能要談的：
① Codex 做完後的設計驗收（字型 Figtree 是否合意、深色模式實際觀感）
② `docs/open-questions.md` 裡還沒裁決的四項（種子來源抓取方式、Skill 排名公式、契約測試覆蓋、「淘汰」是否改成可封存狀態）
③ v2 方向。

我完全沒有程式背景，專有名詞第一次出現請先用白話解釋。

---
## 已知的技術債

- `docs/open-questions.md` 四項待裁決（使用者 2026-07-24 表示暫時不動）。
- 尚未設定 git 遠端；Tavily 契約測試因無 API key 持續跳過。

---
## 本輪狀態（Codex，2026-07-24）

**狀態：已完成。** 實作位於 `codex/frontend-brand-refactor` 分支，依
`docs/plan-frontend.md` 的 Task 1–11 逐一以 TDD 完成並分段 commit。

### 已完成

- 建立可測試的淺／深色品牌 token、WCAG 對比度紅線、Figtree + Noto Sans TC 字型與字級系統。
- Streamlit 原生雙模式設定與共用品牌 CSS；主要按鈕固定為品牌藍綠底＋ONYX 深字。
- 側欄品牌標誌、首頁今日戰情、選題左右審核、可掃視流水線看板／編輯 dialog、建議優先成效頁。
- 保留所有既有後端、資料庫、LLM、抓取與成效計算邏輯不變。
- 實測修正 SVG 被 Markdown 判成 code block，以及全域字型蓋掉 Streamlit Material icon 的問題。

### 驗證證據

- 自動測試：`.venv/bin/pytest -q` → `68 passed, 3 deselected`。
- 1280×800 桌機與 375×812 手機完成兩輪截圖自檢；手機頁面無橫向捲動。
- 1440×900 的五欄流水線無欄位溢位或重疊。
- 四頁均走過深色模式；輸入框、卡片、圖表與文字同步切換。
- 鍵盤 focus 為 2px 品牌色外框＋2px offset。
- `prefers-reduced-motion` 開啟後只保留顏色過場，不再位移或縮放。
- 最終桌機截圖：`.screenshots/round2/desktop.png`
- 最終手機截圖：`.screenshots/round2/mobile.png`
- 最終深色截圖：`.screenshots/round2/home-dark.png`

### 剩餘限制

- 3 個真實 API 契約測試因沒有 API key 依既有設定排除，未在本輪呼叫付費或外部服務。
- 首頁暫顯示「已發內容」總數；資料表缺少狀態改成已發的時間，無法誠實計算「本週已發」。
- Streamlit 1.60 的淺／深模式不能各自設定圖表分類色盤，先使用共用品牌色盤。
- 上述兩個產品／框架限制已記錄於 `docs/open-questions.md`。
