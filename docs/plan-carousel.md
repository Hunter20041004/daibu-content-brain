# TDD 實作計畫：貼文輪播圖產生器（Task 1–17）

設計依據：`docs/specs/2026-07-28-貼文輪播圖產生器-design.md`。
**每一條有疑問的地方都以那份規格為準，不要自行更動產品方向。**

**目標**：讓「AI 新創介紹」這個主題，從選題到產出一整套可以直接發的 IG 輪播圖。

**架構**：分兩階段。階段 A 先讓選題產得出具體公司（因為沒有公司名，階段 B 的 AI
不知道要介紹誰）；階段 B 才做產圖。階段 A 自己就有價值，中途停下來交付的是
「選題變好用了」，不是半個功能。

**技術棧**：Python 3.11、Streamlit、SQLite、Playwright（本輪新增）、
LINE Seed TW 字型。

**視覺一律以網站 PRD（DIVE AI 官網）為上游**——配色、字體、間距、吉祥物姿勢
都對齊它，詳見設計規格 §11。

---

## 給 Codex 的作業規則

- **嚴格 TDD、垂直切片**：一次只寫**一個**失敗測試 → 讓它綠 → 重構 → 下一個。
  禁止「先寫完 t1,t2,t3 再寫 i1,i2,i3」的水平切法。
- 每個 Task 做完就 `commit`，訊息寫清楚做了哪一刀。
- 用專案自己的環境：`.venv/bin/python`、`.venv/bin/pytest`。
- **紅→綠循環只跑當前那一個測試檔**，Task 收尾才跑一次全套（省 token）。
- 頁面層的測試用 `streamlit.testing.v1.AppTest`，`tests/test_app_smoke.py` 有完整範例
  （`monkeypatch.setenv("DAIBU_DB_PATH", ...)` 建臨時資料庫 → `AppTest.from_file(...)`
  → 對 `app.markdown` / `app.button` 斷言）。
- 設計層疑點寫進 `docs/open-questions.md`，不要自行拍板。

### 紅線（一個字都不准改）

- `daibu/theme.py` 的 `LIGHT` / `DARK` 色票**數值**
- `tests/test_theme.py` 裡所有既有的對比度斷言
- `daibu/fetch/rss.py`、`daibu/fetch/search.py`

### 基線

目前 `codex/ia-topic-first` 上 `.venv/bin/pytest -q` 為
`167 passed, 3 deselected`。每個 Task 完成後這個數字只能往上加，不能有紅燈。

---

## Global Constraints（全域約束，每個 Task 都適用）

- **貼文圖的顏色一律寫死**，不得使用會隨深淺模式變動的 CSS 變數或 `light-dark()`。
  貼文圖是要匯出的成品，不是介面。（規格 §6.3）
- **配色只能用這幾個值**（全部對齊網站 PRD）：外框 `#D5E6F4`、白卡 `#FBFCFE`、
  文字 `#47819A`、次級文字 `#8F8FA2`、強調 `#F8C5A9`、吉祥物機身 `#8ACDD6`。
  **強調色只有一個，且面積不得超過畫面 10%。**
  主色 `#8ACDD6` **不可**當白底上的文字（對比不足），文字一律 `#47819A`。
- **畫布尺寸固定 1080 × 1350**（4:5 直式）。
- **字體只用 LINE Seed TW**，中英文皆同，且**只用 400／700／800 三個字重**。
  PRD 明文禁止 `font-weight: 500 / 600` 與斜體。
- **白卡圓角 40px、陰影 `0 6px 36px rgba(38,38,65,.06)`、間距一律 4 的倍數。**
- **不得呼叫任何圖片生成 API。**
- 頁型 slug 固定為：`cover`、`who`、`problem`、`how-ai`、`results`、`why-care`、`cta`。
- 吉祥物姿勢 slug 固定為：`wave`、`think`、`happy`、`point`、`note`、`confused`、`lost`
  （七種，與網站共用；貼文只用到前五種）。

### 語氣鐵律（來自網站 PRD，寫進 AI 指令）

1. 講邏輯，不講工具
2. **降低焦慮，不製造焦慮**——嚴禁「不懂就落伍」「不學就被取代」這類框架
3. 知道下一步——CTA 要給具體去處，不是空喊追蹤

---

## 檔案結構

| 檔案 | 負責什麼 | 動作 |
|---|---|---|
| `daibu/db.py` | schema、搬遷、CRUD | 修改 |
| `daibu/models.py` | `StoredIdea` 加兩欄 | 修改 |
| `daibu/llm/base.py` | `Idea` 加兩欄 | 修改 |
| `daibu/llm/prompt.py` | 選題指令改寫、輪播指令新增 | 修改 |
| `daibu/seeds.py` | 「AI 新創介紹」的來源清單 | 修改 |
| `daibu/cards/__init__.py` | 套件 | 新增 |
| `daibu/cards/pages.py` | 七格結構、姿勢對應、字數上限（純資料，無相依） | 新增 |
| `daibu/cards/draft.py` | 呼叫 LLM 產草稿並存進 DB | 新增 |
| `daibu/cards/render.py` | 一格資料 → 一份 HTML | 新增 |
| `daibu/cards/shoot.py` | HTML → PNG → zip（唯一碰 Playwright 的檔案） | 新增 |
| `daibu/cards/templates/ai-startup.html` | 版面 | 新增 |
| `daibu/cards/templates/ai-startup.css` | 配色、字體、pattern | 新增 |
| `assets/fonts/LINESeedTW_OTF_*.otf` | 三個字重的字型檔（出圖不依賴網路） | 新增 |
| `assets/mascot/*.svg` | 七種姿勢（與網站共用） | 新增 |
| `pages/1_選題.py` | 候選卡片、產貼圖區塊 | 修改 |
| `requirements.txt` | 加 `playwright` | 修改 |

**`daibu/cards/` 底下四個檔案刻意分開**：`pages.py` 是純資料、`draft.py` 只碰 LLM 與 DB、
`render.py` 只碰字串、`shoot.py` 只碰 Playwright。這樣前三個都能在沒有瀏覽器的環境下測試，
只有 `shoot.py` 需要真的開瀏覽器。

---

# 階段 A — 讓選題產得出具體公司（Task 1–6）

> 做完這段就先讓使用者看一次。這段自己就有交付價值。

## Task 1 — `ideas` 新增 `company` 與 `source_excerpt` 兩欄

**Files:**
- Modify: `daibu/db.py:181-256`（`init_schema`）
- Test: `tests/test_db_migration.py`

**Interfaces:**
- Produces：`ideas` 資料表多出 `company TEXT NOT NULL DEFAULT ''` 與
  `source_excerpt TEXT NOT NULL DEFAULT ''` 兩欄。

- [ ] **Step 1: 寫失敗的測試**

在 `tests/test_db_migration.py` 末尾新增：

```python
def test_adds_company_and_excerpt_columns_to_existing_db(tmp_path):
    """舊資料庫升級後要多出兩欄，且既有題目不得消失。"""
    path = tmp_path / "old.db"
    conn = db.connect(str(path))
    db.init_schema(conn)
    conn.execute(
        """
        INSERT INTO ideas (theme_id, title, angle, status)
        VALUES (NULL, '舊題目', '舊切角', '候選')
        """
    )
    conn.commit()
    # 模擬舊結構：把新欄位拿掉
    conn.execute("ALTER TABLE ideas DROP COLUMN company")
    conn.execute("ALTER TABLE ideas DROP COLUMN source_excerpt")
    conn.commit()
    conn.close()

    conn = db.connect(str(path))
    db.init_schema(conn)

    columns = {row["name"] for row in conn.execute("PRAGMA table_info(ideas)")}
    assert "company" in columns
    assert "source_excerpt" in columns

    rows = conn.execute("SELECT title, company FROM ideas").fetchall()
    assert len(rows) == 1
    assert rows[0]["title"] == "舊題目"
    assert rows[0]["company"] == ""
    conn.close()
```

- [ ] **Step 2: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_db_migration.py::test_adds_company_and_excerpt_columns_to_existing_db -q`
Expected: FAIL — `assert 'company' in columns`

- [ ] **Step 3: 最小實作**

在 `daibu/db.py` 的 `init_schema` 裡，`CREATE TABLE IF NOT EXISTS ideas` 的
`source_url` 後面加上兩欄定義：

```sql
company TEXT NOT NULL DEFAULT '',
source_excerpt TEXT NOT NULL DEFAULT '',
```

然後在 `conn.executescript(...)` 之後、`DELETE FROM config` 之前，加上補欄邏輯
（`CREATE TABLE IF NOT EXISTS` 對已存在的表不會補欄，所以必須另外處理）：

```python
    idea_columns = _table_columns(conn, "ideas")
    for column in ("company", "source_excerpt"):
        if column not in idea_columns:
            conn.execute(
                f"ALTER TABLE ideas ADD COLUMN {column} TEXT NOT NULL DEFAULT ''"
            )
```

- [ ] **Step 4: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_db_migration.py -q`
Expected: PASS（含既有的搬遷測試全綠）

- [ ] **Step 5: Commit**

```bash
git add daibu/db.py tests/test_db_migration.py
git commit -m "feat(db): ideas 新增 company 與 source_excerpt 欄位"
```

---

## Task 2 — `Idea` / `StoredIdea` 帶上新欄位，讀寫接通

**Files:**
- Modify: `daibu/llm/base.py:10-14`（`Idea`）
- Modify: `daibu/models.py:29-39`（`StoredIdea`）
- Modify: `daibu/db.py:481-532`（`add_idea`、`get_ideas`）
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes：Task 1 的兩個欄位。
- Produces：
  - `Idea(title, angle, source_url, company='', source_excerpt='')`
  - `StoredIdea(..., company: str, source_excerpt: str)`
  - `db.add_idea` 會寫入這兩欄，`db.get_ideas` 會讀回來。

- [ ] **Step 1: 寫失敗的測試**

在 `tests/test_db.py` 末尾新增：

```python
def test_add_and_get_idea_keeps_company_and_excerpt(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea = Idea(
        title="讓文字開口說話",
        angle="語音合成的成本結構被改寫",
        source_url="https://example.com/a",
        company="ElevenLabs",
        source_excerpt="ElevenLabs 於 2022 年在倫敦成立。",
    )

    idea_id = db.add_idea(conn, None, idea)
    stored = [item for item in db.get_ideas(conn) if item.id == idea_id][0]

    assert stored.company == "ElevenLabs"
    assert stored.source_excerpt == "ElevenLabs 於 2022 年在倫敦成立。"
    conn.close()
```

（`Idea` 從 `daibu.llm.base` 匯入；`tests/test_db.py` 已有匯入區塊，加上去即可。）

- [ ] **Step 2: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_db.py::test_add_and_get_idea_keeps_company_and_excerpt -q`
Expected: FAIL — `TypeError: Idea.__init__() got an unexpected keyword argument 'company'`

- [ ] **Step 3: 最小實作**

`daibu/llm/base.py`：

```python
@dataclass(frozen=True)
class Idea:
    title: str
    angle: str
    source_url: str
    company: str = ""
    source_excerpt: str = ""
```

`daibu/models.py`：`StoredIdea` 加上兩個欄位（放在 `source_url` 之後）：

```python
    company: str = ""
    source_excerpt: str = ""
```

`daibu/db.py` 的 `add_idea`：INSERT 欄位改成

```python
        """
        INSERT INTO ideas (
            theme_id, title, angle, source_url, company, source_excerpt,
            status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            theme_id,
            idea.title,
            idea.angle,
            idea.source_url,
            idea.company,
            idea.source_excerpt,
            status,
            _now(),
        ),
```

`daibu/db.py` 的 `get_ideas`：`StoredIdea(...)` 加上

```python
            company=row["company"],
            source_excerpt=row["source_excerpt"],
```

- [ ] **Step 4: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_db.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add daibu/llm/base.py daibu/models.py daibu/db.py tests/test_db.py
git commit -m "feat: Idea 與 StoredIdea 帶上 company 與 source_excerpt"
```

---

## Task 3 — 產候選的指令改寫成「找出一家具體公司」

**Files:**
- Modify: `daibu/llm/prompt.py:7-62`
- Test: `tests/test_llm.py`

**Interfaces:**
- Consumes：Task 2 的 `Idea` 新欄位。
- Produces：
  - `prompt.build(theme_name, materials, n, avoid_titles=None)` 產出的字串含
    「公司」「不要產出沒有公司名」等要求，且要求 JSON 物件含
    `company`、`title`、`angle`、`source_url`、`source_excerpt` 五個鍵。
  - `prompt.parse_ideas(raw)` 會讀出 `company` 與 `source_excerpt`。

- [ ] **Step 1: 寫失敗的測試（先測 parse）**

在 `tests/test_llm.py` 末尾新增：

```python
def test_parse_ideas_reads_company_and_excerpt():
    raw = """[
      {"company": "ElevenLabs",
       "title": "讓文字開口說話",
       "angle": "配音成本被改寫",
       "source_url": "https://example.com/a",
       "source_excerpt": "2022 年於倫敦成立。"}
    ]"""

    ideas = prompt.parse_ideas(raw)

    assert ideas[0].company == "ElevenLabs"
    assert ideas[0].source_excerpt == "2022 年於倫敦成立。"
```

- [ ] **Step 2: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_llm.py::test_parse_ideas_reads_company_and_excerpt -q`
Expected: FAIL — `AttributeError` 或 `assert '' == 'ElevenLabs'`

- [ ] **Step 3: 最小實作**

`daibu/llm/prompt.py` 的 `parse_ideas`，在 `Idea(...)` 裡加上：

```python
            company=str(item.get("company", "")),
            source_excerpt=str(item.get("source_excerpt", "")),
```

- [ ] **Step 4: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_llm.py::test_parse_ideas_reads_company_and_excerpt -q`
Expected: PASS

- [ ] **Step 5: 寫第二個失敗的測試（改 build）**

```python
def test_build_prompt_demands_a_named_company():
    materials = [Material(title="t", url="https://example.com/a", snippet="s")]

    text = prompt.build("AI 新創介紹", materials, 3)

    assert "公司" in text
    assert "company" in text
    assert "source_excerpt" in text
    # 明確禁止產出無公司名的通用觀點文
    assert "沒有公司名" in text
    # 寧可少產也不要湊數
    assert "寧可少產" in text
```

- [ ] **Step 6: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_llm.py::test_build_prompt_demands_a_named_company -q`
Expected: FAIL — `assert 'company' in text`

- [ ] **Step 7: 改寫 `build()` 的「要求」段落**

把 `daibu/llm/prompt.py:37-41` 那段要求整段換成：

```python
要求：
- 每一則候選必須是**一家具體的公司**，而且公司名要出現在素材裡，不可憑印象編造。
- 嚴禁產出沒有公司名的通用觀點文（例如「文組生在 AI 新創的價值」這類）。
- 若素材裡找得到的公司不足 {n} 家，寧可少產幾則，也不要湊數。
- 切入角度使用文組視角，拆解邏輯，避免紅海 hype 腔。
- source_url 必須是該公司所依據的那一則素材的網址。
- source_excerpt 是該素材中支持這則候選的原文片段，原樣抄錄，不要改寫。
- 只輸出 JSON 陣列，不要 Markdown 或額外說明。
- 每個物件只含 company、title、angle、source_url、source_excerpt。
```

其中 `title` 是「一句話說明這家公司在做什麼」，`angle` 是「為什麼現在值得講」——
把這兩句也寫進要求裡。

- [ ] **Step 8: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_llm.py -q`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add daibu/llm/prompt.py tests/test_llm.py
git commit -m "feat(llm): 選題指令改為必須產出具體公司"
```

---

## Task 4 — 「AI 新創介紹」的來源收斂到 5 個

**Files:**
- Modify: `daibu/seeds.py:55-75`
- Modify: `daibu/db.py`（新增一次性收斂）
- Test: `tests/test_seeds.py`

**Interfaces:**
- Produces：`db.init_schema` 執行後，若 `config` 沒有 `startup_sources_pruned`
  標記，就把「AI 新創介紹」的 `theme_sources` 收斂到 5 個，然後寫入標記。

**為什麼要一次性搬遷而不只改 seeds**：seeds 只在資料庫全新時灌一次，
使用者現有的 `daibu.db` 已經綁了 15 個，只改 seeds 對他無效。
用 `config` 標記確保只跑一次，使用者之後自己加回來也不會被再次刪掉。

- [ ] **Step 1: 寫失敗的測試**

在 `tests/test_seeds.py` 末尾新增：

```python
KEEP = {"Product Hunt AI", "Y Combinator Blog", "a16z", "TechCrunch", "INSIDE"}


def test_startup_theme_sources_are_pruned_once(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    seeds.load_if_empty(conn)

    theme = [t for t in db.get_themes(conn) if t.name == "AI 新創介紹"][0]
    names = {
        s.name for s in db.get_sources(conn) if s.id in set(theme.source_ids)
    }
    assert names == KEEP

    # 使用者自己加回一個之後，再跑一次 init_schema 不可以又被刪掉
    other = [s for s in db.get_sources(conn) if s.name == "Hacker News"][0]
    conn.execute(
        "INSERT INTO theme_sources (theme_id, source_id) VALUES (?, ?)",
        (theme.id, other.id),
    )
    conn.commit()

    db.init_schema(conn)

    theme = [t for t in db.get_themes(conn) if t.name == "AI 新創介紹"][0]
    names = {
        s.name for s in db.get_sources(conn) if s.id in set(theme.source_ids)
    }
    assert "Hacker News" in names
    conn.close()
```

（`seeds.load_if_empty` 的實際函式名以 `daibu/seeds.py` 現況為準，
若不同名就改成實際的那個。）

- [ ] **Step 2: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_seeds.py::test_startup_theme_sources_are_pruned_once -q`
Expected: FAIL — `assert {15 個名字} == {5 個名字}`

- [ ] **Step 3: 最小實作**

`daibu/seeds.py:58-74` 的來源清單換成：

```python
        [
            "Product Hunt AI",
            "Y Combinator Blog",
            "a16z",
            "TechCrunch",
            "INSIDE",
        ],
```

`daibu/db.py` 的 `init_schema`，在補欄邏輯之後加上：

```python
    already_pruned = conn.execute(
        "SELECT 1 FROM config WHERE key = 'startup_sources_pruned'"
    ).fetchone()
    if not already_pruned and _table_exists(conn, "theme_sources"):
        conn.execute(
            """
            DELETE FROM theme_sources
            WHERE theme_id IN (SELECT id FROM themes WHERE name = 'AI 新創介紹')
              AND source_id NOT IN (
                  SELECT id FROM sources WHERE name IN (
                      'Product Hunt AI', 'Y Combinator Blog',
                      'a16z', 'TechCrunch', 'INSIDE'
                  )
              )
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
            ("startup_sources_pruned", "1"),
        )
```

- [ ] **Step 4: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_seeds.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add daibu/seeds.py daibu/db.py tests/test_seeds.py
git commit -m "feat: AI 新創介紹的來源收斂到 5 個並一次性清理既有綁定"
```

---

## Task 5 — 候選卡片顯示公司名與來源

**Files:**
- Modify: `pages/1_選題.py`（候選卡片渲染的區塊）
- Test: `tests/test_app_smoke.py`

**Interfaces:**
- Consumes：`StoredIdea.company`、`StoredIdea.source_url`。
- Produces：候選區塊的畫面上會出現公司名；`company` 為空時顯示「未指定公司」。

- [ ] **Step 1: 寫失敗的測試**

在 `tests/test_app_smoke.py` 末尾新增：

```python
def test_candidate_shows_company_name(tmp_path, monkeypatch):
    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn, Theme(id=None, name="AI 新創介紹", weekday=4,
                    source_ids=[], n_ideas=3)
    )
    db.add_idea(
        conn,
        theme_id,
        Idea(
            title="讓文字開口說話",
            angle="配音成本被改寫",
            source_url="https://example.com/a",
            company="ElevenLabs",
            source_excerpt="2022 年於倫敦成立。",
        ),
    )
    conn.close()

    app = AppTest.from_file("pages/1_選題.py").run()
    rendered = " ".join(block.value for block in app.markdown)

    assert "ElevenLabs" in rendered


def test_candidate_without_company_shows_placeholder(tmp_path, monkeypatch):
    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn, Theme(id=None, name="AI 新創介紹", weekday=4,
                    source_ids=[], n_ideas=3)
    )
    db.add_idea(conn, theme_id, Idea(title="舊題目", angle="舊切角", source_url=""))
    conn.close()

    app = AppTest.from_file("pages/1_選題.py").run()
    rendered = " ".join(block.value for block in app.markdown)

    assert "未指定公司" in rendered
```

- [ ] **Step 2: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_app_smoke.py::test_candidate_shows_company_name -q`
Expected: FAIL — `assert 'ElevenLabs' in rendered`

- [ ] **Step 3: 最小實作**

在 `pages/1_選題.py` 渲染候選的地方，公司名放在標題**之前**（它是判斷要不要採用的第一眼），
來源連結放在切角之後：

```python
company_label = idea.company or "未指定公司"
st.markdown(
    f'<div class="idea-company">{html.escape(company_label)}</div>',
    unsafe_allow_html=True,
)
```

樣式加在 `daibu/theme.py` 既有的 CSS 裡（**不得在 `pages/` 寫死色碼**），
字級小於標題、用 `var(--brand-secondary)`。

來源連結：`source_url` 非空時渲染成可點的連結，空的時候不渲染。

- [ ] **Step 4: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_app_smoke.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pages/1_選題.py daibu/theme.py tests/test_app_smoke.py
git commit -m "feat(ui): 候選卡片顯示公司名與來源連結"
```

---

## Task 6 — 階段 A 收尾：跑全套並讓使用者驗收

- [ ] **Step 1: 跑全套測試**

Run: `.venv/bin/pytest -q`
Expected: 通過數 > 167，`0 failed`

- [ ] **Step 2: 用複本實際跑一次（不要碰真實資料庫）**

```bash
cp daibu.db /tmp/daibu-carousel.db
DAIBU_DB_PATH=/tmp/daibu-carousel.db .venv/bin/streamlit run app.py --server.port 8502
```

確認三件事：
1. 舊的 6 則候選還在，公司名顯示「未指定公司」，沒有壞掉
2. 「AI 新創介紹」的來源在設定頁只剩 5 個
3. 實際按「產生候選」，新產出的候選有公司名（**會花 AI 額度與幾秒**）

- [ ] **Step 3: 記錄結果並回報**

把測試數字與上面三點的實際結果寫進 `HANDOFF.md` 的「本輪狀態」，
**停下來讓使用者驗收，不要直接往階段 B 衝。**

---

# 階段 B — 產輪播圖（Task 7–17）

## Task 7 — 七格結構的定義（純資料）

**Files:**
- Create: `daibu/cards/__init__.py`（空檔）
- Create: `daibu/cards/pages.py`
- Test: `tests/test_cards_pages.py`

**Interfaces:**
- Produces：
  - `pages.PAGE_TYPES: tuple[str, ...]` — 七個 slug，順序即頁序
  - `pages.MASCOT_FOR: dict[str, str]` — 頁型 → 姿勢 slug
  - `pages.LIMITS: dict[str, int]` — `"hook"`, `"company"`, `"heading"`, `"body"`
  - `pages.label(page_type: str) -> str` — 頁型的中文標籤

- [ ] **Step 1: 寫失敗的測試**

Create `tests/test_cards_pages.py`：

```python
from daibu.cards import pages


def test_seven_page_types_in_order():
    assert pages.PAGE_TYPES == (
        "cover", "who", "problem", "how-ai", "results", "why-care", "cta",
    )


def test_every_page_type_maps_to_a_known_mascot_pose():
    """七種姿勢與網站 PRD 共用；貼文只會用到其中五種。"""
    assert pages.POSES == (
        "wave", "think", "happy", "point", "note", "confused", "lost",
    )
    assert set(pages.MASCOT_FOR) == set(pages.PAGE_TYPES)
    assert set(pages.MASCOT_FOR.values()) <= set(pages.POSES)


def test_character_limits_match_spec():
    assert pages.LIMITS == {
        "hook": 20, "company": 16, "heading": 14, "body": 60,
    }


def test_label_returns_chinese_name():
    assert pages.label("how-ai") == "他們怎麼運用 AI"


def test_why_care_page_uses_the_brand_voice_name():
    """沿用網站 PRD 週報的「呆一布這週怎麼看」，讓兩邊是同一個聲音。"""
    assert pages.label("why-care") == "呆一布怎麼看"
```

- [ ] **Step 2: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_cards_pages.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'daibu.cards'`

- [ ] **Step 3: 最小實作**

Create `daibu/cards/__init__.py`（空檔）。

Create `daibu/cards/pages.py`：

```python
PAGE_TYPES = (
    "cover", "who", "problem", "how-ai", "results", "why-care", "cta",
)

# 七種姿勢與網站 PRD 共用同一組素材；貼文只用到前五種，
# confused 與 lost 是網站的空狀態與 404 頁在用的。
POSES = ("wave", "think", "happy", "point", "note", "confused", "lost")

MASCOT_FOR = {
    "cover": "wave",
    "who": "point",
    "problem": "think",
    "how-ai": "point",
    "results": "happy",
    "why-care": "note",
    "cta": "wave",
}

LIMITS = {"hook": 20, "company": 16, "heading": 14, "body": 60}

_LABELS = {
    "cover": "封面",
    "who": "他們是誰",
    "problem": "他們盯上什麼問題",
    "how-ai": "他們怎麼運用 AI",
    "results": "做出了什麼",
    "why-care": "呆一布怎麼看",
    "cta": "結尾",
}


def label(page_type: str) -> str:
    return _LABELS[page_type]
```

- [ ] **Step 4: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_cards_pages.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add daibu/cards/ tests/test_cards_pages.py
git commit -m "feat(cards): 七格結構、姿勢對應與字數上限"
```

---

## Task 8 — `carousel_pages` 資料表與讀寫

**Files:**
- Modify: `daibu/db.py`（`init_schema` 加表；檔案末尾加 CRUD）
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes：Task 7 的 `pages.PAGE_TYPES`。
- Produces：
  - `db.save_carousel(conn, idea_id, rows) -> None`
    `rows` 是 `list[dict]`，每個含 `page_no`、`page_type`、`heading`、`body`、
    `grounding`、`source_quote`。**整份覆寫**（先刪該 idea 的舊列再插入）。
  - `db.get_carousel(conn, idea_id) -> list[sqlite3.Row]`，依 `page_no` 排序
  - `db.update_carousel_page(conn, page_id, heading, body) -> None`

- [ ] **Step 1: 寫失敗的測試**

在 `tests/test_db.py` 末尾新增：

```python
def _seven_rows():
    from daibu.cards import pages
    return [
        {
            "page_no": index + 1,
            "page_type": page_type,
            "heading": f"標題{index}",
            "body": f"內文{index}",
            "grounding": "source" if index < 3 else "model",
            "source_quote": "原文" if index < 3 else "",
        }
        for index, page_type in enumerate(pages.PAGE_TYPES)
    ]


def test_save_and_get_carousel(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(conn, None, Idea(title="t", angle="a", source_url=""))

    db.save_carousel(conn, idea_id, _seven_rows())
    got = db.get_carousel(conn, idea_id)

    assert [row["page_no"] for row in got] == [1, 2, 3, 4, 5, 6, 7]
    assert got[0]["page_type"] == "cover"
    assert got[6]["grounding"] == "model"
    conn.close()


def test_save_carousel_overwrites_previous_draft(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(conn, None, Idea(title="t", angle="a", source_url=""))

    db.save_carousel(conn, idea_id, _seven_rows())
    db.save_carousel(conn, idea_id, _seven_rows())

    assert len(db.get_carousel(conn, idea_id)) == 7
    conn.close()


def test_update_single_carousel_page(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(conn, None, Idea(title="t", angle="a", source_url=""))
    db.save_carousel(conn, idea_id, _seven_rows())
    page_id = db.get_carousel(conn, idea_id)[0]["id"]

    db.update_carousel_page(conn, page_id, "新標題", "新內文")

    assert db.get_carousel(conn, idea_id)[0]["heading"] == "新標題"
    conn.close()
```

- [ ] **Step 2: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_db.py::test_save_and_get_carousel -q`
Expected: FAIL — `AttributeError: module 'daibu.db' has no attribute 'save_carousel'`

- [ ] **Step 3: 最小實作**

`daibu/db.py` 的 `init_schema` 的 `executescript` 裡加一張表：

```sql
        CREATE TABLE IF NOT EXISTS carousel_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id INTEGER NOT NULL,
            page_no INTEGER NOT NULL,
            page_type TEXT NOT NULL,
            heading TEXT NOT NULL DEFAULT '',
            body TEXT NOT NULL DEFAULT '',
            grounding TEXT NOT NULL DEFAULT 'model',
            source_quote TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (idea_id) REFERENCES ideas(id)
        );
```

檔案末尾加三個函式：

```python
def save_carousel(
    conn: sqlite3.Connection,
    idea_id: int,
    rows: list[dict],
) -> None:
    conn.execute("DELETE FROM carousel_pages WHERE idea_id = ?", (idea_id,))
    conn.executemany(
        """
        INSERT INTO carousel_pages (
            idea_id, page_no, page_type, heading, body,
            grounding, source_quote, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                idea_id,
                row["page_no"],
                row["page_type"],
                row["heading"],
                row["body"],
                row["grounding"],
                row["source_quote"],
                _now(),
            )
            for row in rows
        ],
    )
    conn.commit()


def get_carousel(conn: sqlite3.Connection, idea_id: int) -> list:
    return conn.execute(
        "SELECT * FROM carousel_pages WHERE idea_id = ? ORDER BY page_no",
        (idea_id,),
    ).fetchall()


def update_carousel_page(
    conn: sqlite3.Connection,
    page_id: int,
    heading: str,
    body: str,
) -> None:
    conn.execute(
        """
        UPDATE carousel_pages
        SET heading = ?, body = ?, updated_at = ?
        WHERE id = ?
        """,
        (heading, body, _now(), page_id),
    )
    conn.commit()
```

- [ ] **Step 4: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_db.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add daibu/db.py tests/test_db.py
git commit -m "feat(db): carousel_pages 資料表與讀寫"
```

---

## Task 9 — 刪除連帶清乾淨，淘汰要保留草稿

**Files:**
- Modify: `daibu/db.py`（`delete_idea`、`delete_theme`、`count_theme_content`）
- Modify: `pages/1_選題.py`（刪主題的告知訊息）
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes：Task 8 的 `carousel_pages`。
- Produces：`db.count_theme_content` 多回傳一個「輪播草稿份數」。

**這個專案上一輪出過「刪主題產生孤兒題目」的資料錯誤，這一刀就是防同一類問題。**

- [ ] **Step 1: 寫失敗的測試**

在 `tests/test_db.py` 末尾新增：

```python
def test_rejecting_idea_keeps_its_carousel(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(conn, None, Idea(title="t", angle="a", source_url=""))
    db.save_carousel(conn, idea_id, _seven_rows())

    pipeline.set_status(conn, idea_id, "已淘汰")

    assert len(db.get_carousel(conn, idea_id)) == 7
    conn.close()


def test_deleting_idea_removes_its_carousel(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(conn, None, Idea(title="t", angle="a", source_url=""))
    db.save_carousel(conn, idea_id, _seven_rows())

    db.delete_idea(conn, idea_id)

    orphans = conn.execute("SELECT COUNT(*) AS n FROM carousel_pages").fetchone()
    assert orphans["n"] == 0
    conn.close()


def test_deleting_theme_removes_carousels_of_its_ideas(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn, Theme(id=None, name="X", weekday=1, source_ids=[], n_ideas=3)
    )
    idea_id = db.add_idea(conn, theme_id, Idea(title="t", angle="a", source_url=""))
    db.save_carousel(conn, idea_id, _seven_rows())

    db.delete_theme(conn, theme_id)

    orphans = conn.execute("SELECT COUNT(*) AS n FROM carousel_pages").fetchone()
    assert orphans["n"] == 0
    conn.close()
```

- [ ] **Step 2: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_db.py::test_deleting_idea_removes_its_carousel -q`
Expected: FAIL — `assert 7 == 0`

- [ ] **Step 3: 最小實作**

`daibu/db.py` 的 `delete_idea`，在刪 idea 之前加：

```python
    conn.execute("DELETE FROM carousel_pages WHERE idea_id = ?", (idea_id,))
```

`daibu/db.py` 的 `delete_theme`，在刪題目之前加：

```python
    conn.execute(
        """
        DELETE FROM carousel_pages
        WHERE idea_id IN (SELECT id FROM ideas WHERE theme_id = ?)
        """,
        (theme_id,),
    )
```

`count_theme_content` 加上輪播草稿份數的計算，回傳值多一項。
`pages/1_選題.py` 的刪主題確認訊息改成同時說明會刪掉幾則題目與幾份輪播草稿。

- [ ] **Step 4: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_db.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add daibu/db.py pages/1_選題.py tests/test_db.py
git commit -m "fix(db): 刪除連帶清掉輪播草稿，淘汰則保留"
```

---

## Task 10 — 輪播草稿的指令與解析（含依據標記）

**Files:**
- Modify: `daibu/llm/prompt.py`（末尾新增兩個函式）
- Test: `tests/test_llm.py`

**Interfaces:**
- Consumes：Task 7 的 `pages.PAGE_TYPES`、`pages.LIMITS`。
- Produces：
  - `prompt.build_carousel(company, title, angle, source_excerpt) -> str`
  - `prompt.parse_carousel(raw) -> list[dict]`，七個 dict，鍵為
    `page_no`、`page_type`、`heading`、`body`、`grounding`、`source_quote`

- [ ] **Step 1: 寫失敗的測試（先測 parse）**

```python
def test_parse_carousel_returns_seven_pages_with_grounding():
    raw = """[
      {"page_type": "cover", "heading": "讓文字開口說話",
       "body": "ElevenLabs", "grounding": "source",
       "source_quote": "2022 年於倫敦成立。"},
      {"page_type": "who", "heading": "他們是誰", "body": "英國新創",
       "grounding": "source", "source_quote": "2022 年於倫敦成立。"},
      {"page_type": "problem", "heading": "配音很貴", "body": "小團隊做不起",
       "grounding": "model", "source_quote": ""},
      {"page_type": "how-ai", "heading": "學會說話的節奏", "body": "不只唸字",
       "grounding": "model", "source_quote": ""},
      {"page_type": "results", "heading": "誰在用", "body": "有聲書與遊戲",
       "grounding": "model", "source_quote": ""},
      {"page_type": "why-care", "heading": "成本被改寫", "body": "內容產業變了",
       "grounding": "model", "source_quote": ""},
      {"page_type": "cta", "heading": "追蹤呆一布", "body": "每週五更新",
       "grounding": "model", "source_quote": ""}
    ]"""

    got = prompt.parse_carousel(raw)

    assert len(got) == 7
    assert [row["page_no"] for row in got] == [1, 2, 3, 4, 5, 6, 7]
    assert got[0]["grounding"] == "source"
    assert got[2]["grounding"] == "model"
    assert got[2]["source_quote"] == ""


def test_parse_carousel_rejects_wrong_page_count():
    with pytest.raises(ValueError):
        prompt.parse_carousel('[{"page_type": "cover"}]')


def test_parse_carousel_defaults_unknown_grounding_to_model():
    """AI 沒標或亂標時，一律當成需查證，不可預設為有依據。"""
    payload = [
        {"page_type": page_type, "heading": "h", "body": "b"}
        for page_type in (
            "cover", "who", "problem", "how-ai", "results", "why-care", "cta",
        )
    ]
    got = prompt.parse_carousel(json.dumps(payload, ensure_ascii=False))

    assert {row["grounding"] for row in got} == {"model"}
```

- [ ] **Step 2: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_llm.py::test_parse_carousel_returns_seven_pages_with_grounding -q`
Expected: FAIL — `AttributeError: module has no attribute 'parse_carousel'`

- [ ] **Step 3: 最小實作**

`daibu/llm/prompt.py` 末尾：

```python
def parse_carousel(raw: str) -> list[dict]:
    from daibu.cards import pages as card_pages

    array_start = raw.find("[")
    if array_start < 0:
        raise ValueError("LLM 回覆中找不到 JSON 陣列")
    decoded, _ = json.JSONDecoder().raw_decode(raw[array_start:])
    if not isinstance(decoded, list):
        raise ValueError("LLM 回覆的 JSON 必須是陣列")
    if len(decoded) != len(card_pages.PAGE_TYPES):
        raise ValueError(
            f"輪播必須剛好 {len(card_pages.PAGE_TYPES)} 頁，收到 {len(decoded)} 頁"
        )

    rows = []
    for index, item in enumerate(decoded):
        grounding = str(item.get("grounding", "")).strip().lower()
        if grounding != "source":
            grounding = "model"
        rows.append(
            {
                "page_no": index + 1,
                "page_type": card_pages.PAGE_TYPES[index],
                "heading": str(item.get("heading", "")),
                "body": str(item.get("body", "")),
                "grounding": grounding,
                "source_quote": (
                    str(item.get("source_quote", "")) if grounding == "source" else ""
                ),
            }
        )
    return rows
```

**注意 `grounding` 的預設值是 `model`**——AI 沒標或亂標時一律當成需查證，
絕不可預設成「有依據」，那會讓使用者誤以為某格查過了。

- [ ] **Step 4: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_llm.py -q`
Expected: PASS

- [ ] **Step 5: 寫第二個失敗的測試（build_carousel）**

```python
def test_build_carousel_prompt_carries_limits_and_grounding_rule():
    text = prompt.build_carousel(
        "ElevenLabs", "讓文字開口說話", "配音成本被改寫", "2022 年於倫敦成立。"
    )

    assert "ElevenLabs" in text
    assert "2022 年於倫敦成立。" in text
    assert "grounding" in text
    # 字數上限要寫進指令
    assert "14" in text and "60" in text
    # 七個頁型都要出現
    for page_type in ("cover", "who", "problem", "how-ai", "results",
                      "why-care", "cta"):
        assert page_type in text


def test_build_carousel_prompt_forbids_anxiety_framing():
    """網站 PRD 第二條營運鐵律：降低焦慮，不製造焦慮。"""
    text = prompt.build_carousel("ElevenLabs", "t", "a", "片段")

    assert "焦慮" in text
    assert "落伍" in text
    assert "取代" in text
```

- [ ] **Step 6: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_llm.py::test_build_carousel_prompt_carries_limits_and_grounding_rule -q`
Expected: FAIL — `AttributeError: module has no attribute 'build_carousel'`

- [ ] **Step 7: 實作 `build_carousel`**

```python
def build_carousel(
    company: str,
    title: str,
    angle: str,
    source_excerpt: str,
) -> str:
    from daibu.cards import pages as card_pages

    limits = card_pages.LIMITS
    outline = "\n".join(
        f"{index + 1}. {page_type} — {card_pages.label(page_type)}"
        for index, page_type in enumerate(card_pages.PAGE_TYPES)
    )
    return f"""
你是「呆一布 AI 共學實驗室」社群組的貼文編輯。
請為以下這家公司寫一份 IG 輪播貼文，剛好 {len(card_pages.PAGE_TYPES)} 頁。

公司：{company}
它在做什麼：{title}
為什麼現在值得講：{angle}
原文片段：{source_excerpt}

頁序與每頁要寫的東西（順序不可更動）：
{outline}

這則貼文是在介紹「一家公司如何運用 AI」，不是在教讀者怎麼使用工具。
不要寫定價、不要寫操作步驟。第 4 頁 how-ai 是整份的核心，要寫得最具體。
第 6 頁 why-care 是「呆一布怎麼看」，要寫自己的觀點，不是複述新聞。

呆一布的三條語氣鐵律，每一頁都適用：
1. **講邏輯，不講工具**——寫「為什麼這樣做」，不是「又出了什麼新東西」。
2. **降低焦慮，不製造焦慮**——嚴禁「不懂就落伍」「不學就被取代」
   「再不跟上就來不及」這類寫法。第 6 頁最容易犯，因為「值得注意」
   很容易被寫成威脅。正確做法是講清楚它改變了什麼，讓讀者自己判斷。
3. **知道下一步**——第 7 頁 cta 要給具體去處與時間（例如這個系列每週幾更新），
   不可只寫「追蹤我們」「留言告訴我」這種空話。

字數上限（超過就自己縮短，不可截成半句）：
- 第 1 頁的 heading（鉤子）最多 {limits["hook"]} 字，body 放公司名，最多 {limits["company"]} 字元
- 第 2–7 頁的 heading 最多 {limits["heading"]} 字，body 最多 {limits["body"]} 字

每一頁都要標 grounding：
- 寫成 "source"：這頁的內容在上面的原文片段裡找得到，
  並在 source_quote 原樣抄錄支持它的那一句
- 寫成 "model"：原文片段裡沒有，是你從自己的知識補的，source_quote 留空字串

**不確定的時候一律標 "model"。** 標錯成 "source" 會讓編輯以為查證過了。
數字（融資金額、用戶數、成立年份）除非原文片段裡明確出現，否則一律標 "model"。

只輸出 JSON 陣列，不要 Markdown 或額外說明。
每個物件只含 page_type、heading、body、grounding、source_quote。
""".strip()
```

- [ ] **Step 8: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_llm.py -q`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add daibu/llm/prompt.py tests/test_llm.py
git commit -m "feat(llm): 輪播草稿的指令與解析，含依據標記"
```

---

## Task 11 — 產草稿並存進資料庫

**Files:**
- Create: `daibu/cards/draft.py`
- Test: `tests/test_cards_draft.py`

**Interfaces:**
- Consumes：`prompt.build_carousel`、`prompt.parse_carousel`、`db.save_carousel`。
- Produces：`draft.generate(conn, idea, generate_text) -> list[dict]`
  其中 `generate_text: Callable[[str], str]` 是「餵一段字串、回一段字串」的函式，
  這樣測試可以直接傳假的進去，不必碰真的 LLM。

- [ ] **Step 1: 寫失敗的測試**

Create `tests/test_cards_draft.py`：

```python
import json

from daibu import db
from daibu.cards import draft, pages
from daibu.llm.base import Idea


def _fake_response() -> str:
    return json.dumps(
        [
            {
                "page_type": page_type,
                "heading": f"標題{index}",
                "body": f"內文{index}",
                "grounding": "source" if index == 0 else "model",
                "source_quote": "原文" if index == 0 else "",
            }
            for index, page_type in enumerate(pages.PAGE_TYPES)
        ],
        ensure_ascii=False,
    )


def test_generate_saves_seven_pages(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea(
            title="讓文字開口說話",
            angle="配音成本被改寫",
            source_url="https://example.com/a",
            company="ElevenLabs",
            source_excerpt="2022 年於倫敦成立。",
        ),
    )
    idea = [item for item in db.get_ideas(conn) if item.id == idea_id][0]

    rows = draft.generate(conn, idea, lambda _prompt: _fake_response())

    assert len(rows) == 7
    assert len(db.get_carousel(conn, idea_id)) == 7
    conn.close()


def test_generate_passes_company_into_the_prompt(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea(title="t", angle="a", source_url="", company="ElevenLabs",
             source_excerpt="片段"),
    )
    idea = [item for item in db.get_ideas(conn) if item.id == idea_id][0]
    seen = {}

    def spy(prompt_text: str) -> str:
        seen["text"] = prompt_text
        return _fake_response()

    draft.generate(conn, idea, spy)

    assert "ElevenLabs" in seen["text"]
    assert "片段" in seen["text"]
    conn.close()


def test_generate_refuses_when_company_is_empty(tmp_path):
    """沒有公司名就不該送出去燒額度。"""
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(conn, None, Idea(title="t", angle="a", source_url=""))
    idea = [item for item in db.get_ideas(conn) if item.id == idea_id][0]

    called = []

    try:
        draft.generate(conn, idea, lambda text: called.append(text) or "")
    except ValueError as error:
        assert "公司" in str(error)
    else:
        raise AssertionError("空公司名應該要擋下來")

    assert called == []
    conn.close()
```

- [ ] **Step 2: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_cards_draft.py -q`
Expected: FAIL — `ImportError: cannot import name 'draft'`

- [ ] **Step 3: 最小實作**

Create `daibu/cards/draft.py`：

```python
import sqlite3
from typing import Callable

from daibu import db
from daibu.llm import prompt
from daibu.models import StoredIdea


def generate(
    conn: sqlite3.Connection,
    idea: StoredIdea,
    generate_text: Callable[[str], str],
) -> list[dict]:
    if not idea.company.strip():
        raise ValueError("這則題目沒有公司名，無法產生輪播草稿")

    prompt_text = prompt.build_carousel(
        idea.company,
        idea.title,
        idea.angle,
        idea.source_excerpt,
    )
    rows = prompt.parse_carousel(generate_text(prompt_text))
    db.save_carousel(conn, idea.id, rows)
    return rows
```

- [ ] **Step 4: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_cards_draft.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add daibu/cards/draft.py tests/test_cards_draft.py
git commit -m "feat(cards): 產生輪播草稿並存進資料庫"
```

---

## Task 12 — 字型檔與七種吉祥物姿勢

**Files:**
- Create: `assets/fonts/LINESeedTW_OTF_Rg.otf`、`_Bd.otf`、`_XBd.otf`、`OFL.txt`
- Create: `assets/mascot/wave.svg`、`think.svg`、`happy.svg`、`point.svg`、
  `note.svg`、`confused.svg`、`lost.svg`
- Test: `tests/test_cards_assets.py`

**Interfaces:**
- Produces：`assets/mascot/<pose>.svg` 七個檔案，每個是可獨立渲染的 SVG。

**做法**：以 `assets/mascot.svg` 為底（它是幾何 SVG：長方形、圓形、path），
改寫出七種姿勢。**不呼叫任何生圖 API。**

**七種是與網站 PRD 合併後的清單**（PRD 已定義揮手／困惑／開心／思考／迷路五種，
本專案另需指引與筆記兩種）。貼文只用得到前五種，但一次畫齊比日後補畫更容易
維持是同一隻，且網站可以共用同一組素材。

| 姿勢 | 怎麼改 | 誰在用 |
|---|---|---|
| `wave` | 右側加一條舉起的手臂 path，掌心朝外；嘴巴維持笑弧 | 貼文封面／結尾、網站 hero |
| `think` | 右側手臂彎起靠近臉頰；嘴巴改成一條短斜線；眼睛改成上弧 | 貼文問題頁、網站載入中 |
| `happy` | 兩側各一條舉高的手臂；眼睛改成 `^` 形（兩條短弧）；嘴巴弧度加大 | 貼文成果頁、網站成就卡 |
| `point` | 右側加一條水平伸出的手臂 path，末端一個小圓當手 | 貼文的 who／how-ai |
| `note` | 左側手臂前伸，前方加一個小圓角矩形當筆記本 | 貼文的呆一布怎麼看 |
| `confused` | 頭部微傾；嘴巴改成波浪線；頭頂右上加一個問號 | 網站空狀態 |
| `lost` | 兩隻手臂垂下攤開；眼睛改成兩個小點；嘴巴改成一條平線 | 網站 404 |

**顏色一律寫死**（機身 `#8ACDD6`、臉板 `#FBFCFE`、墨 `#47819A`、強調 `#F8C5A9`），
**不使用 CSS 變數**——這些 SVG 會被嵌進貼文圖，不是介面元素。
注意這組顏色已對齊網站 PRD 的色票。

- [ ] **Step 1: 寫失敗的測試**

Create `tests/test_cards_assets.py`：

```python
from pathlib import Path

from daibu.cards import pages

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def test_every_mascot_pose_file_exists():
    """七種都要有——網站共用同一組素材。"""
    for pose in pages.POSES:
        path = ASSETS / "mascot" / f"{pose}.svg"
        assert path.exists(), f"缺少姿勢素材：{path}"


def test_mascot_svgs_do_not_use_css_variables():
    """貼文圖是匯出的成品，顏色不得跟著介面深淺變。"""
    for pose in pages.POSES:
        text = (ASSETS / "mascot" / f"{pose}.svg").read_text(encoding="utf-8")
        assert "var(--" not in text, f"{pose}.svg 不得使用 CSS 變數"


def test_mascot_svgs_use_the_prd_palette():
    """機身必須是品牌主色，不得自創顏色。"""
    for pose in pages.POSES:
        text = (ASSETS / "mascot" / f"{pose}.svg").read_text(encoding="utf-8")
        assert "#8ACDD6" in text, f"{pose}.svg 的機身色不是品牌主色"


def test_three_font_weights_are_bundled():
    """出圖不得依賴網路字型，否則匯出的圖會跟預覽不一樣。"""
    for name in (
        "LINESeedTW_OTF_Rg.otf",
        "LINESeedTW_OTF_Bd.otf",
        "LINESeedTW_OTF_XBd.otf",
    ):
        assert (ASSETS / "fonts" / name).exists(), f"缺少字重：{name}"


def test_font_license_is_bundled():
    assert (ASSETS / "fonts" / "OFL.txt").exists()
```

- [ ] **Step 2: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_cards_assets.py -q`
Expected: FAIL — `缺少姿勢素材`

- [ ] **Step 3: 下載字型、畫七個 SVG**

字型是 **LINE Seed TW**（LINE 與華康合作，2025-08 發布，SIL 開放字型授權 1.1，
免費商用，14,038 個字符）。**不在 Google Fonts 上**，從官網下載：

<https://seed.line.me/index_tw.html>

解壓後把 Regular／Bold／ExtraBold 三個字重放進 `assets/fonts/`，
授權條款存成 `assets/fonts/OFL.txt`。

```bash
mkdir -p assets/fonts
# 手動下載並解壓後確認：
ls -la assets/fonts/
```

確認每個字重的檔案大小合理（繁中字型通常數 MB 到十幾 MB，不是幾百 bytes）。
**若官網改版導致檔名不同，以實際檔名為準，同步改掉測試裡的檔名。**

七個姿勢 SVG 以 `assets/mascot.svg` 為底改寫，放進 `assets/mascot/`。

- [ ] **Step 4: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_cards_assets.py -q`
Expected: PASS

- [ ] **Step 5: 目視檢查（不可跳過）**

把七個 SVG 併排寫成一份暫時的 HTML，用瀏覽器打開截圖，確認：
- 七隻看起來是同一隻角色（頭型、比例、配色一致）
- 姿勢看得出差別
- 沒有破圖、路徑沒有斷開

**截圖附在回報裡給使用者挑。不滿意就退回重畫，這是使用者明確要參與的一步。**
這組素材網站也會用，所以值得多花時間挑。

- [ ] **Step 6: Commit**

```bash
git add assets/fonts/ assets/mascot/ tests/test_cards_assets.py
git commit -m "feat(assets): LINE Seed TW 字型與七種吉祥物姿勢 SVG"
```

---

## Task 13 — 模板與 HTML 渲染

**Files:**
- Create: `daibu/cards/templates/ai-startup.html`
- Create: `daibu/cards/templates/ai-startup.css`
- Create: `daibu/cards/render.py`
- Test: `tests/test_cards_render.py`

**Interfaces:**
- Consumes：Task 7 的 `pages`、Task 12 的素材。
- Produces：`render.page_html(row: dict, company: str) -> str`
  回傳一份完整的、可獨立開啟的 HTML（CSS 內嵌、字型以 `file://` 絕對路徑載入、
  吉祥物 SVG 內嵌）。

- [ ] **Step 1: 寫失敗的測試**

Create `tests/test_cards_render.py`：

```python
import html as html_lib

from daibu.cards import pages, render


def _row(page_type="cover", heading="讓文字開口說話", body="ElevenLabs"):
    return {
        "page_no": pages.PAGE_TYPES.index(page_type) + 1,
        "page_type": page_type,
        "heading": heading,
        "body": body,
        "grounding": "model",
        "source_quote": "",
    }


def test_html_contains_the_text():
    out = render.page_html(_row(), company="ElevenLabs")
    assert "讓文字開口說話" in out
    assert "ElevenLabs" in out


def test_html_declares_the_exact_canvas_size():
    out = render.page_html(_row(), company="ElevenLabs")
    assert "1080" in out and "1350" in out


def test_html_has_no_theme_dependent_colors():
    """貼文圖的顏色必須寫死。"""
    out = render.page_html(_row(), company="ElevenLabs")
    assert "var(--" not in out
    assert "light-dark(" not in out
    assert "prefers-color-scheme" not in out


def test_html_embeds_the_matching_mascot_pose():
    out = render.page_html(_row("problem"), company="ElevenLabs")
    think_svg = (render.ASSETS / "mascot" / "think.svg").read_text(encoding="utf-8")
    assert think_svg.split(">", 1)[1][:60] in out


def test_html_escapes_user_text():
    out = render.page_html(_row(heading='<script>x</script>'), company="A")
    assert "<script>x</script>" not in out
    assert html_lib.escape("<script>x</script>") in out


def test_font_is_loaded_from_local_files():
    out = render.page_html(_row(), company="ElevenLabs")
    assert "LINESeedTW_OTF_Rg.otf" in out
    assert "LINESeedTW_OTF_XBd.otf" in out
    assert "http" not in out.split("</style>")[0].replace("file://", "")


def test_only_permitted_font_weights_are_used():
    """網站 PRD 明文禁止 500 / 600 與斜體。"""
    out = render.page_html(_row(), company="ElevenLabs")
    assert "font-weight: 500" not in out
    assert "font-weight: 600" not in out
    assert "font-style: italic" not in out


def test_colors_match_the_brand_palette():
    out = render.page_html(_row(), company="ElevenLabs")
    assert "#D5E6F4" in out and "#FBFCFE" in out and "#47819A" in out
    # 已作廢的舊色不得殘留
    for retired in ("#2E5C9E", "#F6BCC8", "#E8912D", "#5B8FC9"):
        assert retired not in out, f"{retired} 是改版前的舊色，不該出現"
```

- [ ] **Step 2: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_cards_render.py -q`
Expected: FAIL — `ImportError: cannot import name 'render'`

- [ ] **Step 3: 寫模板與 `render.py`**

`daibu/cards/templates/ai-startup.css` 的重點（完整版面照規格 §6.2）：

```css
@font-face {
  font-family: "LINE Seed TW"; font-weight: 400;
  src: url("__FONT_RG__") format("opentype");
}
@font-face {
  font-family: "LINE Seed TW"; font-weight: 700;
  src: url("__FONT_BD__") format("opentype");
}
@font-face {
  font-family: "LINE Seed TW"; font-weight: 800;
  src: url("__FONT_XBD__") format("opentype");
}
html, body { margin: 0; padding: 0; }
.canvas {
  width: 1080px; height: 1350px; position: relative; overflow: hidden;
  background: #D5E6F4;
  font-family: "LINE Seed TW", sans-serif; color: #47819A;
  font-weight: 400;
}
.stripes {
  position: absolute; left: 0; bottom: 0; width: 560px; height: 320px;
  background: repeating-linear-gradient(
    -16deg, rgba(255,255,255,.9) 0 16px, transparent 16px 45px);
  -webkit-mask-image: linear-gradient(to top right, #000 24%, transparent 76%);
}
.dots {
  position: absolute; right: 0; top: 0; width: 500px; height: 400px;
  background-image: radial-gradient(rgba(255,255,255,.85) 24%, transparent 26%);
  background-size: 34px 34px;
  -webkit-mask-image: linear-gradient(to bottom left, #000 14%, transparent 70%);
}
.card {
  position: absolute; inset: 70px; border-radius: 40px; background: #FBFCFE;
  box-shadow: 0 6px 36px rgba(38,38,65,.06);
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 88px 72px; text-align: center;
}
.tag {
  font-size: 32px; font-weight: 700; letter-spacing: .2em;
  color: #8F8FA2; margin-bottom: 48px;
}
.heading {
  font-size: 72px; font-weight: 800; line-height: 1.3; letter-spacing: .04em;
}
.mark {
  background: linear-gradient(180deg, transparent 58%,
              #F8C5A9 58%, #F8C5A9 96%, transparent 96%);
  padding: 0 4px;
}
.body { font-size: 44px; font-weight: 400; line-height: 1.75; margin-top: 44px; }
.company { font-size: 104px; font-weight: 800; line-height: 1.15; margin-top: 48px; }
.mascot { width: 216px; margin-top: 48px; }
.handle {
  position: absolute; right: 100px; bottom: 96px;
  font-size: 32px; font-weight: 400; letter-spacing: .12em; color: #8F8FA2;
}
```

**字重只能用 400／700／800**（網站 PRD 明文禁止 500／600 與斜體）。
層次靠字重與字級一起做——標題 800、標籤 700、內文 400。
所有間距都是 4 的倍數。強調色 `#F8C5A9` 只用在 `.mark` 底線，面積遠低於 10%。

`daibu/cards/render.py`：

```python
import html
from pathlib import Path

from daibu.cards import pages

ASSETS = Path(__file__).resolve().parent.parent.parent / "assets"
TEMPLATES = Path(__file__).resolve().parent / "templates"


def _mascot_svg(page_type: str) -> str:
    pose = pages.MASCOT_FOR[page_type]
    return (ASSETS / "mascot" / f"{pose}.svg").read_text(encoding="utf-8")


FONT_FILES = {
    "__FONT_RG__": "LINESeedTW_OTF_Rg.otf",
    "__FONT_BD__": "LINESeedTW_OTF_Bd.otf",
    "__FONT_XBD__": "LINESeedTW_OTF_XBd.otf",
}


def page_html(row: dict, company: str) -> str:
    css = (TEMPLATES / "ai-startup.css").read_text(encoding="utf-8")
    for token, filename in FONT_FILES.items():
        css = css.replace(token, (ASSETS / "fonts" / filename).as_uri())

    shell = (TEMPLATES / "ai-startup.html").read_text(encoding="utf-8")
    is_cover = row["page_type"] == "cover"
    main = (
        f'<div class="heading">{html.escape(row["heading"])}</div>'
        f'<div class="company">{html.escape(company)}</div>'
        if is_cover
        else f'<div class="heading">{html.escape(row["heading"])}</div>'
        f'<div class="body">{html.escape(row["body"])}</div>'
    )
    return (
        shell.replace("__CSS__", css)
        .replace("__TAG__", html.escape(pages.label(row["page_type"])))
        .replace("__MAIN__", main)
        .replace("__MASCOT__", _mascot_svg(row["page_type"]))
    )
```

`daibu/cards/templates/ai-startup.html`：

```html
<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<style>__CSS__</style></head>
<body><div class="canvas">
  <div class="stripes"></div><div class="dots"></div>
  <div class="card">
    <div class="tag">__TAG__</div>
    __MAIN__
    <div class="mascot">__MASCOT__</div>
  </div>
  <div class="handle">@呆一布</div>
</div></body></html>
```

- [ ] **Step 4: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_cards_render.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add daibu/cards/render.py daibu/cards/templates/ tests/test_cards_render.py
git commit -m "feat(cards): 貼文圖模板與 HTML 渲染"
```

---

## Task 14 — Playwright 出圖（含像素契約測試）

**Files:**
- Create: `daibu/cards/shoot.py`
- Modify: `requirements.txt`
- Modify: `README.md`、`AGENTS.md`（補安裝步驟）
- Test: `tests/test_cards_shoot.py`

**Interfaces:**
- Consumes：Task 13 的 `render.page_html`。
- Produces：`shoot.png_bytes(html_text: str) -> bytes`（單張 1080×1350 的 PNG）

**這一刀是規格 §7.1 指名的風險**：匯出的圖跟預覽不一樣。
**必須真的產一張圖出來檢查像素，不可以只測函式有沒有被呼叫。**

- [ ] **Step 1: 裝 Playwright**

```bash
echo "playwright" >> requirements.txt
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
```

在 `README.md` 與 `AGENTS.md` 的安裝段落補上
`.venv/bin/playwright install chromium`（首次約 150 MB）。

- [ ] **Step 2: 寫失敗的測試**

Create `tests/test_cards_shoot.py`：

```python
import io
import struct

import pytest

from daibu.cards import pages, render, shoot


def _png_size(data: bytes) -> tuple[int, int]:
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def _row():
    return {
        "page_no": 1, "page_type": "cover",
        "heading": "讓文字開口說話", "body": "ElevenLabs",
        "grounding": "model", "source_quote": "",
    }


@pytest.mark.contract
def test_png_has_the_exact_canvas_size():
    data = shoot.png_bytes(render.page_html(_row(), company="ElevenLabs"))
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert _png_size(data) == (1080, 1350)


@pytest.mark.contract
def test_frame_and_card_pixels_are_the_specified_colors():
    """真的看畫出來的像素，不是看函式回傳值。"""
    from PIL import Image

    data = shoot.png_bytes(render.page_html(_row(), company="ElevenLabs"))
    image = Image.open(io.BytesIO(data)).convert("RGB")

    # 左上角 (20, 20) 在白卡外，應該是外框淡藍
    assert image.getpixel((20, 20)) == (0xD5, 0xE6, 0xF4)
    # 畫布正中央在白卡內，應該是 PRD 的卡片背景色
    assert image.getpixel((540, 300)) == (0xFB, 0xFC, 0xFE)


@pytest.mark.contract
def test_text_actually_rendered_with_the_bundled_font():
    """字型沒載到的話，文字區域會是空白的一片白。"""
    from PIL import Image

    data = shoot.png_bytes(render.page_html(_row(), company="ElevenLabs"))
    image = Image.open(io.BytesIO(data)).convert("RGB")

    band = [
        image.getpixel((x, 470))
        for x in range(140, 940, 4)
    ]
    inked = [pixel for pixel in band if sum(pixel) < 600]
    assert len(inked) > 20, "白卡中央那一橫排完全沒有深色像素，代表字沒有畫出來"
```

`pytest.ini` 若尚未有 `contract` 標記，補上
`markers = contract: 需要真實瀏覽器的契約測試`。**這三個測試預設要跑**
（Playwright 是本機相依，不像 Tavily 需要金鑰）。

`Pillow` 加進 `requirements.txt`（只有測試用，但列進去比較省事）。

- [ ] **Step 3: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_cards_shoot.py -q`
Expected: FAIL — `ImportError: cannot import name 'shoot'`

- [ ] **Step 4: 最小實作**

Create `daibu/cards/shoot.py`：

```python
from playwright.sync_api import sync_playwright

WIDTH = 1080
HEIGHT = 1350


def png_bytes(html_text: str) -> bytes:
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        try:
            page = browser.new_page(
                viewport={"width": WIDTH, "height": HEIGHT},
                device_scale_factor=1,
            )
            page.set_content(html_text, wait_until="load")
            # 字型與 pattern 都畫完才截圖，否則會拍到半成品
            page.evaluate("() => document.fonts.ready")
            return page.locator(".canvas").screenshot(type="png")
        finally:
            browser.close()
```

- [ ] **Step 5: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_cards_shoot.py -q`
Expected: PASS（第一次會比較慢，要開瀏覽器）

若 `test_text_actually_rendered_with_the_bundled_font` 紅燈，**不要改測試的門檻**，
先確認 `@font-face` 的 `file://` 路徑對不對、`document.fonts.ready` 有沒有真的等到。

- [ ] **Step 6: Commit**

```bash
git add daibu/cards/shoot.py requirements.txt README.md AGENTS.md pytest.ini tests/test_cards_shoot.py
git commit -m "feat(cards): Playwright 出圖與像素契約測試"
```

---

## Task 15 — 超長文字不得爆版

**Files:**
- Modify: `daibu/cards/render.py`
- Test: `tests/test_cards_shoot.py`

**Interfaces:**
- Produces：`render.page_html` 會把超過 `pages.LIMITS` 的字截到上限並補「…」。

**這一刀是規格 §7.2 指名的風險。** AI 產的字沒有硬性保證，指令只是要求，
模板這一層必須自己擋住。

- [ ] **Step 1: 寫失敗的測試**

在 `tests/test_cards_shoot.py` 末尾新增：

```python
@pytest.mark.contract
def test_absurdly_long_text_does_not_overflow_the_canvas():
    from PIL import Image

    row = {
        "page_no": 3, "page_type": "problem",
        "heading": "配" * 200, "body": "音" * 800,
        "grounding": "model", "source_quote": "",
    }
    data = shoot.png_bytes(render.page_html(row, company="A" * 200))
    image = Image.open(io.BytesIO(data)).convert("RGB")

    assert _png_size(data) == (1080, 1350)
    # 畫布最底一橫排必須還是外框色，代表文字沒有溢出白卡撐破版面
    bottom = [image.getpixel((x, 1345)) for x in range(0, 1080, 40)]
    assert all(pixel == (0xD5, 0xE6, 0xF4) for pixel in bottom)
```

- [ ] **Step 2: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_cards_shoot.py::test_absurdly_long_text_does_not_overflow_the_canvas -q`
Expected: FAIL — 底部像素不是外框色

- [ ] **Step 3: 最小實作**

在 `daibu/cards/render.py` 加上截斷，並在 `page_html` 裡套用：

```python
def clamp(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"
```

`page_html` 裡：`cover` 的 heading 用 `LIMITS["hook"]`、company 用 `LIMITS["company"]`；
其餘頁的 heading 用 `LIMITS["heading"]`、body 用 `LIMITS["body"]`。

- [ ] **Step 4: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_cards_shoot.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add daibu/cards/render.py tests/test_cards_shoot.py
git commit -m "fix(cards): 超長文字截斷，不得撐破畫布"
```

---

## Task 16 — 打包成 zip

**Files:**
- Modify: `daibu/cards/shoot.py`
- Test: `tests/test_cards_shoot.py`

**Interfaces:**
- Produces：`shoot.zip_bytes(rows: list[dict], company: str) -> bytes`
  檔名格式 `01-cover.png` … `07-cta.png`

- [ ] **Step 1: 寫失敗的測試**

```python
@pytest.mark.contract
def test_zip_contains_seven_numbered_pngs():
    import zipfile

    rows = [
        {
            "page_no": index + 1, "page_type": page_type,
            "heading": f"標題{index}", "body": f"內文{index}",
            "grounding": "model", "source_quote": "",
        }
        for index, page_type in enumerate(pages.PAGE_TYPES)
    ]

    data = shoot.zip_bytes(rows, company="ElevenLabs")

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = sorted(archive.namelist())
    assert names == [
        "01-cover.png", "02-who.png", "03-problem.png", "04-how-ai.png",
        "05-results.png", "06-why-care.png", "07-cta.png",
    ]
```

- [ ] **Step 2: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_cards_shoot.py::test_zip_contains_seven_numbered_pngs -q`
Expected: FAIL — `AttributeError: module has no attribute 'zip_bytes'`

- [ ] **Step 3: 最小實作**

在 `daibu/cards/shoot.py` 加上（**只開一次瀏覽器跑完七張**，不要每張都開一次）：

```python
import io
import zipfile

from daibu.cards import render


def zip_bytes(rows: list[dict], company: str) -> bytes:
    buffer = io.BytesIO()
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        try:
            page = browser.new_page(
                viewport={"width": WIDTH, "height": HEIGHT},
                device_scale_factor=1,
            )
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                for row in rows:
                    page.set_content(
                        render.page_html(row, company), wait_until="load"
                    )
                    page.evaluate("() => document.fonts.ready")
                    archive.writestr(
                        f"{row['page_no']:02d}-{row['page_type']}.png",
                        page.locator(".canvas").screenshot(type="png"),
                    )
        finally:
            browser.close()
    return buffer.getvalue()
```

- [ ] **Step 4: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_cards_shoot.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add daibu/cards/shoot.py tests/test_cards_shoot.py
git commit -m "feat(cards): 七張圖打包成 zip"
```

---

## Task 17 — 選題頁的「產貼圖」區塊

**Files:**
- Modify: `pages/1_選題.py`
- Test: `tests/test_app_smoke.py`

**Interfaces:**
- Consumes：`draft.generate`、`db.get_carousel`、`db.update_carousel_page`、
  `shoot.zip_bytes`、`pages.label`。

**草稿的存檔必須走跟 `save_body_draft()`（`pages/1_選題.py:34-36`）一樣的機制**
——`on_change` callback ＋ `st.session_state`。這個專案上一輪發生過
「正文草稿在頁面重跑時靜默消失」，規格 §7.3 指名這是必防的風險。

- [ ] **Step 1: 寫失敗的測試**

在 `tests/test_app_smoke.py` 末尾新增：

```python
def _adopted_idea_with_carousel(path):
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn, Theme(id=None, name="AI 新創介紹", weekday=4,
                    source_ids=[], n_ideas=3)
    )
    idea_id = db.add_idea(
        conn, theme_id,
        Idea(title="讓文字開口說話", angle="配音成本被改寫",
             source_url="https://example.com/a", company="ElevenLabs",
             source_excerpt="2022 年於倫敦成立。"),
        status="採用",
    )
    return conn, idea_id


def test_adopted_idea_offers_carousel_button(tmp_path, monkeypatch):
    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn, _ = _adopted_idea_with_carousel(path)
    conn.close()

    app = AppTest.from_file("pages/1_選題.py").run()
    labels = [button.label for button in app.button]

    assert any("產生輪播草稿" in label for label in labels)


def test_existing_draft_is_rendered_with_grounding_warning(tmp_path, monkeypatch):
    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn, idea_id = _adopted_idea_with_carousel(path)
    from daibu.cards import pages as card_pages
    db.save_carousel(conn, idea_id, [
        {
            "page_no": index + 1, "page_type": page_type,
            "heading": f"標題{index}", "body": f"內文{index}",
            "grounding": "model", "source_quote": "",
        }
        for index, page_type in enumerate(card_pages.PAGE_TYPES)
    ])
    conn.close()

    app = AppTest.from_file("pages/1_選題.py").run()
    rendered = " ".join(block.value for block in app.markdown)

    assert "他們怎麼運用 AI" in rendered
    assert "需查證" in rendered
```

- [ ] **Step 2: 跑測試確認它失敗**

Run: `.venv/bin/pytest tests/test_app_smoke.py::test_adopted_idea_offers_carousel_button -q`
Expected: FAIL — `assert any(...)` 為 False

- [ ] **Step 3: 最小實作**

在 `pages/1_選題.py` 已採用題目的區塊底下加「產貼圖」，三個狀態：

1. `db.get_carousel(conn, idea.id)` 是空的 → 顯示按鈕
   「產生輪播草稿」，旁註「會呼叫 AI，約 10 秒」。
   `idea.company` 為空時按鈕 `disabled=True`，並說明原因。
2. 有草稿 → 逐頁渲染，每頁：
   - `pages.label(page_type)` 當標籤
   - `heading` 與 `body` 各一個 `st.text_input` / `st.text_area`，
     `on_change` 走與 `save_body_draft` 相同的 callback 寫回
     `db.update_carousel_page`
   - `grounding == "model"` 時顯示「需查證」的標記；
     `grounding == "source"` 時顯示 `source_quote` 與可點的 `idea.source_url`
3. 有草稿 → 另有「產生圖片」按鈕，按下呼叫 `shoot.zip_bytes`，
   用 `st.download_button` 提供下載，檔名 `{company}-carousel.zip`

配色只能來自 `daibu/theme.py`，**`pages/` 裡不得寫死色碼**。

- [ ] **Step 4: 跑測試確認它通過**

Run: `.venv/bin/pytest tests/test_app_smoke.py -q`
Expected: PASS

- [ ] **Step 5: 跑全套**

Run: `.venv/bin/pytest -q`
Expected: 通過數明顯高於 167，`0 failed`

- [ ] **Step 6: Commit**

```bash
git add pages/1_選題.py daibu/theme.py tests/test_app_smoke.py
git commit -m "feat(ui): 選題頁的產貼圖區塊"
```

---

## 收尾（Task 17 之後）

- [ ] **用複本實際跑完整條流程**（不要碰真實資料庫）

```bash
cp daibu.db /tmp/daibu-carousel.db
DAIBU_DB_PATH=/tmp/daibu-carousel.db .venv/bin/streamlit run app.py --server.port 8502
```

跑完：產候選 → 採用 → 產輪播草稿 → 改幾格字 → 產生圖片 → 下載 zip → 打開七張圖看。

- [ ] **深淺兩種配色模式都要看**，且**要打開彈出視窗**——上一輪就是只截了頁面本身、
  沒開彈出視窗，才讓「四個彈出視窗文字全隱形」整批過關。

- [ ] **確認真實 `daibu.db` 的 SHA-256 前後一致**

- [ ] **把七張圖附給使用者**，這是這一輪唯一真正的驗收標準：
  它們看起來要像呆一布的貼文。

- [ ] **更新 `docs/open-questions.md`**：把「圖片生成付費 vs 只用免費額度」那條
  標為已結案，理由寫「本專案產品程式碼不呼叫任何生圖服務」。

- [ ] **更新 `STATUS.md` 與 `HANDOFF.md`**，照全域規則收尾（合併回 `main`、
  在 `main` 重跑全套、push）。

---

## 自審紀錄

對照規格逐節檢查，確認每一條都有對應的 Task：

| 規格 | Task |
|---|---|
| §4.2 來源收斂 | Task 4 |
| §4.3 候選長相 | Task 1、2、5 |
| §4.4 指令改寫 | Task 3 |
| §4.5 存原文片段 | Task 1、2、3 |
| §4.6 舊資料不壞 | Task 1（測試明確斷言舊題目還在） |
| §5.1 七格結構 | Task 7 |
| §5.2 資料模型 | Task 8 |
| §5.2 刪除與淘汰 | Task 9 |
| §5.3 產草稿與字數上限 | Task 10、11、15 |
| §5.4 依據標記 | Task 10（預設 model）、17（介面呈現） |
| §5.5 介面三狀態 | Task 17 |
| §5.6 Playwright | Task 14 |
| §6.1 尺寸 | Task 13、14 |
| §6.2–6.3 結構與配色 | Task 13 |
| §6.4 字體本地化（LINE Seed TW 三個字重） | Task 12、13 |
| §6.5 吉祥物 SVG（七種，與網站共用） | Task 12 |
| §5.3 三條語氣鐵律 | Task 10 |
| §11 與網站 PRD 對齊 | Global Constraints、Task 7、10、12、13、14 |
| §6.6 檔案位置 | 檔案結構表 |
| §7.1 匯出與預覽一致 | Task 14（像素契約測試） |
| §7.2 字太長爆版 | Task 15 |
| §7.3 草稿靜默消失 | Task 17 |
| §8 使用者側的工作 | Task 12 Step 5、收尾 |
