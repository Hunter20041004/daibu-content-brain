# Startup Content Diversity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce five AI-startup candidates per run while limiting infrastructure to one, every other category to two, and requiring at least three categories.

**Architecture:** Add a focused classification-and-selection module between directory discovery and idea generation. Classify incrementally in 15/10/15-company windows, reuse existing eligibility verification, generate only for the selected five companies, then validate and save all five atomically.

**Tech Stack:** Python 3.11+, Streamlit, SQLite, pytest, existing GoogleTaskRouter/Gemma and Gemini adapters.

## Global Constraints

- Follow strict vertical TDD: one failing test, minimal implementation, refactor, then the next test.
- AI infrastructure maximum is 1; every other single category maximum is 2; every batch contains exactly 5 companies from at least 3 categories.
- Inspect at most 40 new companies in windows ending at 15, 25, and 40.
- Classification uses directory metadata only and is not persisted.
- Existing ideas are preserved; every failed run writes zero new ideas.
- No new paid service, dependency, API key, or database schema.

---

### Task 1: Category model, prompt, and strict parser

**Files:**
- Create: `daibu/company_diversity.py`
- Create: `tests/test_company_diversity.py`

**Interfaces:**
- Produces `CompanyCategory`, `ClassifiedCompany`, `build_classification_prompt(leads)`, and `parse_classifications(raw, leads)`.
- Parser returns one `ClassifiedCompany` per input lead in input order or raises `CompanyClassificationResponseError`.

- [ ] Write `test_parse_classifications_returns_every_company_in_input_order`, run only that test, and verify it fails because the module is missing.
- [ ] Implement the six category constants, frozen result dataclass, and minimal strict JSON parser; rerun and verify green.
- [ ] Write and green one test at a time for missing company, duplicate company, unknown company, and invalid category.
- [ ] Write `test_classification_prompt_contains_core_product_rule_and_examples`, verify red, then add the minimal Traditional-Chinese JSON-only prompt with the approved examples and directory fields; verify green.
- [ ] Refactor normalization and validation without changing behavior; run `pytest -q tests/test_company_diversity.py`.

### Task 2: Deterministic diversity selector

**Files:**
- Modify: `daibu/company_diversity.py`
- Modify: `tests/test_company_diversity.py`

**Interfaces:**
- Produces `select_diverse_companies(items, count=5) -> tuple[ClassifiedCompany, ...] | None` and `describe_shortage(items, inspected_count)`.

- [ ] Write and red/green `test_selector_caps_infrastructure_at_one` using a six-company fixture.
- [ ] Write and red/green `test_selector_caps_every_other_category_at_two`.
- [ ] Write and red/green `test_selector_requires_three_categories`.
- [ ] Write and red/green `test_selector_returns_exactly_five_and_prefers_more_categories`.
- [ ] Write and red/green `test_selector_returns_none_when_no_combination_exists`.
- [ ] Write and red/green `test_shortage_message_reports_inspected_count_and_category_counts`.
- [ ] Refactor the bounded five-item combination search; run the full module test file.

### Task 3: Discovery supports a 40-company pool

**Files:**
- Modify: `daibu/startup_discovery.py`
- Modify: `tests/test_startup_discovery.py`

**Interfaces:**
- `discover(..., limit=40)` enriches enough YC leads for the requested pool, rather than the former fixed first 12.

- [ ] Write `test_discovery_enriches_up_to_requested_limit`, verify it fails because only 12 are enriched, change the slice to the requested limit, and verify green.
- [ ] Run `pytest -q tests/test_startup_discovery.py` and refactor only code introduced by this task.

### Task 4: Incremental classification and eligibility-aware selection

**Files:**
- Modify: `daibu/company_diversity.py`
- Modify: `daibu/selection.py`
- Modify: `tests/test_selection.py`

**Interfaces:**
- Produces `prepare_diverse_company_materials(conn, provider, leads, warning_sink) -> (materials, categories)` or raises `InsufficientCompanyDiversityError` / `CompanyClassificationError`.
- Classification calls use `provider.generate_research_text` and only send new windows of 15, 10, then 15 leads.

- [ ] Write and red/green a selection test where the first 15 satisfy quotas; assert one classification call and five selected materials.
- [ ] Write and red/green a test where only the 16th–25th companies create a valid combination; assert classification batch sizes `[15, 10]`.
- [ ] Write and red/green a test requiring the final window; assert batch sizes `[15, 10, 15]` and no company is classified twice.
- [ ] Write and red/green a test where 40 companies still fail; assert the stable shortage exception includes inspected count and no idea rows.
- [ ] Write and red/green a test where a selected company fails existing eligibility and a classified replacement is used.
- [ ] Write and red/green a test where both classification model routes fail; assert `CompanyClassificationError` and zero idea rows.
- [ ] Refactor selection helpers, preserving existing general-theme path; run `pytest -q tests/test_selection.py`.

### Task 5: Exact output contract and atomic five-row write

**Files:**
- Modify: `daibu/db.py`
- Modify: `daibu/selection.py`
- Modify: `tests/test_db.py`
- Modify: `tests/test_selection.py`

**Interfaces:**
- Produces `db.add_ideas_atomic(conn, theme_id, ideas, status="候選") -> list[int]`.
- Company generation accepts only output that maps one-to-one to the selected five companies and still passes source evidence validation.

- [ ] Write and red/green `test_add_ideas_atomic_rolls_back_all_rows_when_one_insert_fails` using a SQLite trigger to abort the third insert.
- [ ] Write and red/green `test_company_generation_rejects_fewer_than_five_with_zero_writes`.
- [ ] Write and red/green `test_company_generation_rejects_replaced_or_duplicate_company_with_zero_writes`.
- [ ] Write and red/green `test_company_generation_saves_exactly_five_selected_companies`.
- [ ] Refactor validation into a small helper and run `pytest -q tests/test_db.py tests/test_selection.py`.

### Task 6: Default count migration and user-facing states

**Files:**
- Modify: `daibu/seeds.py`
- Modify: `daibu/db.py`
- Modify: `pages/1_選題.py`
- Modify: `tests/test_db_migration.py`
- Modify: `tests/test_app_smoke.py`

**Interfaces:**
- Existing and newly seeded `company_profile` themes use `n_ideas=5`; general themes retain their stored values.
- UI maps diversity/classification failures to precise Traditional-Chinese messages.

- [ ] Write and red/green a migration test proving an existing company-profile theme changes from 3 to 5 while a general theme stays unchanged.
- [ ] Write and red/green a seed test asserting the default AI startup theme is five.
- [ ] Write and red/green an AppTest assertion for the button label `再產生 5 則`.
- [ ] Write and red/green error-message tests for classification failure and 40-company shortage.
- [ ] Add stage messages through `warning_sink` for classifying 15, expanding to 25, and expanding to 40; test each message one at a time.
- [ ] Run focused migration and AppTest files and refactor only new UI mapping code.

### Task 7: Real boundary, copy database, and visual QA

**Files:**
- Modify: `tests/test_llm_contract.py`
- Modify: `HANDOFF.md`
- Modify: `.gitignore` only if `.screenshots/` is not already ignored.

**Interfaces:**
- Contract test calls the real configured Gemma classification route and parses six approved categories.

- [ ] Write the contract test first and verify collection/skip behavior without a key; run it with the existing local Google key and confirm a parsable result.
- [ ] Run compileall, `git diff --check`, focused tests, then the full suite with `PYTHON_DOTENV_DISABLED=1`.
- [ ] Create a SQLite Backup API copy under `/private/tmp`, record source/copy idea counts and integrity, execute one five-candidate generation against only the copy, and verify formal `daibu.db` count/fingerprint is unchanged.
- [ ] Start the worktree app on port 8502 with the copy database. Use Playwright round one at 1280×800 and 375×812, score all eight visual criteria, and list failures explicitly.
- [ ] Fix each observed UI defect through its own red/green test where applicable; repeat exactly one desktop and one mobile screenshot for round two and verify no horizontal overflow or console/server errors.
- [ ] Complete the nine-field product-owner checkpoint in `HANDOFF.md`, including final screenshot paths, test evidence, cost, security, and remaining classification limits.

### Task 8: Integrate and deploy local production

**Files:**
- Modify: `HANDOFF.md`

**Interfaces:**
- `main` and `origin/main` contain the verified feature; the existing `io.daibu.content-brain` service continues serving `127.0.0.1:8501`.

- [ ] Commit all feature work in reviewable TDD slices and verify the worktree is clean except ignored evidence.
- [ ] Merge `codex/startup-content-diversity` into `main` without touching the user's unrelated dirty files; stop if overlap or conflicts occur.
- [ ] Run the full suite again on `main`, then push and verify the remote commit.
- [ ] Back up the formal database, update only the AI startup theme count from 3 to 5 if needed, restart the existing LaunchAgent, and verify integrity plus unchanged ideas before any real user action.
- [ ] Open the formal site from the home page, run the core five-candidate flow only if it can be done on a database copy, and verify 1280px/375px, console, server log, localhost binding, and final user-visible count.
