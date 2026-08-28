# Six-Page Template Independent Text Layers v4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the six-page v57 template to schema v4 so every logical text role on pages 2–5 can be selected and styled independently while old schema-v3 versions remain immutable and readable.

**Architecture:** Add a versioned registry plus a pure v3→v4 normalizer, and make `parse_layout()` return one canonical v4 `LayoutDocument`. Split each composite Renderer node into sibling background, graphic, label, title, and body nodes so the editor overlay, live preview, validation, and PNG output all consume the same DOM and layout IDs.

**Tech Stack:** Python 3.12, frozen dataclasses, JSON layouts, SQLite, Streamlit custom component, vanilla browser JavaScript, pytest, Playwright/Chromium, Pillow/WeasyPrint rendering pipeline.

## Global Constraints

- Canvas remains exactly 1080×1350.
- Scope is pages 2–5 (`who`, `problem`, `how-ai`, `results`); cover and CTA keep their current structure and visual behavior.
- Every logical text role owns exactly one `data-layout-id`; editable content puts `data-edit-key` on that same DOM node.
- Background and graphic layers never expose `font_size` or `text_align`.
- v3 JSON is normalized in memory only; existing database rows and historical `layout_json` are never rewritten.
- Every new save creates an immutable schema-v4 template version; activation remains a separate explicit action.
- No database table migration, new package, external API, LLM call, paid service, grouping, multiselect, rotation, z-order, arbitrary element creation/deletion, font picker, or palette editor.
- Preserve the approved v57 hierarchy, pastel palette, LINE Seed typography, page geometry, and equal-sized page-5 background cards.
- TDD is vertical: one failing test, minimum implementation, passing focused test, refactor, then commit.
- Before declaring completion, run two screenshot QA rounds at 1280×800 and 375×812, then run the full suite before merge and again on `main`.

---

## File Map

- Create `daibu/cards/layout_migrations.py`: pure schema-v3 to schema-v4 mapping; no I/O and no database writes.
- Modify `daibu/cards/layout_registry.py`: retain the frozen v3 registry for parsing legacy rows and expose the new v4 registry as `ELEMENT_REGISTRY`.
- Modify `daibu/cards/layout_schema.py`: normalize supported input before validation and update page-5 equality validation to the three background layers.
- Modify `daibu/cards/layouts/sticky-notebook-v1.json`: replace the built-in v3 composite layout with the canonical v4 independent-layer layout.
- Modify `daibu/cards/render.py`: emit one formal DOM node per v4 layer and colocate layout/edit hooks.
- Modify `daibu/cards/templates/sticky-notebook-v1.css`: style split siblings without overriding layout-controlled geometry or text styles.
- Modify `daibu/cards/template_editor_payload.py`: derive descriptors and fingerprints from the document's schema registry and reject missing or duplicated hooks.
- Modify `daibu/cards/template_editor_component.py`: keep graphic properties geometry-only and verify sibling/background independence in the real component.
- Modify `daibu/cards/layout_validation.py`: inspect the expanded text layer set without treating background overlap as a collision.
- Modify `daibu/cards/layout_repository.py`: preserve raw historical rows on read and ensure newly saved canonical documents persist as schema v4.
- Modify `daibu/db.py`: seed only the canonical v4 built-in for fresh databases while preserving the existing unsupported-v1/v2 cleanup policy.
- Modify `tests/test_cards_layout_schema.py`: registry, canonical v4, equality, and v3 normalization tests.
- Create `tests/test_cards_layout_migrations.py`: pure normalization mapping and non-mutation tests.
- Create `tests/fixtures/layout-v3.json`: immutable copy of the current production v3 built-in used only as compatibility evidence.
- Modify `tests/test_cards_render.py`: per-page hook, direct text-style, escaping, and approved-structure tests.
- Modify `tests/test_cards_template_editor_payload.py`: descriptor, duplicate-hook, and schema/fingerprint tests.
- Modify `tests/test_template_editor_browser.py`: real selection, font-size, sibling independence, background behavior, save/reopen, mobile, and PNG-consistency flows.
- Modify `tests/test_cards_layout_validation.py`: independent text overflow and collision-policy coverage.
- Modify `tests/test_cards_layout_repository.py`: immutable v3 row / new v4 row contract.
- Modify `tests/test_db_migration.py`: fresh seed v4 and legacy v3 preservation.
- Modify `HANDOFF.md`: product teaching checkpoint, test evidence, backup/version evidence, screenshots, push, and service verification.
- Modify `.gitignore`: ensure `.screenshots/` is ignored if not already present.

---

### Task 1: Establish the schema-v4 registry and canonical built-in layout

**Files:**
- Modify: `daibu/cards/layout_registry.py`
- Modify: `daibu/cards/layout_schema.py`
- Modify: `daibu/cards/layouts/sticky-notebook-v1.json`
- Modify: `tests/test_cards_layout_schema.py`

**Interfaces:**
- Consumes: existing `ElementRule`, `LayoutDocument`, `parse_layout()`, and the v57 v3 geometry.
- Produces: `SCHEMA_V3_REGISTRY`, `ELEMENT_REGISTRY` (v4), `registry_for_schema(schema_version: int)`, and a built-in `LayoutDocument.schema_version == 4` used by every later task.

- [ ] **Step 1: Write the failing canonical-v4 registry test**

Replace the v3 expectation and add representative type assertions in `tests/test_cards_layout_schema.py`:

```python
def test_builtin_layout_is_six_page_schema_v4_with_independent_layers():
    document = load_builtin_layout()

    assert document.schema_version == 4
    assert tuple(document.pages) == carousel_pages.PAGE_TYPES
    assert set(document.pages["results"].elements) >= {
        "audience-bg", "audience-label", "audience-text",
        "before-bg", "before-tag", "before-title", "before-text",
        "intervention-bg", "intervention-arrow", "intervention-title", "intervention-text",
        "after-bg", "after-tag", "after-title", "after-text",
        "core-difference-bg", "core-difference-label", "core-difference-text",
        "value-bg", "value-label", "value-text",
    }
    assert document.pages["results"].elements["before-bg"].text_style is None
    assert document.pages["results"].elements["before-title"].text_style is not None
```

- [ ] **Step 2: Run the focused test and verify Red**

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_layout_schema.py::test_builtin_layout_is_six_page_schema_v4_with_independent_layers
```

Expected: FAIL because the built-in document reports schema 3 and has only `before`, `intervention`, and `after` composites.

- [ ] **Step 3: Add the exact v4 registry inventory**

In `daibu/cards/layout_registry.py`, rename the current map to `SCHEMA_V3_REGISTRY`, define `ELEMENT_REGISTRY` with the following IDs, and make `registry_for_schema()` return the matching immutable map:

```python
V4_ELEMENT_IDS = {
    "cover": (
        "company-logo", "company-name", "heading", "positioning", "mascot",
    ),
    "who": (
        "page-label", "heading", "logo",
        "identity-product", "identity-arrow-1", "identity-user",
        "identity-arrow-2", "identity-value",
        "positioning-bg", "positioning-label", "positioning-text",
        "facts-bg", "facts-label", "facts-text",
        "reason-bg", "reason-label", "reason-text", "mascot",
    ),
    "problem": (
        "page-label", "heading", "question-mark",
        "current-bg", "current-label", "current-text",
        "opportunity-bg", "opportunity-label", "opportunity-text", "spine",
        "stage-1-bg", "stage-1-icon", "stage-1-index", "stage-1-title", "stage-1-text",
        "stage-2-bg", "stage-2-icon", "stage-2-index", "stage-2-title", "stage-2-text",
        "stage-3-bg", "stage-3-icon", "stage-3-index", "stage-3-title", "stage-3-text",
        "mascot",
    ),
    "how-ai": (
        "page-label", "heading", "flow-arrow-1", "flow-arrow-2",
        "step-1-bg", "step-1-tag", "step-1-title", "step-1-text",
        "step-2-bg", "step-2-tag", "step-2-title", "step-2-text",
        "step-3-bg", "step-3-tag", "step-3-title", "step-3-text",
        "traditional-bg", "traditional-label", "traditional-text",
        "ai-role-bg", "ai-role-label", "ai-role-text",
        "human-bg", "human-label", "human-text",
        "difference-bg", "difference-label", "difference-text", "mascot",
    ),
    "results": (
        "page-label", "heading",
        "audience-bg", "audience-label", "audience-text",
        "before-bg", "before-tag", "before-title", "before-text",
        "intervention-bg", "intervention-arrow", "intervention-title", "intervention-text",
        "after-bg", "after-tag", "after-title", "after-text",
        "core-difference-bg", "core-difference-label", "core-difference-text",
        "value-bg", "value-label", "value-text", "mascot",
    ),
    "cta": ("invitation", "mascot"),
}

def registry_for_schema(schema_version: int) -> Mapping[str, Mapping[str, ElementRule]]:
    if schema_version == 3:
        return SCHEMA_V3_REGISTRY
    if schema_version == 4:
        return ELEMENT_REGISTRY
    raise ValueError(f"不支援的 schema_version：{schema_version}")
```

Register `*-bg`, icons, arrows, question mark, spine, Logo, and mascot as `text=False`; give background shapes `collision="background"`. Register fixed typography (`page-label`, tags, indices, identity labels) and editable labels/titles/body as `text=True`. Use labels exactly in the `區塊｜角色` form from the approved spec, e.g. `ElementRule("使用前｜標題", True)`.

- [ ] **Step 4: Replace the built-in JSON with a complete v4 layout**

Use the current composite rectangle unchanged for every new `*-bg`. Place child layers inside that rectangle using these exact insets, which preserve the current CSS proportions and give each text a non-overlapping box:

```python
SECTION_SPLIT = {
    "label": {"left": 26, "top": 22, "right": 26, "height": 30, "font_size": 18},
    "text": {"left": 26, "top": 66, "right": 26, "bottom": 22, "font_size": 22},
}
NODE_SPLIT = {
    "tag": {"left": 22, "top": 24, "right": 22, "height": 28, "font_size": 18},
    "title": {"left": 22, "top": 82, "right": 22, "height": 44, "font_size": 26},
    "text": {"left": 22, "top": 142, "right": 22, "bottom": 24, "font_size": 22},
}
```

For the short page-5 cards (245×356), use tag y offsets 52, title 142, text 214 relative to the background; use heights 30, 48, and 74. For page-4 step cards (251×302), use tag y offsets 40, title 122, text 184 and heights 32, 42, and 68. Keep all three page-5 backgrounds at 245×356 and all three page-4 step backgrounds at 251×302. Carry existing cover/CTA entries byte-for-byte except `schema_version: 4`.

- [ ] **Step 5: Validate v4 and update equality rules**

In `parse_layout()`, accept schema 4 and change page-5 equality validation to:

```python
result_cards = tuple(
    parsed_pages["results"].elements[element_id].rect
    for element_id in ("before-bg", "intervention-bg", "after-bg")
)
```

Keep the equality tolerance at one canvas pixel and report `intervention-bg` on failure.

- [ ] **Step 6: Run the schema file and verify Green**

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_layout_schema.py
```

Expected: PASS; update old assertions that intentionally named v3 composites to their v4 equivalents, without weakening unknown-property, bounds, or font-size validation.

- [ ] **Step 7: Commit the schema contract**

```bash
git add daibu/cards/layout_registry.py daibu/cards/layout_schema.py daibu/cards/layouts/sticky-notebook-v1.json tests/test_cards_layout_schema.py
git commit -m "feat: define template layout schema v4"
```

---

### Task 2: Normalize schema v3 in memory without mutating history

**Files:**
- Create: `daibu/cards/layout_migrations.py`
- Modify: `daibu/cards/layout_schema.py`
- Create: `tests/test_cards_layout_migrations.py`

**Interfaces:**
- Consumes: raw schema-v3 mapping and `SCHEMA_V3_REGISTRY`.
- Produces: `normalize_layout_mapping(value: Mapping[str, object]) -> dict[str, object]`, returning a new schema-v4 mapping without modifying `value`.

- [ ] **Step 1: Write the failing non-mutation and mapping test**

```python
from pathlib import Path
import copy
import json

from daibu.cards.layout_migrations import normalize_layout_mapping
from daibu.cards.layout_schema import parse_layout


def test_v3_results_card_normalizes_to_independent_v4_layers_without_mutating_input():
    raw = json.loads(Path("tests/fixtures/layout-v3.json").read_text())
    original = copy.deepcopy(raw)

    normalized = normalize_layout_mapping(raw)

    assert raw == original
    assert normalized["schema_version"] == 4
    result = normalized["pages"]["results"]["elements"]
    assert result["before-bg"] == {
        key: raw["pages"]["results"]["elements"]["before"][key]
        for key in ("x", "y", "w", "h")
    }
    assert result["before-title"]["font_size"] != result["before-text"]["font_size"]
    assert parse_layout(raw).schema_version == 4
```

Create `tests/fixtures/layout-v3.json` by copying the committed pre-v4 built-in from `git show cfd48d2:daibu/cards/layouts/sticky-notebook-v1.json`; the fixture is immutable compatibility evidence, not production data.

- [ ] **Step 2: Run the focused test and verify Red**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_layout_migrations.py::test_v3_results_card_normalizes_to_independent_v4_layers_without_mutating_input
```

Expected: FAIL because `layout_migrations` does not exist.

- [ ] **Step 3: Implement a pure normalizer**

Create `daibu/cards/layout_migrations.py` with these public and internal interfaces:

```python
from copy import deepcopy
from typing import Mapping


def _rect(raw: Mapping[str, object]) -> dict[str, object]:
    return {key: raw[key] for key in ("x", "y", "w", "h")}


def _child(
    parent: Mapping[str, object], *, left: float, top: float,
    right: float, height: float | None = None, bottom: float | None = None,
    font_size: float | None = None, text_align: str = "left",
) -> dict[str, object]:
    result = {
        "x": float(parent["x"]) + left,
        "y": float(parent["y"]) + top,
        "w": float(parent["w"]) - left - right,
        "h": height if height is not None else float(parent["h"]) - top - float(bottom),
    }
    if font_size is not None:
        result.update(font_size=font_size, text_align=text_align)
    return result


def normalize_layout_mapping(value: Mapping[str, object]) -> dict[str, object]:
    version = value.get("schema_version")
    if version == 4:
        return deepcopy(dict(value))
    if version != 3:
        raise ValueError(f"不支援的 schema_version：{version}")
    result = deepcopy(dict(value))
    result["schema_version"] = 4
    result["pages"] = _upgrade_pages_v3_to_v4(result["pages"])
    return result
```

Implement `_upgrade_pages_v3_to_v4()` with explicit page functions `_upgrade_who`, `_upgrade_problem`, `_upgrade_how_ai`, and `_upgrade_results`. Each function copies heading/Logo/mascot/spine geometry, maps old composite geometry to `*-bg`, and creates every child listed in `V4_ELEMENT_IDS`. Cover's optional legacy heading compatibility default must be applied before normalization or explicitly copied into the v4 result.

- [ ] **Step 4: Route parsing through normalization**

At the start of `parse_layout()`:

```python
try:
    normalized = normalize_layout_mapping(value)
except ValueError as error:
    raise LayoutValidationError(None, "不支援的 schema_version") from error
value = normalized
```

Then validate only against the canonical v4 registry. `layout_to_mapping(parse_layout(v3_raw))` must serialize v4, while the caller's original `v3_raw` remains unchanged.

- [ ] **Step 5: Run migration and schema tests and verify Green**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_layout_migrations.py tests/test_cards_layout_schema.py
```

Expected: PASS, including all four page mappings, v4 idempotence, unknown schema rejection, and input non-mutation.

- [ ] **Step 6: Commit the compatibility layer**

```bash
git add daibu/cards/layout_migrations.py daibu/cards/layout_schema.py tests/fixtures/layout-v3.json tests/test_cards_layout_migrations.py tests/test_cards_layout_schema.py
git commit -m "feat: normalize legacy template layouts to v4"
```

---

### Task 3: Split page 2 and page 3 Renderer layers

**Files:**
- Modify: `daibu/cards/render.py`
- Modify: `daibu/cards/templates/sticky-notebook-v1.css`
- Modify: `tests/test_cards_render.py`

**Interfaces:**
- Consumes: canonical v4 layout IDs from Tasks 1–2.
- Produces: `_background_box()`, `_text_box()`, and Renderer DOM for `who` and `problem` where each layout ID occurs once.

- [ ] **Step 1: Write the failing page-2 colocated-hook test**

```python
def test_who_text_roles_are_independent_layout_nodes(tmp_path):
    markup = _markup(_render(tmp_path, 1))

    assert 'data-layout-id="positioning-bg"' in markup
    assert (
        'data-layout-id="positioning-text" '
        'data-edit-key="page.who.section.0.text"' in markup
    )
    assert 'data-layout-id="positioning-label"' in markup
    assert markup.count('data-layout-id="positioning-text"') == 1
    assert 'data-layout-id="positioning"' not in markup
```

- [ ] **Step 2: Run it and verify Red**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_render.py::test_who_text_roles_are_independent_layout_nodes
```

Expected: FAIL because `positioning` is still a composite section.

- [ ] **Step 3: Add explicit sibling helpers and split page 2**

Add helpers in `render.py`:

```python
def _background_box(element_id: str, classes: str) -> str:
    return _layout_box(element_id, "", classes=classes)


def _text_box(
    element_id: str, value: str, *, classes: str,
    edit_key: str | None = None, tag: str = "div",
) -> str:
    return _layout_box(
        element_id,
        html.escape(value),
        tag=tag,
        classes=classes,
        edit_key=edit_key,
    )
```

Rewrite page 2 so background, label, and content are siblings. Use direct `edit_key=` only on `positioning-text`, `facts-text`, and `reason-text`. Emit identity labels/arrows and `page-label` with their registered IDs. Remove nested `b`/`span` ownership from these sections.

- [ ] **Step 4: Run the page-2 test and verify Green**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_render.py::test_who_text_roles_are_independent_layout_nodes
```

Expected: PASS.

- [ ] **Step 5: Write the failing page-3 node test**

```python
def test_problem_node_title_body_icon_and_background_are_independent(tmp_path):
    markup = _markup(_render(tmp_path, 2))

    for element_id in (
        "stage-1-bg", "stage-1-icon", "stage-1-index",
        "stage-1-title", "stage-1-text",
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    assert (
        'data-layout-id="stage-1-title" '
        'data-edit-key="page.problem.diagram.0.title"' in markup
    )
    assert (
        'data-layout-id="stage-1-text" '
        'data-edit-key="page.problem.diagram.0.text"' in markup
    )
```

- [ ] **Step 6: Run it, verify Red, then split page 3 minimally**

Run the single test and expect missing `stage-1-bg`. Replace `_node_card()` use for `problem` with `_problem_node_layers(page, index) -> str`, emitting `stage-N-bg`, SVG `stage-N-icon`, fixed `stage-N-index`, and direct title/text nodes. Split `current` and `opportunity` into background/label/text siblings; register `page-label` and `question-mark` in the DOM.

- [ ] **Step 7: Remove CSS text overrides and run page 2–3 tests**

Move visual card styles to `*-bg` classes. Text classes may set weight, color, line-height, overflow wrapping, and pointer behavior, but remove fixed `font-size` and relative `em` declarations from the actual layout text nodes. Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_render.py::test_who_text_roles_are_independent_layout_nodes \
  tests/test_cards_render.py::test_problem_node_title_body_icon_and_background_are_independent \
  tests/test_cards_render.py::test_renderer_escapes_unsafe_text_on_all_pages
```

Expected: 3 passed.

- [ ] **Step 8: Commit pages 2–3**

```bash
git add daibu/cards/render.py daibu/cards/templates/sticky-notebook-v1.css tests/test_cards_render.py
git commit -m "feat: split who and problem template layers"
```

---

### Task 4: Split page 4 Renderer layers

**Files:**
- Modify: `daibu/cards/render.py`
- Modify: `daibu/cards/templates/sticky-notebook-v1.css`
- Modify: `tests/test_cards_render.py`

**Interfaces:**
- Consumes: `_background_box()` and `_text_box()` from Task 3.
- Produces: `_how_ai_node_layers(page: CarouselPage, index: int) -> str` and independent context-card layers.

- [ ] **Step 1: Write the failing step-layer test**

```python
def test_how_ai_step_roles_and_context_roles_are_independent(tmp_path):
    markup = _markup(_render(tmp_path, 3))

    for element_id in (
        "step-1-bg", "step-1-tag", "step-1-title", "step-1-text",
        "traditional-bg", "traditional-label", "traditional-text",
        "flow-arrow-1", "flow-arrow-2",
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    assert (
        'data-layout-id="step-1-title" '
        'data-edit-key="page.how-ai.diagram.0.title"' in markup
    )
    assert (
        'data-layout-id="traditional-text" '
        'data-edit-key="page.how-ai.section.0.text"' in markup
    )
```

- [ ] **Step 2: Run the focused test and verify Red**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_render.py::test_how_ai_step_roles_and_context_roles_are_independent
```

Expected: FAIL because the old DOM still exposes `step-1` and `traditional` composites.

- [ ] **Step 3: Implement the page-4 split**

Emit each step background, fixed tag (`IN`, `AI`, `OUT`), editable title, editable body, and the two registered arrow graphics as siblings. Emit each context background, fixed label, and editable body as siblings. Preserve hidden expression hooks for the internal diagram expressions so `editable_values()` still finds every key exactly once.

The title and body nodes must use this direct pattern:

```python
_text_box(
    f"step-{index + 1}-title",
    node.title,
    classes="step-title",
    edit_key=f"page.how-ai.diagram.{index}.title",
    tag="b",
)
```

- [ ] **Step 4: Adjust page-4 CSS and verify Green**

Move background fill/shadow/fold styles to `.step-bg` and `.context-note-bg`; style text siblings using registered geometry. Keep colors, weights, and line-height, but remove `.step b { font-size: ... }`, `.step span { font-size: ... }`, and corresponding context descendants.

Run:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_render.py::test_how_ai_step_roles_and_context_roles_are_independent \
  tests/test_cards_render.py::test_renderer_exposes_every_editable_value_once \
  tests/test_cards_render.py::test_renderer_escapes_unsafe_text_on_all_pages
```

Expected: 3 passed.

- [ ] **Step 5: Commit page 4**

```bash
git add daibu/cards/render.py daibu/cards/templates/sticky-notebook-v1.css tests/test_cards_render.py
git commit -m "feat: split how-ai template layers"
```

---

### Task 5: Split page 5 Renderer layers and preserve equal card geometry

**Files:**
- Modify: `daibu/cards/render.py`
- Modify: `daibu/cards/templates/sticky-notebook-v1.css`
- Modify: `tests/test_cards_render.py`
- Modify: `tests/test_cards_layout_schema.py`

**Interfaces:**
- Consumes: sibling-layer helpers and v4 page-5 layout.
- Produces: `_result_node_layers(page: CarouselPage, index: int) -> str`, with independent BEFORE/arrow/AFTER tags, titles, and bodies.

- [ ] **Step 1: Write the failing independent-font-target test**

```python
def test_results_text_roles_are_direct_layout_and_edit_nodes(tmp_path):
    markup = _markup(_render(tmp_path, 4))

    for element_id in (
        "before-bg", "before-tag", "before-title", "before-text",
        "intervention-bg", "intervention-arrow", "intervention-title", "intervention-text",
        "after-bg", "after-tag", "after-title", "after-text",
    ):
        assert markup.count(f'data-layout-id="{element_id}"') == 1
    assert (
        'data-layout-id="before-title" '
        'data-edit-key="page.results.diagram.0.title"' in markup
    )
    assert (
        'data-layout-id="before-text" '
        'data-edit-key="page.results.diagram.0.text"' in markup
    )
    assert 'data-layout-id="before"' not in markup
```

- [ ] **Step 2: Run it and verify Red**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_render.py::test_results_text_roles_are_direct_layout_and_edit_nodes
```

Expected: FAIL because the current Renderer emits one `before` section.

- [ ] **Step 3: Implement the page-5 split**

Create `_result_node_layers()` that emits:

```python
tag_ids = ("before-tag", "intervention-arrow", "after-tag")
tag_values = ("BEFORE", "→", "AFTER")
prefixes = ("before", "intervention", "after")
```

For each index emit `prefix-bg`, fixed tag/arrow, editable `prefix-title`, editable `prefix-text`, and the existing hidden expression edit hook. Split audience, core difference, and value into `*-bg`, `*-label`, and `*-text` siblings.

- [ ] **Step 4: Move page-5 appearance to backgrounds and verify direct styles**

Replace nested `.result-card i/b/span` sizing with classes on the direct sibling nodes. Keep each background's fill, shadow, and folded corner. Ensure Renderer layout CSS remains the only source of `font-size` and `text-align` for registered text layers.

Add this assertion:

```python
def test_results_layout_css_targets_title_and_body_independently(tmp_path):
    layout = replace_element(load_builtin_layout(), "results", "before-title", font_size=41)
    layout = replace_element(layout, "results", "before-text", font_size=23)
    output = render.page_html(
        carousel_draft().pages[4], "ElevenLabs",
        brand_asset(_logo(tmp_path)), layout,
    )
    assert '[data-layout-id="before-title"]{position:absolute!important' in output
    assert "font-size:41px" in output
    assert '[data-layout-id="before-text"]{position:absolute!important' in output
    assert "font-size:23px" in output
```

- [ ] **Step 5: Run page-5 and all Renderer tests**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_render.py tests/test_cards_layout_schema.py
```

Expected: PASS. The schema equality test must compare `before-bg`, `intervention-bg`, and `after-bg`, not text boxes.

- [ ] **Step 6: Commit page 5**

```bash
git add daibu/cards/render.py daibu/cards/templates/sticky-notebook-v1.css tests/test_cards_render.py tests/test_cards_layout_schema.py
git commit -m "feat: split results template layers"
```

---

### Task 6: Make the editor and validator understand independent layers

**Files:**
- Modify: `daibu/cards/template_editor_payload.py`
- Modify: `daibu/cards/template_editor_component.py`
- Modify: `daibu/cards/layout_validation.py`
- Modify: `tests/test_cards_template_editor_payload.py`
- Modify: `tests/test_cards_layout_validation.py`
- Modify: `tests/test_template_editor_browser.py`

**Interfaces:**
- Consumes: canonical v4 `LayoutDocument` and per-schema registry.
- Produces: duplicate-aware `preview_layout_id_counts(preview_html: str) -> Mapping[str, int]`, schema-specific payload descriptors, and browser behavior where graphic selection is geometry-only.

- [ ] **Step 1: Write the failing payload type and duplicate-hook tests**

```python
def test_results_payload_separates_background_and_title_properties():
    layout = load_builtin_layout()
    version = SimpleNamespace(id=11, version_no=1, created_at="now", layout=layout)
    preview = "".join(
        f'<span data-layout-id="{element_id}"></span>'
        for element_id in layout.pages["results"].elements
    )
    payload = template_editor_payload(
        SimpleNamespace(id=7, name="AI 新創介紹"),
        [version], version, "results", preview,
    )
    by_id = {item["elementId"]: item for item in payload["elements"]}
    assert by_id["before-bg"]["editableProperties"] == ["x", "y", "w", "h"]
    assert by_id["before-title"]["editableProperties"] == [
        "x", "y", "w", "h", "font_size", "text_align",
    ]


def test_template_payload_rejects_duplicate_renderer_layout_hook():
    layout = load_builtin_layout()
    version = SimpleNamespace(id=11, version_no=1, created_at="now", layout=layout)
    preview = "".join(
        f'<span data-layout-id="{element_id}"></span>'
        for element_id in layout.pages["results"].elements
    ) + '<span data-layout-id="before-title"></span>'
    payload = template_editor_payload(
        SimpleNamespace(id=7, name="AI 新創介紹"),
        [version], version, "results", preview,
    )
    assert "重複版面元素：before-title" in payload["previewSyncError"]
```

- [ ] **Step 2: Run payload tests and verify Red**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_template_editor_payload.py::test_results_payload_separates_background_and_title_properties \
  tests/test_cards_template_editor_payload.py::test_template_payload_rejects_duplicate_renderer_layout_hook
```

Expected: first test fails on missing v4 descriptors or fixture helper; second fails because only missing IDs are checked.

- [ ] **Step 3: Make payload registry selection and hook checks canonical**

Use `registry_for_schema(selected_version.layout.schema_version)` instead of importing a single assumed registry. Replace the set-only check with counts:

```python
def preview_layout_id_counts(preview_html: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for element_id in _LAYOUT_ID.findall(preview_html):
        counts[element_id] = counts.get(element_id, 0) + 1
    return counts
```

Build `previewSyncError` from missing IDs first, then IDs whose count is greater than one. Include schema version and sorted `(element_id, text, collision)` values in `_registry_fingerprint()` so a v3 working copy cannot survive the v4 upgrade.

- [ ] **Step 4: Write and run the browser background-vs-text test**

```python
def test_results_background_has_no_font_control_but_title_changes_only_itself(tmp_path):
    with running_streamlit(tmp_path, _seed) as base_url:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(f"{base_url}/設定", wait_until="networkidle")
            editor = page.locator('[data-role="template-editor"]')
            editor.get_by_role("button", name="05 使用成果").click()
            background = editor.locator('.template-document [data-layout-id="before-bg"]')
            background.click(position={"x": 10, "y": 10})
            expect(editor.locator('[data-role="property-panel"] input[name="font_size"]')).to_have_count(0)
            title = editor.locator('.template-document [data-layout-id="before-title"]')
            body = editor.locator('.template-document [data-layout-id="before-text"]')
            body_size = body.evaluate("el => getComputedStyle(el).fontSize")
            title.click(position={"x": 10, "y": 10})
            font = editor.locator('[data-role="property-panel"] input[name="font_size"]')
            font.fill("41")
            font.press("Tab")
            expect(title).to_have_css("font-size", "41px")
            assert body.evaluate("el => getComputedStyle(el).fontSize") == body_size
            browser.close()
```

Run it and expect Red before component/payload completion. Make the minimum JavaScript changes needed so descriptors alone control the property fields; do not add page-specific conditionals.

- [ ] **Step 5: Add movement, undo, Escape, and collision assertions**

Extend the same browser file with independent tests that:

- drag `before-bg` and assert `before-title` bounding-box x/y do not change;
- move `before-title`, press undo, redo, and Escape during a drag, asserting only that layer changes;
- verify a background selection reports no collision warning against its own text;
- verify text overflow still blocks the save trigger.
- seed `sessionStorage["daibu-template-1-1"]` with `schemaIdentity: "3:legacy"` and a composite `before` working copy, reload, and assert the stale state is ignored: the page renders `before-bg`, the Save button is disabled, and no `before` selection survives.

Each test must run independently through the real component, not call internal JavaScript helpers.

- [ ] **Step 6: Run editor/payload/validation tests and verify Green**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_template_editor_payload.py \
  tests/test_cards_layout_validation.py \
  tests/test_template_editor_browser.py
```

Expected: PASS, with graphic geometry-only controls, independent text computed styles, background collision exclusion, undo/redo/Escape preservation, and no mobile behavior regression.

- [ ] **Step 7: Commit editor behavior**

```bash
git add daibu/cards/template_editor_payload.py daibu/cards/template_editor_component.py daibu/cards/layout_validation.py tests/test_cards_template_editor_payload.py tests/test_cards_layout_validation.py tests/test_template_editor_browser.py
git commit -m "feat: edit template text layers independently"
```

---

### Task 7: Preserve version immutability and persist only schema v4

**Files:**
- Modify: `daibu/cards/layout_repository.py`
- Modify: `daibu/db.py`
- Modify: `tests/test_cards_layout_repository.py`
- Modify: `tests/test_db_migration.py`
- Modify: `tests/test_template_editor_browser.py`

**Interfaces:**
- Consumes: `parse_layout(v3) -> canonical v4 LayoutDocument` and existing `create_version()` transaction.
- Produces: v4 rows for every new save while historical v3 row bytes and draft bindings remain unchanged.

- [ ] **Step 1: Write the failing immutable-row repository test**

```python
def test_reading_v3_then_saving_creates_v4_without_rewriting_history(tmp_path):
    conn = db.connect(str(tmp_path / "legacy-v3.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "舊版系列", 4, [], 5),
    )
    legacy_json = Path("tests/fixtures/layout-v3.json").read_text()
    with conn:
        cursor = conn.execute(
            "INSERT INTO carousel_template_versions "
            "(theme_id, version_no, schema_version, layout_json) "
            "VALUES (?, 1, 3, ?)",
            (theme_id, legacy_json),
        )
    legacy_id = int(cursor.lastrowid)
    before = conn.execute(
        "SELECT schema_version, layout_json FROM carousel_template_versions WHERE id = ?",
        (legacy_id,),
    ).fetchone()

    loaded = layout_repository.get_version(conn, legacy_id)
    created = layout_repository.create_version(conn, theme_id, loaded.layout)

    after = conn.execute(
        "SELECT schema_version, layout_json FROM carousel_template_versions WHERE id = ?",
        (legacy_id,),
    ).fetchone()
    new_row = conn.execute(
        "SELECT schema_version, layout_json FROM carousel_template_versions WHERE id = ?",
        (created.id,),
    ).fetchone()
    assert dict(after) == dict(before)
    assert new_row["schema_version"] == 4
    assert json.loads(new_row["layout_json"])["schema_version"] == 4
```

- [ ] **Step 2: Run it and verify Red**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q tests/test_cards_layout_repository.py::test_reading_v3_then_saving_creates_v4_without_rewriting_history
```

Expected: FAIL until fixtures/helpers and canonical v4 persistence are wired.

- [ ] **Step 3: Make persistence explicitly canonical**

Keep `_row_to_version()` read-only. In `create_version()`, assert the normalized layout is v4 before insertion:

```python
canonical = parse_layout(layout_to_mapping(layout))
if canonical.schema_version != 4:
    raise ValueError("新模板版本必須使用 schema v4")
canonical_json = _canonical_layout_json(canonical)
```

Insert `canonical.schema_version`, not the caller's raw version. Update fresh database seeding in `db.py` to use `load_builtin_layout()` and schema 4. Do not add SQL that updates existing schema-v3 rows.

- [ ] **Step 4: Write the browser save/reopen contract**

Rename the old `test_template_save_persists_schema_v3_as_an_inactive_version` and assert:

```python
assert row["schema_version"] == 4
assert json.loads(row["layout_json"])["schema_version"] == 4
assert active_version_id == original_version_id
assert draft_template_version_id == original_draft_version_id
```

After saving, select the new version in the version dropdown and verify the changed `before-title` font size reappears. Do not activate it in this test.

- [ ] **Step 5: Run repository, migration, and browser-save tests**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_layout_repository.py \
  tests/test_db_migration.py \
  tests/test_template_editor_browser.py -k 'save or schema or version or legacy'
```

Expected: PASS. Existing tests that intentionally remove unsupported schema v1/v2 remain unchanged; schema v3 is now supported through in-memory normalization, not destructive migration.

- [ ] **Step 6: Commit version safety**

```bash
git add daibu/cards/layout_repository.py daibu/db.py tests/test_cards_layout_repository.py tests/test_db_migration.py tests/test_template_editor_browser.py
git commit -m "feat: persist independent layouts as immutable v4 versions"
```

---

### Task 8: Run product checkpoint, visual QA, full verification, and formal rollout

**Files:**
- Modify: `.gitignore`
- Modify: `HANDOFF.md`
- Create locally/ignored: `.screenshots/template-text-layers-v4-round1-desktop.png`
- Create locally/ignored: `.screenshots/template-text-layers-v4-round1-mobile.png`
- Create locally/ignored: `.screenshots/template-text-layers-v4-final-desktop.png`
- Create locally/ignored: `.screenshots/template-text-layers-v4-final-mobile.png`

**Interfaces:**
- Consumes: all v4 implementation commits.
- Produces: user-visible verification evidence, safe database rollout, synced `main`, and a healthy existing local service.

- [ ] **Step 1: Deliver the product understanding checkpoint before full tests**

Record in `HANDOFF.md` and report to the user:

- Product capability: every page-2–5 text role is independently selectable.
- User experience: background selection is geometry-only; text selection owns font/alignment.
- Technical structure: v3 raw row → pure in-memory v4 normalization → one Renderer DOM → editor/PNG.
- Data flow: working copy → Chromium validation → immutable v4 row → optional activation/draft upgrade.
- Design reason and backup: schema v4 selected over editor-only overlay and page-specific exceptions.
- Safety/cost: no table migration, dependency, API, LLM, or paid call.
- Current focused-test evidence and known remaining limitations.

Do not ask for approval unless a new product-visible decision surfaced; otherwise continue through verification.

- [ ] **Step 2: Run focused template and rendering suites**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q \
  tests/test_cards_layout_schema.py \
  tests/test_cards_layout_migrations.py \
  tests/test_cards_render.py \
  tests/test_cards_template_editor_payload.py \
  tests/test_cards_layout_validation.py \
  tests/test_cards_layout_repository.py \
  tests/test_template_editor_browser.py \
  tests/test_db_migration.py
```

Expected: all selected tests pass with no unexpected warning or deselection.

- [ ] **Step 3: Start an isolated service and perform screenshot QA round 1**

Use a copied SQLite database and a non-production port. With the `playwright-cli` skill:

```bash
playwright-cli open http://127.0.0.1:8768/設定
playwright-cli resize 1280 800
playwright-cli screenshot --filename=.screenshots/template-text-layers-v4-round1-desktop.png
playwright-cli resize 375 812
playwright-cli screenshot --filename=.screenshots/template-text-layers-v4-round1-mobile.png
```

The desktop screenshot must show page 5 with `使用前｜標題` selected and a visible font-size field. The mobile screenshot must show the read-only notice. Inspect only these new images and explicitly grade hierarchy, whitespace, font distinction, maximum-three main colors, alignment, 375px overflow, hover/focus/save/error states, and micro-motion. List every failed item before making fixes.

- [ ] **Step 4: Add one failing regression test per round-1 defect, fix, and rerun focused tests**

For every reproducible defect, first add one narrow browser, Renderer, or validation test; run that test to see Red; make the minimum change; rerun it to Green. Do not change assertions merely to match the broken display.

- [ ] **Step 5: Perform screenshot QA round 2**

Repeat exactly one desktop and one mobile screenshot:

```bash
playwright-cli resize 1280 800
playwright-cli screenshot --filename=.screenshots/template-text-layers-v4-final-desktop.png
playwright-cli resize 375 812
playwright-cli screenshot --filename=.screenshots/template-text-layers-v4-final-mobile.png
```

Require all eight visual checklist categories to pass, mobile `scrollWidth - clientWidth == 0`, no Streamlit exception, and no critical console/server error. Do not reread round-1 images.

- [ ] **Step 6: Verify preview and PNG use the same saved values**

In an isolated database, change `before-title` to 41px and `before-text` to 23px, save v4, reopen it, and export the page-5 1080×1350 PNG. Use the existing Renderer/browser inspection utilities to assert the preview computed styles are 41px and 23px and the generated HTML passed to PNG contains the same layout declarations. Also render all six pages and run `layout_validation.inspect_pages()` with zero issues.

- [ ] **Step 7: Run the complete suite once on the feature branch**

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q
```

Expected: all non-contract tests pass; only the repository's documented external-service deselections and known Starlette/httpx deprecation warning may remain. Record exact counts and elapsed time in `HANDOFF.md`.

- [ ] **Step 8: Create a recoverable production database backup and measure known state**

Before writing template data, identify the actual SQLite path used by `io.daibu.content-brain`, copy it into `.backups/` with a timestamp, and record:

- `PRAGMA integrity_check`
- `PRAGMA foreign_key_check`
- counts for themes, ideas, carousel drafts/pages/sources, template versions
- current active template version ID and current SUN draft template version ID

Calibrate the queries against the known selected rows before using their counts as evidence. Never infer that an empty query proves absence.

- [ ] **Step 9: Create and activate the canonical v4 production version safely**

Use the repository/service APIs rather than handwritten SQL to create the v4 version. Validate the real SUN draft against it before activation. Activate the new version for future drafts; upgrade the existing SUN draft only after its six rendered pages pass `layout_validation.inspect_pages()` and the content/source/Logo fields compare byte-for-byte before and after. If any validation differs unexpectedly, stop and restore the previous active/draft bindings; do not delete the new immutable version.

- [ ] **Step 10: Update handoff, ignore screenshots, and commit**

Ensure `.gitignore` contains:

```gitignore
.screenshots/
```

Add the final screenshot paths, exact tests, backup path, version IDs, integrity checks, limitations, and user-visible result to `HANDOFF.md`, then commit:

```bash
git add .gitignore HANDOFF.md
git commit -m "docs: record template text layer rollout"
```

- [ ] **Step 11: Merge to `main`, rerun the full suite, and push**

Follow `finishing-a-development-branch` and `verification-before-completion`. Fast-forward or merge without overwriting unrelated user changes. On `main`, rerun:

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/pytest -q
```

Only after Green:

```bash
git push origin main
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

Require local and remote SHA to match.

- [ ] **Step 12: Restart the existing service and verify from the user's view**

Restart the existing `io.daibu.content-brain` LaunchAgent without creating a second service or URL. Verify `http://127.0.0.1:8501/_stcore/health`, open `/設定`, select page 5, and exercise the core flow: select background (no font control), select title (font control), change without saving, undo, then reopen/reset so formal data is not accidentally changed. Confirm no new server traceback, no critical console error, no horizontal overflow, and the service still listens only on `127.0.0.1:8501`.

---

## Final Acceptance Checklist

- [ ] Pages 2–5 expose every registered v4 layer exactly once in formal Renderer DOM.
- [ ] Every editable title/body places `data-layout-id` and `data-edit-key` on the same node.
- [ ] A text layer's font size and alignment do not alter sibling layers.
- [ ] A background exposes geometry only and moving it does not move text.
- [ ] Preview, reopened saved version, and PNG use identical layout values.
- [ ] v3 rows remain byte-identical after read/save; the new row is schema v4.
- [ ] Active version and existing draft bindings change only after real validation and backup.
- [ ] Page-5 background cards remain equal-sized; pages 2–5 have no clipping or invalid collisions.
- [ ] Mobile remains read-only with zero horizontal overflow.
- [ ] Two visual QA rounds, focused tests, feature-branch full suite, `main` full suite, remote SHA, service health, console, and core production flow are recorded in `HANDOFF.md`.
