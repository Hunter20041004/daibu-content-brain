import json

import httpx

from daibu.models import CompanyLead


AI_TAGS = {
    "ai",
    "artificial intelligence",
    "generative ai",
    "machine learning",
}


def _get_text(url: str) -> str:
    response = httpx.get(
        url,
        follow_redirects=True,
        timeout=15.0,
        headers={"User-Agent": "daibu-content-brain/1.0"},
    )
    response.raise_for_status()
    return response.text


def _is_ai_tagged(tags: tuple[str, ...]) -> bool:
    normalized = {tag.casefold() for tag in tags}
    return bool(normalized & AI_TAGS) or any(
        tag.startswith("ai ") for tag in normalized
    )


def fetch_yc_launches(
    url: str,
    pages: int = 2,
) -> list[CompanyLead]:
    leads = []
    for page in range(pages):
        payload = json.loads(_get_text(f"{url}?page={page}"))
        for hit in payload.get("hits", []):
            company = hit.get("company") or {}
            tags = tuple(str(tag) for tag in company.get("tags", []))
            if not _is_ai_tagged(tags):
                continue
            slug = str(company.get("slug", "")).strip()
            leads.append(
                CompanyLead(
                    company=str(company.get("name", "")).strip(),
                    description=str(hit.get("tagline", "")).strip(),
                    discovery_url=str(hit.get("search_path", "")).strip(),
                    profile_url=(
                        "https://www.ycombinator.com/companies/"
                        f"{slug}"
                    ),
                    official_url=str(company.get("url", "")).strip(),
                    batch_or_cohort=str(company.get("batch", "")).strip(),
                    tags=tags,
                    published_at=str(hit.get("created_at", "")).strip(),
                    source_name="YC Launches",
                )
            )
    return [
        lead
        for lead in leads
        if lead.company
        and lead.discovery_url.startswith("https://")
        and lead.profile_url.removeprefix(
            "https://www.ycombinator.com/companies/"
        )
    ]
