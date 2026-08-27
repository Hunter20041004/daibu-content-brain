# Editor Scroll and Carousel Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the adopted-item edit button visibly open its editor and make six-page carousel generation recover once from schema-valid but product-invalid LLM output without losing existing content.

**Architecture:** Reuse the existing Streamlit iframe scroll bridge for editor focus. Keep model parsing strict, deterministically replace the fixed CTA, and retry only one validation failure with exact feedback before surfacing a safe product error.

**Tech Stack:** Python 3.11, Streamlit, SQLite, pytest, Google GenAI, Playwright CLI.

## Global Constraints

- TDD is vertical: one failing test, minimal implementation, green, then the next test.
- Keep `check_same_thread=True`; callbacks must not reuse a page-global SQLite connection.
- Use only configured free LLM providers; do not add dependencies or paid calls.
- Never overwrite sources, drafts, or images unless the complete replacement draft validates.
- Reuse the existing brand palette, typography, spacing and motion preferences.

---

### Task 1: Adopted editor selection and scroll bridge

**Files:**
- Modify: `tests/test_app_smoke.py`
- Modify: `pages/1_選題.py`

**Interfaces:**
- Consumes: `st.session_state.selected_adopted_id`, the existing iframe scroll pattern.
- Produces: `scroll_to_adopted_editor_id: int`, anchor `adopted-editor-<id>`, selected label `正在編輯｜<title>`.

- [ ] **Step 1: Write the failing selected-state and scroll-marker test**

Seed two adopted ideas, run the page, click the second `編輯｜...` button, then assert the button becomes `正在編輯｜...` and rendered markdown contains:

```python
assert f'id="adopted-editor-{second_id}"' in scroll_markup
assert 'data-scroll-requested="true"' in scroll_markup
```

- [ ] **Step 2: Run the current test file and verify RED**

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_app_smoke.py -k selecting_adopted_item_marks_and_scrolls
```

Expected: FAIL because the label remains `編輯｜...` and no adopted-editor marker exists.

- [ ] **Step 3: Implement the minimal selection and scroll behavior**

Set both session keys on click, render the selected label from existing state, place a unique anchor before the selected expander, and create a one-shot iframe that runs:

```javascript
anchor.scrollIntoView({
  behavior: reduceMotion ? "auto" : "smooth",
  block: "start",
});
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the Step 2 command. Expected: one passed test.

---

### Task 2: Deterministic fixed CTA

**Files:**
- Modify: `tests/test_cards_draft.py`
- Modify: `daibu/cards/draft.py`

**Interfaces:**
- Consumes: `CarouselDraft`, `pages.CTA_TEXT`.
- Produces: `_with_fixed_cta(draft: CarouselDraft) -> CarouselDraft`.

- [ ] **Step 1: Write the failing CTA normalization test**

Return a structured six-page response whose CTA text is `模型自己寫的 CTA`, call `draft.create()`, and assert:

```python
assert result.pages[-1].sections[0].text == pages.CTA_TEXT
assert result.pages[-1].sections[0].source_ids == ()
assert result.pages[-1].sections[0].evidence_quotes == ()
```

- [ ] **Step 2: Verify RED**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_draft.py -k replaces_model_cta_with_fixed_brand_copy
```

Expected: `LLMResponseError` caused by the fixed-brand-copy validation rule.

- [ ] **Step 3: Implement the minimal immutable replacement**

Use `dataclasses.replace` to replace only the CTA section text and clear its source ids and evidence quotes before grounded validation.

- [ ] **Step 4: Verify GREEN**

Run the Step 2 command. Expected: one passed test.

---

### Task 3: One validation-feedback retry

**Files:**
- Modify: `tests/test_cards_draft.py`
- Modify: `daibu/cards/draft.py`

**Interfaces:**
- Consumes: validation `ValueError`, the original carousel prompt.
- Produces: at most two `generate_text(prompt: str) -> str` calls.

- [ ] **Step 1: Write a failing recoverable-response test**

Make the first response omit evidence from `人仍負責`, make the second response valid, and assert two calls, persisted valid output, and the second prompt contains the exact first validation issue.

- [ ] **Step 2: Verify RED**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_draft.py -k retries_once_with_validation_feedback
```

Expected: first response raises immediately and only one call is observed.

- [ ] **Step 3: Implement one bounded retry**

On parsing or validation `ValueError`, append a concise correction block containing `str(error)` to the original prompt and regenerate the entire six-page array once. Preserve the second raw response in `LLMResponseError` if it still fails.

- [ ] **Step 4: Verify GREEN and the terminal failure contract**

Update the existing invalid-JSON test to expect exactly two calls, then run all of `tests/test_cards_draft.py`.

---

### Task 4: Clean failed research status

**Files:**
- Modify: `tests/test_app_smoke.py`
- Modify: `pages/1_選題.py`

**Interfaces:**
- Consumes: the `research_status` object created by `st.status`.
- Produces: collapsed `state="error"` label `公司資料查證未完成` before the safe error panel.

- [ ] **Step 1: Write the failing status-copy test**

Force `carousel_research_draft.generate` to raise `LLMResponseError`, then assert visible status/error copy contains `公司資料查證未完成`, keeps `既有內容沒有被刪除`, and exposes no raw response.

- [ ] **Step 2: Verify RED**

Run only that AppTest case. Expected: failure because the status retains its original running label.

- [ ] **Step 3: Update status before rendering the product error**

Keep a reference to `research_status`; in the handled error path call:

```python
research_status.update(
    label="公司資料查證未完成",
    state="error",
    expanded=False,
)
```

- [ ] **Step 4: Verify GREEN**

Run the focused AppTest case.

---

### Task 5: Real six-page contract and release verification

**Files:**
- Modify: `tests/test_llm_contract.py`
- Modify: `HANDOFF.md`

**Interfaces:**
- Consumes: configured `GEMINI_API_KEY`, `draft.generate`.
- Produces: a six-page real-boundary contract that checks fixed CTA and grounded sections.

- [ ] **Step 1: Correct the stale contract assertion**

Replace the old seven-page assertion with:

```python
assert len(result.pages) == 6
assert result.pages[-1].sections[0].text == pages.CTA_TEXT
validate_grounded_draft(result)
```

- [ ] **Step 2: Run focused unit tests and the real contract**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_draft.py
.venv/bin/pytest -q -m contract \
  tests/test_llm_contract.py::test_real_llm_returns_valid_sourced_carousel
```

Expected: all selected tests pass; a transient provider timeout is reported separately and retried only as a fresh contract run, not hidden by product code.

- [ ] **Step 3: Run two visual QA rounds**

Use an isolated database and Playwright CLI. Each round captures exactly:

```bash
playwright-cli resize 1280 800
playwright-cli screenshot --filename=.screenshots/editor-scroll/desktop.png
playwright-cli resize 375 812
playwright-cli screenshot --filename=.screenshots/editor-scroll/mobile.png
```

First round identifies failures; fix them. Second round must pass hierarchy, spacing, typography, palette, alignment, responsiveness, states and motion. Confirm editor enters the viewport after click and console has zero errors/warnings.

- [ ] **Step 4: Run full verification, review, update handoff, commit, push and deploy**

Run `PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q`, request an independent code review, update `HANDOFF.md`, commit only scoped files, push `main`, restart `io.daibu.content-brain`, verify health/logs/browser flow on the existing `127.0.0.1:8501` service, then rerun the full suite on `main` if any code changed after review.

