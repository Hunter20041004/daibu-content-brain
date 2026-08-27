from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import sqlite3

from daibu import db
from daibu.cards import layout_repository, layout_validation, render
from daibu.cards.editor_payload import apply_editor_values
from daibu.cards.schema import (
    BrandAsset,
    CarouselDraft,
    DraftValidationError,
    validate_draft,
)


@dataclass(frozen=True)
class EditorIssue:
    page_type: str | None
    field_key: str | None
    message: str


@dataclass(frozen=True)
class SaveResult:
    draft: CarouselDraft
    revision: int
    issues: tuple[EditorIssue, ...]


_ELEMENT_FIELDS = {
    "heading": "heading",
    "positioning": "section.0.text",
    "facts": "section.1.text",
    "caution": "section.2.text",
    "before-title": "diagram.0.title",
    "before-copy": "diagram.0.text",
    "after-title": "diagram.2.title",
    "after-copy": "diagram.2.text",
    "summary": "section.2.text",
    "thesis": "section.0.text",
    "question": "section.1.text",
    "invitation": "section.2.text",
}


def _field_key(page_type: str, element_id: str) -> str:
    suffix = _ELEMENT_FIELDS.get(element_id)
    if suffix is None and element_id.startswith("stage-"):
        suffix = f"diagram.{int(element_id.removeprefix('stage-')) - 1}.text"
    if suffix is None and element_id.startswith("step-"):
        suffix = f"diagram.{int(element_id.removeprefix('step-')) - 1}.text"
    if suffix is None and element_id.startswith("signal-"):
        suffix = f"diagram.{int(element_id.removeprefix('signal-')) - 1}.text"
    return f"page.{page_type}.{suffix or 'heading'}"


def _conflict_result(
    draft: CarouselDraft,
    revision: int,
) -> SaveResult:
    return SaveResult(
        draft,
        revision,
        (
            EditorIssue(
                None,
                None,
                "其他畫面更新了這份草稿，請重新整理後再編輯。",
            ),
        ),
    )


def save_editor_payload(
    conn: sqlite3.Connection,
    idea_id: int,
    saved_draft: CarouselDraft,
    payload: Mapping[str, object],
    company: str,
    brand_asset: BrandAsset | None,
) -> SaveResult:
    """Validate all six pages, then atomically save one content revision."""
    metadata = db.get_carousel_draft_meta(conn, idea_id)
    if metadata is None:
        return SaveResult(
            saved_draft,
            0,
            (EditorIssue(None, None, "這份草稿尚未綁定模板版本。"),),
        )
    revision = payload.get("revision")
    values = payload.get("values")
    if revision != metadata.content_revision:
        return _conflict_result(saved_draft, metadata.content_revision)
    if not isinstance(values, Mapping):
        return SaveResult(
            saved_draft,
            metadata.content_revision,
            (EditorIssue(None, None, "儲存內容格式不正確。"),),
        )

    try:
        edited = apply_editor_values(saved_draft, values)
        validate_draft(edited)
    except DraftValidationError as error:
        return SaveResult(
            error.draft,
            metadata.content_revision,
            tuple(
                EditorIssue(
                    page_type,
                    f"page.{page_type}.heading" if page_type else None,
                    message,
                )
                for page_type, message in error.issues
            ),
        )
    except (TypeError, ValueError) as error:
        return SaveResult(
            saved_draft,
            metadata.content_revision,
            (EditorIssue(None, None, str(error)),),
        )

    version = layout_repository.get_version(conn, metadata.template_version_id)
    rendered = render.draft_html_pages(
        edited,
        company,
        brand_asset,
        version.layout,
        allow_logo_placeholder=True,
    )
    layout_issues = layout_validation.inspect_pages(rendered)
    if layout_issues:
        return SaveResult(
            edited,
            metadata.content_revision,
            tuple(
                EditorIssue(
                    issue.page_type,
                    _field_key(issue.page_type, issue.element_id),
                    issue.message,
                )
                for issue in layout_issues
            ),
        )

    try:
        revised_metadata = db.save_carousel_draft(
            conn,
            idea_id,
            edited,
            expected_revision=metadata.content_revision,
        )
    except db.RevisionConflict:
        current = db.get_carousel_draft_meta(conn, idea_id)
        return _conflict_result(
            saved_draft,
            current.content_revision if current else metadata.content_revision,
        )
    assert revised_metadata is not None
    return SaveResult(edited, revised_metadata.content_revision, ())
