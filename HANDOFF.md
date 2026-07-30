# HANDOFF — 呆一布選題大腦（daibu-content-brain）

> 於 2026-07-30 更新。
> 一句話現況：**輪播重設 Phase C 與免費 LLM 換模已合併本機 main；
> 全測與真實契約通過，但 repository 沒有 remote，尚未 push。**

## 本輪目標與驗收

依 `docs/plan-carousel-redesign.md` 完成 Phase C：

- 七頁結構化草稿、已驗證 Logo、固定圖解組成 1080×1350 滿版 HTML；
- Chromium 一次輸出七張 PNG，量測 Logo、overflow、來源位置與下半部內容；
- 桌機／手機兩輪視覺自檢，保留第 4 頁 A1／M1 與可讀字級。

## 本輪狀態

- 工作分支：`codex/carousel-redesign-phase-c`。
- Task 6 提交 `4c1b948`：新版 HTML renderer、七頁 section／Logo／來源／安全跳脫。
- Task 7 提交 `4f6c631`：七張 PNG、`LayoutReport`、真實瀏覽器版面契約。
- 第二輪視覺驗收全部合格：
  - `.screenshots/carousel-redesign/round2/desktop.png`
  - `.screenshots/carousel-redesign/round2/mobile.png`
- 本機全套：`304 passed, 9 deselected`；高於 Phase B 的 303。
- 2026-07-30 免費 LLM 契約修正與換模：
  - Idea 真實 fixture 改成含具名公司；真實契約 `1 passed in 6.58s`。
  - `LLMProvider` 新增輪播專用入口；Gemini 使用 JSON Schema 鎖七頁、必要欄位、
    section `source_ids`，Groq 保留既有文字生成備援。
  - 原 `gemini-2.5-flash` 每日 20 次額度用盡；2.5 Flash-Lite 對新使用者已 404。
    即時 `models.list` 確認後改用 stable `gemini-3.1-flash-lite`。
  - Gemini 3.1 使用 `thinking_level=medium`、45 秒單次 timeout；輪播真實契約
    `1 passed in 29.57s`，Idea 同模型亦通過，既有 validator 與修稿均未放寬。
  - transport timeout、504 deadline 與 429 quota 都轉成可理解的產品錯誤。
  - provider／設定頁預設與本機 SQLite `llm_model` 均已切到 3.1 Flash-Lite。
  - commit `38bce29` 已 fast-forward 合併本機 `main`；main 全套
    `312 passed, 9 deselected in 18.44s`。
  - `git remote -v` 為空，無法 push；專案目前也沒有正式部署流程。
  - `.DS_Store`、`.claude/` 保持原有未追蹤狀態，未碰觸。

## 產品理解檢查點

1. **產品能力**：查證來源＋官方 Logo 可產七張輪播圖。
2. **使用者體驗**：每頁回答一題、Logo 每頁可見；缺 Logo 阻擋但不刪草稿。
3. **技術結構**：schema、DB、LLM、Logo／SVG、HTML、Playwright。
4. **資料流程**：來源包 → 草稿 → 驗證 → 儲存 → Logo → HTML → PNG。
5. **設計理由**：固定讀者任務、彈性 AI 角色、自然垂直敘事。
6. **替代方案**：一次接完整 UI 較快，但故障難定位；本輪分層完成出圖核心。
7. **安全與成本**：API key 仍只走環境變數；只用免費 provider，修稿最多兩次呼叫。
8. **測試證據**：3.1 Flash-Lite 的 Idea 與輪播真實契約均通過。
9. **剩餘限制**：Groq 無 key 未跑真實契約；Google 免費額度仍可能調整。

## 下一步

先提供／設定既有 Git remote，再 push 本機 main。下一輪再規劃來源蒐集＋Logo
上傳＋ZIP＋選題頁接線。

## 最容易踩的坑

1. 不可為了契約綠燈放寬來源引用、140 字門檻或改成 mock。
2. 不可因缺 Logo 降級成純文字，也不可刪掉已存草稿。
3. 第 4 頁維持 A1／M1：無虛線、無頭像背景框，步驟字級 36／30px。
4. 不可重新開放 SVG 外部網址、`style` 或非 `#fragment` 引用。
