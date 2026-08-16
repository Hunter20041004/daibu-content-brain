"""Orchestrate official-site and third-party Logo discovery."""

from dataclasses import dataclass

from daibu.cards import brandfetch, logo_browser, logo_discovery, official_site
from daibu.cards.logo_discovery import LogoCandidate
from daibu.cards.official_site import OfficialSite
from daibu.cards.schema import VerifiedSource


@dataclass(frozen=True)
class LogoSearchContext:
    company: str
    title: str
    angle: str
    body: str
    sources: tuple[VerifiedSource, ...]


@dataclass(frozen=True)
class LogoSearchResult:
    site: OfficialSite
    candidates: tuple[LogoCandidate, ...]
    used_brandfetch: bool


class LogoSearchError(ValueError):
    def __init__(self, stage: str, user_message: str) -> None:
        self.stage = stage
        self.user_message = user_message
        super().__init__(user_message)


def find_candidates(
    context: LogoSearchContext,
    *,
    site_resolver=official_site.resolve,
    official_finder=logo_discovery.extract_candidates,
    rendered_fetch_fn=logo_browser.render_site,
    brandfetch_finder=brandfetch.fetch_candidates,
    brandfetch_client_id: str | None = None,
) -> LogoSearchResult:
    text_context = " ".join(
        value.strip()
        for value in (context.title, context.angle, context.body)
        if value.strip()
    )
    try:
        site = site_resolver(
            context.company,
            context=text_context,
            sources=context.sources,
        )
    except official_site.OfficialSiteError as error:
        raise LogoSearchError("official_site", str(error)) from error
    try:
        official = official_finder(
            site,
            rendered_fetch_fn=rendered_fetch_fn,
        )
    except OSError as error:
        raise LogoSearchError(
            "service",
            "公司官網暫時無法讀取；你可以重新搜尋或手動上傳 Logo。",
        ) from error
    if official:
        return LogoSearchResult(site, official, False)
    try:
        fallback = brandfetch_finder(
            site,
            client_id=brandfetch_client_id,
        )
    except brandfetch.BrandfetchNotConfigured as error:
        raise LogoSearchError("brandfetch", str(error)) from error
    except OSError as error:
        raise LogoSearchError(
            "service",
            "Brandfetch 暫時無法使用；你可以重新搜尋或手動上傳 Logo。",
        ) from error
    if not fallback:
        raise LogoSearchError(
            "brandfetch",
            "官網與 Brandfetch 都沒有可用 Logo；請手動上傳。",
        )
    return LogoSearchResult(site, fallback, True)
