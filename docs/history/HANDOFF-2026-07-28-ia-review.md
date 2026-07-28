# HANDOFF — 呆一布選題大腦（daibu-content-brain）

> 兩個貼上區塊：規劃找 🧠 Claude、實作找 🖐 Codex。由 Claude 於 2026-07-28 更新。
> 一句話現況：**操作驗收修正（Task 1–24）與整體驗收全部完成，停在使用者複驗點。**
> 專案全貌、設計決策、測試基線、分支現況一律看 `STATUS.md`，這裡不重複。

---

## 這一輪要做什麼

**兩件事，做完就結束這一輪：**

1. **使用者複驗** `codex/ia-topic-first` 上的最終版本
2. **決定這個分支怎麼整合回 `main`**（合併／保留／捨棄）

實作已經全綠：`.venv/bin/pytest -q` → `167 passed, 3 deselected`（原始基線 99）。
上一輪的完整實作紀錄與驗收證據在 `docs/history/HANDOFF-2026-07-26-qa-fixes.md`。

### 複驗怎麼跑（不要碰真實資料庫）

```
cp daibu.db /tmp/daibu-review.db
DAIBU_DB_PATH=/tmp/daibu-review.db .venv/bin/streamlit run app.py --server.port 8502
```

使用者自己常開著一個 Streamlit 在 8501，請挑別的 port。
「產生候選」是真的會呼叫 AI 與 15 個外部來源的（會花配額、要等幾秒）。

---

## ⚠️ 這一輪最容易踩的坑

1. **不要動到真實 `daibu.db`。** 上一輪驗收前後的 SHA-256 一致，維持這個紀律。
2. **驗收要打開彈出視窗看。** 之前就是只截了頁面本身、沒開彈出視窗，才讓
   「四個彈出視窗文字全隱形」整批過關。深淺兩種配色模式都要看。
3. **合併前先在 `main` 重跑一次全套測試**，再照全域規則收尾（push、部署）。

---

## ▼ 貼給 🖐 Codex（照計畫實作）

這一輪沒有新的實作工單。若使用者決定合併：

先讀 `STATUS.md`，然後把 `codex/ia-topic-first` 合併回 `main`、在 `main` 重跑
`.venv/bin/pytest -q` 確認 `167 passed, 3 deselected`，再照全域規則收尾。
遇到衝突或測試不過就停下來回報，不要硬推。

---

## ▼ 貼給 🧠 Claude（討論／規劃／決策）

我要繼續呆一布選題大腦。先讀 `STATUS.md` 與 `docs/open-questions.md`。

複驗完之後要談的：

1. `codex/ia-topic-first` 與 `codex/frontend-brand-refactor` 兩個分支怎麼整合回 `main`
2. **下一輪的大功能：分平台產文字（Threads／IG／LinkedIn）＋由文字產貼圖**
   —— 需要獨立一輪設計，且要先解決「圖片生成服務多數付費」與既定的
   「只用免費額度」成本策略的衝突
3. `docs/open-questions.md` 裡剩下的待裁決項目

我完全沒有程式背景，專有名詞第一次出現請先用白話解釋。
**我負責產品決策，實作交給 Codex；請不要直接動程式碼。**

---

## 已知的技術債（這一輪不處理）

- 尚未設定 git 遠端；Tavily 契約測試因無 API key 持續跳過。
- **成效紀錄只能新增、不能修改或刪除。** 回填錯了沒辦法更正。
- **API 金鑰只存在記憶體**，關掉 app 就消失，每次重開都要重填。
- **同一批候選之間沒有防重複**，也沒有「這批我都不要，重產一次」的按鈕。
- 「AI 近期大事」的可抓來源在刪掉 manual 來源後變少，若在意需另尋替代來源。

---

## 歷史

每一輪的完整實作紀錄與驗收證據放在 `docs/history/`，這份交接單只留當前這一輪
（上限 4 KB，由 `~/.claude/hooks/handoff-size-gate.mjs` 把關）。
