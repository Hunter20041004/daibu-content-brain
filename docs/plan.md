# 呆一布 選題大腦 — v1 實作計畫（Implementation Plan）

> **For agentic workers:** 照本計畫**逐一 Task** 實作。每個 Step 用 `- [ ]` 追蹤。**嚴格 TDD**：先寫失敗測試 → 跑它確認紅 → 最小實作 → 跑它確認綠 → 重構 → commit。**一次一個失敗測試，垂直切片，禁止水平切片。** 先讀 `docs/spec.md` 與 `AGENTS.md`。

**Goal:** 做出單人本機的「選題大腦」——設定主題與來源白名單，讓免費 LLM 從白名單抓最新內容、產出帶守門線分數的貼文候選，經流水線到已發並回填成效。

**Architecture:** 核心邏輯放在可測的 `daibu/` 套件（不依賴 Streamlit）；Streamlit 頁面只做薄薄的 UI 綁定。外部系統（LLM、搜尋、RSS）都藏在有明確介面的模組後面，可 mock、可切換。

**Tech Stack:** Python 3.11+、Streamlit、SQLite（`sqlite3` 標準庫）、pytest、feedparser、tavily-python、google-genai（Gemini）／groq、python-dotenv。

## Global Constraints（每個 Task 都隱含適用）

- Python 3.11+；UI=Streamlit；DB=SQLite 單檔；測試=pytest。
- **LLM 只用免費 provider，做成可切換 adapter**：預設 Gemini Flash，備援 Groq。**⛔ 不得使用 Claude 或任何付費模型。**
- 秘鑰一律走環境變數（`.env` + python-dotenv），**不得 hardcode、不得 commit**；提供 `.env.example`。
- **不得實作 pillar / 四支柱**。品管只有「守門線分數（gate_score 0–100）」。
- 外部邊界（LLM／搜尋／RSS）除 mock 單元測試外，**須有真實邊界的契約測試**；mock 與真實對不上時**修實作、不改 mock**。
- v1 不做：自動製圖、自動發文、自動回留言、多人、雲端。

---

## File Structure

```
daibu-content-brain/
  app.py                 # Streamlit 入口 + 導覽
  pages/                 # Streamlit 頁面（薄）：0_設定.py 1_選題.py 2_流水線.py 3_成效.py
  daibu/
    __init__.py
    models.py            # dataclass: Theme, Source, Material, Idea, Performance
    db.py                # SQLite：init schema + CRUD
    fetch/rss.py         # RSS 抓取
    fetch/search.py      # 搜尋 API（限白名單網域）
    fetch/collector.py   # 依主題的來源層彙整素材
    llm/base.py          # LLMProvider 介面 + 工廠
    llm/prompt.py        # 組 prompt + 解析 JSON
    llm/gemini.py        # GeminiProvider
    llm/groq.py          # GroqProvider
    selection.py         # 產生本週選題（fetch + llm + 存 DB）
    pipeline.py          # 狀態流轉
    performance.py       # 回填成效 + 彙總建議
    seeds.py             # 初始白名單 + 範例主題
  tests/                 # 對應各模組
  requirements.txt
  .env.example
```

**測試共用約定：** 每個測試用**臨時 DB 檔**（pytest `tmp_path` 或 `:memory:`），不碰真實資料。外部呼叫預設 mock；契約測試另外標記（`@pytest.mark.contract`），無 key 時 skip。

---

## Task 1：專案骨架 + 資料層（models + db）

**Files:** Create `requirements.txt`, `.env.example`, `daibu/__init__.py`, `daibu/models.py`, `daibu/db.py`, `tests/test_db.py`

**Interfaces — Produces:**
- `models.Theme(id:int|None, name:str, weekday:int, kind:str, source_layers:list[str], n_ideas:int)`
- `models.Source(id:int|None, name:str, url:str, layer:str, fetch_type:str, enabled:bool)`
- `db.connect(path:str) -> sqlite3.Connection`
- `db.init_schema(conn)`
- `db.add_theme(conn, theme:Theme) -> int`（回傳 id）；`db.get_themes(conn) -> list[Theme]`
- `db.add_source(conn, source:Source) -> int`；`db.get_sources(conn, layer:str|None=None) -> list[Source]`

- [x] **Step 1: 建骨架檔**
`requirements.txt`：
```
streamlit
feedparser
tavily-python
google-genai
groq
python-dotenv
pytest
```
`.env.example`：
```
LLM_PROVIDER=gemini
GEMINI_API_KEY=
GROQ_API_KEY=
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=
```

- [x] **Step 2: 寫失敗測試** `tests/test_db.py`
```python
from daibu import db
from daibu.models import Theme, Source

def test_add_and_get_theme(tmp_path):
    conn = db.connect(str(tmp_path / "t.db")); db.init_schema(conn)
    tid = db.add_theme(conn, Theme(None, "AI 近期大事", weekday=0,
                                   kind="timely", source_layers=["L1","L3"], n_ideas=3))
    got = db.get_themes(conn)
    assert len(got) == 1
    assert got[0].id == tid and got[0].name == "AI 近期大事"
    assert got[0].kind == "timely" and got[0].source_layers == ["L1","L3"]

def test_add_and_get_source_filter_by_layer(tmp_path):
    conn = db.connect(str(tmp_path / "t.db")); db.init_schema(conn)
    db.add_source(conn, Source(None, "TechCrunch", "https://techcrunch.com/feed/", "L1", "rss", True))
    db.add_source(conn, Source(None, "a16z", "https://a16z.com/feed/", "L5", "rss", True))
    assert len(db.get_sources(conn)) == 2
    assert [s.name for s in db.get_sources(conn, layer="L1")] == ["TechCrunch"]
```

- [x] **Step 3: 跑測試確認紅** — `pytest tests/test_db.py -v` → FAIL（module/函式不存在）
- [x] **Step 4: 最小實作** `models.py`（dataclasses）＋ `db.py`。`source_layers` 在 DB 以逗號字串存，讀時 split。schema 依 spec §7（**無 pillar**）。
- [x] **Step 5: 跑測試確認綠** — `pytest tests/test_db.py -v` → PASS
- [x] **Step 6: 重構**（命名、SQL 去重）後全綠
- [x] **Step 7: Commit** — `git init && git add -A && git commit -m "feat: 資料層 models + sqlite db"`（先加 `.gitignore`：`.venv/ .env *.db __pycache__/`）

---

## Task 2：RSS 抓取

**Files:** Create `daibu/fetch/__init__.py`, `daibu/fetch/rss.py`, `tests/test_rss.py`, `tests/fixtures/sample_feed.xml`

**Interfaces — Produces:** `rss.fetch(url:str, limit:int=10) -> list[Material]`；`Material(title:str, url:str, snippet:str)`（加到 `models.py`）

- [x] **Step 1: 放假 feed fixture** `tests/fixtures/sample_feed.xml`（含 2 篇 item：title/link/description）
- [x] **Step 2: 寫失敗測試** `tests/test_rss.py`
```python
from daibu.fetch import rss

def test_fetch_parses_items(monkeypatch):
    import feedparser, pathlib
    raw = pathlib.Path("tests/fixtures/sample_feed.xml").read_text()
    monkeypatch.setattr(rss, "_download", lambda url: raw)   # 不打真網路
    items = rss.fetch("http://example.com/feed", limit=5)
    assert len(items) == 2
    assert items[0].title and items[0].url.startswith("http")
    assert isinstance(items[0].snippet, str)
```

- [x] **Step 3: 跑測試確認紅**
- [x] **Step 4: 最小實作** `rss.py`：`_download(url)` 用 urllib 取字串；`fetch` 用 `feedparser.parse(raw)`，map 成 `Material`（snippet 取 summary 前 N 字、去 HTML）。
- [x] **Step 5: 綠**
- [x] **Step 6: 契約煙霧測試（標記 contract）**
```python
import pytest
@pytest.mark.contract
def test_real_rss_smoke():
    from daibu.fetch import rss
    items = rss.fetch("https://techcrunch.com/feed/", limit=3)
    assert len(items) >= 1 and items[0].title
```
跑 `pytest -m contract -v`（需要網路；CI 可略）。
- [x] **Step 7: Commit** — `feat: RSS 抓取`

---

## Task 3：搜尋抓取（限白名單網域）

**Files:** Create `daibu/fetch/search.py`, `tests/test_search.py`

**Interfaces — Produces:** `search.search(query:str, allowed_domains:list[str], limit:int=5) -> list[Material]`

- [x] **Step 1: 失敗測試（mock Tavily client）**
```python
from daibu.fetch import search

def test_search_maps_and_scopes(monkeypatch):
    fake = {"results":[
        {"title":"A","url":"https://techcrunch.com/x","content":"..."},
        {"title":"B","url":"https://spam.com/y","content":"..."}]}
    monkeypatch.setattr(search, "_raw_search", lambda q, domains, k: fake)
    out = search.search("AI news", allowed_domains=["techcrunch.com"], limit=5)
    assert [m.url for m in out] == ["https://techcrunch.com/x"]   # 網域外被濾掉
```

- [x] **Step 2: 紅**
- [x] **Step 3: 實作** `_raw_search` 呼叫 Tavily（`include_domains=allowed_domains`）；`search` 再做一次網域白名單過濾（雙保險），map 成 `Material`。缺 key → raise 明確錯誤。
- [x] **Step 4: 綠** →（可選 contract 測試打真實 Tavily，標 `@pytest.mark.contract`，無 key skip）
- [x] **Step 5: Commit** — `feat: 白名單內搜尋抓取`

---

## Task 4：Collector（依主題彙整素材，容錯）

**Files:** Create `daibu/fetch/collector.py`, `tests/test_collector.py`

**Interfaces — Produces:** `collector.collect(theme:Theme, sources:list[Source]) -> list[Material]`

- [x] **Step 1: 失敗測試** — 一個 rss source 正常、一個丟例外 → 回傳正常那個的素材、不整批失敗；常青型（kind="evergreen"）回傳 `[]`。
```python
from daibu.fetch import collector
from daibu.models import Theme, Source, Material

def test_collect_skips_failing_source(monkeypatch):
    monkeypatch.setattr(collector.rss, "fetch",
        lambda url, limit=10: (_ for _ in ()).throw(RuntimeError("down"))
        if "bad" in url else [Material("t","https://ok.com/1","s")])
    theme = Theme(1,"大事",0,"timely",["L1"],3)
    srcs = [Source(1,"ok","https://ok.com/feed","L1","rss",True),
            Source(2,"bad","https://bad.com/feed","L1","rss",True)]
    out = collector.collect(theme, srcs)
    assert [m.url for m in out] == ["https://ok.com/1"]

def test_evergreen_returns_empty():
    theme = Theme(1,"新創",0,"evergreen",["L1"],3)
    assert collector.collect(theme, []) == []
```

- [x] **Step 2: 紅** → **Step 3: 實作**（依 `theme.source_layers` 篩 sources；`fetch_type` 分派 rss/search；try/except 逐來源跳過並記 log）→ **Step 4: 綠** → **Step 5: Commit** `feat: collector 容錯彙整`

---

## Task 5：LLM 轉接層（介面 + Gemini + 解析）＋ 契約測試

**Files:** Create `daibu/llm/__init__.py`, `daibu/llm/base.py`, `daibu/llm/prompt.py`, `daibu/llm/gemini.py`, `daibu/llm/groq.py`, `tests/test_llm.py`, `tests/test_llm_contract.py`

**Interfaces — Produces:**
- `base.Idea(title:str, angle:str, gate_score:int, gate_reason:str, source_url:str)`
- `base.LLMProvider`（Protocol，方法 `generate_ideas(theme_name, kind, materials, gate_line, n) -> list[Idea]`）
- `base.get_provider(config) -> LLMProvider`（工廠，依 `LLM_PROVIDER`）
- `prompt.build(...) -> str`；`prompt.parse_ideas(raw:str) -> list[Idea]`（防禦性 JSON 解析）

- [x] **Step 1: 失敗測試（解析，最關鍵）** `tests/test_llm.py`
```python
from daibu.llm import prompt

def test_parse_ideas_tolerates_codefence():
    raw = '''```json
    [{"title":"NotebookLM 整理期中報告","angle":"文組視角拆解",
      "gate_score":88,"gate_reason":"直接對應報告痛點","source_url":"https://x.com/a"}]
    ```'''
    ideas = prompt.parse_ideas(raw)
    assert len(ideas) == 1
    assert ideas[0].gate_score == 88 and isinstance(ideas[0].gate_score, int)
    assert ideas[0].title.startswith("NotebookLM")
```

- [x] **Step 2: 紅** → **Step 3: 實作** `base.py`（dataclass/Protocol/工廠）、`prompt.build`（含主題、素材清單、**守門線原文**、產幾則、以及「切入角度用文組視角＋拆解邏輯、避免紅海 hype 腔、輸出純 JSON 陣列」指示）、`prompt.parse_ideas`（剝除 code fence／多餘文字後 `json.loads`，欄位缺失給預設、gate_score 轉 int）。
- [x] **Step 4: 綠**
- [x] **Step 5: 實作 Gemini/Groq provider** — `GeminiProvider.generate_ideas` 用 `google-genai` 呼叫 → 取回文字 → `prompt.parse_ideas`；`GroqProvider` 用 groq（OpenAI 相容）。加一個測試：mock provider 的底層呼叫回傳固定 JSON，驗證 `generate_ideas` 產出 `list[Idea]`。
- [x] **Step 6: 契約測試（真實邊界，符合 TDD 規範）** `tests/test_llm_contract.py`
```python
import os, pytest
from daibu.llm import base
from daibu.models import Material

@pytest.mark.contract
@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY") and not os.getenv("GROQ_API_KEY"),
                    reason="無 LLM key")
def test_real_llm_returns_parsable_ideas():
    provider = base.get_provider_from_env()
    ideas = provider.generate_ideas(
        "AI 近期大事", "timely",
        [Material("OpenAI 發表新模型","https://openai.com/blog/x","...")],
        gate_line="怕 AI 的文組同學看完會不會覺得我也可以？", n=2)
    assert len(ideas) >= 1
    assert all(0 <= i.gate_score <= 100 for i in ideas)
    assert all(i.title and i.angle for i in ideas)
```
跑 `pytest -m contract`。**若真實輸出無法解析 → 修 `prompt`（強化格式指示/解析容錯），不要放寬 assert。**
- [x] **Step 7: Commit** — `feat: LLM 可切換 adapter（Gemini/Groq）+ 契約測試`

---

## Task 6：產生本週選題（tracer bullet：跑通 fetch→llm→存 DB）

**Files:** Create `daibu/selection.py`, `tests/test_selection.py`

**Interfaces — Produces:** `selection.generate_for_theme(conn, theme:Theme, provider, sources, gate_line:str) -> list[int]`（回傳新建 idea ids，狀態=候選）

- [x] **Step 1: 失敗測試**（mock collector + mock provider，驗證有存進 DB、狀態=候選）
```python
from daibu import selection, db
from daibu.models import Theme, Idea  # 若 Idea 在 llm.base，改 import 來源

def test_generate_persists_candidates(tmp_path, monkeypatch):
    conn = db.connect(str(tmp_path/"t.db")); db.init_schema(conn)
    theme = Theme(None,"大事",0,"timely",["L1"],2)
    monkeypatch.setattr(selection.collector, "collect", lambda t, s: [])
    class FakeP:
        def generate_ideas(self,*a,**k):
            from daibu.llm.base import Idea
            return [Idea("標題","角度",80,"理由","https://x.com/a")]
    ids = selection.generate_for_theme(conn, theme, FakeP(), [], gate_line="…")
    rows = db.get_ideas(conn, status="候選")
    assert len(ids) == 1 and len(rows) == 1 and rows[0].gate_score == 80
```
（本 Task 順帶在 `db.py` 補 `add_idea`／`get_ideas(status=...)`，先寫其測試再實作。）

- [x] **Step 2: 紅** → **Step 3: 實作** `generate_for_theme`（時效型先 `collector.collect`，呼叫 `provider.generate_ideas`，逐一 `db.add_idea(status="候選")`）→ **Step 4: 綠** → **Step 5: 重構** → **Step 6: Commit** `feat: 產生本週選題（存為候選）`

---

## Task 7：內容流水線狀態流轉

**Files:** Create `daibu/pipeline.py`, `tests/test_pipeline.py`

**Interfaces — Produces:** `pipeline.STATUSES = ["候選","採用","草稿","已排程","已發"]`；`pipeline.set_status(conn, idea_id, new_status)`（驗證合法值）；`pipeline.update_body(conn, idea_id, body)`

- [x] **Step 1: 失敗測試** — 合法轉換成功、非法狀態值 raise、可寫入 body。
- [x] **Step 2: 紅** → **Step 3: 實作**（更新 `ideas.status`／`ideas.body`；非法值 `ValueError`）→ **Step 4: 綠** → **Step 5: Commit** `feat: 流水線狀態流轉`

---

## Task 8：成效回填 + 彙總建議

**Files:** Create `daibu/performance.py`, `tests/test_performance.py`

**Interfaces — Produces:** `performance.record(conn, idea_id, platform, likes, reach, engagement)`；`performance.summary_by_theme(conn) -> list[dict]`（每主題平均互動）；`performance.suggest(summary) -> str`

- [x] **Step 1: 失敗測試** — 存兩筆不同主題成效 → summary 依主題彙整 → suggest 指出表現最好/最差主題。
```python
def test_summary_and_suggest(tmp_path):
    ...  # 建 theme A/B、各發一則、record 成效
    s = performance.summary_by_theme(conn)
    assert {r["theme"] for r in s} == {"A","B"}
    txt = performance.suggest(s)
    assert "A" in txt or "B" in txt
```
- [x] **Step 2: 紅** → **Step 3: 實作**（SQL join ideas×performance group by theme；suggest 用簡單規則排序）→ **Step 4: 綠** → **Step 5: Commit** `feat: 成效回填 + 彙總建議`

---

## Task 9：種子資料（初始白名單 + 範例主題）

**Files:** Create `daibu/seeds.py`, `tests/test_seeds.py`

**Interfaces — Produces:** `seeds.load(conn)`（把 spec §6 的白名單與三個範例主題寫入空 DB；已存在則不重複）

- [x] **Step 1: 失敗測試** — 空 DB 執行 `seeds.load` 後，sources 含 L1–L5、themes 含三個範例（大事/Skill/新創），且再跑一次不重複。
- [x] **Step 2: 紅** → **Step 3: 實作**（依 spec §6 表格；用 name 去重）→ **Step 4: 綠** → **Step 5: Commit** `feat: 種子白名單與範例主題`

---

## Task 10：Streamlit 四頁 UI（薄組裝）

**Files:** Create `app.py`, `pages/0_設定.py`, `pages/1_選題.py`, `pages/2_流水線.py`, `pages/3_成效.py`, `tests/test_app_smoke.py`

**約定：** UI 只呼叫 `daibu/` 的函式，**不放商業邏輯**。首次啟動若 DB 空 → 呼叫 `seeds.load`。

- [ ] **Step 1: 煙霧測試** 用 `streamlit.testing.v1.AppTest` 驗證各頁能載入不報錯（DB 用臨時檔、LLM/搜尋 mock 掉）。
```python
from streamlit.testing.v1 import AppTest
def test_selection_page_loads(monkeypatch, tmp_path):
    # 設環境變數指向臨時 DB、mock generate_for_theme
    at = AppTest.from_file("pages/1_選題.py"); at.run()
    assert not at.exception
```
- [ ] **Step 2: 紅** → **Step 3: 實作四頁**：
  - `0_設定`：主題/來源 CRUD 表單、守門線文字、provider 與 key。
  - `1_選題`：「產生本週選題」按鈕 → 對每個「今天該發」的主題呼叫 `selection.generate_for_theme` → 候選卡（採用/淘汰/微調 → `pipeline.set_status`）。
  - `2_流水線`：依 `pipeline.STATUSES` 分欄顯示 `db.get_ideas`，可改狀態/編 body。
  - `3_成效`：回填表單 → `performance.record`；顯示 `summary_by_theme` 圖表 + `suggest` 文字。
- [ ] **Step 4: 綠**（`pytest`）＋ 人工 `streamlit run app.py` 走一遍
- [ ] **Step 5: Commit** — `feat: Streamlit 四頁 UI 串接`

---

## 收尾檢查（Codex 做完全部 Task 後）

- [ ] `pytest` 全綠；`pytest -m contract`（有 key 時）通過，確認 LLM/RSS 真實邊界如預期。
- [ ] `streamlit run app.py` 能走完：設定主題→產生選題→採用→流水線→回填成效→看到建議。
- [ ] `docs/open-questions.md` 若有累積疑點，整理給人類裁決。

---

## Self-Review（本計畫對照 spec 的覆蓋檢查）

- spec §4 四頁 → Task 10 ✅；§5 資料流 → Task 4+6 ✅；§6 白名單 → Task 9 ✅；§7 資料表 → Task 1(+6 補 ideas)✅；§8 LLM 契約 → Task 5 ✅；§9 錯誤處理 → Task 4（來源容錯）、Task 5 Step6（解析容錯/重試）✅；§2 無 pillar → 全表無 pillar 欄 ✅；免費/可切換 LLM → Task 5 ✅。
- 型別一致：`Material`（Task 2 定義，Task 3/4/5/6 使用）、`Idea`（Task 5 `llm.base` 定義，Task 6 使用）、`STATUSES`（Task 7 定義，Task 10 使用）— 一致。
