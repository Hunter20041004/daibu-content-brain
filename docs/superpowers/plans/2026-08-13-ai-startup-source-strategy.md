# AI Startup Source Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken AI-startup RSS discovery path with a source-backed YC Launches + YC Companies + a16z Speedrun + TechCrunch Startups pipeline that consistently finds new, private AI startups without deleting any existing content.

**Architecture:** Add focused public-source adapters that return typed `CompanyLead` records, then compose at most two directory-only leads plus one directory lead enriched by a recent TechCrunch article. `selection.generate_for_theme` will use this pipeline only for `company_profile`; general themes keep the existing collector. Existing Tavily + free-LLM eligibility verification remains the final gate.

**Tech Stack:** Python 3.11+, Streamlit, SQLite, pytest, `httpx`, `feedparser`, Google Gemini free tier with Groq fallback configuration, Tavily free tier.

## Global Constraints

- Strict vertical TDD: **Red → Green → Refactor**; one failing test → minimal implementation → green → refactor before the next test.
- During red/green loops run only the current test file or exact node id; run the full suite only at task boundaries and final integration.
- Do not add a paid service, dependency, API key, scheduler, background crawler, or full directory mirror.
- Keep the eligibility rule unchanged: founded no more than 10 years ago, not public, not acquired, and still private/independent.
- A directory status of `Active` is a lead, not proof of private independence; final eligibility still needs cross-source evidence.
- Do not delete or rewrite `ideas`, bodies, statuses, `idea_sources`, `carousel_sources`, carousel pages, or `company_eligibility` rows.
- Old YC Blog remains enabled but is unbound from `AI 新創介紹`; old a16z RSS remains as a disabled row and is unbound.
- Keep every other existing source unchanged and do not re-seed unrelated sources a user previously deleted.
- One user click may make public directory/RSS requests, at most one idea-generation LLM call, one Tavily search per unseen company, and one batch eligibility LLM call. Never retry to fill a quota of three.
- Logs must not contain API keys, full prompts, or complete downloaded pages.
- Any user-visible UI change requires two screenshot-review rounds at 1280×800 and 375×812 using the project Playwright workflow.
- Work in an isolated `codex/` branch/worktree because the main checkout contains unrelated user edits.

---

## File Map

**Create**

- `daibu/fetch/startup_directories.py` — HTTP boundary and parsers for YC Launches, YC Companies, and Speedrun.
- `daibu/startup_discovery.py` — filtering, deduplication, TechCrunch matching, lead mix, diagnostics, and product errors.
- `tests/fixtures/yc_launches.json` — minimal stable YC Launches response.
- `tests/fixtures/yc_company_active.html` — YC `data-page` fixture with an active company.
- `tests/fixtures/yc_company_public.html` — YC `data-page` fixture with a public company.
- `tests/fixtures/speedrun_companies.html` — minimal Speedrun `__NEXT_DATA__` directory payload.
- `tests/fixtures/speedrun_cohort.json` — minimal latest-cohort API payload.
- `tests/fixtures/techcrunch_startups.xml` — AI startup, IPO/acquisition, and unrelated-news entries.
- `tests/test_startup_directories.py` — adapter unit and real-boundary contract tests.
- `tests/test_startup_discovery.py` — orchestration, mix, dedupe, warnings, and safe diagnostics.

**Modify**

- `daibu/models.py` — add `CompanyLead`, `DiscoveryStats`, and `DiscoveryResult` dataclasses.
- `daibu/fetch/rss.py` — expose a tagged/date-aware entry reader without changing `fetch()`.
- `daibu/selection.py` — use discovery for company profiles, keep general themes unchanged, and expose precise product errors.
- `daibu/llm/base.py` — add transient-unavailable error type.
- `daibu/llm/gemini.py` — translate Gemini 503 into a stable product error for both idea and carousel text generation.
- `daibu/db.py` — idempotent source-strategy migration for existing databases.
- `daibu/seeds.py` — new defaults for genuinely new databases.
- `pages/1_選題.py` — directory source label, source warnings, and precise error copy.
- `tests/test_rss.py` — tagged RSS behavior and updated real source contracts.
- `tests/test_selection.py` — company discovery integration and early-dedupe behavior.
- `tests/test_llm.py` — Gemini 503 translation.
- `tests/test_db_migration.py` — exact old/new source state plus no-content-change proof.
- `tests/test_seeds.py` — fresh-database source set.
- `tests/test_app_smoke.py` — directory label and user-facing error branches.
- `HANDOFF.md` — final product explanation, test evidence, screenshots, migration backup, and remaining limits.

---

### Task 1: Typed company leads and YC Launches adapter

**Files:**
- Modify: `daibu/models.py`
- Create: `daibu/fetch/startup_directories.py`
- Create: `tests/fixtures/yc_launches.json`
- Create: `tests/test_startup_directories.py`

**Interfaces:**
- Produces: `CompanyLead`, `DiscoveryStats`, `DiscoveryResult`.
- Produces: `fetch_yc_launches(url: str, pages: int = 2) -> list[CompanyLead]`.
- Depends only on: `httpx`, `json`, standard-library URL handling.

- [ ] **Step 1: Write one failing mapping test**

```python
def test_yc_launches_maps_only_ai_companies(monkeypatch):
    payload = Path("tests/fixtures/yc_launches.json").read_text()
    calls = []
    monkeypatch.setattr(
        startup_directories,
        "_get_text",
        lambda url: calls.append(url) or payload,
    )

    leads = startup_directories.fetch_yc_launches(
        "https://www.ycombinator.com/launches",
        pages=1,
    )

    assert calls == ["https://www.ycombinator.com/launches?page=0"]
    assert [(lead.company, lead.batch_or_cohort) for lead in leads] == [
        ("Almanac", "Summer 2026")
    ]
    assert leads[0].tags == ("Generative AI", "AI", "AI Assistant")
    assert leads[0].source_name == "YC Launches"
```

Fixture contains one AI-tagged launch and one unrelated launch. Run:

```bash
.venv/bin/pytest -q tests/test_startup_directories.py::test_yc_launches_maps_only_ai_companies
```

Expected: FAIL because `CompanyLead` / module does not exist.

- [ ] **Step 2: Add the minimal typed records**

```python
@dataclass(frozen=True)
class CompanyLead:
    company: str
    description: str
    discovery_url: str
    profile_url: str = ""
    official_url: str = ""
    founded_year: int | None = None
    ownership_status: str = "unknown"
    batch_or_cohort: str = ""
    tags: tuple[str, ...] = ()
    published_at: str = ""
    source_name: str = ""


@dataclass(frozen=True)
class DiscoveryStats:
    fetched_by_source: tuple[tuple[str, int], ...] = ()
    filtered_non_ai: int = 0
    filtered_duplicate: int = 0
    filtered_status: int = 0
    matched_news: int = 0


@dataclass(frozen=True)
class DiscoveryResult:
    leads: tuple[CompanyLead, ...]
    warnings: tuple[str, ...] = ()
    stats: DiscoveryStats = DiscoveryStats()
```

- [ ] **Step 3: Implement only YC Launches JSON mapping**

```python
AI_TAGS = {"ai", "artificial intelligence", "generative ai", "machine learning"}


def _get_text(url: str) -> str:
    response = httpx.get(
        url,
        follow_redirects=True,
        timeout=15.0,
        headers={"User-Agent": "daibu-content-brain/1.0"},
    )
    response.raise_for_status()
    return response.text


def _is_ai_tagged(tags: tuple[str, ...]) -> bool:
    return any(tag.casefold() in AI_TAGS or " ai" in f" {tag.casefold()}" for tag in tags)


def fetch_yc_launches(url: str, pages: int = 2) -> list[CompanyLead]:
    leads = []
    for page in range(pages):
        payload = json.loads(_get_text(f"{url}?page={page}"))
        for hit in payload.get("hits", []):
            company = hit.get("company") or {}
            tags = tuple(str(tag) for tag in company.get("tags", []))
            if not _is_ai_tagged(tags):
                continue
            leads.append(CompanyLead(
                company=str(company.get("name", "")).strip(),
                description=str(hit.get("tagline", "")).strip(),
                discovery_url=str(hit.get("search_path", "")).strip(),
                profile_url=(
                    "https://www.ycombinator.com/companies/"
                    f"{str(company.get('slug', '')).strip()}"
                ),
                official_url=str(company.get("url", "")).strip(),
                batch_or_cohort=str(company.get("batch", "")).strip(),
                tags=tags,
                published_at=str(hit.get("created_at", "")).strip(),
                source_name="YC Launches",
            ))
    return [lead for lead in leads if lead.company and lead.discovery_url.startswith("https://")]
```

- [ ] **Step 4: Run the exact test green, then the file**

```bash
.venv/bin/pytest -q tests/test_startup_directories.py::test_yc_launches_maps_only_ai_companies
.venv/bin/pytest -q tests/test_startup_directories.py
```

Expected: `1 passed`, then all tests in the new file pass.

- [ ] **Step 5: Commit the vertical slice**

```bash
git add daibu/models.py daibu/fetch/startup_directories.py tests/fixtures/yc_launches.json tests/test_startup_directories.py
git commit -m "feat: read AI companies from YC Launches"
```

---

### Task 2: YC Companies enrichment and early public/acquired rejection

**Files:**
- Modify: `daibu/fetch/startup_directories.py`
- Modify: `tests/test_startup_directories.py`
- Create: `tests/fixtures/yc_company_active.html`
- Create: `tests/fixtures/yc_company_public.html`

**Interfaces:**
- Consumes: `CompanyLead` from Task 1.
- Produces: `enrich_yc_company(lead: CompanyLead) -> CompanyLead`.
- Product rule: `Public` and `Acquired` are early rejection signals; `Active` maps to `active`, not `private_independent`.

- [ ] **Step 1: Write and run one failing active-company test**

```python
def test_yc_company_enrichment_reads_status_and_founding_year(monkeypatch):
    html = Path("tests/fixtures/yc_company_active.html").read_text()
    monkeypatch.setattr(startup_directories, "_get_text", lambda _url: html)
    lead = CompanyLead(
        "Almanac", "Agent with a company brain",
        "https://www.ycombinator.com/launches/almanac",
        profile_url="https://www.ycombinator.com/companies/almanac",
        batch_or_cohort="Summer 2026", source_name="YC Launches",
    )

    enriched = startup_directories.enrich_yc_company(lead)

    assert enriched.founded_year == 2026
    assert enriched.ownership_status == "active"
    assert enriched.official_url == "https://usealmanac.com"
```

Run exact node id; expected FAIL because enrichment is missing.

- [ ] **Step 2: Implement YC `data-page` extraction and run green**

```python
def _yc_company_url(lead: CompanyLead) -> str:
    prefix = "https://www.ycombinator.com/companies/"
    if not lead.profile_url.startswith(prefix):
        raise ValueError("YC Companies 公司網址不合法")
    return lead.profile_url


def _extract_yc_company(html_text: str) -> dict[str, object]:
    match = re.search(r'data-page="([^"]+)"', html_text)
    if not match:
        raise ValueError("YC Companies 找不到公司資料")
    page = json.loads(html.unescape(match.group(1)))
    company = page.get("props", {}).get("company")
    if not isinstance(company, dict):
        raise ValueError("YC Companies 公司資料格式改變")
    return company


def enrich_yc_company(lead: CompanyLead) -> CompanyLead:
    company = _extract_yc_company(_get_text(_yc_company_url(lead)))
    status = str(company.get("ycdc_status", "")).casefold()
    mapped = status if status in {"active", "public", "acquired"} else "unknown"
    return replace(
        lead,
        official_url=str(company.get("website", "")).strip(),
        founded_year=company.get("year_founded") if isinstance(company.get("year_founded"), int) else None,
        ownership_status=mapped,
        tags=tuple(str(tag) for tag in company.get("tags", [])) or lead.tags,
    )
```

- [ ] **Step 3: Add one failing public-company test, then minimal green code**

```python
def test_public_yc_company_is_an_early_rejection(monkeypatch):
    html = Path("tests/fixtures/yc_company_public.html").read_text()
    monkeypatch.setattr(startup_directories, "_get_text", lambda _url: html)
    lead = CompanyLead(
        "Groww",
        "Investing",
        "https://www.ycombinator.com/launches/groww",
        profile_url="https://www.ycombinator.com/companies/groww",
    )

    assert startup_directories.enrich_yc_company(lead).ownership_status == "public"
```

No extra inference: the adapter only maps the site value.

- [ ] **Step 4: Run the adapter file and commit**

```bash
.venv/bin/pytest -q tests/test_startup_directories.py
git add daibu/fetch/startup_directories.py tests/test_startup_directories.py tests/fixtures/yc_company_active.html tests/fixtures/yc_company_public.html
git commit -m "feat: enrich YC startup status before AI review"
```

---

### Task 3: Speedrun latest-cohort AI-company adapter

**Files:**
- Modify: `daibu/fetch/startup_directories.py`
- Modify: `tests/test_startup_directories.py`
- Create: `tests/fixtures/speedrun_companies.html`
- Create: `tests/fixtures/speedrun_cohort.json`

**Interfaces:**
- Produces: `fetch_speedrun_companies(url: str) -> list[CompanyLead]`.
- Reads the newest cohort from public `__NEXT_DATA__`, then makes one bounded request to the public API host referenced by that page.
- Maps founding year and official URL from the cohort response and keeps only exact approved AI categories.

- [ ] **Step 1: Write one failing newest-cohort mapping test**

```python
def test_speedrun_keeps_ai_categories_and_newest_cohort(monkeypatch):
    html_text = Path("tests/fixtures/speedrun_companies.html").read_text()
    cohort_json = Path("tests/fixtures/speedrun_cohort.json").read_text()
    responses = iter((html_text, cohort_json))
    calls = []
    monkeypatch.setattr(
        startup_directories,
        "_get_text",
        lambda url: calls.append(url) or next(responses),
    )

    leads = startup_directories.fetch_speedrun_companies(
        "https://speedrun.a16z.com/companies"
    )

    assert calls == [
        "https://speedrun.a16z.com/companies",
        "https://speedrun-be.a16z.com/api/companies/companies/"
        "?limit=100&cohort=SR006",
    ]
    assert [lead.company for lead in leads] == ["Acceler8"]
    assert leads[0].batch_or_cohort == "SR006"
    assert "AI Agents" in leads[0].tags
    assert leads[0].founded_year == 2025
    assert leads[0].official_url == "https://useacceler8.com"
```

The HTML fixture exposes `cohorts=[SR005, SR006]` and the same public API URL used by the live page. The JSON fixture contains SR006 AI and Gaming-only records.

- [ ] **Step 2: Implement bounded `__NEXT_DATA__` and cohort mapping**

```python
SPEEDRUN_AI_TAGS = {
    "AI Agents", "AI Infra", "AI Models / Research",
    "AI Voice", "AI Generative Media",
}
SPEEDRUN_API_HOST = "speedrun-be.a16z.com"


def _speedrun_page_data(text: str) -> dict[str, object]:
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        text,
        re.DOTALL,
    )
    if not match:
        raise ValueError("Speedrun 找不到目錄資料")
    return json.loads(match.group(1))["props"]["pageProps"]


def _latest_speedrun_url(page: dict[str, object]) -> str:
    cohort = max(str(item["name"]) for item in page["cohorts"])
    next_url = str(page["companies"]["next"])
    parsed = urlparse(next_url)
    if parsed.scheme != "https" or parsed.netloc != SPEEDRUN_API_HOST:
        raise ValueError("Speedrun API 網址不合法")
    return (
        f"https://{SPEEDRUN_API_HOST}{parsed.path}"
        f"?limit=100&cohort={quote(cohort)}"
    )


def fetch_speedrun_companies(url: str) -> list[CompanyLead]:
    page = _speedrun_page_data(_get_text(url))
    newest = max(str(item["name"]) for item in page["cohorts"])
    rows = json.loads(_get_text(_latest_speedrun_url(page))).get("results", [])
    leads = []
    for row in rows:
        tags = tuple(str(item) for item in row.get("industries", []))
        if not SPEEDRUN_AI_TAGS.intersection(tags):
            continue
        slug = str(row.get("slug", "")).strip()
        profile_url = f"https://speedrun.a16z.com/companies/{slug}"
        leads.append(CompanyLead(
            company=str(row.get("name", "")).strip(),
            description=str(row.get("preamble", "")).strip(),
            discovery_url=profile_url,
            profile_url=profile_url,
            official_url=str(row.get("website_url", "")).strip(),
            founded_year=(
                row.get("founded_year")
                if isinstance(row.get("founded_year"), int)
                else None
            ),
            batch_or_cohort=newest,
            tags=tags,
            source_name="a16z Speedrun Companies",
        ))
    return [lead for lead in leads if lead.company and lead.discovery_url]
```

- [ ] **Step 3: Add one failing API-host safety test, then keep it green**

Change the fixture's `companies.next` host to `evil.example`; assert `fetch_speedrun_companies` raises `ValueError("Speedrun API 網址不合法")` before the second HTTP call. This prevents downloaded HTML from redirecting the adapter to an arbitrary host.

- [ ] **Step 4: Run the adapter file and commit**

```bash
.venv/bin/pytest -q tests/test_startup_directories.py
git add daibu/fetch/startup_directories.py tests/test_startup_directories.py tests/fixtures/speedrun_companies.html tests/fixtures/speedrun_cohort.json
git commit -m "feat: discover current AI startups from Speedrun"
```

---

### Task 4: Tagged TechCrunch news and deterministic 2+1 lead mix

**Files:**
- Modify: `daibu/fetch/rss.py`
- Modify: `daibu/models.py`
- Create: `daibu/startup_discovery.py`
- Modify: `tests/test_rss.py`
- Create: `tests/fixtures/techcrunch_startups.xml`
- Create: `tests/test_startup_discovery.py`

**Interfaces:**
- Produces: `TaggedFeedEntry(title, url, snippet, published_at, tags)` in `daibu.models`.
- Produces: `rss.fetch_tagged(url: str, limit: int = 20) -> list[TaggedFeedEntry]`.
- Produces: `mix_leads(directory_leads, news_entries, limit=3) -> tuple[CompanyLead, ...]`.
- News only enriches already identified directory companies; it does not ask AI to guess a company from an arbitrary headline.

- [ ] **Step 1: Write one failing tagged-RSS test, then add the minimal reader**

```python
def test_fetch_tagged_preserves_date_and_categories(monkeypatch):
    raw = Path("tests/fixtures/techcrunch_startups.xml").read_text()
    monkeypatch.setattr(rss, "_download", lambda _url: raw)

    entries = rss.fetch_tagged("https://techcrunch.com/category/startups/feed/")

    assert entries[0].published_at == "Wed, 12 Aug 2026 18:19:12 +0000"
    assert {"AI", "Startups", "Cognition"} <= set(entries[0].tags)
```

Minimal implementation maps `entry.published`, `entry.tags[*].term`, and reuses `_plain_text`. Keep existing `rss.fetch()` byte-for-byte behavior.

- [ ] **Step 2: Write one failing news-matching test**

```python
def test_recent_ai_news_enriches_one_known_company_only():
    leads = (
        CompanyLead("Cognition", "AI coding", "https://yc.example/cognition", source_name="YC Launches"),
        CompanyLead("Almanac", "Agent", "https://yc.example/almanac", source_name="YC Launches"),
        CompanyLead("Acceler8", "Workforce AI", "https://speedrun.example/acceler8", source_name="a16z Speedrun Companies"),
    )
    news = rss.fetch_tagged("fixture://techcrunch")

    mixed = startup_discovery.mix_leads(leads, news, limit=3)

    assert [lead.company for lead in mixed] == ["Cognition", "Almanac", "Acceler8"]
    assert mixed[0].source_name == "TechCrunch Startups"
    assert sum(lead.source_name == "TechCrunch Startups" for lead in mixed) == 1
```

- [ ] **Step 3: Implement exact news eligibility and mix**

```python
BLOCKED_NEWS_TERMS = ("ipo", "goes public", "acquired", "acquisition completed")


def _normal(value: str) -> str:
    return " ".join(value.casefold().split())


def _eligible_news(entry: TaggedFeedEntry) -> bool:
    tags = {_normal(tag) for tag in entry.tags}
    text = _normal(f"{entry.title} {entry.snippet}")
    return "ai" in tags and "startups" in tags and not any(term in text for term in BLOCKED_NEWS_TERMS)


def _news_for(lead: CompanyLead, entries: list[TaggedFeedEntry]) -> TaggedFeedEntry | None:
    company = _normal(lead.company)
    if len(company) < 4:
        return None
    return next(
        (entry for entry in entries if _eligible_news(entry) and company in _normal(f"{entry.title} {entry.snippet}")),
        None,
    )


def mix_leads(
    directory_leads: tuple[CompanyLead, ...],
    news_entries: list[TaggedFeedEntry],
    limit: int = 3,
) -> tuple[CompanyLead, ...]:
    news_enriched = []
    directory_only = []
    for lead in directory_leads:
        news = _news_for(lead, news_entries)
        if news and not news_enriched:
            news_enriched.append(replace(
                lead,
                description=news.snippet,
                discovery_url=news.url,
                published_at=news.published_at,
                source_name="TechCrunch Startups",
            ))
        else:
            directory_only.append(lead)
    return tuple((news_enriched + directory_only)[:limit])
```

The pool itself enforces one recent-news item maximum; when no directory company matches news, fill all available slots from directories.

- [ ] **Step 4: Add one failing blocked-news test, then make it green with the exact blocked terms**

Test an AI/Startups article containing `IPO` and assert it does not replace the directory lead.

- [ ] **Step 5: Run focused tests and commit**

```bash
.venv/bin/pytest -q tests/test_rss.py tests/test_startup_discovery.py
git add daibu/models.py daibu/fetch/rss.py daibu/startup_discovery.py tests/test_rss.py tests/test_startup_discovery.py tests/fixtures/techcrunch_startups.xml
git commit -m "feat: mix startup directories with timely AI news"
```

---

### Task 5: Discovery orchestration, early dedupe, and safe source diagnostics

**Files:**
- Modify: `daibu/startup_discovery.py`
- Modify: `tests/test_startup_discovery.py`

**Interfaces:**
- Produces: `discover(sources, excluded_company_keys, limit=3, warning_sink=None) -> DiscoveryResult`.
- Produces errors: `NoAvailableStartupSourcesError`, `AllStartupCompaniesRepeatedError`.
- Directory detail and news requests happen only after normalized historical/cache exclusion.

- [ ] **Step 1: Write one failing early-dedupe call-order test**

```python
def test_discovery_excludes_history_before_detail_and_news_calls(monkeypatch):
    detail_calls = []
    monkeypatch.setattr(startup_discovery.directories, "fetch_yc_launches", lambda *_a, **_k: [
        CompanyLead("SeenCo", "old", "https://yc/seen", source_name="YC Launches"),
        CompanyLead("NewCo", "new", "https://yc/new", source_name="YC Launches"),
    ])
    monkeypatch.setattr(
        startup_discovery.directories,
        "enrich_yc_company",
        lambda lead: detail_calls.append(lead.company) or lead,
    )
    monkeypatch.setattr(startup_discovery.rss, "fetch_tagged", lambda *_a, **_k: [])

    result = startup_discovery.discover(
        configured_sources(), {"seenco"}, limit=3,
    )

    assert detail_calls == ["NewCo"]
    assert [lead.company for lead in result.leads] == ["NewCo"]
```

- [ ] **Step 2: Implement source routing, normalization, and per-source isolation**

Use exact source names/URLs from the approved migration. For each enabled and bound source:

```python
READERS = {
    "YC Launches": directories.fetch_yc_launches,
    "a16z Speedrun Companies": directories.fetch_speedrun_companies,
}


def discover(
    sources: list[Source],
    excluded_company_keys: set[str],
    limit: int = 3,
    warning_sink: Callable[[str], None] | None = None,
) -> DiscoveryResult:
    warnings, directory_leads, fetched = [], [], []
    for source in sources:
        if not source.enabled or source.name not in READERS:
            continue
        try:
            items = READERS[source.name](source.url)
            directory_leads.extend(items)
            fetched.append((source.name, len(items)))
        except Exception:
            message = f"{source.name} 暫時讀不到，已改用其他來源。"
            warnings.append(message)
            if warning_sink:
                warning_sink(message)
    if not directory_leads:
        raise NoAvailableStartupSourcesError("目前沒有可用的公司來源，請稍後再試。")
    unique = []
    seen = set(excluded_company_keys)
    for lead in directory_leads:
        key = _normal(lead.company)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(lead)
    if not unique:
        raise AllStartupCompaniesRepeatedError("這批來源裡的公司都介紹過了。")
    # YC needs a bounded detail read; Speedrun already carries structured details.
    enriched = _enrich_yc_candidates(unique[:12], warnings, warning_sink)
    allowed = [lead for lead in enriched if lead.ownership_status not in {"public", "acquired"}]
    news = _fetch_news_source(sources, warnings, warning_sink)
    leads = mix_leads(tuple(allowed), news, limit=limit)
    return DiscoveryResult(
        leads=leads,
        warnings=tuple(warnings),
        stats=DiscoveryStats(
            fetched_by_source=tuple(fetched),
            filtered_duplicate=len(directory_leads) - len(unique),
            filtered_status=len(enriched) - len(allowed),
            matched_news=sum(lead.source_name == "TechCrunch Startups" for lead in leads),
        ),
    )
```

`_enrich_yc_candidates` enriches YC leads and passes Speedrun leads through unchanged. A single YC detail failure emits a warning and drops that lead rather than inventing missing fields.

- [ ] **Step 3: Add and green one source-failure continuation test**

Make YC raise, Speedrun return one lead, assert the result survives and warning text names YC but does not contain the raw exception.

- [ ] **Step 4: Add and green one safe-log test**

Use `caplog`, raise `RuntimeError("TAVILY_API_KEY=secret-value")`, and assert neither `secret-value` nor the exception text appears. Log only source name, counts, elapsed milliseconds, and a fixed failure category:

```python
logger.warning("startup_source_failed source=%s category=%s", source.name, type(error).__name__)
logger.info(
    "startup_discovery fetched=%s duplicate=%d status=%d news=%d final=%d",
    dict(result.stats.fetched_by_source),
    result.stats.filtered_duplicate,
    result.stats.filtered_status,
    result.stats.matched_news,
    len(result.leads),
)
```

- [ ] **Step 5: Run and commit**

```bash
.venv/bin/pytest -q tests/test_startup_discovery.py
git add daibu/startup_discovery.py tests/test_startup_discovery.py
git commit -m "feat: diagnose startup discovery without leaking secrets"
```

---

### Task 6: Integrate discovery into company-profile selection

**Files:**
- Modify: `daibu/selection.py`
- Modify: `tests/test_selection.py`

**Interfaces:**
- `generate_for_theme(..., warning_sink: Callable[[str], None] | None = None) -> list[int]` remains list-compatible.
- General themes continue to call `collector.collect` unchanged.
- Company profiles call `startup_discovery.discover`, convert the bounded leads to `Material`, generate once, validate exact source quote, and then reuse eligibility cache/search.

- [ ] **Step 1: Write one failing company-profile routing test**

```python
def test_company_profile_uses_discovery_but_general_theme_keeps_collector(tmp_path, monkeypatch):
    conn = db.connect(str(tmp_path / "routing.db"))
    db.init_schema(conn)
    company_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1, content_kind="company_profile"),
    )
    general_id = db.add_theme(conn, Theme(None, "AI 工具", 1, [], 1))
    calls = []

    def fake_discover(
        _sources,
        excluded_company_keys,
        limit,
        warning_sink=None,
    ):
        del excluded_company_keys, limit, warning_sink
        calls.append("discovery")
        return DiscoveryResult((CompanyLead(
            "NewCo",
            "AI workflow",
            "https://www.ycombinator.com/launches/newco",
            source_name="YC Launches",
        ),))

    monkeypatch.setattr(selection.startup_discovery, "discover", fake_discover)
    monkeypatch.setattr(
        selection.collector,
        "collect",
        lambda _theme, _sources: calls.append("collector") or [
            Material("General", "https://example.com/general", "General source")
        ],
    )

    class FakeProvider:
        def generate_ideas(self, _theme, materials, _n, **kwargs):
            if kwargs["content_kind"] == "company_profile":
                return [Idea(
                    "NewCo workflow",
                    "new angle",
                    materials[0].url,
                    company="NewCo",
                    source_excerpt=materials[0].snippet,
                )]
            return [Idea("General title", "general angle", materials[0].url)]

    selection.generate_for_theme(
        conn,
        Theme(company_id, "AI 新創介紹", 4, [], 1, "company_profile"),
        FakeProvider(),
        [],
    )
    selection.generate_for_theme(
        conn,
        Theme(general_id, "AI 工具", 1, [], 1),
        FakeProvider(),
        [],
    )

    assert calls == ["discovery", "collector"]
```

Run only this node id and see red before changing `selection.py`.

- [ ] **Step 2: Add minimal routing and lead-to-material conversion**

```python
def _lead_material(lead: CompanyLead) -> Material:
    facts = [lead.description]
    if lead.founded_year is not None:
        facts.append(f"Founded {lead.founded_year}")
    if lead.batch_or_cohort:
        facts.append(lead.batch_or_cohort)
    return Material(
        title=lead.company,
        url=lead.discovery_url,
        snippet=" | ".join(part for part in facts if part),
    )
```

At the start of the company branch, build `avoid_titles`, `avoid_companies`, and cache exactly as today, then:

```python
result = startup_discovery.discover(
    [source for source in sources if source.id in theme.source_ids],
    excluded_company_keys={_normalize_identity(name) for name in avoid_companies},
    limit=theme.n_ideas,
    warning_sink=warning_sink,
)
materials = [_lead_material(lead) for lead in result.leads]
```

Call `provider.generate_ideas` exactly once with these materials.

- [ ] **Step 3: Add one failing early-status/cache test, then green it**

Test that a cached `ineligible` / `unknown` company is included in discovery exclusions and no directory detail, Tavily, or LLM call is made for it. Keep cached `eligible` available if a new source points to it only when it has never been an idea; existing company history still wins.

- [ ] **Step 4: Add one failing exact-source validation test, then green it**

Provider returns an invented URL or paraphrased excerpt. Assert it is rejected and no idea is written. `_is_verified_company_candidate` remains the enforcement point.

- [ ] **Step 5: Add one failing no-eligible-company error distinction**

When discovery finds leads but all fresh eligibility records are `ineligible`/`unknown`, write this complete regression test:

```python
def test_company_leads_all_filtered_has_a_precise_error(tmp_path, monkeypatch):
    conn = db.connect(str(tmp_path / "all-filtered.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1, "company_profile"),
    )
    lead = CompanyLead(
        "NewCo",
        "AI workflow",
        "https://www.ycombinator.com/launches/newco",
        source_name="YC Launches",
    )
    monkeypatch.setattr(
        selection.startup_discovery,
        "discover",
        lambda *_args, **_kwargs: DiscoveryResult((lead,)),
    )

    class FakeProvider:
        def generate_ideas(self, _theme, materials, _n, **_kwargs):
            return [Idea(
                "NewCo workflow",
                "new angle",
                materials[0].url,
                company="NewCo",
                source_excerpt=materials[0].snippet,
            )]

    def unknown_result(companies, *_args, **_kwargs):
        return {
            "newco": CompanyEligibility(
                "newco",
                companies[0],
                "unknown",
                None,
                "unknown",
                "證據不足",
                (),
                "2026-08-13 09:00:00",
            )
        }

    monkeypatch.setattr(
        selection.company_eligibility,
        "evaluate_companies",
        unknown_result,
    )

    with pytest.raises(
        selection.NoVerifiedCompanyCandidatesError,
        match="找到公司，但沒有符合本系列資格的公司",
    ):
        selection.generate_for_theme(
            conn,
            Theme(theme_id, "AI 新創介紹", 4, [], 1, "company_profile"),
            FakeProvider(),
            [],
        )

    assert db.get_company_eligibilities(conn)["newco"].verdict == "unknown"
    assert db.get_ideas(conn) == []
```

This replaces the ambiguous existing copy only for the all-filtered branch.

- [ ] **Step 6: Run focused selection tests and commit**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_selection.py
git add daibu/selection.py tests/test_selection.py
git commit -m "feat: generate company ideas from qualified startup leads"
```

---

### Task 7: Idempotent source migration and fresh-database defaults

**Files:**
- Modify: `daibu/db.py`
- Modify: `daibu/seeds.py`
- Modify: `tests/test_db_migration.py`
- Modify: `tests/test_seeds.py`

**Interfaces:**
- Migration key: `startup_source_strategy_v1`.
- New source rows:
  - `YC Launches` → `https://www.ycombinator.com/launches` → `directory`.
  - `YC Companies` → `https://www.ycombinator.com/companies` → `directory`.
  - `a16z Speedrun Companies` → `https://speedrun.a16z.com/companies` → `directory`.
  - `TechCrunch Startups` → `https://techcrunch.com/category/startups/feed/` → `rss`.

- [ ] **Step 1: Write one failing migration-state test**

Create an existing database with the exact current source state, 10 ideas, `idea_sources`, `carousel_sources`, carousel pages, and eligibility rows. Record complete row tuples before migration. After `db.init_schema(conn)` twice, assert:

```python
assert by_name["Y Combinator Blog"].enabled is True
assert by_name["a16z"].enabled is False
assert bound_names == {
    "YC Launches", "YC Companies",
    "a16z Speedrun Companies", "TechCrunch Startups",
}
assert before_content_rows == after_content_rows
assert db.get_config(conn, "startup_source_strategy_v1") == "1"
```

- [ ] **Step 2: Implement migration as one transaction**

Insert new sources with `WHERE NOT EXISTS`; update only old `a16z.enabled`; delete only the target theme's old `theme_sources`; insert the four new bindings; insert config flag last. Do not set the flag when no `AI 新創介紹` theme exists, so a truly empty database can still be seeded correctly.

Use source names as identity only for this migration and never rewrite an existing row's URL except the old a16z enabled flag.

- [ ] **Step 3: Run migration test green**

```bash
.venv/bin/pytest -q tests/test_db_migration.py::test_startup_source_strategy_migrates_without_changing_content
```

- [ ] **Step 4: Write one failing fresh-seed test and update defaults**

```python
def test_fresh_startup_theme_uses_only_approved_discovery_sources(tmp_path):
    conn = db.connect(str(tmp_path / "fresh.db"))
    db.init_schema(conn)
    seeds.load(conn)
    theme = db.get_themes(conn)[0]
    names = {source.name for source in db.get_sources(conn) if source.id in theme.source_ids}
    assert names == {
        "YC Launches", "YC Companies",
        "a16z Speedrun Companies", "TechCrunch Startups",
    }
```

Update `DEFAULT_SOURCES` and `DEFAULT_THEMES`; retain all unrelated defaults so source-library behavior for future themes is unchanged.

- [ ] **Step 5: Run DB/seed tests and commit**

```bash
.venv/bin/pytest -q tests/test_db_migration.py tests/test_seeds.py tests/test_db.py
git add daibu/db.py daibu/seeds.py tests/test_db_migration.py tests/test_seeds.py
git commit -m "feat: migrate startup series to qualified sources"
```

---

### Task 8: Friendly Gemini failures and precise Streamlit recovery states

**Files:**
- Modify: `daibu/llm/base.py`
- Modify: `daibu/llm/gemini.py`
- Modify: `pages/1_選題.py`
- Modify: `tests/test_llm.py`
- Modify: `tests/test_app_smoke.py`

**Interfaces:**
- Produces: `LLMUnavailableError(RuntimeError)`.
- `GeminiProvider.generate_text()` and `generate_carousel_text()` both map Google `ServerError(code=503)` to `LLMUnavailableError("Gemini 暫時繁忙，請稍後再試。")`.
- Page maps known product errors to stable Traditional Chinese messages; unknown exceptions remain generic and never print raw text.

- [ ] **Step 1: Write one failing Gemini idea-generation 503 test**

```python
def test_gemini_text_503_has_a_product_error(monkeypatch):
    class FakeModels:
        def generate_content(self, **_kwargs):
            raise errors.ServerError(503, {"error": {"status": "UNAVAILABLE", "message": "high demand"}})
    class FakeClient:
        def __init__(self, **_kwargs):
            self.models = FakeModels()
    monkeypatch.setattr("daibu.llm.gemini.genai.Client", FakeClient)

    with pytest.raises(base.LLMUnavailableError, match="Gemini 暫時繁忙"):
        GeminiProvider(api_key="fake").generate_text("prompt")
```

- [ ] **Step 2: Add the exception and one shared Gemini call wrapper**

Refactor both methods through `_generate_content(...)`; catch only timeout, 503, and 429 into `LLMTimeoutError`, `LLMUnavailableError`, and `LLMQuotaError`. Re-raise every other SDK error unchanged. Run `tests/test_llm.py` green before continuing.

- [ ] **Step 3: Write one failing page test per product branch, vertically**

Add and run one at a time:

```python
@pytest.mark.parametrize(("error", "message"), [
    (NoAvailableStartupSourcesError("x"), "目前沒有可用的公司來源"),
    (AllStartupCompaniesRepeatedError("x"), "這批來源裡的公司都介紹過了"),
    (NoVerifiedCompanyCandidatesError("x"), "沒有符合本系列資格的公司"),
    (LLMUnavailableError("x"), "Gemini 暫時繁忙"),
])
def test_generation_shows_precise_safe_error(monkeypatch, tmp_path, error, message):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(conn, Theme(None, "AI 新創介紹", 4, [], 1, "company_profile"))
    monkeypatch.setattr(base, "get_provider", lambda _config: object())

    def raise_product_error(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(selection, "generate_for_theme", raise_product_error)
    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        button for button in app.button if button.label == "開始找題材"
    ).click().run()

    rendered = " ".join(item.value for item in app.error)
    assert message in rendered
    assert "產生失敗：" not in rendered
    assert "x" not in rendered
```

- [ ] **Step 4: Implement a small page-only error mapper**

```python
def generation_error_message(error: Exception) -> str:
    if isinstance(error, NoAvailableStartupSourcesError):
        return "目前沒有可用的公司來源，請稍後再試。"
    if isinstance(error, AllStartupCompaniesRepeatedError):
        return "這批來源裡的公司都介紹過了。"
    if isinstance(error, NoVerifiedCompanyCandidatesError):
        return "找到公司，但沒有符合本系列資格的公司。"
    if isinstance(error, LLMUnavailableError):
        return "Gemini 暫時繁忙，請稍後再試。"
    return "這次沒有完成，原本內容都還在；請稍後再試。"
```

Collect discovery warnings in a local list via `warning_sink=warnings.append`, render each fixed safe warning after the call, and never use `st.error(f"...{error}")`.

- [ ] **Step 5: Add directory source labels to the existing source editor**

The selectbox options become `("rss", "search", "directory")`; display mapping is `RSS`, `網域搜尋`, `公司目錄`. When adding/editing `directory`, accept only the three approved URLs and show a validation error for arbitrary domains. This prevents the UI from implying it can parse any company directory.

- [ ] **Step 6: Run focused UI/LLM tests and commit**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_llm.py tests/test_app_smoke.py
git add daibu/llm/base.py daibu/llm/gemini.py pages/1_選題.py tests/test_llm.py tests/test_app_smoke.py
git commit -m "fix: explain startup source and Gemini failures"
```

---

### Task 9: Real external-boundary contracts

**Files:**
- Modify: `tests/test_startup_directories.py`
- Modify: `tests/test_rss.py`

**Interfaces:**
- These tests are marked `@pytest.mark.contract` and remain deselected in normal unit runs.
- Tests validate only fields the product actually depends on, not page layout or large snapshots.

- [ ] **Step 1: Add and run YC Launches real contract**

```python
@pytest.mark.contract
def test_real_yc_launches_returns_ai_company_fields():
    leads = fetch_yc_launches("https://www.ycombinator.com/launches", pages=1)
    assert leads
    assert all(lead.company and lead.discovery_url.startswith("https://") for lead in leads)
    assert all(lead.tags for lead in leads)
```

- [ ] **Step 2: Add and run YC Companies real status contract**

Use the known calibration company Groww and assert `founded_year == 2016` and `ownership_status == "public"`. If the site changes truthful data, update the calibration company based on an authoritative visible status, not by weakening assertions.

- [ ] **Step 3: Add and run Speedrun real contract**

Assert at least one latest-cohort AI lead and require company, cohort, discovery URL, official URL, founded year, and one approved AI tag directly from the cohort response. If the public schema differs from fixtures, fix the adapter and re-run unit + contract tests.

- [ ] **Step 4: Replace obsolete startup RSS contract with TechCrunch Startups**

Remove the claim that five old startup feeds are all bound. Keep generic RSS smoke tests where still relevant, and add:

```python
@pytest.mark.contract
def test_real_techcrunch_startups_has_tagged_ai_entries():
    entries = rss.fetch_tagged("https://techcrunch.com/category/startups/feed/", limit=20)
    assert entries
    assert any("AI" in entry.tags and "Startups" in entry.tags for entry in entries)
```

- [ ] **Step 5: Run all four real contracts together and commit**

```bash
.venv/bin/pytest -q -m contract \
  tests/test_startup_directories.py tests/test_rss.py
git add tests/test_startup_directories.py tests/test_rss.py daibu/fetch/startup_directories.py daibu/fetch/rss.py
git commit -m "test: verify live startup source contracts"
```

Expected: all selected contracts pass. A real format mismatch blocks rollout and must be fixed before Task 10.

---

### Task 10: Product checkpoint, full verification, visual QA, and formal-data rollout

**Files:**
- Modify: `.gitignore` only if `.screenshots/` is not already ignored.
- Modify: `HANDOFF.md`
- Use: a temporary SQLite copy and then `daibu.db` after backup.

**Interfaces:**
- No new code interfaces.
- This task proves the actual user result and preserves formal data.

- [ ] **Step 1: Deliver the product-understanding checkpoint before full tests**

Record in `HANDOFF.md` all nine fields required by `product-owner-teaching`:

1. Product capability: finds current private AI startups from directories plus news.
2. User experience: one click, precise errors, old content remains.
3. Technical components: adapters, discovery, LLM formatting, eligibility gate, SQLite.
4. Data flow: directory → early filters → news → idea LLM → eligibility → candidate.
5. Design reason: separation of identity, timeliness, and proof.
6. Alternatives: RSS-only and directory-only, with why rejected.
7. Security/cost: public reads, free quotas, no secrets in logs.
8. Test evidence: focused red/green cycles and contracts.
9. Remaining limits: public HTML may change; no scheduled refresh or aliases.

- [ ] **Step 2: Run focused suite, then full suite once**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_startup_directories.py tests/test_startup_discovery.py \
  tests/test_rss.py tests/test_selection.py tests/test_llm.py \
  tests/test_db_migration.py tests/test_seeds.py tests/test_app_smoke.py
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q
```

Expected: exit 0; contract tests deselected in the normal full run. Report exact pass/deselect/warning counts.

- [ ] **Step 3: Calibrate a temporary DB copy before the real flow**

```bash
cp daibu.db /private/tmp/daibu-startup-source-acceptance.db
DAIBU_DB_PATH=/private/tmp/daibu-startup-source-acceptance.db \
  .venv/bin/streamlit run server.py --server.address 127.0.0.1 --server.port 8502
```

Before generation, query the copy and prove it has the same 10 `ideas` rows and the same visible Railway/Moove pair as formal data. Run one real “再產生 3 則” flow. Success criterion: at least one new eligible company, or a precise stage log proving a truthful external shortage without relaxing rules. Verify no raw API error reaches the page.

- [ ] **Step 4: Perform two visual review rounds**

Use `playwright-cli` exactly as required:

```bash
playwright-cli open http://127.0.0.1:8502/選題
playwright-cli resize 1280 800 && playwright-cli screenshot --filename=.screenshots/startup-sources-round1-desktop.png
playwright-cli resize 375 812 && playwright-cli screenshot --filename=.screenshots/startup-sources-round1-mobile.png
```

Review hierarchy, whitespace, font, ≤3 primary colors, alignment, 375px overflow, hover/focus/empty/loading/error states, and micro-motion. Explicitly list failures, fix one vertical UI slice at a time with AppTest protection, then repeat with `round2` filenames. Do not reread round1 screenshots after fixes.

- [ ] **Step 5: Back up and migrate formal SQLite only after the copy passes**

Use SQLite online backup, not a raw copy while the app may be running:

```bash
mkdir -p backups
sqlite3 daibu.db ".backup 'backups/daibu-before-startup-sources-20260813.db'"
```

Calibrate the measurement method against the known 10 ideas and 2 visible candidates, compute a complete ordered `ideas` content hash, restart the local service so `db.init_schema` applies the migration, then prove:

- 10 `ideas` rows and identical content hash.
- Railway and Moove remain the 2 visible candidates before new generation.
- Old a16z row exists, is disabled, and has zero theme bindings.
- YC Blog exists, is enabled, and has zero theme bindings.
- Exactly the four approved sources are bound.
- All eligibility rows are unchanged.

Do not generate formal candidates until these invariants pass.

- [ ] **Step 6: Run the formal core flow and user-view verification**

At `http://127.0.0.1:8501/選題`, click once, observe the final message, inspect safe logs, confirm no console/server critical errors, and query SQLite to verify only eligible new companies were inserted. Do not repeatedly click to fill three.

- [ ] **Step 7: Final full suite, HANDOFF, and implementation commit**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q
git add HANDOFF.md .gitignore \
  daibu pages tests
git commit -m "feat: source current private AI startups"
```

Do not stage unrelated pre-existing user edits or generated secrets/databases. `.screenshots/` should be ignored, so record paths in `HANDOFF.md` rather than committing image files.

- [ ] **Step 8: Review, merge, push, and local-service verification**

Use `requesting-code-review`, address only verified findings, then:

1. Ensure feature worktree tests pass.
2. Merge to `main` without overwriting the user's unrelated dirty files; stop on overlap/conflict.
3. Run the full suite again on `main`.
4. Push the existing remote and confirm the remote contains the final commit.
5. Restart `io.daibu.content-brain`, confirm health, listener only on `127.0.0.1:8501`, browser console/server errors zero, and exercise the core generation flow once.
6. Report that this project has no production deployment flow; localhost is the delivered runtime.

---

## Plan Self-Review Checklist

- Spec coverage: adapters, 2+1 mix, eligibility preservation, old-source disposition, cost caps, safe logs, precise UI errors, migration, contracts, screenshots, formal-data protection, merge/push/local verification are all assigned to Tasks 1–10.
- Placeholder scan: plan contains no TBD/TODO/“implement later” steps.
- Type consistency: `CompanyLead.profile_url` keeps launch/news URLs separate from directory profiles; `TaggedFeedEntry`, `DiscoveryStats`, `DiscoveryResult`, `fetch_yc_launches`, `fetch_speedrun_companies`, `enrich_yc_company`, `mix_leads`, and `discover` use the same names/signatures throughout.
- Scope: no scheduler, full directory mirror, aliases, paid provider, or unrelated source cleanup.
