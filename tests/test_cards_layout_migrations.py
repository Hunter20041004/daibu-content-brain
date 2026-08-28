from pathlib import Path
import copy
import json

from daibu.cards.layout_migrations import normalize_layout_mapping
from daibu.cards.layout_schema import parse_layout


def _legacy_layout():
    return json.loads(
        Path("tests/fixtures/layout-v3.json").read_text(encoding="utf-8")
    )


def test_v3_results_card_normalizes_to_independent_v4_layers_without_mutating_input():
    raw = _legacy_layout()
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
