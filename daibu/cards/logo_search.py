"""Orchestrate official-site Logo discovery."""

from dataclasses import dataclass

from daibu.cards import logo_browser, logo_discovery, official_site
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
        return LogoSearchResult(site, official)
    raise LogoSearchError(
        "official_assets",
        "官網沒有找到可安全預覽的 Logo；請手動上傳。",
    )
