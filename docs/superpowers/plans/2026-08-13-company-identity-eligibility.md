# Company Identity Eligibility Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` task-by-task. Do not use subagents unless the user explicitly requests delegation.

**Goal:** Stop same-name companies from contaminating startup eligibility decisions, and preserve YC/Speedrun identity facts through the final evidence check.

**Architecture:** Pass each discovered `CompanyLead` into eligibility evaluation instead of reducing it to a bare company name. Build a traceable identity material from the directory profile and enrich the single Tavily query with the official domain, profile, cohort, and known year. Before a public/acquired claim can disqualify a company, require its evidence to match the known identity; unmatched evidence becomes unknown rather than a false rejection.

**Tech Stack:** Python 3.11, SQLite, Streamlit, pytest, Tavily, Gemini/Groq adapter, Playwright CLI.

## Global Constraints

- Keep the existing eligibility definition: founded no more than ten years ago, not public, not acquired/subsidiary, and private independent.
- One Tavily request per unchecked company and one free-LLM request per batch; no retries to fill three ideas.
- Directory facts must retain their source URL and remain auditable; model memory alone is never evidence.
- A public/acquired fact that cannot be tied to the official domain or directory identity may not disqualify a company.
- Unknown evidence remains excluded; do not weaken the gate or add a manual allowlist.
- Do not modify or delete existing `ideas`; preserve unrelated dirty build-story files.
- Use vertical TDD: one failing test, minimum implementation, green, refactor, then the next test.

## File Map

- Modify `daibu/company_eligibility.py`: accept identity-rich inputs, build identity-aware search/prompt materials, and reject mismatched disqualifying evidence.
- Modify `daibu/selection.py`: retain the discovered lead for each generated company and pass it to eligibility evaluation.
- Modify `tests/test_company_eligibility.py`: query, directory evidence, and same-name regression coverage.
- Modify `tests/test_selection.py`: selection-to-eligibility identity packet contract.
- Modify `HANDOFF.md`: root cause, TDD evidence, database-copy acceptance, production correction, and remaining limits.

---

### Task 1: Carry directory identity into eligibility research

**Files:** `daibu/company_eligibility.py`, `tests/test_company_eligibility.py`

**Interface:** `evaluate_companies(companies: list[str | CompanyLead], ...) -> dict[str, CompanyEligibility]` remains compatible with string callers; a `CompanyLead` adds profile URL, official URL, year, cohort, and directory status.

- [ ] Add `test_evaluate_companies_searches_with_official_identity` using an Almanac lead and capture the single search query.
- [ ] Run that test and observe that the query contains only the bare name and generic terms.
- [ ] Extend input normalization and query construction with `usealmanac.com`, the YC profile, `Summer 2026`, and known year when present.
- [ ] Re-run the single test and verify one search call with the complete identity.
- [ ] Add `test_directory_year_is_traceable_evidence` for Feldy/Marengo and observe `unknown` because directory facts are absent from verifier materials.
- [ ] Add one synthetic `Material` backed by the profile/discovery URL with only the directory fields actually present; verify the year claim can match it without treating `active` as proof of private ownership.
- [ ] Run `tests/test_company_eligibility.py` and commit the green slice.

### Task 2: Reject a disqualifying fact from a same-name company

**Files:** `daibu/company_eligibility.py`, `tests/test_company_eligibility.py`

- [ ] Add `test_acquired_evidence_for_different_official_domain_does_not_disqualify_almanac`: Almanac identity is `usealmanac.com`, while the only acquired evidence URL/text identifies Almanac Realty Investors; expect `unknown`, not `ineligible`.
- [ ] Run the test and observe the current false `ineligible` result.
- [ ] Add a deterministic identity matcher for public/acquired evidence. Known official/profile identity must appear in the evidence URL or material text; otherwise drop that disqualifying claim before deriving the verdict.
- [ ] Re-run the regression test and verify green.
- [ ] Run existing Cloudflare public and acquired-company tests to prove evidence tied to the intended company still produces `ineligible`.
- [ ] Refactor identity helpers without changing behavior; run the focused file and commit.

### Task 3: Preserve identity through candidate generation

**Files:** `daibu/selection.py`, `tests/test_selection.py`

- [ ] Add `test_company_selection_passes_discovery_identity_to_eligibility`, capture the evaluator input, and assert the lead retains official/profile URLs, year, cohort, and source name.
- [ ] Run the test and observe that eligibility receives only company-name strings.
- [ ] Map verified generated companies back to their normalized discovery leads and pass those leads to `evaluate_companies`; retain the string fallback only for legacy backfill.
- [ ] Re-run the single test, then the complete selection test file.
- [ ] Add a safety regression proving a genuinely public matched company still creates zero ideas and caches `ineligible`; run green and commit.

### Task 4: Correct the three polluted records on a production copy

**Files:** `HANDOFF.md`

- [ ] Create a SQLite Backup API copy of formal `daibu.db`; calibrate 12 ideas, 13 eligibility records, and the full idea fingerprint.
- [ ] Delete only `almanac`, `feldy`, and `marengo` eligibility rows in the copy; verify all idea fields and the other ten eligibility records are unchanged.
- [ ] Run one real identity-aware eligibility batch for those three companies on the copy. Verify Almanac is never rejected using Almanac Realty Investors evidence; inspect Feldy/Marengo traceable evidence and verdicts without weakening unknown handling.
- [ ] If the real boundary differs from mocks, fix implementation with a new single failing contract regression rather than changing expected evidence.
- [ ] Start the copy on port 8502 and run the core generation flow at most once; verify no partial writes on failure and only eligible companies become ideas.
- [ ] Complete two rounds of exactly one 1280×800 and one 375×812 screenshot, checking hierarchy, spacing, typography, palette, alignment, overflow, states, and motion.

### Task 5: Finish, merge, correct formal metadata, and deploy

**Files:** `HANDOFF.md`

- [ ] Deliver the nine-field product-owner checkpoint before full tests.
- [ ] Run `PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q`, `git diff --check`, compile checks, and a production-diff secret scan.
- [ ] Commit the feature branch, merge into `main` without touching unrelated dirty files, and re-run the full suite on `main`.
- [ ] Back up formal `daibu.db`; record integrity, 12-idea fingerprint, and 13 eligibility rows before metadata correction.
- [ ] Delete only the three confirmed polluted eligibility rows. Do not call the production API automatically; the next user generation will use the corrected identity-aware pipeline.
- [ ] Verify the ideas fingerprint and all other eligibility rows are unchanged, then push `main` and confirm local/remote equality.
- [ ] Restart `io.daibu.content-brain`, verify health and `127.0.0.1:8501` binding, then inspect the real desktop/mobile page without clicking generation.
- [ ] Update `HANDOFF.md`, commit/push final evidence, remove the owned worktree/branch, and report the localhost URL plus public-evidence limitations.
