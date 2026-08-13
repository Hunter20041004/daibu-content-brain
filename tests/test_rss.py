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


def test_fetch_tagged_preserves_date_and_categories(monkeypatch):
    raw = Path("tests/fixtures/techcrunch_startups.xml").read_text()
    monkeypatch.setattr(rss, "_download", lambda _url: raw)

    entries = rss.fetch_tagged(
        "https://techcrunch.com/category/startups/feed/"
    )

    assert entries[0].published_at == "Wed, 12 Aug 2026 18:19:12 +0000"
    assert {"AI", "Startups", "Cognition"} <= set(entries[0].tags)


@pytest.mark.contract
def test_real_rss_smoke():
    items = rss.fetch("https://techcrunch.com/feed/", limit=3)

    assert len(items) >= 1
    assert items[0].title


@pytest.mark.contract
def test_real_techcrunch_startups_has_tagged_ai_entries():
    entries = rss.fetch_tagged(
        "https://techcrunch.com/category/startups/feed/",
        limit=20,
    )

    assert entries
    assert any(
        "AI" in entry.tags and "Startups" in entry.tags
        for entry in entries
    )
