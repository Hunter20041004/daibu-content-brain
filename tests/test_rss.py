from pathlib import Path

import pytest

from daibu.fetch import rss


def test_fetch_parses_items(monkeypatch):
    raw = Path("tests/fixtures/sample_feed.xml").read_text()
    monkeypatch.setattr(rss, "_download", lambda url: raw)

    items = rss.fetch("http://example.com/feed", limit=5)

    assert len(items) == 2
    assert items[0].title
    assert items[0].url.startswith("http")
    assert isinstance(items[0].snippet, str)


@pytest.mark.contract
def test_real_rss_smoke():
    items = rss.fetch("https://techcrunch.com/feed/", limit=3)

    assert len(items) >= 1
    assert items[0].title
