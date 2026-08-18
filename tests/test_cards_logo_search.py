import pytest

from daibu.cards import logo_search
from daibu.cards.logo_discovery import LogoCandidate
from daibu.cards.official_site import OfficialSite, OfficialSiteError


VALID_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 80">'
    b'<path d="M0 0h240v80H0z"/></svg>'
)


def candidate():
    return LogoCandidate(
        "Acme",
        "acme.svg",
        VALID_SVG,
        "https://acme.example/brand",
        "https://acme.example/acme.svg",
        "https://acme.example/",
        "official_site",
    )


def context():
    return logo_search.LogoSearchContext(
        "Acme",
        "Acme 新創介紹",
        "產品角度",
        "Acme 提供企業工具。",
        (),
    )


def test_official_candidate_is_returned_with_its_resolved_site():
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
    )

    assert result.site == site
    assert result.candidates == (candidate(),)


def test_empty_official_paths_require_manual_upload_without_a_fallback_call():
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
            rendered_fetch_fn=lambda _url: pytest.fail(
                "official_finder owns the rendered fallback"
            ),
        )

    assert captured.value.stage == "official_assets"
    assert captured.value.user_message == (
        "官網沒有找到可安全預覽的 Logo；請手動上傳。"
    )


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
