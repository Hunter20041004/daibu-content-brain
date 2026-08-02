import pytest

from daibu.cards import logo_discovery
from daibu.models import Material


VALID_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 80">'
    b'<path fill="#111" d="M0 0h240v80H0z"/></svg>'
)


def test_discover_downloads_logo_referenced_by_official_brand_page():
    pages = {
        "https://acme.example/": (
            '<html><head><title>Acme</title></head><body>'
            '<a href="/brand">Brand assets</a></body></html>'
        ),
        "https://acme.example/brand": (
            '<html><head><title>Acme brand assets</title></head><body>'
            '<img alt="Acme logo" src="/assets/acme-logo.svg">'
            '</body></html>'
        ),
    }
    downloaded = []

    candidate = logo_discovery.discover(
        "Acme",
        search_fn=lambda _query, _limit: [
            Material(
                "Acme | Official website",
                "https://acme.example/",
                "The official Acme homepage",
            )
        ],
        html_fetch_fn=lambda url: pages[url],
        asset_fetch_fn=lambda url: (
            downloaded.append(url) or (VALID_SVG, "image/svg+xml")
        ),
    )

    assert candidate.company == "Acme"
    assert candidate.filename == "acme-logo.svg"
    assert candidate.data == VALID_SVG
    assert candidate.official_page_url == "https://acme.example/brand"
    assert candidate.asset_url == "https://acme.example/assets/acme-logo.svg"
    assert downloaded == ["https://acme.example/assets/acme-logo.svg"]


def test_discover_prefers_dark_logo_over_white_variant():
    downloaded = []
    html = (
        '<html><body>'
        '<img alt="Acme Logo" class="navbar-logo-light" '
        'src="/assets/acme-logo-white.svg">'
        '<img alt="Acme Logo" class="navbar-logo-dark" '
        'src="/assets/acme-logo.svg">'
        '</body></html>'
    )

    candidate = logo_discovery.discover(
        "Acme",
        search_fn=lambda _query, _limit: [
            Material(
                "Acme | Official website",
                "https://acme.example/",
                "The official Acme homepage",
            )
        ],
        html_fetch_fn=lambda _url: html,
        asset_fetch_fn=lambda url: (
            downloaded.append(url) or (VALID_SVG, "image/svg+xml")
        ),
    )

    assert candidate.asset_url == "https://acme.example/assets/acme-logo.svg"
    assert downloaded == ["https://acme.example/assets/acme-logo.svg"]


def test_discover_skips_editorial_and_unrelated_search_results():
    results = [
        Material(
            "Acme company profile",
            "https://techcrunch.com/acme",
            "News about Acme",
        ),
        Material(
            "Another company",
            "https://unrelated.example/",
            "Official homepage for someone else",
        ),
    ]

    with pytest.raises(
        logo_discovery.LogoDiscoveryError,
        match="官方 SVG 或透明 PNG",
    ):
        logo_discovery.discover(
            "Acme",
            search_fn=lambda _query, _limit: results,
            html_fetch_fn=lambda _url: pytest.fail(
                "Blocked or unrelated pages must not be fetched"
            ),
        )


def test_discover_skips_an_unsafe_asset_and_uses_the_next_valid_logo():
    unsafe_svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 80">'
        b'<script>alert(1)</script></svg>'
    )
    assets = {
        "https://acme.example/assets/unsafe-logo.svg": unsafe_svg,
        "https://acme.example/assets/safe-logo.svg": VALID_SVG,
    }
    downloaded = []

    candidate = logo_discovery.discover(
        "Acme",
        search_fn=lambda _query, _limit: [
            Material(
                "Acme | Official website",
                "https://acme.example/",
                "The official Acme homepage",
            )
        ],
        html_fetch_fn=lambda _url: (
            '<img alt="Acme unsafe logo" '
            'src="/assets/unsafe-logo.svg">'
            '<img alt="Acme safe logo" src="/assets/safe-logo.svg">'
        ),
        asset_fetch_fn=lambda url: (
            downloaded.append(url) or (assets[url], "image/svg+xml")
        ),
    )

    assert candidate.asset_url.endswith("/safe-logo.svg")
    assert downloaded == [
        "https://acme.example/assets/unsafe-logo.svg",
        "https://acme.example/assets/safe-logo.svg",
    ]
