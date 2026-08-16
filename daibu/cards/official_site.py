"""Resolve a company's official website before looking for brand assets."""

import re
import ssl
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import certifi

from daibu.cards.schema import VerifiedSource
from daibu.fetch import company_research, search
from daibu.models import Material


_DIRECTORY_PUBLISHERS = {
    "y combinator",
    "yc launches",
    "a16z speedrun",
    "product hunt",
}
_BLOCKED_DOMAINS = (
    *company_research.TRUSTED_EDITORIAL_DOMAINS,
    "apps.apple.com",
    "crunchbase.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "play.google.com",
    "wikipedia.org",
    "x.com",
    "youtube.com",
)
MAX_HTML_BYTES = 1_048_576


class OfficialSiteError(ValueError):
    pass


class AmbiguousOfficialSiteError(OfficialSiteError):
    pass


@dataclass(frozen=True)
class SiteEvidence:
    kind: str
    source_url: str
    detail: str


@dataclass(frozen=True)
class OfficialSite:
    company: str
    website_url: str
    domain: str
    confidence: str
    evidence: tuple[SiteEvidence, ...]


class _LinkParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__()
        self.page_url = page_url
        self.urls: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag != "a":
            return
        values = dict(attrs)
        if values.get("href"):
            self.urls.append(urljoin(self.page_url, values["href"] or ""))


def _hostname(url: str) -> str:
    return (urlparse(url).hostname or "").casefold().removeprefix("www.")


def _is_blocked(url: str) -> bool:
    hostname = _hostname(url)
    return any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in _BLOCKED_DOMAINS
    )


def _contains_name(text: str, company: str) -> bool:
    return bool(
        re.search(
            rf"(?<![\w]){re.escape(company.strip())}(?![\w])",
            text,
            flags=re.IGNORECASE,
        )
    )


def _context_terms(context: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            term.casefold()
            for term in re.findall(r"[A-Za-z0-9一-鿿]+", context)
            if len(term) >= 2
        )
    )[:12]


def _context_matches(text: str, context: str) -> int:
    folded = text.casefold()
    return sum(term in folded for term in _context_terms(context))


def _query_context(context: str) -> str:
    return " ".join(
        term
        for term in re.findall(r"[A-Za-z0-9一-鿿]+", context)
        if len(term) >= 2
    )[:160]


def resolve(
    company: str,
    *,
    context: str = "",
    sources: Iterable[VerifiedSource] = (),
    search_fn: Callable[[str, int], list[Material]] | None = None,
    html_fetch_fn: Callable[[str], str] | None = None,
) -> OfficialSite:
    """Return one evidence-backed official site or a recovery error."""
    company = company.strip()
    if not company:
        raise OfficialSiteError("沒有公司名稱，無法辨認官方網站。")
    do_search = search_fn or search.search_web
    fetch_html = html_fetch_fn or _download_html
    for source in sources:
        if source.publisher.strip().casefold() not in _DIRECTORY_PUBLISHERS:
            continue
        try:
            parser = _LinkParser(source.url)
            parser.feed(fetch_html(source.url))
        except (OSError, UnicodeError, ValueError):
            continue
        source_domain = _hostname(source.url)
        for target in parser.urls:
            target_domain = _hostname(target)
            if (
                urlparse(target).scheme != "https"
                or not target_domain
                or target_domain == source_domain
                or _is_blocked(target)
            ):
                continue
            try:
                target_html = fetch_html(target)
            except (OSError, UnicodeError, ValueError):
                continue
            if (
                _contains_name(target_html, company)
                and _context_matches(target_html, context) >= 2
            ):
                return OfficialSite(
                    company,
                    target,
                    target_domain,
                    "high",
                    (
                        SiteEvidence(
                            "directory_link",
                            source.url,
                            f"{source.publisher} 明確連到公司官網",
                        ),
                        SiteEvidence(
                            "site_context",
                            target,
                            "網站名稱與產品描述相符",
                        ),
                    ),
                )
    queries = [f'"{company}" official website']
    if context.strip():
        context_query = _query_context(context)
        queries.append(f'"{company}" "{context_query}" official website')

    results: list[Material] = []
    for query in queries:
        results.extend(do_search(query, 5))

    scored: list[tuple[int, Material, tuple[SiteEvidence, ...]]] = []
    seen: set[str] = set()
    for material in results:
        domain = _hostname(material.url)
        parsed = urlparse(material.url)
        if (
            parsed.scheme != "https"
            or not domain
            or domain in seen
            or _is_blocked(material.url)
        ):
            continue
        seen.add(domain)
        try:
            html = fetch_html(material.url)
        except (OSError, UnicodeError, ValueError):
            continue
        evidence: list[SiteEvidence] = []
        score = 0
        search_text = f"{material.title} {material.snippet}"
        if _contains_name(search_text, company):
            score += 1
            evidence.append(SiteEvidence("search_name", material.url, "搜尋結果含公司名"))
        if _context_matches(search_text, context) >= 2:
            score += 1
            evidence.append(SiteEvidence("search_context", material.url, "搜尋摘要符合產品描述"))
        if _contains_name(html, company):
            score += 2
            evidence.append(SiteEvidence("site_name", material.url, "網站內容含公司名"))
        if _context_matches(html, context) >= 2:
            score += 1
            evidence.append(SiteEvidence("site_context", material.url, "網站內容符合產品描述"))
        if score >= 3:
            scored.append((score, material, tuple(evidence)))

    if not scored:
        raise OfficialSiteError("找不到可信的官方網站。請提供官網或重新搜尋。")
    scored.sort(key=lambda item: item[0], reverse=True)
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        raise AmbiguousOfficialSiteError(
            "找到多個可能的同名公司，請選擇正確官網。"
        )
    _score, winner, evidence = scored[0]
    return OfficialSite(
        company,
        winner.url,
        _hostname(winner.url),
        "high",
        evidence,
    )


def _download_html(url: str) -> str:
    context = ssl.create_default_context(cafile=certifi.where())
    request = Request(
        url,
        headers={"User-Agent": "daibu-content-brain/1.0"},
    )
    with urlopen(request, timeout=15, context=context) as response:
        return response.read(MAX_HTML_BYTES).decode("utf-8", errors="replace")
