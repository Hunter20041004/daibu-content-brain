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


def test_raw_search_explains_missing_api_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
        search._raw_search("AI news", ["techcrunch.com"], 5)


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
