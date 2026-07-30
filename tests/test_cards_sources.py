import pytest

from daibu.cards import sources
from tests.card_fixtures import verified_sources


def test_new_sources_take_the_smallest_free_number():
    pack = verified_sources()
    assert sources.next_source_id(()) == "S1"
    assert sources.next_source_id(pack) == "S4"

    without_middle = sources.remove(pack, "S2")

    assert [item.source_id for item in without_middle] == ["S1", "S3"]
    assert sources.next_source_id(without_middle) == "S2"


def test_pack_rejects_incomplete_rows_and_caps_at_eight():
    pack = verified_sources()

    with pytest.raises(ValueError, match="出版方"):
        sources.add(
            pack,
            "  ",
            "2026-07-20",
            "https://a.example/x",
            "內容夠長",
        )
    with pytest.raises(ValueError, match="https"):
        sources.add(
            pack,
            "A",
            "2026-07-20",
            "http://a.example/x",
            "內容夠長",
        )
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        sources.add(
            pack,
            "A",
            "2026/07/20",
            "https://a.example/x",
            "內容夠長",
        )

    full = pack
    while len(full) < sources.MAX_SOURCES:
        full = sources.add(
            full,
            "A",
            "2026-07-20",
            f"https://a.example/{len(full)}",
            "這段引文足夠長，用來代表已查證的原文片段。",
        )

    assert len(full) == 8
    with pytest.raises(ValueError, match="最多 8 筆"):
        sources.add(
            full,
            "A",
            "2026-07-20",
            "https://a.example/9",
            "這段引文足夠長，用來代表已查證的原文片段。",
        )
