# Remove Problem Causal Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the entire pink dashed causal guide, its three circles, and arrow from carousel page 3 without moving its cards or text.

**Architecture:** Delete the decorative `causal-spine` node from the shared Renderer and remove its now-unused CSS. Because editor preview and PNG export both consume the Renderer, one change removes the graphic everywhere without schema or database changes.

**Tech Stack:** Python 3.11, Streamlit, HTML/CSS Renderer, pytest, Playwright Chromium.

## Global Constraints

- Preserve all page-3 card and text coordinates.
- Do not change schema v4, layout JSON, migration code, SQLite tables, template bindings, or content revisions.
- Use strict vertical TDD: one failing test, minimal implementation, Green, then refactor.
- Complete two 1280×800 and 375×812 screenshot QA rounds before rollout.
- Preserve root untracked `.DS_Store`, `.claude/`, and `.impeccable/`.

---

### Task 1: Remove the decorative causal spine

**Files:**
- Modify: `tests/test_cards_render.py`
- Modify: `daibu/cards/render.py`
- Modify: `daibu/cards/templates/sticky-notebook-v1.css`

**Interfaces:**
- Consumes: existing `_problem_page()` Renderer composition and page-3 visual regression test.
- Produces: page-3 markup with the same registered layout hooks but no `causal-spine` decoration.

- [ ] **Step 1: Change one Renderer assertion to the new expected behavior**

In `test_problem_restores_the_approved_v57_story_layers`, replace:

```python
assert markup.count('data-visual="causal-spine"') == 1
```

with:

```python
assert 'data-visual="causal-spine"' not in markup
```

- [ ] **Step 2: Run the single test and verify Red**

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_render.py::test_problem_restores_the_approved_v57_story_layers
```

Expected: FAIL because the current Renderer still emits one `causal-spine` element.

- [ ] **Step 3: Remove the Renderer node**

In `_problem_page()`, remove only this concatenated block:

```python
+ _layout_box(
    "spine",
    "",
    classes="causal-spine",
    attributes='data-visual="causal-spine"',
)
```

Keep `_problem_node_layers(page, 0..2)` in the same order and do not alter their layout elements.

- [ ] **Step 4: Run the single test and verify Green**

Run the Step 2 command again.

Expected: `1 passed`.

- [ ] **Step 5: Remove unused CSS and verify no production reference remains**

Delete these rules from `sticky-notebook-v1.css`:

```css
.causal-spine{z-index:1;border-left:6px dashed var(--coral)}
.causal-spine{border-left:6px dashed var(--coral)}
.causal-spine::before{content:"";position:absolute;left:-10px;top:0;width:12px;height:12px;border:3px solid var(--coral);border-radius:50%;background:var(--paper);box-sizing:border-box;box-shadow:0 300px 0 -3px var(--paper),0 300px 0 0 var(--coral),0 610px 0 -3px var(--paper),0 610px 0 0 var(--coral)}
.causal-spine::after{content:"";position:absolute;left:-11px;bottom:-5px;width:16px;height:13px;background:var(--coral);clip-path:polygon(0 0,100% 0,50% 100%)}
```

Run:

```bash
rg -n "causal-spine" daibu
```

Expected: no matches and exit code 1. An empty result is valid only after the Red/Green Renderer test has calibrated the search target.

- [ ] **Step 6: Run focused rendering and layout tests**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_render.py \
  tests/test_cards_layout_validation.py \
  tests/test_cards_shoot.py \
  tests/test_cards_template_editor_payload.py
```

Expected: all selected tests pass; the page-3 three-card and independent-layer assertions remain Green.

- [ ] **Step 7: Commit the implementation**

```bash
git add tests/test_cards_render.py daibu/cards/render.py \
  daibu/cards/templates/sticky-notebook-v1.css
git commit -m "fix: remove problem causal spine"
```

---

### Task 2: Verify visually and roll out

**Files:**
- Modify: `HANDOFF.md`
- Create locally/ignored: `.screenshots/remove-causal-spine-round1-desktop.png`
- Create locally/ignored: `.screenshots/remove-causal-spine-round1-mobile.png`
- Create locally/ignored: `.screenshots/remove-causal-spine-final-desktop.png`
- Create locally/ignored: `.screenshots/remove-causal-spine-final-mobile.png`

**Interfaces:**
- Consumes: Task 1 Renderer output.
- Produces: verified `main`, synced remote, and healthy existing production service.

- [ ] **Step 1: Start an isolated service with a copied SQLite database**

Run:

```bash
mkdir -p /tmp/daibu-remove-causal-spine
sqlite3 /Users/cengweiting/Developer/daibu-content-brain/daibu.db \
  ".backup '/tmp/daibu-remove-causal-spine/qa.db'"
DAIBU_DB_PATH=/tmp/daibu-remove-causal-spine/qa.db \
PYTHON_DOTENV_DISABLED=1 .venv/bin/streamlit run server.py \
  --server.address=127.0.0.1 --server.port=8768 --server.headless=true
```

Expected: copied DB `PRAGMA integrity_check` returns `ok`; isolated health endpoint returns `ok`. Do not write to the production DB during visual QA.

- [ ] **Step 2: Perform visual QA round 1**

Open `/設定`, select page 3, and take exactly one desktop and one mobile screenshot:

```bash
playwright-cli resize 1280 800
playwright-cli screenshot --filename=.screenshots/remove-causal-spine-round1-desktop.png
playwright-cli resize 375 812
playwright-cli screenshot --filename=.screenshots/remove-causal-spine-round1-mobile.png
```

Inspect only these new images. Require the line, circles, and arrow to be absent; three problem cards and their text remain visible. Grade hierarchy, whitespace, font distinction, maximum-three main colors, alignment, 375px overflow, states, and micro-motion.

- [ ] **Step 3: Fix any reproducible defect through one Red→Green test**

For each defect, add one narrow failing Renderer or browser test, run it Red, make the minimum fix, and rerun it Green. Do not alter card coordinates merely to make the screenshot look different.

- [ ] **Step 4: Perform visual QA round 2**

Take exactly one replacement desktop and mobile screenshot using `remove-causal-spine-final-*.png`. Require all eight visual categories to pass, mobile overflow 0, Streamlit exceptions 0, and console errors/warnings 0.

- [ ] **Step 5: Deliver the product checkpoint and run the feature-branch full suite**

Record in `HANDOFF.md`: visible result, Renderer→preview/PNG data flow, why DOM removal was chosen over CSS hiding, no schema/data/cost impact, focused tests, screenshots, and remaining limits.

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q
```

Expected: all non-contract tests pass; only documented external-service deselections and the known Starlette/httpx warning may remain.

- [ ] **Step 6: Commit the handoff and merge**

```bash
git add HANDOFF.md
git commit -m "docs: record causal spine removal"
```

Fast-forward merge into `main` without touching unrelated untracked files, then rerun the complete suite on `main`.

- [ ] **Step 7: Push and verify the existing production service**

Push `main`, require `git rev-parse HEAD` and `git ls-remote origin refs/heads/main` to match, then restart only `io.daibu.content-brain`. Verify:

- `http://127.0.0.1:8501/_stcore/health` returns `ok`.
- `/設定` page 3 contains zero `.causal-spine` / `data-visual="causal-spine"` elements.
- The three problem cards remain present.
- Desktop and 375px mobile overflow are 0.
- No new Streamlit exception, critical console error, or server traceback appears.

- [ ] **Step 8: Preserve screenshot evidence and clean the feature worktree**

Copy the four ignored screenshots to main `.screenshots/`, remove the merged worktree, prune registrations, and delete the merged feature branch. Do not remove the production database backup.
