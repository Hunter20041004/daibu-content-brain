# Company Profile Deduplication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Do not use subagents unless the user explicitly requests delegation.

**Goal:** Make company-profile series show and generate only one verified candidate per company across the full history of that series.

**Architecture:** Read all historical company/title identities for the selected series, pass them to the LLM as a cost-saving hint, then enforce the same exclusions deterministically before persistence. A pure presentation filter keeps legacy blank-company rows and later duplicate-company rows in SQLite while hiding them from company-profile workflows. General series retain their current behavior.

**Tech Stack:** Python 3.11, Streamlit, SQLite, pytest, Gemini/Groq adapters, Playwright CLI.

## Product and Safety Constraints

- A company may appear only once in the full history of one company-profile series, regardless of status.
- Compare company names after trimming and Unicode-aware case folding; do not add fuzzy matching.
- Compare titles after trimming and case folding.
- Never delete, rewrite, or change the status of legacy ideas.
- For existing duplicates, the earliest `created_at`, then lowest `id`, is the visible record.
- Invalid or duplicate generated ideas must not be persisted.
- Do not retry the LLM merely to fill the requested count.
- General-content series must preserve existing behavior.
- Preserve the user's unrelated dirty build-story files.
- Use vertical TDD: exactly one new failing test before each minimal implementation.

## File Map

- Modify `daibu/db.py`: read title/company exclusions for one series across every status.
- Modify `daibu/llm/base.py`, `daibu/llm/gemini.py`, `daibu/llm/groq.py`, `daibu/llm/prompt.py`: carry and render seen companies.
- Modify `daibu/selection.py`: normalize identities, hard-filter history and within-batch duplicates, and expose the pure legacy visibility filter.
- Modify `pages/1_選題.py`: use filtered company-profile history and replace comparison wording.
- Modify `tests/test_db.py`, `tests/test_llm.py`, `tests/test_selection.py`, `tests/test_app_smoke.py`: regression coverage.
- Modify `HANDOFF.md`: record product behavior, test evidence, screenshots, and remaining exact-match limitation.

---

### Task 1: Read all historical exclusions for a series

**Files:**
- Modify: `tests/test_db.py`
- Modify: `daibu/db.py`

- [ ] **Step 1 — RED:** Add `test_get_idea_exclusions_includes_every_status_and_skips_blank_companies`. Create ideas in candidate, adopted, published, and rejected states; include one blank company and an idea from another theme. Expect ordered titles from every same-theme row and only nonblank same-theme companies.
- [ ] **Step 2 — Verify RED:** Run `.venv/bin/pytest -q tests/test_db.py::test_get_idea_exclusions_includes_every_status_and_skips_blank_companies`. Expect missing `get_idea_exclusions`.
- [ ] **Step 3 — GREEN:** Add `get_idea_exclusions(conn, theme_id) -> tuple[list[str], list[str]]` using one parameterized query ordered by `created_at, id`. Do not change schema or data.
- [ ] **Step 4 — Verify GREEN:** Re-run the single test; expect `1 passed`.
- [ ] **Step 5 — Refactor:** Keep SQL and return construction small; re-run the same test.
- [ ] **Step 6 — Commit:** `git commit -am "feat: read company profile history exclusions"`.

### Task 2: Tell the LLM which companies already appeared

**Files:**
- Modify: `tests/test_llm.py`
- Modify: `daibu/llm/prompt.py`
- Modify: `daibu/llm/base.py`
- Modify: `daibu/llm/gemini.py`
- Modify: `daibu/llm/groq.py`

- [ ] **Step 1 — RED:** Add `test_company_profile_prompt_avoids_seen_companies_and_titles`. Expect a company-profile prompt to contain separate seen-company and seen-title sections and state that both are forbidden.
- [ ] **Step 2 — Verify RED:** Run only that test and observe the unsupported `avoid_companies` argument.
- [ ] **Step 3 — GREEN:** Add optional `avoid_companies` through the provider protocol/adapters and prompt builder. Preserve optional defaults so existing general-series callers keep working.
- [ ] **Step 4 — Verify GREEN:** Re-run the single test.
- [ ] **Step 5 — RED:** Add one adapter mapping test proving Gemini forwards `avoid_companies` into the built prompt.
- [ ] **Step 6 — Verify RED:** Run only the new adapter test and observe the missing forwarding.
- [ ] **Step 7 — GREEN:** Forward the keyword in Gemini and Groq with no unrelated response changes.
- [ ] **Step 8 — Verify GREEN and refactor:** Run `tests/test_llm.py` quietly and remove duplicated prompt-section construction if needed.
- [ ] **Step 9 — Commit:** `git commit -am "feat: tell idea providers about seen companies"`.

### Task 3: Enforce history and batch deduplication before persistence

**Files:**
- Modify: `tests/test_selection.py`
- Modify: `daibu/selection.py`

- [ ] **Step 1 — RED:** Add `test_company_generation_rejects_seen_company_across_all_statuses`. Seed a previously adopted `Railway`, return `railway` plus a new verified company, and expect only the new company to be written.
- [ ] **Step 2 — Verify RED:** Run only this test and observe that both are stored.
- [ ] **Step 3 — GREEN:** Normalize via `strip().casefold()`, fetch exclusions from Task 1, pass them to the provider, and reject historical company matches before `add_idea`.
- [ ] **Step 4 — Verify GREEN:** Re-run the single test.
- [ ] **Step 5 — RED:** Add `test_company_generation_rejects_seen_title_and_same_batch_duplicates`. Return one historical title, two case/space variants of the same new company, and one distinct new company; expect one record per new company and no historical title.
- [ ] **Step 6 — Verify RED:** Run only this test and observe duplicate persistence.
- [ ] **Step 7 — GREEN:** Track accepted normalized companies and titles while preserving provider order; filter before persistence.
- [ ] **Step 8 — Verify GREEN:** Re-run the single test.
- [ ] **Step 9 — RED:** Add a test proving a fully filtered response raises `NoVerifiedCompanyCandidatesError` and leaves existing rows unchanged.
- [ ] **Step 10 — Verify RED/GREEN:** Update the error message to say no **new** verified company was found, then run the single test.
- [ ] **Step 11 — Refactor and focused suite:** Run `.venv/bin/pytest -q tests/test_selection.py tests/test_db.py tests/test_llm.py`.
- [ ] **Step 12 — Commit:** `git commit -am "fix: block repeated company profile ideas"`.

### Task 4: Hide incompatible legacy rows without deleting them

**Files:**
- Modify: `tests/test_selection.py`
- Modify: `daibu/selection.py`
- Modify: `tests/test_app_smoke.py`
- Modify: `pages/1_選題.py`

- [ ] **Step 1 — RED:** Add `test_visible_company_profile_ideas_keeps_earliest_valid_company`. Supply blank-company legacy data, two Railway variants with different timestamps/ids, and Cloudflare. Expect blank rows and later Railway hidden while input objects remain unchanged.
- [ ] **Step 2 — Verify RED:** Run only the pure selection test and observe missing helper.
- [ ] **Step 3 — GREEN:** Add `visible_company_profile_ideas(ideas)` that determines keepers in oldest-first order and returns them in the caller's original display order.
- [ ] **Step 4 — Verify GREEN:** Re-run the single test.
- [ ] **Step 5 — RED:** Add an AppTest regression seeded with the same shape. Expect the candidate heading and buttons to contain only the earliest Railway and Cloudflare, while direct DB reads still contain every row.
- [ ] **Step 6 — Verify RED:** Run only the AppTest and observe legacy/duplicate rows still displayed.
- [ ] **Step 7 — GREEN:** Load all ideas once, filter only ideas whose theme is `company_profile`, then rebuild candidate/adopted/published lists. Keep general-series rows untouched.
- [ ] **Step 8 — Verify GREEN:** Re-run the AppTest and the existing general candidate test.
- [ ] **Step 9 — Commit:** `git commit -am "fix: hide legacy non-company candidates"`.

### Task 5: Replace misleading comparison wording

**Files:**
- Modify: `tests/test_app_smoke.py`
- Modify: `pages/1_選題.py`

- [ ] **Step 1 — RED:** Update/add one company-profile AppTest to require 「瀏覽」/「查看」 copy and forbid candidate-workflow text beginning with 「比較｜」.
- [ ] **Step 2 — Verify RED:** Run the single test and observe old wording.
- [ ] **Step 3 — GREEN:** Change only the research/decision coach, loading message, caption, and fallback button copy. Keep the existing visual system, button hierarchy, focus behavior, and loading spinner.
- [ ] **Step 4 — Verify GREEN:** Re-run the single test.
- [ ] **Step 5 — Regression:** Update existing tests that intentionally asserted the replaced wording, then run `.venv/bin/pytest -q tests/test_app_smoke.py`.
- [ ] **Step 6 — UI review:** Use the required Before/After table. Confirm labels remain explicit accessible names, loading feedback remains present, one primary action remains, and no new animation is needed for frequently used candidate navigation.
- [ ] **Step 7 — Commit:** `git commit -am "fix: clarify company candidate browsing copy"`.

### Task 6: Verify real boundaries, visuals, and the whole product

**Files:**
- Modify: `.gitignore` only if `.screenshots/` is not already ignored.
- Modify: `HANDOFF.md`

- [ ] **Step 1 — Focused test:** Run `.venv/bin/pytest -q tests/test_db.py tests/test_llm.py tests/test_selection.py tests/test_app_smoke.py`.
- [ ] **Step 2 — Real Gemini contract:** Run `.venv/bin/pytest -q -m contract tests/test_llm_contract.py::test_real_llm_returns_parsable_ideas`. Verify the real response still parses into company-profile `Idea` fields; never print API keys.
- [ ] **Step 3 — Safe browser database:** Copy `daibu.db` to a temporary database. Start the worktree app on a non-production port with `DAIBU_DB_PATH` pointing at the copy; never click generation against the real database.
- [ ] **Step 4 — Screenshot round 1:** Use Playwright CLI at 1280×800 and 375×812, exactly two screenshots. Inspect hierarchy, whitespace, typography, palette, alignment, responsiveness/overflow, states, and motion. Record every failure explicitly.
- [ ] **Step 5 — Correct failures:** Make the smallest necessary change, covered by a focused test where behavior changed.
- [ ] **Step 6 — Screenshot round 2:** Repeat exactly the desktop/mobile pair and confirm all eight checks pass. Do not re-read old screenshots.
- [ ] **Step 7 — Product checkpoint:** Report product ability, user experience, technical structure, data flow, design reason, alternative, safety/cost, test evidence, and remaining exact-match limitation before full-suite/commit.
- [ ] **Step 8 — Full suite:** Run `.venv/bin/pytest -q`; do not claim success unless exit code is zero.
- [ ] **Step 9 — Update handoff:** Record root cause, visible before/after, real DB calibration method, TDD evidence, screenshot paths, contract/full-suite results, costs, and limitations.
- [ ] **Step 10 — Final commit:** Stage only task files and commit `fix: prevent repeated company introductions`.

### Task 7: Integrate, push, and verify the running localhost app

- [ ] **Step 1:** Confirm the implementation worktree is clean and all task commits exist.
- [ ] **Step 2:** Merge the implementation branch into `main` without overwriting the user's unrelated dirty files. Stop if paths overlap or Git reports a conflict.
- [ ] **Step 3:** On `main`, run `.venv/bin/pytest -q` again.
- [ ] **Step 4:** Push `main` to the existing remote and verify `origin/main` contains the final commit.
- [ ] **Step 5:** Restart the existing `io.daibu.content-brain` LaunchAgent through the supported local service command, without changing `.env` or the real database.
- [ ] **Step 6:** Open `http://localhost:8501/選題`, verify the real 10-row database now presents only the three valid unique companies, verify 「比較｜」 is absent from the company candidate workflow, and check browser console/server errors. Do not generate new candidates during this production-data verification.
- [ ] **Step 7:** Update `HANDOFF.md` with final localhost evidence if it differs from the safe-copy evidence, commit/push that evidence, and report the clickable local URL.
