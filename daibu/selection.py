import sqlite3
from datetime import datetime
from typing import Callable

from daibu import company_eligibility, db, startup_discovery
from daibu.fetch import collector, search
from daibu.llm.base import Idea, LLMProvider
from daibu.models import CompanyLead, Material, Source, StoredIdea, Theme


class NoVerifiedCompanyCandidatesError(RuntimeError):
    pass


class CompanyEligibilityVerificationError(RuntimeError):
    pass


def _normalize_identity(value: str) -> str:
    return value.strip().casefold()


def visible_company_profile_ideas(
    ideas: list[StoredIdea],
    disallowed_company_keys: set[str] | None = None,
) -> list[StoredIdea]:
    disallowed = disallowed_company_keys or set()
    keeper_ids: set[int] = set()
    seen_companies: set[tuple[int | None, str]] = set()
    for idea in sorted(ideas, key=lambda item: (item.created_at, item.id)):
        company_key = _normalize_identity(idea.company)
        if not company_key:
            continue
        if company_key in disallowed:
            continue
        series_company = (idea.theme_id, company_key)
        if series_company in seen_companies:
            continue
        seen_companies.add(series_company)
        keeper_ids.add(idea.id)
    return [idea for idea in ideas if idea.id in keeper_ids]


def _is_verified_company_candidate(
    idea: Idea,
    materials: list[Material],
) -> bool:
    if not idea.company.strip() or not idea.title.strip():
        return False
    if not idea.source_url.startswith("https://"):
        return False
    if not idea.source_excerpt.strip():
        return False
    return any(
        material.url == idea.source_url
        and idea.source_excerpt in material.snippet
        for material in materials
    )


def _lead_material(lead: CompanyLead) -> Material:
    facts = [lead.description]
    if lead.founded_year is not None:
        facts.append(f"Founded {lead.founded_year}")
    if lead.batch_or_cohort:
        facts.append(lead.batch_or_cohort)
    return Material(
        title=lead.company,
        url=lead.discovery_url,
        snippet=" | ".join(part for part in facts if part),
    )


def generate_for_theme(
    conn: sqlite3.Connection,
    theme: Theme,
    provider: LLMProvider,
    sources: list[Source],
    warning_sink: Callable[[str], None] | None = None,
) -> list[int]:
    if theme.content_kind == "company_profile":
        avoid_titles, avoid_companies = db.get_idea_exclusions(
            conn,
            theme.id,
        )
        eligibility_cache = db.get_company_eligibilities(conn)
        avoided_keys = {
            _normalize_identity(company) for company in avoid_companies
        }
        for record in eligibility_cache.values():
            if record.verdict not in {"ineligible", "unknown"}:
                continue
            if record.company_key in avoided_keys:
                continue
            avoid_companies.append(record.company)
            avoided_keys.add(record.company_key)
        result = startup_discovery.discover(
            [source for source in sources if source.id in theme.source_ids],
            excluded_company_keys=set(avoided_keys),
            limit=theme.n_ideas,
            warning_sink=warning_sink,
        )
        materials = [_lead_material(lead) for lead in result.leads]
        generated = provider.generate_ideas(
            theme.name,
            materials,
            theme.n_ideas,
            avoid_titles=avoid_titles,
            content_kind=theme.content_kind,
            avoid_companies=avoid_companies,
        )
    else:
        materials = collector.collect(theme, sources)
        avoid_titles = db.get_rejected_titles(conn, theme.id)
        avoid_companies = []
        generated = provider.generate_ideas(
            theme.name,
            materials,
            theme.n_ideas,
            avoid_titles=avoid_titles,
            content_kind=theme.content_kind,
        )
    if theme.content_kind == "company_profile":
        seen_companies = {
            _normalize_identity(company) for company in avoid_companies
        }
        seen_titles = {
            _normalize_identity(title) for title in avoid_titles
        }
        accepted: list[Idea] = []
        for idea in generated:
            company_key = _normalize_identity(idea.company)
            title_key = _normalize_identity(idea.title)
            if not _is_verified_company_candidate(idea, materials):
                continue
            if company_key in seen_companies or title_key in seen_titles:
                continue
            accepted.append(idea)
            seen_companies.add(company_key)
            seen_titles.add(title_key)
        cached_eligible: set[str] = set()
        unseen: dict[str, str] = {}
        for idea in accepted:
            company_key = _normalize_identity(idea.company)
            cached = eligibility_cache.get(company_key)
            if cached is None:
                unseen.setdefault(company_key, idea.company.strip())
            elif cached.verdict == "eligible":
                cached_eligible.add(company_key)
        fresh: dict[str, object] = {}
        if unseen:
            try:
                fresh = company_eligibility.evaluate_companies(
                    list(unseen.values()),
                    search.search_web,
                    getattr(provider, "generate_text", lambda _prompt: ""),
                    current_year=datetime.now().year,
                )
            except Exception as error:
                raise CompanyEligibilityVerificationError(
                    "公司新創資格查核失敗，這次沒有新增候選，請稍後再試。"
                ) from error
            for record in fresh.values():
                db.save_company_eligibility(conn, record)
        generated = [
            idea
            for idea in accepted
            if _normalize_identity(idea.company) in cached_eligible
            or getattr(
                fresh.get(_normalize_identity(idea.company)),
                "verdict",
                None,
            )
            == "eligible"
        ]
        if not generated:
            raise NoVerifiedCompanyCandidatesError(
                "找到公司，但沒有符合本系列資格的公司。"
            )
    return [
        db.add_idea(conn, theme.id, idea, status="候選")
        for idea in generated
    ]
