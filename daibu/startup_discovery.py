import logging
from dataclasses import replace
from typing import Callable

from daibu.fetch import rss
from daibu.fetch import startup_directories as directories
from daibu.models import (
    CompanyLead,
    DiscoveryResult,
    DiscoveryStats,
    Source,
    TaggedFeedEntry,
)


logger = logging.getLogger(__name__)


BLOCKED_NEWS_TERMS = (
    "ipo",
    "goes public",
    "go public",
    "acquired",
    "acquisition completed",
)
DIRECTORY_READERS = {
    "YC Launches": "fetch_yc_launches",
    "a16z Speedrun Companies": "fetch_speedrun_companies",
}


class NoAvailableStartupSourcesError(RuntimeError):
    pass


class AllStartupCompaniesRepeatedError(RuntimeError):
    pass


def _normal(value: str) -> str:
    return " ".join(value.casefold().split())


def _eligible_news(entry: TaggedFeedEntry) -> bool:
    tags = {_normal(tag) for tag in entry.tags}
    text = _normal(f"{entry.title} {entry.snippet}")
    return (
        "ai" in tags
        and "startups" in tags
        and not any(term in text for term in BLOCKED_NEWS_TERMS)
    )


def _news_for(
    lead: CompanyLead,
    entries: list[TaggedFeedEntry],
) -> TaggedFeedEntry | None:
    company = _normal(lead.company)
    if len(company) < 4:
        return None
    return next(
        (
            entry
            for entry in entries
            if _eligible_news(entry)
            and company in _normal(f"{entry.title} {entry.snippet}")
        ),
        None,
    )


def mix_leads(
    directory_leads: tuple[CompanyLead, ...],
    news_entries: list[TaggedFeedEntry],
    limit: int = 3,
) -> tuple[CompanyLead, ...]:
    news_enriched = []
    directory_only = []
    for lead in directory_leads:
        news = _news_for(lead, news_entries)
        if news and not news_enriched:
            news_enriched.append(
                replace(
                    lead,
                    description=news.snippet,
                    discovery_url=news.url,
                    published_at=news.published_at,
                    source_name="TechCrunch Startups",
                )
            )
        else:
            directory_only.append(lead)
    return tuple((news_enriched + directory_only)[:limit])


def _enrich_yc_candidates(
    leads: list[CompanyLead],
    warnings: list[str],
    warning_sink: Callable[[str], None] | None,
) -> list[CompanyLead]:
    enriched = []
    for lead in leads:
        if lead.source_name != "YC Launches":
            enriched.append(lead)
            continue
        try:
            enriched.append(directories.enrich_yc_company(lead))
        except Exception:
            message = "YC Companies 暫時讀不到，已跳過該公司。"
            warnings.append(message)
            if warning_sink:
                warning_sink(message)
    return enriched


def _fetch_news_source(
    sources: list[Source],
    warnings: list[str],
    warning_sink: Callable[[str], None] | None,
) -> list[TaggedFeedEntry]:
    source = next(
        (
            item
            for item in sources
            if item.enabled and item.name == "TechCrunch Startups"
        ),
        None,
    )
    if source is None:
        return []
    try:
        return rss.fetch_tagged(source.url)
    except Exception as error:
        logger.warning(
            "startup_source_failed source=%s category=%s",
            source.name,
            type(error).__name__,
        )
        message = (
            "TechCrunch Startups 暫時讀不到，已使用公司目錄。"
        )
        warnings.append(message)
        if warning_sink:
            warning_sink(message)
        return []


def discover(
    sources: list[Source],
    excluded_company_keys: set[str],
    limit: int = 3,
    warning_sink: Callable[[str], None] | None = None,
) -> DiscoveryResult:
    warnings: list[str] = []
    directory_batches: list[list[CompanyLead]] = []
    fetched: list[tuple[str, int]] = []
    for source in sources:
        reader_name = DIRECTORY_READERS.get(source.name)
        if not source.enabled or reader_name is None:
            continue
        try:
            items = getattr(directories, reader_name)(source.url)
        except Exception as error:
            logger.warning(
                "startup_source_failed source=%s category=%s",
                source.name,
                type(error).__name__,
            )
            message = f"{source.name} 暫時讀不到，已改用其他來源。"
            warnings.append(message)
            if warning_sink:
                warning_sink(message)
            continue
        directory_batches.append(items)
        fetched.append((source.name, len(items)))
    directory_leads = [
        batch[index]
        for index in range(max(map(len, directory_batches), default=0))
        for batch in directory_batches
        if index < len(batch)
    ]
    if not directory_leads:
        raise NoAvailableStartupSourcesError(
            "目前沒有可用的公司來源，請稍後再試。"
        )
    unique = []
    seen = set(excluded_company_keys)
    for lead in directory_leads:
        key = _normal(lead.company)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(lead)
    if not unique:
        raise AllStartupCompaniesRepeatedError(
            "這批來源裡的公司都介紹過了。"
        )
    enriched = _enrich_yc_candidates(unique[:limit], warnings, warning_sink)
    allowed = [
        lead
        for lead in enriched
        if lead.ownership_status not in {"public", "acquired"}
    ]
    leads = mix_leads(
        tuple(allowed),
        _fetch_news_source(sources, warnings, warning_sink),
        limit=limit,
    )
    result = DiscoveryResult(
        leads=leads,
        warnings=tuple(warnings),
        stats=DiscoveryStats(
            fetched_by_source=tuple(fetched),
            filtered_duplicate=len(directory_leads) - len(unique),
            filtered_status=len(enriched) - len(allowed),
            matched_news=sum(
                lead.source_name == "TechCrunch Startups" for lead in leads
            ),
        ),
    )
    logger.info(
        "startup_discovery fetched=%s duplicate=%d status=%d news=%d final=%d",
        dict(result.stats.fetched_by_source),
        result.stats.filtered_duplicate,
        result.stats.filtered_status,
        result.stats.matched_news,
        len(result.leads),
    )
    return result
