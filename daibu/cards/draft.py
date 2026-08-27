import sqlite3
from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING

from daibu import db
from daibu.cards import pages
from daibu.llm import base, prompt
from daibu.models import StoredIdea

if TYPE_CHECKING:
    from daibu.cards.schema import CarouselDraft, VerifiedSource


def _with_fixed_brand_cta(draft: "CarouselDraft") -> "CarouselDraft":
    normalized_pages = []
    for page in draft.pages:
        if page.page_type != "cta" or len(page.sections) != 1:
            normalized_pages.append(page)
            continue
        section = replace(
            page.sections[0],
            text=pages.CTA_TEXT,
            source_ids=(),
            evidence_quotes=(),
        )
        normalized_pages.append(
            replace(page, sections=(section,), source_label="")
        )
    return replace(draft, pages=tuple(normalized_pages))


def _retry_prompt(original_prompt: str, error: ValueError) -> str:
    validation_feedback = str(error)[:2000]
    return f"""{original_prompt}

上一次輸出未通過格式與查證規則。請依照下列問題重新輸出完整六頁 JSON；
不要解釋、不要沿用錯誤內容，也不要增加第七頁：
{validation_feedback}
"""


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
    current_prompt = prompt_text
    for attempt in range(2):
        raw = generate_text(current_prompt)
        try:
            result = _with_fixed_brand_cta(
                prompt.decode_carousel(raw, sources)
            )
            validate_grounded_draft(result)
        except ValueError as error:
            if attempt == 1:
                raise base.LLMResponseError(raw) from error
            current_prompt = _retry_prompt(prompt_text, error)
            continue
        return result
    raise AssertionError("輪播產生重試流程未回傳結果")
