import sqlite3
from collections.abc import Callable
from typing import TYPE_CHECKING

from daibu import db
from daibu.cards import pages as page_contract
from daibu.llm import base, prompt
from daibu.models import StoredIdea

if TYPE_CHECKING:
    from daibu.cards.schema import CarouselDraft, CarouselPage, VerifiedSource


def _pages_in_expected_slots(
    draft: "CarouselDraft",
) -> dict[str, "CarouselPage"]:
    expected = enumerate(page_contract.PAGE_TYPES, start=1)
    return {
        page_type: page
        for (page_no, page_type), page in zip(expected, draft.pages)
        if page.page_no == page_no and page.page_type == page_type
    }


def generate(
    conn: sqlite3.Connection,
    idea: StoredIdea,
    sources: tuple["VerifiedSource", ...],
    generate_text: Callable[[str], str],
) -> "CarouselDraft":
    from daibu.cards.schema import (
        CarouselDraft,
        DraftValidationError,
        validate_draft,
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
    last_raw = ""
    last_error: ValueError | None = None
    request_text = prompt_text
    failed_draft: CarouselDraft | None = None
    repair_page_types: frozenset[str] = frozenset()
    for attempt in range(2):
        last_raw = generate_text(request_text)
        try:
            if attempt == 1 and failed_draft is not None:
                repaired = prompt.decode_carousel(last_raw, sources)
                original_by_type = _pages_in_expected_slots(failed_draft)
                repaired_by_type = _pages_in_expected_slots(repaired)
                merged_pages = []
                for page_type in page_contract.PAGE_TYPES:
                    candidates = (
                        repaired_by_type
                        if page_type in repair_page_types
                        else original_by_type
                    )
                    page = candidates.get(page_type)
                    if page is None:
                        raise ValueError(
                            f"修復回覆缺少可安全合併的 {page_type} 頁"
                        )
                    merged_pages.append(page)
                result = CarouselDraft(
                    sources,
                    tuple(merged_pages),
                )
                validate_draft(result)
            else:
                result = prompt.parse_carousel(last_raw, sources)
            db.save_carousel_draft(conn, idea.id, result)
            return result
        except ValueError as error:
            last_error = error
            if attempt == 0:
                if isinstance(error, DraftValidationError):
                    failed_draft = error.draft
                    valid_slots = _pages_in_expected_slots(failed_draft)
                    repair_page_types = frozenset(
                        set(error.page_types)
                        | (
                            set(page_contract.PAGE_TYPES)
                            - set(valid_slots)
                        )
                    )
                request_text = prompt.build_carousel_repair(
                    prompt_text,
                    last_raw,
                    error,
                )
    raise base.LLMResponseError(last_raw) from last_error
