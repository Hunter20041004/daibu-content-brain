from dataclasses import replace

from daibu.models import CompanyLead, TaggedFeedEntry


BLOCKED_NEWS_TERMS = (
    "ipo",
    "goes public",
    "go public",
    "acquired",
    "acquisition completed",
)


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
