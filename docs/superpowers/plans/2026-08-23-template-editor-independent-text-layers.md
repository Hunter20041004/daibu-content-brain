# Template Editor Independent Text Layers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every visible text role across the seven carousel pages an independently selectable layout element whose size, position, font size, and alignment update the real preview immediately.

**Architecture:** Introduce layout schema v2 with a registry entry and direct DOM hook for each semantic text, background, and illustration layer. Read-time normalization upgrades immutable schema-v1 rows into an in-memory v2 document; saving creates a new v2 template version. The production Renderer remains the single preview and export implementation.

**Tech Stack:** Python 3.11, Streamlit Components v2, SQLite, HTML/CSS, browser JavaScript, pytest, Playwright/Chromium.

## Global Constraints

- Follow strict vertical TDD: one failing test, minimum implementation, green, refactor, then the next slice.
- Keep existing database template rows immutable; do not rewrite old `layout_json` or change existing post bindings.
- Do not add external dependencies, CDN assets, LLM calls, paid services, arbitrary CSS, arbitrary HTML, URLs, or file paths.
- Template editing changes layout only; wording remains controlled by the existing content editor.
- Registry IDs and editable properties remain whitelist-only.
- Mobile remains read-only and must not expose the new-version save control.
- Preserve the approved deep navy, cyan, coral, paper-white palette and LINE Seed typography.
- User-owned uncommitted HTML and personal files in the primary checkout must remain untouched.

---

## File Map

- Modify `daibu/cards/layout_registry.py`: keep the schema-v1 composite registry and define the schema-v2 independent-layer registry.
- Create `daibu/cards/layout_upgrade.py`: normalize schema-v1 mappings into schema v2 without database writes.
- Modify `daibu/cards/layout_schema.py`: parse schema v1 through normalization and validate schema v2 directly.
- Replace `daibu/cards/layouts/editorial-v15-1.json`: store the built-in schema-v2 geometry and typography defaults.
- Modify `daibu/cards/render.py`: emit one `data-layout-id` per independent layer while keeping existing `data-edit-key` content hooks.
- Modify `daibu/cards/templates/editorial-v15-1.css`: retain color, weight, line height, and decoration; remove font-size and geometry overrides that defeat layout v2.
- Modify `daibu/cards/template_editor_component.py`: invalidate incompatible cached working copies and keep direct style synchronization.
- Modify `daibu/cards/template_editor_payload.py`: expose schema identity and validate every v2 Renderer hook.
- Modify `daibu/cards/template_stress.py`, `daibu/cards/layout_validation.py`, and related tests only where the expanded registry changes collision or overflow semantics.
- Add focused tests under `tests/test_cards_layout_upgrade.py`, `tests/test_cards_layout_schema.py`, `tests/test_cards_render.py`, and `tests/test_template_editor_browser.py`.

---

### Task 1: Schema-v1 Read Compatibility and Schema-v2 Registry

**Files:**
- Modify: `daibu/cards/layout_registry.py`
- Create: `daibu/cards/layout_upgrade.py`
- Modify: `daibu/cards/layout_schema.py`
- Test: `tests/test_cards_layout_upgrade.py`
- Test: `tests/test_cards_layout_schema.py`

**Interfaces:**
- Produces `registry_for_schema(schema_version: int) -> Mapping[str, Mapping[str, ElementRule]]`.
- Produces `normalize_layout_mapping(value: Mapping[str, object]) -> dict[str, object]`.
- `parse_layout()` returns a schema-v2 `LayoutDocument` for both valid schema-v1 and schema-v2 inputs.

- [ ] **Step 1: Write a failing test proving an old composite layout is normalized without mutation**

```python
def test_schema_v1_layout_normalizes_to_independent_schema_v2_layers():
    raw_v1 = legacy_builtin_layout_mapping()
    before = deepcopy(raw_v1)
    normalized = normalize_layout_mapping(raw_v1)
    assert raw_v1 == before
    assert normalized["schema_version"] == 2
    who = normalized["pages"]["who"]["elements"]
    assert {"facts-bg", "facts-label", "facts-body"} <= set(who)
    assert "facts" not in who
```

- [ ] **Step 2: Run the single test and verify RED**

Run: `PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_layout_upgrade.py::test_schema_v1_layout_normalizes_to_independent_schema_v2_layers`

Expected: FAIL because `normalize_layout_mapping` does not exist.

- [ ] **Step 3: Implement the registry selector and pure normalizer**

The normalizer must deep-copy input, reject unsupported schema versions, derive child geometry from checked-in legacy baselines and v2 defaults, and never execute SQL. For a composite box, transform the v2 child default rectangle by the old box's move and scale relative to the legacy default rectangle. Map an old composite `font_size` to the corresponding body text layer only.

- [ ] **Step 4: Run the focused normalization test and verify GREEN**

Run the Step 2 command. Expected: `1 passed`.

- [ ] **Step 5: Write a failing parser round-trip test**

```python
def test_parse_layout_accepts_v1_and_serializes_normalized_v2():
    document = parse_layout(legacy_builtin_layout_mapping())
    serialized = layout_to_mapping(document)
    assert document.schema_version == 2
    assert serialized["schema_version"] == 2
    assert parse_layout(serialized) == document
```

- [ ] **Step 6: Run RED, then route schema v1 through the normalizer and validate v2 against the v2 registry**

Run: `PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_layout_schema.py::test_parse_layout_accepts_v1_and_serializes_normalized_v2`

Expected before implementation: FAIL. Expected after minimum implementation: PASS.

- [ ] **Step 7: Add rejection tests for unknown schema, missing v2 layers, and unsafe properties one at a time**

Each test must first fail for the expected validation reason, then receive only the minimum validation change. Required cases:

- schema version other than 1 or 2;
- missing `facts-body` in schema v2;
- `font_size` on `facts-bg`;
- unknown element ID;
- normalization input remains byte-for-byte equivalent after failure.

- [ ] **Step 8: Run schema tests and commit**

Run: `PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_layout_upgrade.py tests/test_cards_layout_schema.py`

Commit: `feat: add independent layout schema normalization`

---

### Task 2: Second-page Vertical Slice and Direct Font-size Synchronization

**Files:**
- Modify: `daibu/cards/layouts/editorial-v15-1.json`
- Modify: `daibu/cards/render.py`
- Modify: `daibu/cards/templates/editorial-v15-1.css`
- Modify: `daibu/cards/layout_registry.py`
- Test: `tests/test_cards_render.py`
- Test: `tests/test_template_editor_browser.py`

**Interfaces:**
- Renderer emits `facts-bg`, `facts-label`, `facts-body`, `positioning-bg`, `positioning-label`, and `positioning-body` as siblings.
- Dynamic `data-edit-key` is placed on `facts-body` and `positioning-body` directly.

- [ ] **Step 1: Add a failing Renderer contract for second-page independent layers**

```python
def test_who_page_exposes_background_label_and_body_as_independent_layers():
    output = page_html(who_page(), "公司名稱", None, load_builtin_layout(), allow_logo_placeholder=True)
    for element_id in (
        "positioning-bg", "positioning-label", "positioning-body",
        "facts-bg", "facts-label", "facts-body",
    ):
        assert output.count(f'data-layout-id="{element_id}"') == 1
    assert 'data-layout-id="facts"' not in output
```

- [ ] **Step 2: Run RED**

Run: `PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_render.py::test_who_page_exposes_background_label_and_body_as_independent_layers`

Expected: FAIL because the Renderer still emits `facts` and `positioning` composite sections.

- [ ] **Step 3: Split only the second-page Renderer and CSS, add matching v2 defaults**

Use sibling elements inside the article. Keep background colors and typography weight/line-height in CSS. Put X/Y/W/H/font-size/text-align only in schema-v2 layout CSS. Preserve the original visual positions as the initial defaults.

- [ ] **Step 4: Run the Renderer test and existing production render tests**

Run: `PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_render.py tests/test_cards_render_editorial.py`

Expected: all selected tests pass.

- [ ] **Step 5: Add a failing real-browser font-size test**

```python
def test_who_facts_body_font_size_updates_the_real_text_node(tmp_path):
    # Open isolated Streamlit, select page 02 and facts-body.
    # Record getComputedStyle(actual).fontSize and selection bounding box.
    # Increase the property panel font size by 8 and blur.
    # Assert computed font size increased by 8 canvas px after scale conversion,
    # and actual/selection bounds differ by no more than 1 CSS px.
```

- [ ] **Step 6: Run RED and capture the old failure**

Run: `PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_template_editor_browser.py::test_who_facts_body_font_size_updates_the_real_text_node`

Expected on the old behavior: the right-side value changes but computed font size does not.

- [ ] **Step 7: Make direct DOM synchronization pass without descendant overrides**

Keep `applyWorkingLayout()` targeted to the selected `data-layout-id`. Remove only CSS declarations that overwrite v2 text-layer font size. Do not use broad descendant `!important` rules.

- [ ] **Step 8: Add a failing independence test, then make it green**

The browser test selects `facts-label`, changes X by 40 canvas px, and asserts:

- label moves;
- `facts-body` moves 0 px;
- `facts-bg` moves 0 px;
- selection and label bounds differ by at most 1 CSS px.

- [ ] **Step 9: Run the second-page slice and commit**

Run: `PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_render.py tests/test_template_editor_browser.py -k 'who or facts or positioning'`

Commit: `feat: split company profile text layers`

---

### Task 3: Independent Header, Problem, and AI-role Layers

**Files:**
- Modify: `daibu/cards/layout_registry.py`
- Modify: `daibu/cards/layouts/editorial-v15-1.json`
- Modify: `daibu/cards/render.py`
- Modify: `daibu/cards/templates/editorial-v15-1.css`
- Test: `tests/test_cards_render.py`
- Test: `tests/test_cards_layout_registry.py`

**Interfaces:**
- Header becomes `series` and `company-name` text layers on pages 2–7.
- Problem stages expose `stage-N-bg`, `stage-N-icon`, `stage-N-label`, `stage-N-body`, and visible `stage-N-context` layers.
- AI steps expose `step-N-bg`, `step-N-icon`, `step-N-label`, `step-N-body`; caution exposes `caution-bg`, `caution-label`, and `caution-body`.

- [ ] **Step 1: Add and run one failing header-layer test**

Assert pages 2–7 each emit exactly one `series` and `company-name`, and no `header` layout hook. Run only this test and observe RED.

- [ ] **Step 2: Split `_editorial_header` into direct layout siblings and turn the test GREEN**

Keep series/company wording escaped. Preserve the same initial placement in v2 layout.

- [ ] **Step 3: Add one failing problem-page inventory test, implement one stage, and turn it GREEN**

Start with stage 1. Its background, icon, label, main sentence, and context must be separate siblings. Repeat vertically for stages 2 and 3 only after the previous stage passes.

- [ ] **Step 4: Add one failing AI-step inventory test, implement one step, and turn it GREEN**

Repeat vertically for steps 2 and 3, then for the three caution layers.

- [ ] **Step 5: Add registry completeness and unique-hook tests**

For pages 2–4, assert every v2 registry ID appears exactly once and every visible text node with non-whitespace content is either a registered text layer or an explicitly approved non-layout accessibility node.

- [ ] **Step 6: Run page 2–4 Renderer, schema, overflow, and collision tests**

Run: `PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_render.py tests/test_cards_layout_registry.py tests/test_cards_layout_validation.py -k 'who or problem or how_ai or how-ai or registry'`

- [ ] **Step 7: Commit**

Commit: `feat: split header problem and ai text layers`

---

### Task 4: Independent Results, Signals, and Closing Layers

**Files:**
- Modify: `daibu/cards/layout_registry.py`
- Modify: `daibu/cards/layouts/editorial-v15-1.json`
- Modify: `daibu/cards/render.py`
- Modify: `daibu/cards/templates/editorial-v15-1.css`
- Test: `tests/test_cards_render.py`
- Test: `tests/test_cards_layout_registry.py`

**Interfaces:**
- Results expose independent left/right backgrounds, titles, icons, main sentences, supplementary copy, transition label, `to`, axis, summary, and mascot.
- Signals expose three independent backgrounds, icons, labels, main sentences, supplementary copy, and mascot.
- Closing exposes thesis/question backgrounds, labels and bodies, invitation, heading, header text, and mascot.

- [ ] **Step 1: Add a failing results-page inventory test**

Assert each visible results text role has its own text registry entry and hook, while left/right backgrounds and axis are non-text entries.

- [ ] **Step 2: Split results one semantic group at a time**

Order: left background/copy → axis/to → right background/copy → summary. After each group, run the single inventory test and the results overflow test.

- [ ] **Step 3: Add a failing signals-page inventory test and split each signal vertically**

For each signal, add background, icon, label, body, and context. Verify the primary signal keeps its approved deep background and all text remains readable.

- [ ] **Step 4: Add a failing closing-page inventory test and split thesis/question groups**

Keep fixed label wording locked while making label typography independently adjustable.

- [ ] **Step 5: Add the all-seven visible-text coverage contract**

Render each placeholder page, traverse visible text-bearing elements, and assert every layout-relevant visible text node owns a v2 text `data-layout-id`. The test must explicitly allow only SVG accessibility text and Streamlit/editor chrome outside `.carousel-canvas`.

- [ ] **Step 6: Run all Renderer and layout tests**

Run: `PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_render.py tests/test_cards_render_editorial.py tests/test_cards_layout_registry.py tests/test_cards_layout_schema.py tests/test_cards_layout_validation.py`

- [ ] **Step 7: Commit**

Commit: `feat: split remaining carousel text layers`

---

### Task 5: Editor Cache Compatibility, Save Round-trip, and Immutable Versions

**Files:**
- Modify: `daibu/cards/template_editor_component.py`
- Modify: `daibu/cards/template_editor_payload.py`
- Modify: `daibu/cards/layout_repository.py` only if schema metadata persistence needs adaptation
- Test: `tests/test_cards_template_editor_component.py`
- Test: `tests/test_cards_template_editor_payload.py`
- Test: `tests/test_cards_layout_repository.py`
- Test: `tests/test_template_editor_browser.py`

**Interfaces:**
- Payload exposes `layoutSchemaVersion: 2` and a deterministic registry fingerprint.
- Session cache key includes schema version/fingerprint; incompatible schema-v1 working copies are ignored rather than partially applied.

- [ ] **Step 1: Add a failing cache-compatibility component contract**

Assert persisted state is restored only when `layoutSchemaVersion` and `registryFingerprint` match the current payload.

- [ ] **Step 2: Run RED, implement cache identity, and run GREEN**

Do not clear unrelated browser storage. Ignore only the incompatible template working copy.

- [ ] **Step 3: Add a failing repository immutability test**

Seed a schema-v1 row, load it as normalized v2, save an edit as the next template version, then assert:

- original row JSON is byte-for-byte unchanged;
- new row stores schema version 2;
- version number increments once;
- active pointer remains unchanged.

- [ ] **Step 4: Implement the minimum persistence adaptation and run GREEN**

Use existing `create_version`; do not update old rows.

- [ ] **Step 5: Add a failing browser save/reopen round-trip**

On an isolated SQLite copy, change `facts-body` font size and `facts-label` X, save as a new version, reload that version, and assert both values and computed DOM styles persist.

- [ ] **Step 6: Run all template editor tests and commit**

Run: `PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_template_editor_component.py tests/test_cards_template_editor_payload.py tests/test_cards_layout_repository.py tests/test_template_editor_browser.py`

Commit: `feat: persist independent template text layers`

---

### Task 6: Detailed Functional, Visual, and Production QA

**Files:**
- Modify: `HANDOFF.md`
- Modify: `.gitignore` only if `.screenshots/` is not already ignored
- Test: all affected unit, integration, browser, and stress suites

**Interfaces:**
- No new production interfaces. This task proves the completed feature from the user's viewpoint.

- [ ] **Step 1: Calibrate every numerical measurement**

Before measuring font or movement, test the browser script against a known +8px font change and +40px X change. Record the input delta, rendered CSS delta, preview scale, and selection/actual-element difference.

- [ ] **Step 2: Run seven-page independent-layer interaction QA**

For each page:

- select at least one label, one main/body text, and one background or graphic;
- change font size on text and assert computed font changes;
- move one text layer and assert sibling text/background movement is 0;
- undo, redo, and Escape-cancel one interaction;
- confirm no missing-hook alert and save eligibility follows dirty state.

- [ ] **Step 3: Run three-company stress validation**

Render SUN, Billow AI Labs, and Shiraz AI with horizontal, vertical, and square Logo cases across all seven pages. Assert no text overflow, canvas overflow, illegal collision, missing hook, source/date/page-number regression, or invalid PNG dimensions.

- [ ] **Step 4: Run frontend screenshot loop one**

Use an isolated database on port 8502. Capture exactly:

```bash
playwright-cli resize 1280 800
playwright-cli screenshot --filename=.screenshots/independent-layers-round1-desktop.png
playwright-cli resize 375 812
playwright-cli screenshot --filename=.screenshots/independent-layers-round1-mobile.png
```

Evaluate hierarchy, whitespace rhythm, LINE Seed typography, three-color discipline, alignment, 375px overflow, hover/focus/disabled/error/empty states, and restrained microinteraction. Write every failed item before changing code.

- [ ] **Step 5: Fix visual findings one at a time and run screenshot loop two**

Capture only fresh final images:

- `.screenshots/independent-layers-round2-desktop.png`
- `.screenshots/independent-layers-round2-mobile.png`

Do not reuse round-one screenshots as final evidence.

- [ ] **Step 6: Deliver the product-owner checkpoint before final full tests**

Report product capability, user experience, technical components, data flow, design reason, rejected alternatives, security/cost, focused test evidence, and remaining limits.

- [ ] **Step 7: Run the complete verification suite**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q
PYTHON_DOTENV_DISABLED=1 .venv/bin/python -m compileall -q daibu app.py
git diff --check
```

All commands must exit 0. Existing deselected external contract tests and the known Starlette/httpx warning must be reported, not hidden.

- [ ] **Step 8: Update HANDOFF and commit QA evidence**

Record exact test counts, interaction measurements, screenshot paths, schema migration evidence, formal-database write counts, and remaining limits.

Commit: `docs: record independent text layer QA`

- [ ] **Step 9: Merge, verify main, push, and restart the existing production service**

Preserve user-owned changes. Merge the feature branch into `main`, rerun the full suite on main, push `origin/main`, restart `io.daibu.content-brain`, and verify `http://127.0.0.1:8501`.

- [ ] **Step 10: Verify the production user flow without saving**

On the formal settings page:

- page 02 shows independently selectable `facts-bg`, `facts-label`, and `facts-body`;
- changing `facts-body` font size changes its computed font size;
- moving `facts-label` leaves background/body stationary;
- template version count is unchanged before/after QA;
- desktop/mobile console has 0 errors and 0 warnings;
- 375px has no horizontal overflow and no save button.

Save production screenshots under `.screenshots/`, update HANDOFF with exact measurements, commit, push, and verify remote SHA.
