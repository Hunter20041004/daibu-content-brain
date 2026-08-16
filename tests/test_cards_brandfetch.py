import pytest

from daibu.cards import brandfetch, logo
from daibu.cards.official_site import OfficialSite


VALID_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 80">'
    b'<path fill="#111" d="M0 0h240v80H0z"/></svg>'
)


def test_brandfetch_uses_explicit_domain_route_and_404_fallback():
    seen = []
    candidates = brandfetch.fetch_candidates(
        OfficialSite(
            "SUN",
            "https://sunapp.ai/",
            "sunapp.ai",
            "high",
            (),
        ),
        client_id="client-test",
        fetch_fn=lambda url: (
            seen.append(url) or (VALID_SVG, "image/svg+xml", 200)
        ),
    )

    assert candidates
    assert all("/domain/sunapp.ai/" in url for url in seen)
    assert all("/fallback/404/" in url for url in seen)
    assert all("SUN" not in url for url in seen)
    assert all(item.source_kind == "brandfetch" for item in candidates)
    assert all("client-test" not in item.asset_url for item in candidates)


def test_brandfetch_discards_404_empty_and_non_image_responses():
    valid_symbol = VALID_SVG.replace(b'#111', b'#222')
    responses = iter(
        (
            (VALID_SVG, "image/svg+xml", 404),
            (b"", "image/svg+xml", 200),
            (b"<html>not a logo</html>", "text/html", 200),
            (valid_symbol, "image/svg+xml", 200),
        )
    )

    candidates = brandfetch.fetch_candidates(
        OfficialSite(
            "SUN",
            "https://sunapp.ai/",
            "sunapp.ai",
            "high",
            (),
        ),
        client_id="client-test",
        fetch_fn=lambda _url: next(responses),
    )

    assert len(candidates) == 1
    assert candidates[0].data == valid_symbol
    assert candidates[0].logo_kind == "symbol"
    assert candidates[0].theme == "light"
    logo.validate_upload(candidates[0].data, candidates[0].filename)


def test_brandfetch_requires_a_client_id_before_network_calls():
    with pytest.raises(
        brandfetch.BrandfetchNotConfigured,
        match="尚未設定 Brandfetch Client ID，仍可手動上傳 Logo",
    ):
        brandfetch.fetch_candidates(
            OfficialSite(
                "SUN",
                "https://sunapp.ai/",
                "sunapp.ai",
                "high",
                (),
            ),
            client_id="",
            fetch_fn=lambda _url: pytest.fail(
                "Missing configuration must stop before network access"
            ),
        )
