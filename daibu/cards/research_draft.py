"""Orchestrate trusted company research and one atomic grounded draft save."""

import sqlite3
from collections.abc import Callable, Iterable
from urllib.parse import urlsplit

from daibu import db
from daibu.cards import draft
from daibu.cards.schema import BrandAsset, CarouselDraft
from daibu.fetch import company_research
from daibu.models import Material, SourceSuggestion, StoredIdea


def _official_domains(asset: BrandAsset | None) -> tuple[str, ...]:
    if asset is None:
        return ()
    hostname = urlsplit(asset.official_source_url).hostname or ""
    return (hostname,) if hostname else ()


def generate(
    conn: sqlite3.Connection,
    idea: StoredIdea,
    configured_domains: Iterable[str],
    brand_asset: BrandAsset | None,
    search_fn: Callable[..., list[Material]] | None,
    fetch_fn: Callable[[str], SourceSuggestion] | None,
    generate_text: Callable[[str], str],
    *,
    reuse_existing_sources: bool = True,
) -> CarouselDraft:
    """Research fully, generate once, then replace sources and pages together."""
    researched = company_research.research(
        idea.company,
        (
            db.get_idea_sources(conn, idea.id)
            if reuse_existing_sources
            else ()
        ),
        configured_domains,
        _official_domains(brand_asset),
        search_fn=search_fn,
        fetch_fn=fetch_fn,
    )
    result = draft.create(idea, researched.sources, generate_text)
    db.save_researched_draft(conn, idea.id, result)
    return result
