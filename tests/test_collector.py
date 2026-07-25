from daibu.fetch import collector
from daibu.models import Material, Source, Theme


def test_collect_skips_failing_source(monkeypatch):
    def fake_fetch(url, limit=10):
        if "bad" in url:
            raise RuntimeError("down")
        return [Material("t", "https://ok.com/1", "s")]

    monkeypatch.setattr(collector.rss, "fetch", fake_fetch)
    theme = Theme(1, "大事", 0, [1, 2], 3)
    sources = [
        Source(1, "ok", "https://ok.com/feed", "rss", True),
        Source(2, "bad", "https://bad.com/feed", "rss", True),
    ]

    materials = collector.collect(theme, sources)

    assert [material.url for material in materials] == ["https://ok.com/1"]


def test_collect_only_uses_sources_bound_to_the_theme(monkeypatch):
    monkeypatch.setattr(
        collector.rss,
        "fetch",
        lambda url, limit=10: [Material(url, url, "")],
    )
    theme = Theme(1, "大事", 0, [1], 3)
    sources = [
        Source(1, "已綁定", "https://bound.example/feed", "rss", True),
        Source(2, "未綁定", "https://other.example/feed", "rss", True),
    ]

    materials = collector.collect(theme, sources)

    assert [material.url for material in materials] == [
        "https://bound.example/feed"
    ]


def test_theme_without_sources_collects_nothing(monkeypatch):
    monkeypatch.setattr(
        collector.rss,
        "fetch",
        lambda url, limit=10: [Material("不該抓", url, "")],
    )
    theme = Theme(1, "新創", 0, [], 3)
    sources = [
        Source(1, "來源", "https://example.com/feed", "rss", True)
    ]

    assert collector.collect(theme, sources) == []


def test_collect_dispatches_search_with_source_domain(monkeypatch):
    calls = []

    def fake_search(query, allowed_domains, limit=5):
        calls.append((query, allowed_domains, limit))
        return [Material("搜尋結果", "https://techcrunch.com/x", "摘要")]

    monkeypatch.setattr(collector.search, "search", fake_search)
    theme = Theme(1, "AI 大事", 0, [1], 3)
    sources = [
        Source(
            1,
            "TechCrunch 搜尋",
            "https://techcrunch.com/",
            "search",
            True,
        )
    ]

    materials = collector.collect(theme, sources)

    assert [material.title for material in materials] == ["搜尋結果"]
    assert calls == [("AI 大事", ["techcrunch.com"], 10)]
