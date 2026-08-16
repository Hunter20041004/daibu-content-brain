import pytest

from daibu.cards import brandfetch, logo_search
from daibu.cards.logo_discovery import LogoCandidate
from daibu.cards.official_site import OfficialSite, OfficialSiteError


VALID_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 80">'
    b'<path d="M0 0h240v80H0z"/></svg>'
)


def candidate(source_kind="official_site"):
    return LogoCandidate(
        "Acme",
        "acme.svg",
        VALID_SVG,
        "https://acme.example/brand",
        "https://acme.example/acme.svg",
        "https://acme.example/",
        source_kind,
    )


def context():
    return logo_search.LogoSearchContext(
        "Acme",
        "Acme 新創介紹",
        "產品角度",
        "Acme 提供企業工具。",
        (),
    )


def test_official_candidate_prevents_brandfetch_call():
    site = OfficialSite(
        "Acme",
        "https://acme.example/",
        "acme.example",
        "high",
        (),
    )

    result = logo_search.find_candidates(
        context(),
        site_resolver=lambda *_args, **_kwargs: site,
        official_finder=lambda *_args, **_kwargs: (candidate(),),
        brandfetch_finder=lambda *_args, **_kwargs: pytest.fail(
            "Brandfetch must not run after official success"
        ),
    )

    assert result.site == site
    assert result.candidates == (candidate(),)
    assert result.used_brandfetch is False


def test_brandfetch_runs_after_official_paths_are_empty():
    site = OfficialSite(
        "Acme",
        "https://acme.example/",
        "acme.example",
        "high",
        (),
    )
    received = []
    fallback = candidate("brandfetch")

    result = logo_search.find_candidates(
        context(),
        site_resolver=lambda *_args, **_kwargs: site,
        official_finder=lambda *_args, **_kwargs: (),
        brandfetch_finder=lambda received_site, **kwargs: (
            received.append((received_site, kwargs["client_id"]))
            or (fallback,)
        ),
        brandfetch_client_id="client-test",
    )

    assert received == [(site, "client-test")]
    assert result.candidates == (fallback,)
    assert result.used_brandfetch is True


def test_official_site_failure_has_a_stage_and_recovery_action():
    with pytest.raises(logo_search.LogoSearchError) as captured:
        logo_search.find_candidates(
            context(),
            site_resolver=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                OfficialSiteError(
                    "找不到可信的官方網站。請提供官網或重新搜尋。"
                )
            ),
        )

    assert captured.value.stage == "official_site"
    assert captured.value.user_message == (
        "找不到可信的官方網站。請提供官網或重新搜尋。"
    )


def test_missing_brandfetch_config_preserves_manual_upload_recovery():
    site = OfficialSite(
        "Acme",
        "https://acme.example/",
        "acme.example",
        "high",
        (),
    )

    with pytest.raises(logo_search.LogoSearchError) as captured:
        logo_search.find_candidates(
            context(),
            site_resolver=lambda *_args, **_kwargs: site,
            official_finder=lambda *_args, **_kwargs: (),
            brandfetch_finder=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                brandfetch.BrandfetchNotConfigured(
                    "尚未設定 Brandfetch Client ID，仍可手動上傳 Logo。"
                )
            ),
        )

    assert captured.value.stage == "brandfetch"
    assert "手動上傳" in captured.value.user_message


def test_empty_brandfetch_result_explains_that_both_paths_failed():
    site = OfficialSite(
        "Acme",
        "https://acme.example/",
        "acme.example",
        "high",
        (),
    )

    with pytest.raises(logo_search.LogoSearchError) as captured:
        logo_search.find_candidates(
            context(),
            site_resolver=lambda *_args, **_kwargs: site,
            official_finder=lambda *_args, **_kwargs: (),
            brandfetch_finder=lambda *_args, **_kwargs: (),
            brandfetch_client_id="client-test",
        )

    assert captured.value.stage == "brandfetch"
    assert captured.value.user_message == (
        "官網與 Brandfetch 都沒有可用 Logo；請手動上傳。"
    )


def test_temporary_official_asset_service_error_hides_raw_details():
    site = OfficialSite(
        "Acme",
        "https://acme.example/",
        "acme.example",
        "high",
        (),
    )

    with pytest.raises(logo_search.LogoSearchError) as captured:
        logo_search.find_candidates(
            context(),
            site_resolver=lambda *_args, **_kwargs: site,
            official_finder=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                OSError("socket token=private-provider-detail")
            ),
        )

    assert captured.value.stage == "service"
    assert captured.value.user_message == (
        "公司官網暫時無法讀取；你可以重新搜尋或手動上傳 Logo。"
    )
    assert "private-provider-detail" not in str(captured.value)


def test_temporary_brandfetch_error_names_the_service_without_raw_details():
    site = OfficialSite(
        "Acme",
        "https://acme.example/",
        "acme.example",
        "high",
        (),
    )

    with pytest.raises(logo_search.LogoSearchError) as captured:
        logo_search.find_candidates(
            context(),
            site_resolver=lambda *_args, **_kwargs: site,
            official_finder=lambda *_args, **_kwargs: (),
            brandfetch_finder=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                OSError("upstream client-test private detail")
            ),
            brandfetch_client_id="client-test",
        )

    assert captured.value.stage == "service"
    assert captured.value.user_message == (
        "Brandfetch 暫時無法使用；你可以重新搜尋或手動上傳 Logo。"
    )
    assert "client-test" not in str(captured.value)
