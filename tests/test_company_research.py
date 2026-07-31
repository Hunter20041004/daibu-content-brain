from dataclasses import dataclass

import pytest

from daibu.models import Material, SourceSuggestion


@dataclass
class SearchCall:
    query: str
    domains: tuple[str, ...]
    limit: int


def test_research_only_keeps_allowed_relevant_company_articles():
    from daibu.fetch.company_research import research

    calls: list[SearchCall] = []

    def fake_search(query, allowed_domains, limit=5):
        calls.append(SearchCall(query, tuple(allowed_domains), limit))
        return [
            Material(
                "Railway company profile",
                "https://techcrunch.com/railway",
                "Railway profile",
            ),
            Material(
                "Wrong host",
                "https://spam.example/railway",
                "Railway profile",
            ),
            Material(
                "Another company",
                "https://techcrunch.com/not-railway",
                "Unrelated",
            ),
        ]

    def fake_fetch(url):
        excerpts = {
            "https://techcrunch.com/railway": (
                "Railway provides cloud deployment tools for developers."
            ),
            "https://techcrunch.com/not-railway": (
                "This article only discusses another startup."
            ),
        }
        return SourceSuggestion(
            "TechCrunch",
            "2026-07-30",
            url,
            excerpts[url],
        )

    result = research(
        "Railway",
        (),
        ["techcrunch.com"],
        [],
        search_fn=fake_search,
        fetch_fn=fake_fetch,
    )

    assert [source.url for source in result.sources] == [
        "https://techcrunch.com/railway",
    ]
    assert result.sources[0].source_kind == "third_party"
    assert len(calls) == 3
    assert all(call.domains for call in calls)
    assert all(call.limit == 3 for call in calls)


def test_research_keeps_valid_articles_when_one_download_fails():
    from daibu.fetch.company_research import research

    searches = 0

    def fake_search(query, allowed_domains, limit=5):
        nonlocal searches
        searches += 1
        if searches > 1:
            return []
        return [
            Material("Railway blocked", "https://techcrunch.com/bad", ""),
            Material("Railway profile", "https://techcrunch.com/good", ""),
        ]

    def fake_fetch(url):
        if url.endswith("/bad"):
            raise ValueError("抓取失敗")
        return SourceSuggestion(
            "TechCrunch",
            "2026-07-30",
            url,
            "Railway builds cloud deployment tools.",
        )

    result = research(
        "Railway",
        (),
        ["techcrunch.com"],
        [],
        search_fn=fake_search,
        fetch_fn=fake_fetch,
    )

    assert [source.source_id for source in result.sources] == ["S1"]
    assert result.failures == (
        "https://techcrunch.com/bad：抓取失敗",
    )


def test_research_explains_recovery_when_nothing_is_valid():
    from daibu.fetch.company_research import research

    with pytest.raises(ValueError, match="手動新增來源") as error:
        research(
            "Railway",
            (),
            ["techcrunch.com"],
            [],
            search_fn=lambda *_args, **_kwargs: [],
            fetch_fn=lambda _url: None,
        )

    assert "techcrunch.com" in str(error.value)


def test_research_marks_a_verified_company_domain_as_official():
    from daibu.fetch.company_research import research

    def fake_search(query, allowed_domains, limit=5):
        return [
            Material(
                "Railway official update",
                "https://blog.railway.com/update",
                "Railway update",
            )
        ]

    def fake_fetch(url):
        return SourceSuggestion(
            "Railway Blog",
            "2026-07-30",
            url,
            "Railway published a documented platform update.",
        )

    result = research(
        "Railway",
        (),
        [],
        ["railway.com"],
        search_fn=fake_search,
        fetch_fn=fake_fetch,
    )

    assert result.sources[0].source_kind == "official"


@pytest.mark.contract
def test_real_company_research_stays_inside_the_whitelist():
    import os

    from dotenv import load_dotenv

    from daibu.fetch.company_research import research

    load_dotenv()
    if not os.getenv("TAVILY_API_KEY"):
        pytest.skip("無 TAVILY_API_KEY")

    result = research(
        "Railway",
        (),
        ["techcrunch.com", "venturebeat.com", "prnewswire.com"],
        [],
    )

    assert result.sources
    assert all(
        source.url.startswith(
            (
                "https://techcrunch.com/",
                "https://venturebeat.com/",
                "https://www.prnewswire.com/",
                "https://prnewswire.com/",
            )
        )
        for source in result.sources
    )
