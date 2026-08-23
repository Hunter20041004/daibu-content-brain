from __future__ import annotations

from dataclasses import dataclass
import sqlite3

import streamlit as st

from daibu import db
from daibu.cards import editor_service, layout_repository, render
from daibu.cards.editor_component import mount_content_editor
from daibu.cards.editor_payload import draft_to_editor_payload
from daibu.cards.schema import BrandAsset, CarouselDraft
from daibu.models import StoredIdea
from daibu.ui import queue_toast


@dataclass(frozen=True)
class ContentWorkbenchState:
    dirty: bool
    issues: tuple[editor_service.EditorIssue, ...]
    revision: int
    request_regenerate: bool = False
    request_research: bool = False


def render_content_workbench(
    conn: sqlite3.Connection,
    idea: StoredIdea,
    draft: CarouselDraft,
    brand_asset: BrandAsset | None,
) -> ContentWorkbenchState:
    """Mount the seven-page editor and coordinate its atomic save action."""
    metadata = db.get_carousel_draft_meta(conn, idea.id)
    if metadata is None:
        st.error("這份草稿尚未綁定模板版本，請重新產生草稿。")
        return ContentWorkbenchState(False, (), 0)

    version = layout_repository.get_version(
        conn,
        metadata.template_version_id,
    )
    previews = render.draft_html_pages(
        draft,
        idea.company,
        brand_asset,
        version.layout,
        allow_logo_placeholder=True,
        browser_preview=True,
    )
    payload = draft_to_editor_payload(
        draft,
        previews,
        metadata.content_revision,
        idea_id=idea.id,
    )
    issue_key = f"carousel-editor-issues-{idea.id}"
    payload["serverIssues"] = st.session_state.get(issue_key, [])

    st.markdown("#### 七頁內容編輯器")
    st.caption(
        "左側切換頁面，中間修改內容，右側同步預覽；"
        "查證來源與頁面結構會保持鎖定。"
    )
    event = mount_content_editor(payload, key=f"carousel-editor-{idea.id}")
    issues: tuple[editor_service.EditorIssue, ...] = ()
    if event.save_payload is not None:
        with st.spinner("正在檢查七頁文字與版面…"):
            saved = editor_service.save_editor_payload(
                conn,
                idea.id,
                draft,
                event.save_payload,
                idea.company,
                brand_asset,
            )
        issues = saved.issues
        if issues:
            st.session_state[issue_key] = [
                {
                    "pageType": issue.page_type,
                    "fieldKey": issue.field_key,
                    "message": issue.message,
                }
                for issue in issues
            ]
            for issue in issues:
                st.error(issue.message)
        else:
            st.session_state.pop(issue_key, None)
            queue_toast(st.session_state, "七頁變更已全部儲存。")
            st.rerun()

    return ContentWorkbenchState(
        event.dirty or bool(issues),
        issues,
        metadata.content_revision,
        event.request_regenerate,
        event.request_research,
    )
