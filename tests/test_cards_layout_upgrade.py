from copy import deepcopy
import json
from pathlib import Path

from daibu.cards.layout_upgrade import normalize_layout_mapping


LAYOUT_PATH = (
    Path(__file__).parents[1]
    / "daibu"
    / "cards"
    / "layouts"
    / "editorial-v15-1.json"
)


def test_schema_v1_layout_normalizes_to_independent_schema_v2_layers():
    raw_v1 = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    before = deepcopy(raw_v1)

    normalized = normalize_layout_mapping(raw_v1)

    assert raw_v1 == before
    assert normalized["schema_version"] == 2
    who = normalized["pages"]["who"]["elements"]
    assert {"facts-bg", "facts-label", "facts-body"} <= set(who)
    assert "facts" not in who
