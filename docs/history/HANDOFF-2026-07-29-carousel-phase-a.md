# HANDOFF 歷史 — 貼文輪播圖產生器 階段 A（2026-07-29 收）

計畫：`docs/plan-carousel.md` Task 1–6。設計：`docs/specs/2026-07-28-貼文輪播圖產生器-design.md`。

## 這一輪做了什麼

讓「AI 新創介紹」的選題產得出**具體公司**。Task 1–6 全數完成，一個 Task 一個 commit：

| commit | 內容 |
|---|---|
| `152e118` | `ideas` 新增 `company` 與 `source_excerpt` 兩欄（含舊資料庫就地升級） |
| `7442446` | `Idea` 與 `StoredIdea` 帶上新欄位，讀寫接通 |
| `99a8325` | 選題指令改為必須產出具體公司 |
| `0ee40ce` | 「AI 新創介紹」的來源收斂到 5 個並一次性清理既有綁定 |
| `587fd4d` | 候選卡片顯示公司名與來源連結 |
| `1ad6b37` | Codex 自己的階段 A 驗收紀錄 |

## Codex 自述的收尾結果

- 全套 **174 passed、3 deselected、0 failed**（實作前基線 167）。
- 複本實測：舊 6 則保留、5 來源綁定；真實產生 Hint、Pangram、Vela 後共 9 則，
  公司名、網址、引文齊全，console 0 errors。
- 限制：Y Combinator／INSIDE 缺 Tavily key、a16z 回 404；本次由另 2 個來源產題。
- 截圖：`.screenshots/desktop-round2.png`、`.screenshots/mobile-round2.png`。

## Claude 的獨立驗收（2026-07-29）

**結論：通過。** 以下每一項都是重跑過的，不是照抄上面。

1. **測試**：自行重跑 `.venv/bin/pytest -q` → `174 passed, 3 deselected`、0 失敗。
   多出的 7 個測試對應 Task 1–5 新增的斷言。
2. **真實 `daibu.db` 沒被動過**：唯讀檢查確認仍是舊的 9 欄結構、仍綁 15 個來源。
   Codex 全程跑在複本上。
3. **搬遷在真實資料上可行**：從 `daibu.db` 另複製一份實測 →
   舊 8 則題目全部存活且 `company` 為空、來源收斂成 5 個。
   **一次性保護有效**：手動把 Hacker News 加回去、再跑一次 `init_schema`，
   它沒有被刪掉（這是最容易寫錯的一條）。
4. **畫面**：跑在複本上（port 8502），桌機 1280×800 與手機 375×812 各一張自檢 →
   公司名以 14px／700／`--brand-secondary` 顯示在標題之上，層次清楚；
   舊 6 則顯示「未指定公司」未破版；有 `source_url` 才出現「查看來源」；
   375px 無橫向捲動、側欄正常收合；console 與伺服器皆 0 錯誤。
5. **AI 真的產得出具體公司**：3 則都有可點的真實來源網址（TechCrunch ×2、
   Product Hunt ×1）與原文引文。

## 驗收時發現、已寫進計畫的三件事

1. **5 個來源實際只有 2 個抓得到** → 新增 `Task 6.5`。逐一實測過的結論：
   `a16z` 官網已無任何可用 feed（7 個常見路徑全 404），要換掉不是修好；
   `Y Combinator Blog` 與 `INSIDE` 都有可用的 RSS，改成 `rss` 型就不必再依賴
   `TAVILY_API_KEY`。並要求補一組打真實網路的契約測試——這一輪三個來源壞掉
   沒被發現，正是因為既有測試全是假資料。
2. **引文品質不齊會拖垮階段 B** → 寫進 `Task 11` Step 6–9。TechCrunch 給的引文
   有 190～207 字真實事實，Product Hunt 給的是 47 字的網頁邊角料
   （`The AI Recruiting Coordinator Discussion | Link`）。引文是邊角料時七格會
   幾乎全標成「需查證」，等於沒省到力。門檻 `MIN_EXCERPT_CHARS = 60`。
3. **舊的 6 則「未指定公司」不給產圖** → 寫進 `Task 17` Step 5–8。
   沒有公司名時整個產貼圖區塊不顯示；引文不足時顯示但按鈕停用並說明原因。

## 分支現況（順帶更正）

舊交接單寫的 `codex/frontend-brand-refactor` **不存在**。實際狀況：

- `codex/ia-topic-first`（目前在的分支）領先 `main` **58 個 commit、0 衝突**，
  合併是 fast-forward。
- `refactor/ia-topic-first` 只多 1 個 commit `b6b66bc`，訊息自己寫著
  「越權實作的探路稿，僅供參考」，可直接刪除。
- 這個 repo **沒有設定任何遠端儲存庫**，推不上 GitHub、也沒有正式站可部署。
