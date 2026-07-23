# 呆一布 選題大腦 — v1 設計文件（spec）

> 本文件自給自足：接手的人（Codex）不需要看任何對話紀錄，只讀本檔＋ `plan.md` 即可開工。
> 開發方式一律遵守專案根目錄 `AGENTS.md` 與使用者全域 TDD 規範。

---

## 0. 背景與定位（為什麼做這個）

- **組織**：呆一布 AI 共學實驗室（DiveAI）的「社群組」。本專案是社群組的**內容決策大腦**。
- **社群組定位**：整個實驗室的「連接層」——決定內容**給誰看、怎麼被看到**（不是單純的小編發文組）。
- **品牌調性 / 定位**：「**不焦慮、會思考、陪你學**」——文組視角的 AI 紀實。
- **目標受眾（TA）**：怕 AI、非技術背景的政大文商科學生。
- **守門線（Gate Line，每則貼文的品管線，也是 AI 打分的核心依據）**：
  > 「一個**怕 AI 的文組同學**看完這則，會不會覺得『**原來我也可以，而且我更會想事情了**』？」
  - 這句話存在設定檔，會被原封餵給 LLM 當評分標準。使用者可在設定頁修改。

---

## 1. 產品一句話

一個**單人網頁儀表板**：使用者設定「大主題 × 星期幾」與「來源白名單」→ 一鍵讓 AI 從白名單抓最新內容、為每個主題挖出**具體貼文題目**（附切入角度、守門線分數、來源連結）→ 使用者挑選/微調 → 推進內容流水線（候選 → 採用 → 草稿 → 已排程 → 已發）→ 發完回填成效 → 看板告訴他哪個主題表現好、下週該補哪個。

**本質：AI 當軍師（產生＋評分），使用者當決策者（採用／淘汰）。**

---

## 2. v1 範圍（做什麼 / 不做什麼）

**v1 要做：** 選題（含抓取來源）、守門線打分、內容流水線狀態管理、成效回填與彙總建議。**單人、本機。**

**v1 明確不做（是之後的垂直切片，Codex 不要提前做）：**
- ❌ 自動製圖
- ❌ 自動發文 / 排程真正推送到平台
- ❌ 自動回覆留言
- ❌ 多人登入 / 雲端部署

**已移除、不要實作：**
- ❌ **「四支柱 / pillars」分類**——設計中曾有，現已全部拿掉。資料表、卡片、成效分析**都不要有 pillar 欄位或概念**。品管只靠「守門線分數」。

---

## 3. 技術棧與硬性約束

- **語言/框架**：Python 3.11+、**Streamlit**（UI）、**SQLite**（本機單檔資料庫）、**pytest**（測試）。
- **LLM：可切換 provider（adapter 模式，見 §8）。**
  - 預設：**Google AI Studio（Gemini Flash 免費層）**，例如 `gemini-2.5-flash`／`gemini-2.0-flash`（以當下免費可用者為準）。
  - 備援：**Groq**（開源模型如 `llama-3.3-70b-versatile`，OpenAI 相容 API，免費層）。
  - ⛔ **不要用 Claude 或任何付費模型**（使用者要求免費）。
- **取材**：
  - RSS 解析：`feedparser`。
  - 網頁搜尋：搜尋 API **限定在白名單網域內**，用 Tavily（`tavily-python`）或 Brave Search API 的免費層（Codex 擇一，預設 Tavily）。
- **秘鑰管理**：所有 API key 走環境變數（`.env` + `python-dotenv`）或設定頁輸入，**絕不 hardcode、不要 commit 進 git**。附 `.env.example`。

---

## 4. 四個頁面（Streamlit）

1. **設定頁 Settings**
   - 大主題清單 CRUD：每個主題 = 名稱、綁星期幾、類型（常青/時效）、吃哪幾層來源、每次產幾則。
   - 來源白名單 CRUD：分層 L1–L5，可增刪（見 §6）。
   - 守門線文字（可編輯）。
   - API key 輸入（LLM provider 選擇＋key、搜尋 API key）。

2. **本週選題頁 Radar**（核心）
   - 按「產生本週選題」→ 對每個主題產出數張**候選題目卡**。
   - 每張卡顯示：標題點子、切入角度、**守門線分數 0–100 ＋一句理由**、來源連結。
   - 每張卡操作：**採用 / 淘汰 / 微調**。採用 → 寫入 `ideas`（狀態=採用）。

3. **內容流水線頁 Pipeline**
   - 看板式，欄位＝**候選 / 採用 / 草稿 / 已排程 / 已發**。
   - 卡片可切換狀態、編輯內容。

4. **成效頁 Performance**
   - 已發貼文回填數據（讚 / 觸及 / 互動）。
   - 圖表：**各主題**表現對比。
   - 文字建議：哪個主題強、哪個弱、下週該補哪個。

---

## 5. 內容模型與資料流

**大主題分兩類，取材方式不同：**
- **常青型**（例：AI 新創介紹、拆解某工具原理）→ 不抓取，直接讓 LLM 用自身知識生。
- **時效型**（例：本週熱門 Claude/Codex Skill、AI 近期大事）→ 先抓最新素材再交給 LLM。

**「產生本週選題」的資料流：**
```
for 每個主題:
  if 時效型:
     materials = 抓取(主題綁定的來源層)      # RSS 解析 + 搜尋 API（限白名單網域）
  else:
     materials = []                          # 常青型不抓
  ideas = llm.generate_ideas(主題, materials, 守門線, n)
  存入 ideas 表（狀態=候選）
顯示候選卡
```

---

## 6. 來源白名單（v1 起始值）

以下為初始種子值，之後在設定頁可增刪。

| 層級 | 角色 | 來源 |
|---|---|---|
| **L1 權威報導** | 查證事實 | TechCrunch、iThome AI、科技新報 TechNews |
| **L2 一手來源** | 拆解邏輯（最權威） | OpenAI / Anthropic / Google DeepMind 官方部落格；Y Combinator（新創） |
| **L3 過濾器** | 看本週重點 | TLDR AI、Ben's Bites |
| **L4 熱度偵測器** | 找題目 | Hacker News、GitHub（Trending＋主題搜尋）、Product Hunt(AI)、Reddit r/ClaudeAI、r/LocalLLaMA |
| **L5 觀點（要標立場）** | 補角度 | a16z 部落格、INSIDE |

**三個主題各吃哪幾層：**
- 📰 **AI 近期大事**（時效）→ L1 ＋ L2(labs) ＋ L3 ＋ Hacker News
- 🔧 **本週熱門 Claude/Codex Skill**（時效，**半手動**）→ GitHub 主題/關鍵字搜尋（`claude-skill`、`claude-code-plugin`、`agent-skills`、`codex`、`openai-codex` 等，依「最近建立/最近爆星」排序）＋ 官方 repo releases（`anthropics/skills` 等）＋ 社群 awesome 清單 ＋ r/ClaudeAI。**注意：此主題生態很新、沒有現成排行榜，自動偵測不穩，需允許使用者手動補來源當後備。**
- 🚀 **AI 新創介紹**（常青為主）→ TechCrunch ＋ Y Combinator ＋ Product Hunt ＋ a16z(觀點)

> 取材優先挑「有 RSS / 電子報」的來源（穩、好抓）；X、IG 這類難自動抓、易被擋，v1 不做。

---

## 7. 資料結構（SQLite）

> **無 pillar 欄位。** 欄位可依實作微調，但語意不變。

- **themes**：`id`, `name`, `weekday`(0–6), `kind`(evergreen|timely), `source_layers`(如 "L1,L2,L3"), `n_ideas`(每次產幾則)
- **sources**：`id`, `name`, `url`(或 feed url), `layer`(L1..L5), `fetch_type`(rss|search|manual), `enabled`
- **config**（單列 key-value 或單列表）：`gate_line`(守門線文字), `llm_provider`, `llm_model`, `search_provider`
- **ideas**：`id`, `theme_id`, `title`, `angle`, `gate_score`(int 0–100), `gate_reason`, `source_url`, `status`(候選|採用|草稿|已排程|已發), `body`(草稿內容, 可空), `created_at`
- **performance**：`id`, `idea_id`, `platform`, `likes`, `reach`, `engagement`, `posted_at`

---

## 8. LLM 轉接層契約（interface）

**目的：讓 provider 可切換（Gemini ↔ Groq ↔ 未來其他），上層邏輯不變。**

```python
# 抽象介面
class LLMProvider(Protocol):
    def generate_ideas(
        self, theme_name: str, kind: str, materials: list[Material],
        gate_line: str, n: int
    ) -> list[Idea]: ...

@dataclass
class Material:  # 抓來的一則素材
    title: str
    url: str
    snippet: str

@dataclass
class Idea:
    title: str          # 貼文標題點子
    angle: str          # 切入角度（要體現文組視角/拆解邏輯）
    gate_score: int     # 0–100，服不服務守門線
    gate_reason: str    # 一句話理由
    source_url: str     # 引用來源（時效型必填；常青型可空）
```

**實作要求：**
- 具體 provider（`GeminiProvider`, `GroqProvider`）在 prompt 中要求模型**回傳可解析的 JSON**（陣列），程式端**防禦性解析**（容忍多餘文字、markdown code fence）。
- prompt 必含：主題名、素材清單、**守門線原文**、要產幾則、以及「切入角度要用文組視角＋拆解邏輯、避免紅海 hype 腔」的指示。
- provider 由 `config.llm_provider` 決定，用工廠函式建立。

---

## 9. 錯誤處理

- 某來源抓取失敗 → 只跳過該來源、記錄「本次未取得」，**不讓整批失敗**。
- LLM 回傳無法解析 → **自動重試一次**；再失敗顯示原始回覆讓使用者手動處理。
- 缺 API key → 明確提示到設定頁填。
- 時效型主題本週抓不到新素材 → 提示「要不要手動貼幾個來源？」（manual 後備）。

---

## 10. 非功能性 / 限制

- **免費層速率/每日上限**存在，但用途是「單人、一週產一次選題」，量極小，正常在免費範圍內。
- **隱私提醒**：免費 LLM 層可能將輸入用於改善產品；本工具輸入為公開來源、非機密，可接受（已與使用者確認）。
- 只跑本機、單人；無需登入。

---

## 11. 開發方式

**嚴格 TDD（Red → Green → Refactor）、垂直切片、對外部邊界做契約測試。** 詳細切片順序與每片的測試見 `plan.md`。
