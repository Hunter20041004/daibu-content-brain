import html
import json
import re
from dataclasses import replace
from urllib.parse import quote, urlparse

import httpx

from daibu.models import CompanyLead


AI_TAGS = {
    "ai",
    "artificial intelligence",
    "generative ai",
    "machine learning",
}
SPEEDRUN_AI_TAGS = {
    "AI Agents",
    "AI Infra",
    "AI Models / Research",
    "AI Voice",
    "AI Generative Media",
}
SPEEDRUN_API_HOST = "speedrun-be.a16z.com"


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


def _yc_company_url(lead: CompanyLead) -> str:
    prefix = "https://www.ycombinator.com/companies/"
    if not lead.profile_url.startswith(prefix):
        raise ValueError("YC Companies 公司網址不合法")
    return lead.profile_url


def _extract_yc_company(html_text: str) -> dict[str, object]:
    match = re.search(r'data-page="([^"]+)"', html_text)
    if not match:
        raise ValueError("YC Companies 找不到公司資料")
    page = json.loads(html.unescape(match.group(1)))
    company = page.get("props", {}).get("company")
    if not isinstance(company, dict):
        raise ValueError("YC Companies 公司資料格式改變")
    return company


def enrich_yc_company(lead: CompanyLead) -> CompanyLead:
    company = _extract_yc_company(_get_text(_yc_company_url(lead)))
    status = str(company.get("ycdc_status", "")).casefold()
    mapped = status if status in {"active", "public", "acquired"} else "unknown"
    year = company.get("year_founded")
    return replace(
        lead,
        official_url=str(company.get("website", "")).strip(),
        founded_year=year if isinstance(year, int) else None,
        ownership_status=mapped,
        tags=tuple(str(tag) for tag in company.get("tags", [])) or lead.tags,
    )


def _speedrun_page_data(text: str) -> dict[str, object]:
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        text,
        re.DOTALL,
    )
    if not match:
        raise ValueError("Speedrun 找不到目錄資料")
    return json.loads(match.group(1))["props"]["pageProps"]


def _latest_speedrun_url(page: dict[str, object]) -> str:
    cohorts = page["cohorts"]
    companies = page["companies"]
    cohort = max(str(item["name"]) for item in cohorts)
    parsed = urlparse(str(companies["next"]))
    if parsed.scheme != "https" or parsed.netloc != SPEEDRUN_API_HOST:
        raise ValueError("Speedrun API 網址不合法")
    return (
        f"https://{SPEEDRUN_API_HOST}{parsed.path}"
        f"?limit=100&cohort={quote(cohort)}"
    )


def fetch_speedrun_companies(url: str) -> list[CompanyLead]:
    page = _speedrun_page_data(_get_text(url))
    newest = max(str(item["name"]) for item in page["cohorts"])
    rows = json.loads(_get_text(_latest_speedrun_url(page))).get("results", [])
    leads = []
    for row in rows:
        tags = tuple(str(item) for item in row.get("industries", []))
        if not SPEEDRUN_AI_TAGS.intersection(tags):
            continue
        slug = str(row.get("slug", "")).strip()
        profile_url = f"https://speedrun.a16z.com/companies/{slug}"
        year = row.get("founded_year")
        leads.append(
            CompanyLead(
                company=str(row.get("name", "")).strip(),
                description=str(row.get("preamble", "")).strip(),
                discovery_url=profile_url,
                profile_url=profile_url,
                official_url=str(row.get("website_url", "")).strip(),
                founded_year=year if isinstance(year, int) else None,
                batch_or_cohort=newest,
                tags=tags,
                source_name="a16z Speedrun Companies",
            )
        )
    return [lead for lead in leads if lead.company and lead.discovery_url]
