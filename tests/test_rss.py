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


@pytest.mark.contract
@pytest.mark.parametrize(
    "url",
    [
        "https://www.producthunt.com/feed",
        "https://www.ycombinator.com/blog/rss",
        "https://venturebeat.com/category/ai/feed/",
        "https://techcrunch.com/feed/",
        "https://www.inside.com.tw/feed/rss",
    ],
)
def test_startup_theme_feeds_are_reachable(url):
    """「AI 新創介紹」綁的 5 個來源必須真的抓得到，且真的是 RSS。"""
    items = rss.fetch(url)

    assert items, f"{url} 抓不到任何項目"
