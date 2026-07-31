import sqlite3
from collections.abc import Callable
from typing import TYPE_CHECKING

from daibu import db
from daibu.llm import base, prompt
from daibu.models import StoredIdea

if TYPE_CHECKING:
    from daibu.cards.schema import CarouselDraft, VerifiedSource


def generate(
    conn: sqlite3.Connection,
    idea: StoredIdea,
    sources: tuple["VerifiedSource", ...],
    generate_text: Callable[[str], str],
) -> "CarouselDraft":
    result = create(idea, sources, generate_text)
    db.save_carousel_draft(conn, idea.id, result)
    return result


def create(
    idea: StoredIdea,
    sources: tuple["VerifiedSource", ...],
    generate_text: Callable[[str], str],
) -> "CarouselDraft":
    """Generate and validate a draft without mutating persistent state."""
    from daibu.cards.schema import (
        CarouselDraft,
        validate_company_headings,
        validate_grounded_draft,
        validate_sources,
    )

    if not idea.company.strip():
        raise ValueError("這則題目沒有公司名，無法產生輪播草稿")
    if not sources:
        raise ValueError("至少需要一筆已查證來源")
    validate_sources(sources)

    prompt_text = prompt.build_carousel(
        idea.company,
        idea.title,
        idea.angle,
        sources,
    )
    raw = generate_text(prompt_text)
    try:
        result = prompt.parse_carousel(raw, sources)
        validate_grounded_draft(result)
        validate_company_headings(result, idea.company)
    except ValueError as error:
        raise base.LLMResponseError(raw) from error
    return result
