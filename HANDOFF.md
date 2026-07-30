# HANDOFF — 呆一布選題大腦（daibu-content-brain）

> 於 2026-07-30 更新。
> 一句話現況：**輪播重設 Phase C（Task 6–8）功能與本機視覺驗收完成；
> 真實免費 LLM 契約失敗，尚未合併 main／push。**

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
- 真實契約阻擋：
  - `test_real_llm_returns_parsable_ideas`：免費 provider 回傳 0 個 Idea；
  - `test_real_llm_returns_valid_sourced_carousel`：超過 30 秒未完成；
  - 本輪未修改 LLM，沒有放寬 parser 或 mock。

## 產品理解檢查點

1. **產品能力**：查證來源＋官方 Logo 可產七張輪播圖。
2. **使用者體驗**：每頁回答一題、Logo 每頁可見；缺 Logo 阻擋但不刪草稿。
3. **技術結構**：schema、DB、LLM、Logo／SVG、HTML、Playwright。
4. **資料流程**：來源包 → 草稿 → 驗證 → 儲存 → Logo → HTML → PNG。
5. **設計理由**：固定讀者任務、彈性 AI 角色、自然垂直敘事。
6. **替代方案**：一次接完整 UI 較快，但故障難定位；本輪分層完成出圖核心。
7. **安全與成本**：Logo metadata／SVG 白名單／HTML 跳脫；零圖片生成費。
8. **測試證據**：局部、全套、像素／DOM 契約與兩輪截圖均通過。
9. **剩餘限制**：免費 LLM 契約阻擋整合；來源蒐集、Logo 上傳、ZIP、
   選題頁接線尚未做。

## 下一步

另開新對話先診斷免費 LLM 契約；通過後才合併本分支。再規劃來源蒐集＋Logo
上傳＋ZIP＋選題頁接線。

## 最容易踩的坑

1. 不可為了契約綠燈放寬來源引用、140 字門檻或改成 mock。
2. 不可因缺 Logo 降級成純文字，也不可刪掉已存草稿。
3. 第 4 頁維持 A1／M1：無虛線、無頭像背景框，步驟字級 36／30px。
4. 不可重新開放 SVG 外部網址、`style` 或非 `#fragment` 引用。
