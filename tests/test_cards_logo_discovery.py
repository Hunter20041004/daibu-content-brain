import pytest

from daibu.cards import logo_discovery
from daibu.cards.official_site import OfficialSite
from daibu.models import Material
from tests.card_fixtures import solid_png


VALID_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 80">'
    b'<path fill="#111" d="M0 0h240v80H0z"/></svg>'
)


def test_extract_candidates_returns_three_deduplicated_ranked_assets():
    site = OfficialSite(
        "Acme",
        "https://acme.example/",
        "acme.example",
        "high",
        (),
    )
    html = (
        '<img alt="Acme logo" src="/wordmark.svg">'
        '<img alt="Acme logo duplicate" src="/wordmark.svg">'
        '<img alt="Acme symbol" src="/symbol.svg">'
        '<img alt="Acme app icon" src="/icon.png">'
        '<img alt="Acme extra logo" src="/extra.svg">'
    )

    def fetch(url):
        if url.endswith(".png"):
            return solid_png(128, 128), "image/png"
        return VALID_SVG, "image/svg+xml"

    candidates = logo_discovery.extract_candidates(
        site,
        html_fetch_fn=lambda _url: html,
        asset_fetch_fn=fetch,
    )

    assert [item.logo_kind for item in candidates] == [
        "logo",
        "symbol",
        "icon",
    ]
    assert len({item.asset_url for item in candidates}) == 3


def test_extracts_organization_logo_from_json_ld():
    site = OfficialSite(
        "Acme",
        "https://acme.example/",
        "acme.example",
        "high",
        (),
    )
    html = (
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Organization",'
        '"name":"Acme","logo":"/assets/logo.svg"}'
        "</script>"
    )

    candidates = logo_discovery.extract_candidates(
        site,
        html_fetch_fn=lambda _url: html,
        asset_fetch_fn=lambda _url: (VALID_SVG, "image/svg+xml"),
    )

    assert len(candidates) == 1
    assert candidates[0].asset_url == "https://acme.example/assets/logo.svg"
    assert candidates[0].logo_kind == "logo"
    assert "Organization.logo" in candidates[0].reasons


def test_extracts_srcset_and_explicit_brand_background_only():
    site = OfficialSite(
        "Acme",
        "https://acme.example/",
        "acme.example",
        "high",
        (),
    )
    html = (
        '<img alt="Acme logo" '
        'srcset="/small.svg 1x, /large.svg 2x">'
        '<header><div class="brand-symbol" '
        'style="background-image:url(\'/brand-symbol.svg\')"></div></header>'
        '<article><div class="article-background" '
        'style="background-image:url(\'/story.svg\')"></div></article>'
    )
    fetched = []

    candidates = logo_discovery.extract_candidates(
        site,
        html_fetch_fn=lambda _url: html,
        asset_fetch_fn=lambda url: (
            fetched.append(url) or (VALID_SVG, "image/svg+xml")
        ),
    )

    assert [item.asset_url for item in candidates] == [
        "https://acme.example/large.svg",
        "https://acme.example/brand-symbol.svg",
    ]
    assert "https://acme.example/small.svg" not in fetched
    assert "https://acme.example/story.svg" not in fetched


def test_extract_candidates_keeps_safe_inline_svg():
    site = OfficialSite(
        "Acme",
        "https://acme.example/",
        "acme.example",
        "high",
        (),
    )
    html = (
        '<svg aria-label="Acme logo" viewBox="0 0 240 80">'
        '<path d="M0 0h240v80H0z"/></svg>'
    )

    candidates = logo_discovery.extract_candidates(
        site,
        html_fetch_fn=lambda _url: html,
        asset_fetch_fn=lambda _url: pytest.fail(
            "Inline SVG must not use the asset downloader"
        ),
    )

    assert len(candidates) == 1
    assert candidates[0].filename == "acme-inline-logo.svg"
    assert candidates[0].asset_url == (
        "https://acme.example/#inline-logo-1"
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


def test_discover_extracts_an_inline_svg_logo_from_official_site():
    html = (
        '<html><body><a aria-label="Home" href="/">'
        '<svg class="logo" data-testid="acme-nav-logo" '
        'style="enable-background:new" viewBox="0 0 240 80">'
        '<path fill="#ff4300" d="M0 0h240v80H0z"/>'
        '</svg></a></body></html>'
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
        asset_fetch_fn=lambda _url: pytest.fail(
            "Inline SVG must not be downloaded as a separate asset"
        ),
    )

    logo_discovery.logo.validate_upload(candidate.data, candidate.filename)
    assert candidate.company == "Acme"
    assert candidate.filename == "acme-inline-logo.svg"
    assert candidate.official_page_url == "https://acme.example/"
    assert candidate.asset_url == "https://acme.example/#inline-logo-1"


def test_discover_retries_with_official_site_query_when_brand_search_is_empty():
    queries = []

    def search(query, _limit):
        queries.append(query)
        if len(queries) == 1:
            return []
        return [
            Material(
                "Acme | Official website",
                "https://acme.example/",
                "The official Acme homepage",
            )
        ]

    candidate = logo_discovery.discover(
        "Acme",
        search_fn=search,
        html_fetch_fn=lambda _url: (
            '<svg data-testid="acme-nav-logo" viewBox="0 0 240 80">'
            '<path d="M0 0h240v80H0z"/></svg>'
        ),
    )

    assert candidate.company == "Acme"
    assert queries == [
        '"Acme" official website logo brand assets',
        '"Acme" official website',
    ]


def test_discover_skips_a_domain_that_only_starts_with_the_company_name():
    pages = {
        "https://moovecars.com/": (
            '<img alt="Moove Cars logo" '
            'src="https://moovecars.com/moove-cars.svg">'
        ),
        "https://www.moove.io/": (
            '<img alt="Moove logo" '
            'src="https://www.moove.io/moove.svg">'
        ),
    }

    candidate = logo_discovery.discover(
        "Moove",
        search_fn=lambda _query, _limit: [
            Material(
                "Moove Cars",
                "https://moovecars.com/",
                "A different car company",
            ),
            Material(
                "Moove | Official website",
                "https://www.moove.io/",
                "The mobility fintech company",
            ),
        ],
        html_fetch_fn=lambda url: pages[url],
        asset_fetch_fn=lambda _url: (VALID_SVG, "image/svg+xml"),
    )

    assert candidate.official_page_url == "https://www.moove.io/"
    assert candidate.asset_url == "https://www.moove.io/moove.svg"


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


def test_discover_does_not_trust_an_official_claim_on_an_unrelated_domain():
    with pytest.raises(logo_discovery.LogoDiscoveryError):
        logo_discovery.discover(
            "Acme",
            search_fn=lambda _query, _limit: [
                Material(
                    "Acme official website and brand assets",
                    "https://logo-downloads.example/acme",
                    "Download the official Acme logo here",
                )
            ],
            html_fetch_fn=lambda _url: pytest.fail(
                "A self-proclaimed official result must not be fetched"
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


@pytest.mark.contract
def test_moove_official_site_keeps_an_extractable_inline_logo():
    candidate = logo_discovery.discover(
        "Moove",
        search_fn=lambda _query, _limit: [
            Material(
                "Moove | The Future of Mobility",
                "https://www.moove.io/",
                "Moove's official website",
            )
        ],
    )

    logo_discovery.logo.validate_upload(candidate.data, candidate.filename)
    assert candidate.company == "Moove"
    assert candidate.official_page_url == "https://www.moove.io/"
    assert candidate.asset_url.startswith(
        "https://www.moove.io/#inline-logo-"
    )
