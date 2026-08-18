import os
from urllib.parse import urlparse

import pytest
from dotenv import load_dotenv

from daibu.cards import official_site
from daibu.cards.schema import VerifiedSource
from daibu.fetch import search as web_search
from daibu.models import Material


def test_resolve_continues_after_irrelevant_results_and_uses_context_for_sun():
    calls = []

    def search(query, _limit):
        calls.append(query)
        if len(calls) == 1:
            return [
                Material(
                    "SUNY Brand",
                    "https://www.suny.edu/brand",
                    "University",
                )
            ]
        return [
            Material(
                "SUN — personalized AI audio",
                "https://sunapp.ai/",
                "Create personalized podcasts, audiobooks and audio courses",
            )
        ]

    site = official_site.resolve(
        "SUN",
        context="personalized AI audio podcasts and courses",
        search_fn=search,
        html_fetch_fn=lambda _url: (
            '<title>SUN — personalized AI audio</title>'
            '<script type="application/ld+json">'
            '{"@type":"Organization","name":"SUN"}</script>'
        ),
    )

    assert site.website_url == "https://sunapp.ai/"
    assert site.domain == "sunapp.ai"
    assert len(calls) == 2
    assert "personalized AI audio" in calls[1]


def test_product_directory_official_link_is_strong_evidence():
    source_url = "https://www.producthunt.com/products/sun-ai"
    pages = {
        source_url: (
            '<title>SUN on Product Hunt</title>'
            '<a href="https://sunapp.ai/">Visit website</a>'
        ),
        "https://sunapp.ai/": (
            '<title>SUN — personalized AI audio</title>'
            '<p>Create personalized podcasts and audio courses.</p>'
        ),
    }
    source = VerifiedSource(
        "S1",
        "Product Hunt",
        "2026-08-15",
        source_url,
        "SUN creates personalized podcasts and audio courses.",
        "third_party",
    )

    site = official_site.resolve(
        "SUN",
        context="personalized podcasts and audio courses",
        sources=(source,),
        search_fn=lambda _query, _limit: (_ for _ in ()).throw(
            AssertionError("Strong source-page evidence must avoid Tavily")
        ),
        html_fetch_fn=lambda url: pages[url],
    )

    assert site.website_url == "https://sunapp.ai/"
    assert any(item.kind == "directory_link" for item in site.evidence)


def test_product_directory_ignores_social_links_before_the_official_site():
    source_url = "https://www.producthunt.com/products/sun-ai"
    pages = {
        source_url: (
            '<a href="https://www.linkedin.com/company/sun-ai">LinkedIn</a>'
            '<a href="https://sunapp.ai/">Visit website</a>'
        ),
        "https://sunapp.ai/": (
            "<title>SUN</title><p>personalized podcasts and audio courses</p>"
        ),
    }
    source = VerifiedSource(
        "S1",
        "Product Hunt",
        "2026-08-15",
        source_url,
        "SUN creates personalized podcasts and audio courses.",
        "third_party",
    )

    site = official_site.resolve(
        "SUN",
        context="personalized podcasts and audio courses",
        sources=(source,),
        search_fn=lambda _query, _limit: [],
        html_fetch_fn=lambda url: pages[url],
    )

    assert site.domain == "sunapp.ai"


def test_equally_supported_same_name_sites_require_human_choice():
    results = [
        Material(
            "SUN — official website",
            "https://sunapp.ai/",
            "SUN makes personalized AI audio",
        ),
        Material(
            "SUN — official website",
            "https://getsun.io/",
            "SUN makes personalized AI audio",
        ),
    ]

    with pytest.raises(
        official_site.AmbiguousOfficialSiteError,
        match="找到多個可能的同名公司，請選擇正確官網",
    ):
        official_site.resolve(
            "SUN",
            context="personalized AI audio",
            search_fn=lambda _query, _limit: results,
            html_fetch_fn=lambda _url: (
                "<title>SUN</title><p>personalized AI audio</p>"
            ),
        )


def test_default_html_downloader_decodes_a_bounded_response(monkeypatch):
    seen = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, limit):
            seen["limit"] = limit
            return "<title>SUN 官網</title>".encode()

    def fake_urlopen(request, *, timeout, context):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["context"] = context
        return Response()

    monkeypatch.setattr(official_site, "urlopen", fake_urlopen, raising=False)

    assert official_site._download_html("https://sunapp.ai/") == (
        "<title>SUN 官網</title>"
    )
    assert seen.pop("context") is not None
    assert seen == {
        "url": "https://sunapp.ai/",
        "timeout": 15,
        "limit": official_site.MAX_HTML_BYTES,
    }


@pytest.mark.contract
def test_sun_resolves_to_sunapp_ai_against_real_search():
    load_dotenv()
    if not os.getenv("TAVILY_API_KEY"):
        pytest.skip("需要 TAVILY_API_KEY 才能執行真實搜尋契約")
    inspected_domains = []

    def inspect_search(query, limit):
        results = web_search.search_web(query, limit)
        inspected_domains.extend(
            (urlparse(result.url).hostname or "") for result in results
        )
        return results

    source = VerifiedSource(
        "S1",
        "Product Hunt",
        "2026-08-15",
        "https://www.producthunt.com/products/sun-ai",
        "SUN creates personalized AI podcasts, audiobooks and courses.",
        "third_party",
    )
    try:
        site = official_site.resolve(
            "SUN",
            context="personalized AI audio podcasts audiobooks courses",
            sources=(source,),
            search_fn=inspect_search,
        )
    except official_site.OfficialSiteError as error:
        pytest.fail(
            f"SUN 官網解析失敗；實際檢查網域={inspected_domains!r}；{error}"
        )

    assert site.domain == "sunapp.ai", (
        f"預期 sunapp.ai，實際 {site.domain!r}；"
        f"實際檢查網域={inspected_domains!r}"
    )
