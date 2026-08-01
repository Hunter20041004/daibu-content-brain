import sqlite3

from daibu import db
from daibu.fetch import collector
from daibu.llm.base import Idea, LLMProvider
from daibu.models import Material, Source, Theme


class NoVerifiedCompanyCandidatesError(RuntimeError):
    pass


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
    avoid_titles = db.get_rejected_titles(conn, theme.id)
    generated = provider.generate_ideas(
        theme.name,
        materials,
        theme.n_ideas,
        avoid_titles=avoid_titles,
        content_kind=theme.content_kind,
    )
    if theme.content_kind == "company_profile":
        generated = [
            idea
            for idea in generated
            if _is_verified_company_candidate(idea, materials)
        ]
        if not generated:
            raise NoVerifiedCompanyCandidatesError(
                "這次沒有找到可核對的公司，沒有建立空候選。"
            )
    return [
        db.add_idea(conn, theme.id, idea, status="候選")
        for idea in generated
    ]
