"""Research one company without leaving explicitly trusted domains."""

import re
from dataclasses import dataclass
from collections.abc import Callable, Iterable
from urllib.parse import urlsplit, urlunsplit

from daibu.cards import sources as card_sources
from daibu.cards.schema import VerifiedSource, validate_sources
from daibu.fetch import page, search
from daibu.models import Material, SourceSuggestion

TRUSTED_EDITORIAL_DOMAINS = (
    "techcrunch.com",
    "venturebeat.com",
    "ycombinator.com",
    "a16z.com",
    "producthunt.com",
    "inside.com.tw",
    "reuters.com",
    "prnewswire.com",
    "businesswire.com",
)


@dataclass(frozen=True)
class ResearchResult:
    sources: tuple[VerifiedSource, ...]
    failures: tuple[str, ...]


def _domain(value: str) -> str:
    parsed = urlsplit(value if "://" in value else f"https://{value}")
    hostname = (parsed.hostname or "").lower()
    return hostname.removeprefix("www.")


def _domains(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(filter(None, (_domain(value) for value in values))))


def _canonical_url(value: str) -> str:
    parsed = urlsplit(value)
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            "",
            "",
        )
    )


def _mentions_company(company: str, *values: str) -> bool:
    needle = re.sub(r"[^a-z0-9一-鿿]+", "", company.casefold())
    haystack = re.sub(
        r"[^a-z0-9一-鿿]+",
        "",
        " ".join(values).casefold(),
    )
    return bool(needle and needle in haystack)


def _is_official(hostname: str, official_domains: list[str]) -> bool:
    return any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in official_domains
    )


def research(
    company: str,
    seed_sources: tuple[VerifiedSource, ...],
    configured_domains: Iterable[str],
    official_domains: Iterable[str],
    search_fn: Callable[..., list[Material]] | None = None,
    fetch_fn: Callable[[str], SourceSuggestion] | None = None,
) -> ResearchResult:
    """Return up to eight relevant, verified sources for ``company``."""
    if not company.strip():
        raise ValueError("這則題目沒有公司名，無法搜尋資料。")
    validate_sources(seed_sources)
    official = _domains(official_domains)
    allowed = _domains(
        (
            *configured_domains,
            *official,
            *TRUSTED_EDITORIAL_DOMAINS,
        )
    )
    do_search = search_fn or search.search
    do_fetch = fetch_fn or page.fetch_suggestion
    queries = (
        f'"{company}" company profile',
        f'"{company}" AI product how it works',
        f'"{company}" customers results funding',
    )
    collected = list(seed_sources)
    seen = {_canonical_url(source.url) for source in collected}
    failures: list[str] = []

    for query in queries:
        try:
            materials = do_search(
                query,
                allowed_domains=allowed,
                limit=3,
            )
        except (RuntimeError, ValueError, OSError) as error:
            failures.append(f"{query}：{error}")
            continue
        for material in materials:
            if len(collected) >= card_sources.MAX_SOURCES:
                break
            if not search._is_allowed(material.url, allowed):
                continue
            canonical = _canonical_url(material.url)
            if canonical in seen:
                continue
            try:
                suggestion = do_fetch(material.url)
            except (RuntimeError, ValueError, OSError) as error:
                failures.append(f"{material.url}：{error}")
                continue
            if not _mentions_company(
                company,
                material.title,
                suggestion.excerpt,
            ):
                continue
            if not all(
                (
                    suggestion.publisher.strip(),
                    suggestion.published_at.strip(),
                    suggestion.excerpt.strip(),
                )
            ):
                failures.append(f"{material.url}：來源資料不完整")
                continue
            hostname = _domain(suggestion.url)
            collected.append(
                VerifiedSource(
                    card_sources.next_source_id(tuple(collected)),
                    suggestion.publisher.strip(),
                    suggestion.published_at.strip(),
                    suggestion.url.strip(),
                    suggestion.excerpt.strip(),
                    (
                        "official"
                        if _is_official(hostname, official)
                        else "third_party"
                    ),
                )
            )
            seen.add(canonical)

    result = tuple(collected)
    if not result:
        raise ValueError(
            "在可信網域找不到可驗證的公司資料。"
            f"已搜尋：{'、'.join(allowed)}。"
            "請手動新增來源後再試。"
        )
    validate_sources(result)
    return ResearchResult(result, tuple(failures))
