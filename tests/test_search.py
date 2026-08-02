import os

import pytest
from dotenv import load_dotenv

from daibu.fetch import search


def test_search_maps_and_scopes(monkeypatch):
    fake = {
        "results": [
            {
                "title": "A",
                "url": "https://techcrunch.com/x",
                "content": "可信內容",
            },
            {
                "title": "B",
                "url": "https://spam.com/y",
                "content": "不應進入素材池",
            },
        ]
    }
    monkeypatch.setattr(
        search,
        "_raw_search",
        lambda query, domains, limit: fake,
    )

    materials = search.search(
        "AI news",
        allowed_domains=["techcrunch.com"],
        limit=5,
    )

    assert [material.url for material in materials] == [
        "https://techcrunch.com/x"
    ]


def test_search_web_maps_https_results_without_domain_filter(monkeypatch):
    seen = []
    fake = {
        "results": [
            {
                "title": "Official company website",
                "url": "https://company.example/",
                "content": "Company homepage",
            },
            {
                "title": "Unsafe result",
                "url": "http://unsafe.example/",
                "content": "Not HTTPS",
            },
        ]
    }

    def fake_search(query, domains, limit):
        seen.append((query, domains, limit))
        return fake

    monkeypatch.setattr(search, "_raw_search", fake_search)

    materials = search.search_web("Company official website", limit=4)

    assert seen == [("Company official website", [], 4)]
    assert [material.url for material in materials] == [
        "https://company.example/"
    ]


def test_raw_search_explains_missing_api_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
        search._raw_search("AI news", ["techcrunch.com"], 5)


def test_raw_search_omits_empty_include_domains(monkeypatch):
    seen = []

    class FakeClient:
        def __init__(self, api_key):
            assert api_key == "test-key"

        def search(self, **kwargs):
            seen.append(kwargs)
            return {"results": []}

    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    monkeypatch.setattr(search, "TavilyClient", FakeClient)

    search._raw_search("Company official website", [], 3)

    assert seen == [
        {"query": "Company official website", "max_results": 3}
    ]


@pytest.mark.contract
def test_real_tavily_search_stays_in_allowed_domain():
    load_dotenv()
    if not os.getenv("TAVILY_API_KEY"):
        pytest.skip("無 TAVILY_API_KEY")

    materials = search.search(
        "latest AI news",
        allowed_domains=["techcrunch.com"],
        limit=3,
    )

    assert materials
    assert all(
        search._is_allowed(material.url, ["techcrunch.com"])
        for material in materials
    )


@pytest.mark.contract
def test_real_tavily_web_search_returns_https_official_site_candidates():
    load_dotenv()
    if not os.getenv("TAVILY_API_KEY"):
        pytest.skip("無 TAVILY_API_KEY")

    materials = search.search_web(
        '"BillionToOne" official website',
        limit=5,
    )

    assert materials
    assert all(material.url.startswith("https://") for material in materials)
    assert any("billiontoone.com" in material.url for material in materials)
