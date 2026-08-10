# Startup Eligibility Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` task-by-task. Do not use subagents unless the user explicitly requests delegation.

**Goal:** Ensure company-profile candidates are private, independent companies founded no more than ten years ago, using traceable Tavily evidence and one batch LLM decision before persistence.

**Architecture:** Add a company-level eligibility cache separate from ideas. A pure verifier parses one batch JSON response, proves every accepted fact against exact Tavily URLs and excerpts, and deterministically derives eligible/ineligible/unknown. Selection checks cached verdicts, researches only unseen companies, saves all verdicts, and persists only eligible ideas. A repeatable backfill command applies the same boundary to legacy companies without modifying `ideas`.

**Tech Stack:** Python 3.11, Streamlit, SQLite, pytest, Tavily, Gemini/Groq adapter, Playwright CLI.

## Global Constraints

- Eligibility requires all three: not public, not acquired/subsidiary, and `current_year - founded_year <= 10`.
- Only `private_independent` can be eligible. Missing or contradictory facts produce `unknown`, which is excluded.
- LLM statements are not facts until URL and quote match the actual Tavily result.
- At most one Tavily search per unchecked company and one LLM call per batch.
- Do not retry merely to fill three ideas.
- Do not delete or mutate any existing `ideas` row.
- Preserve general-series behavior and the user's unrelated dirty build-story files.
- Use vertical TDD: one failing test, minimum implementation, green, refactor, then the next test.

## File Map

- Create `daibu/company_eligibility.py`: normalization, prompt, JSON parse, deterministic evidence validation, batch search/classification, backfill CLI.
- Modify `daibu/models.py`: immutable eligibility and evidence records.
- Modify `daibu/db.py`: table creation and eligibility CRUD/query helpers.
- Modify `daibu/selection.py`: cache-aware qualification before idea persistence and display filtering.
- Modify `daibu/llm/prompt.py`: tell idea generation to propose only private independent companies within ten years.
- Modify `pages/1_選題.py`: hide explicit ineligible/unknown legacy companies.
- Create `tests/test_company_eligibility.py` and `tests/test_company_eligibility_contract.py`.
- Modify `tests/test_db.py`, `tests/test_selection.py`, `tests/test_llm.py`, `tests/test_app_smoke.py`, `HANDOFF.md`.

---

### Task 1: Persist auditable company eligibility without touching ideas

**Files:** `daibu/models.py`, `daibu/db.py`, `tests/test_db.py`

- [ ] **RED 1:** Add a schema test expecting `company_eligibility` with company key/name, verdict, founded year, ownership status, reason, evidence JSON, checked time.
- [ ] Run only that test and observe the missing table.
- [ ] **GREEN 1:** Add `CREATE TABLE IF NOT EXISTS company_eligibility` with verdict/status check constraints and no foreign key to ideas.
- [ ] Re-run the single test.
- [ ] **RED 2:** Add a round-trip test for `save_company_eligibility`, `get_company_eligibility`, and `get_company_eligibilities`; include two evidence quotes and null founded year.
- [ ] Run only that test and observe missing models/helpers.
- [ ] **GREEN 2:** Add immutable `EligibilityEvidence` and `CompanyEligibility` records plus JSON serialization/deserialization and upsert CRUD.
- [ ] Re-run the single test.
- [ ] **RED 3:** Add a test proving saving eligibility leaves every `ideas` field and row count unchanged.
- [ ] Run RED, implement only if needed, then run GREEN.
- [ ] Run `tests/test_db.py` and commit `feat: store company eligibility evidence`.

### Task 2: Derive verdicts only from matching evidence

**Files:** `daibu/company_eligibility.py`, `tests/test_company_eligibility.py`

- [ ] **RED 1:** Add a test where founded and private-independent quotes exactly match Tavily materials; expect eligible at the ten-year boundary.
- [ ] Observe missing parser/verifier.
- [ ] **GREEN 1:** Parse a JSON array, normalize company mapping, validate exact URL and quote substring, and return immutable records.
- [ ] **RED 2:** Add an eleven-year-old company test; expect ineligible even if private.
- [ ] Implement deterministic age rejection and verify green.
- [ ] **RED 3:** Add public and acquired evidence cases; expect ineligible with the disqualifying status taking precedence.
- [ ] Implement the two status rejections and verify green.
- [ ] **RED 4:** Add missing quote, wrong URL, contradictory claims, and missing private evidence cases one at a time; each must become unknown rather than eligible.
- [ ] Implement each minimum guard and keep the focused file green after every slice.
- [ ] **RED 5:** Add malformed JSON behavior; expect `EligibilityResponseError` for the whole batch.
- [ ] Implement parse error wrapping without a second LLM call.
- [ ] Refactor claim/status constants and commit `feat: verify startup eligibility evidence`.

### Task 3: Search each company once and classify the batch once

**Files:** `daibu/company_eligibility.py`, `tests/test_company_eligibility.py`

- [ ] **RED 1:** Inject a fake search and generator for three companies; assert three search calls, each `limit=5`, and exactly one generator call containing all companies/materials.
- [ ] Implement `evaluate_companies(companies, search_fn, generate_text, current_year)` with one query per unique normalized company and one batch prompt.
- [ ] **RED 2:** Make one search raise; expect that company unknown while the other company can still be eligible from the same batch.
- [ ] Catch only the per-company search boundary, include empty evidence for that company, and verify green.
- [ ] **RED 3:** Return a company missing from the LLM response; expect unknown for the missing company.
- [ ] Fill missing requested companies with deterministic unknown records.
- [ ] Assert no API secrets or unrelated source bodies appear in errors; commit `feat: research startup eligibility in one batch`.

### Task 4: Gate selection persistence and strengthen the idea prompt

**Files:** `daibu/selection.py`, `daibu/llm/prompt.py`, `tests/test_selection.py`, `tests/test_llm.py`

- [ ] **RED 1:** Add a company-profile prompt test requiring private, independent, no-more-than-ten-year wording; general prompt must not gain these rules.
- [ ] Implement only the prompt rules and verify focused tests.
- [ ] **RED 2:** Seed cached ineligible/unknown/eligible companies plus one unseen company; assert cached disallowed companies are removed, cached eligible needs no search, and only unseen is evaluated.
- [ ] Add cache partitioning and inject/patch `evaluate_companies`; do not change general selection.
- [ ] **RED 3:** Evaluate one eligible, one public, one unknown; expect only eligible persisted and every fresh verdict cached.
- [ ] Implement save-before-filter and verify green.
- [ ] **RED 4:** Make batch parsing fail; expect a clear `CompanyEligibilityVerificationError`, zero new ideas, and existing rows unchanged.
- [ ] Implement atomic idea behavior and clear user-facing error.
- [ ] **RED 5:** Ensure cached ineligible company names are included in the idea-generation avoidance list so repeated public companies do not consume Tavily again.
- [ ] Implement and run `tests/test_selection.py tests/test_llm.py`; commit `fix: require verified startup candidates`.

### Task 5: Hide explicitly disallowed legacy companies and backfill safely

**Files:** `daibu/company_eligibility.py`, `daibu/selection.py`, `pages/1_選題.py`, `tests/test_company_eligibility.py`, `tests/test_selection.py`, `tests/test_app_smoke.py`

- [ ] **RED 1:** Extend the pure visibility test: explicit ineligible/unknown company keys are hidden; explicit eligible and missing legacy records remain compatible; duplicate/blank behavior stays intact.
- [ ] Update `visible_company_profile_ideas` with an optional disallowed set and verify green.
- [ ] **RED 2:** Add AppTest data with Cloudflare ineligible, Railway eligible, Moove legacy-missing, and a general-series company; expect only Cloudflare hidden and unrelated series unchanged.
- [ ] Load disallowed keys from SQLite and wire the page.
- [ ] **RED 3:** Add a backfill test with duplicate Railway ideas and Cloudflare; expect one evaluation per unique unchecked company, eligibility rows saved, and byte-for-byte idea field snapshots unchanged.
- [ ] Implement `backfill_existing` and CLI `python -m daibu.company_eligibility backfill --db <path>`.
- [ ] **RED 4:** Add backfill idempotency: second run makes zero Tavily/LLM calls.
- [ ] Skip already recorded company keys and verify green.
- [ ] Run affected DB/selection/AppTest suites; commit `fix: hide companies that are not startups`.

### Task 6: Verify true Tavily/Gemini behavior and visual output on a database copy

**Files:** `tests/test_company_eligibility_contract.py`, `HANDOFF.md`

- [ ] Add a `contract` test for Cloudflare, Moove, and Railway using the real Tavily key and active free LLM.
- [ ] Run the test. Verify Cloudflare is `ineligible`; Moove/Railway must be `eligible` only with matching founded/private evidence. If either is unknown, improve the real query/prompt/parser rather than weakening mocks.
- [ ] Copy `daibu.db` to a temporary directory and record calibrated idea/company counts.
- [ ] Run the backfill CLI against the copy. Confirm all 10 `ideas` rows and all idea fields are unchanged; inspect three eligibility records and reasons.
- [ ] Start the copy on port 8502. Verify the page hides Cloudflare and shows only eligible legacy candidates.
- [ ] Re-apply `frontend-design`, `emil-design-eng`, `ui-ux-pro-max`, and `playwright-cli` because candidate count/empty/error states are user-visible.
- [ ] Screenshot round 1 exactly twice: 1280×800 and 375×812. Inspect hierarchy, whitespace, typography, palette, alignment, overflow, states, and motion; list failures.
- [ ] Make the smallest correction if needed, with a focused regression test.
- [ ] Screenshot round 2 exactly twice and confirm all checks pass; keep final paths under `.screenshots/`.
- [ ] Run focused suites and provide the nine-field product checkpoint before full tests.

### Task 7: Full verification, integration, production backup/backfill, and deployment

- [ ] Run `PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q` in the feature worktree; run real contract tests separately with dotenv enabled.
- [ ] Update `HANDOFF.md` with root cause, architecture, red/green evidence, API-call counts, contract evidence, screenshot paths, and limitations.
- [ ] Commit only task files after `git diff --check`; request/read-only self-review under the no-subagent project rule.
- [ ] Merge the feature branch into `main` without touching unrelated dirty files.
- [ ] Run the full unit suite again on `main`.
- [ ] Create an explicit timestamped backup of `daibu.db`; verify backup row counts before any metadata write.
- [ ] Run the backfill CLI against production `daibu.db`. Verify ideas remain exactly 10 rows with identical content hashes; only eligibility metadata is added.
- [ ] Push `main` and verify `HEAD == origin/main`.
- [ ] Restart `io.daibu.content-brain`; if the known bootout/bootstrap race occurs, inspect state and recover with the exact label.
- [ ] Open `http://127.0.0.1:8501/選題`; verify Cloudflare absent, Moove/Railway present only if eligible, no critical console/server errors, and no candidate generation is triggered during production verification.
- [ ] Record final evidence, commit/push documentation, remove the owned worktree/feature branch, and report the localhost URL plus remaining best-effort nature of public web evidence.
