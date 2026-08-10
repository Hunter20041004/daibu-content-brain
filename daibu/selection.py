import sqlite3

from daibu import db
from daibu.fetch import collector
from daibu.llm.base import Idea, LLMProvider
from daibu.models import Material, Source, StoredIdea, Theme


class NoVerifiedCompanyCandidatesError(RuntimeError):
    pass


def _normalize_identity(value: str) -> str:
    return value.strip().casefold()


def visible_company_profile_ideas(
    ideas: list[StoredIdea],
) -> list[StoredIdea]:
    keeper_ids: set[int] = set()
    seen_companies: set[tuple[int | None, str]] = set()
    for idea in sorted(ideas, key=lambda item: (item.created_at, item.id)):
        company_key = _normalize_identity(idea.company)
        if not company_key:
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


def generate_for_theme(
    conn: sqlite3.Connection,
    theme: Theme,
    provider: LLMProvider,
    sources: list[Source],
) -> list[int]:
    materials = collector.collect(theme, sources)
    if theme.content_kind == "company_profile":
        avoid_titles, avoid_companies = db.get_idea_exclusions(
            conn,
            theme.id,
        )
        generated = provider.generate_ideas(
            theme.name,
            materials,
            theme.n_ideas,
            avoid_titles=avoid_titles,
            content_kind=theme.content_kind,
            avoid_companies=avoid_companies,
        )
    else:
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
        generated = accepted
        if not generated:
            raise NoVerifiedCompanyCandidatesError(
                "這次沒有找到可核對的公司；只有新的公司才會建立候選。"
            )
    return [
        db.add_idea(conn, theme.id, idea, status="候選")
        for idea in generated
    ]
