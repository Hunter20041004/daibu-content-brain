import sqlite3
from datetime import datetime
from typing import Callable

from daibu import company_diversity, company_eligibility, db, startup_discovery
from daibu.fetch import collector, search
from daibu.llm.base import (
    Idea,
    LLMProvider,
    LLMQuotaError,
    LLMResponseError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from daibu.models import CompanyLead, Material, Source, StoredIdea, Theme


class NoVerifiedCompanyCandidatesError(RuntimeError):
    pass


class CompanyEligibilityVerificationError(RuntimeError):
    pass


class CompanyClassificationError(RuntimeError):
    pass


class InsufficientCompanyDiversityError(RuntimeError):
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


def _evaluate_selected_leads(
    conn: sqlite3.Connection,
    provider: LLMProvider,
    leads: list[CompanyLead],
) -> set[str]:
    cache = db.get_company_eligibilities(conn)
    unseen = [
        lead
        for lead in leads
        if _normalize_identity(lead.company) not in cache
    ]
    if unseen:
        try:
            research_text = getattr(
                provider,
                "generate_research_text",
                None,
            ) or getattr(provider, "generate_text", lambda _prompt: "")
            fresh = company_eligibility.evaluate_companies(
                unseen,
                search.search_web,
                research_text,
                current_year=datetime.now().year,
            )
        except (LLMQuotaError, LLMTimeoutError, LLMUnavailableError):
            raise
        except Exception as error:
            raise CompanyEligibilityVerificationError(
                "公司新創資格查核失敗，這次沒有新增候選，請稍後再試。"
            ) from error
        for record in fresh.values():
            db.save_company_eligibility(conn, record)
        cache.update(fresh)
    return {
        key
        for key, record in cache.items()
        if record.verdict == "eligible"
    }


def _select_diverse_verified_companies(
    conn: sqlite3.Connection,
    provider: LLMProvider,
    leads: list[CompanyLead],
    status_sink: Callable[[str], None] | None,
) -> tuple[company_diversity.ClassifiedCompany, ...]:
    classified: list[company_diversity.ClassifiedCompany] = []
    disallowed: set[str] = set()
    previous_end = 0
    for end in (15, 25, 40):
        batch = leads[previous_end:min(end, len(leads))]
        if not batch:
            break
        if status_sink:
            if end == 15:
                status_sink("正在替前 15 家公司分主類別…")
            else:
                status_sink(
                    f"目前組合太集中，正在查看更多公司（最多 {end} 家）…"
                )
        try:
            raw = provider.generate_research_text(
                company_diversity.build_classification_prompt(batch)
            )
            classified.extend(
                company_diversity.parse_classifications(raw, batch)
            )
        except Exception as error:
            raise CompanyClassificationError(
                "公司主類別分類暫時失敗，這次沒有新增候選。"
            ) from error
        previous_end = end
        while True:
            pool = [
                item
                for item in classified
                if _normalize_identity(item.lead.company) not in disallowed
            ]
            selected = company_diversity.select_diverse_companies(pool)
            if selected is None:
                break
            eligible = _evaluate_selected_leads(
                conn,
                provider,
                [item.lead for item in selected],
            )
            rejected = {
                _normalize_identity(item.lead.company)
                for item in selected
                if _normalize_identity(item.lead.company) not in eligible
            }
            if not rejected:
                return selected
            disallowed.update(rejected)
    inspected = min(len(leads), 40)
    usable = [
        item
        for item in classified
        if _normalize_identity(item.lead.company) not in disallowed
    ]
    raise InsufficientCompanyDiversityError(
        company_diversity.describe_shortage(usable, inspected)
    )


def _generate_diverse_company_ideas(
    conn: sqlite3.Connection,
    theme: Theme,
    provider: LLMProvider,
    sources: list[Source],
    warning_sink: Callable[[str], None] | None,
    status_sink: Callable[[str], None] | None,
) -> list[int]:
    avoid_titles, avoid_companies = db.get_idea_exclusions(conn, theme.id)
    eligibility_cache = db.get_company_eligibilities(conn)
    avoided_keys = {
        _normalize_identity(company) for company in avoid_companies
    }
    for record in eligibility_cache.values():
        if record.verdict not in {"ineligible", "unknown"}:
            continue
        if record.company_key not in avoided_keys:
            avoid_companies.append(record.company)
            avoided_keys.add(record.company_key)
    result = startup_discovery.discover(
        [source for source in sources if source.id in theme.source_ids],
        excluded_company_keys=set(avoided_keys),
        limit=40,
        warning_sink=warning_sink,
    )
    selected = _select_diverse_verified_companies(
        conn,
        provider,
        list(result.leads),
        status_sink,
    )
    materials = [_lead_material(item.lead) for item in selected]
    generated = provider.generate_ideas(
        theme.name,
        materials,
        5,
        avoid_titles=avoid_titles,
        content_kind=theme.content_kind,
        avoid_companies=avoid_companies,
    )
    expected = {
        _normalize_identity(item.lead.company) for item in selected
    }
    material_by_company = {
        _normalize_identity(material.title): material for material in materials
    }
    seen_titles = {_normalize_identity(title) for title in avoid_titles}
    accepted: list[Idea] = []
    for idea in generated:
        company_key = _normalize_identity(idea.company)
        title_key = _normalize_identity(idea.title)
        material = material_by_company.get(company_key)
        if material is None or not title_key or title_key in seen_titles:
            continue
        if (
            idea.source_url != material.url
            or not idea.source_excerpt.strip()
            or idea.source_excerpt not in material.snippet
        ):
            continue
        accepted.append(idea)
        seen_titles.add(title_key)
    actual = [_normalize_identity(idea.company) for idea in accepted]
    if len(accepted) != 5 or len(set(actual)) != 5 or set(actual) != expected:
        raise LLMResponseError("公司候選數量或公司對應不完整")
    return db.add_ideas_atomic(conn, theme.id, accepted, status="候選")


def generate_for_theme(
    conn: sqlite3.Connection,
    theme: Theme,
    provider: LLMProvider,
    sources: list[Source],
    warning_sink: Callable[[str], None] | None = None,
    status_sink: Callable[[str], None] | None = None,
) -> list[int]:
    if theme.content_kind == "company_profile" and theme.n_ideas == 5:
        return _generate_diverse_company_ideas(
            conn,
            theme,
            provider,
            sources,
            warning_sink,
            status_sink,
        )
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
        lead_by_company = {
            _normalize_identity(lead.company): lead for lead in result.leads
        }
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
        unseen: dict[str, str | CompanyLead] = {}
        for idea in accepted:
            company_key = _normalize_identity(idea.company)
            cached = eligibility_cache.get(company_key)
            if cached is None:
                unseen.setdefault(
                    company_key,
                    lead_by_company.get(company_key, idea.company.strip()),
                )
            elif cached.verdict == "eligible":
                cached_eligible.add(company_key)
        fresh: dict[str, object] = {}
        if unseen:
            try:
                research_text = getattr(
                    provider,
                    "generate_research_text",
                    None,
                ) or getattr(
                    provider,
                    "generate_text",
                    lambda _prompt: "",
                )
                fresh = company_eligibility.evaluate_companies(
                    list(unseen.values()),
                    search.search_web,
                    research_text,
                    current_year=datetime.now().year,
                )
            except (LLMQuotaError, LLMTimeoutError, LLMUnavailableError):
                raise
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
