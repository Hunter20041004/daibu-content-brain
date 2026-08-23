from dataclasses import dataclass
import sqlite3

import streamlit as st

from daibu import db
from daibu.cards import layout_repository, render, template_editor_service
from daibu.cards.template_editor_component import mount_template_editor
from daibu.cards.template_editor_payload import template_editor_payload
from daibu.cards.template_stress import build_template_stress_cases


@dataclass(frozen=True)
class TemplateManagementState:
    theme_id: int | None
    version_id: int | None
    dirty: bool


def render_template_management(conn: sqlite3.Connection) -> TemplateManagementState:
    st.subheader("系列模板管理")
    st.caption("在受限制的畫布調整既有元素；每次儲存都建立新版本，不會暗中改掉舊貼文。")
    themes=db.get_themes(conn)
    if not themes:
        st.info("先在內容製作建立內容系列，才能管理模板。")
        return TemplateManagementState(None,None,False)
    theme=st.selectbox("內容系列",themes,format_func=lambda item:item.name,key="template-theme")
    active=layout_repository.ensure_default_version(conn,theme.id)
    versions=layout_repository.list_versions(conn,theme.id)
    # Include the active pointer so Streamlit rebuilds the formatted label after
    # activation instead of preserving the old "尚未啟用" display value.
    select_key=f"template-version-select-{theme.id}-{active.id}"
    pending_key=f"template-version-pending-{theme.id}"
    pending_id=st.session_state.pop(pending_key,None)
    if pending_id is not None:
        st.session_state[select_key]=pending_id
    selected_id=st.session_state.get(select_key,versions[0].id)
    if selected_id not in {item.id for item in versions}: selected_id=versions[0].id
    version_by_id={item.id:item for item in versions}
    chosen_id=st.selectbox("模板版本",list(version_by_id),index=list(version_by_id).index(selected_id),format_func=lambda value:f"v{version_by_id[value].version_no}"+(" · 目前啟用" if value==active.id else " · 尚未啟用"),key=select_key)
    selected=version_by_id[chosen_id]
    page_type=st.session_state.get(f"template-page-{theme.id}","cover")
    stress_cases=build_template_stress_cases(); demo=stress_cases[0]
    page=next(item for item in demo.draft.pages if item.page_type==page_type)
    preview=render.template_editor_page_html(page,demo.company,demo.asset,selected.layout)
    payload=template_editor_payload(theme,versions,selected,page_type,preview)
    event=mount_template_editor(payload,key=f"template-editor-{theme.id}-{selected.id}")
    if event.request_page and event.request_page!=page_type:
        st.session_state[f"template-page-{theme.id}"]=event.request_page
        st.rerun()
    if event.save_payload:
        with st.spinner("正在用三家公司與七頁內容檢查新版面…"):
            result=template_editor_service.save_template_version(conn,theme.id,int(event.save_payload.get("baseVersionId",0)),event.save_payload.get("layout",{}),stress_cases)
        if result.issues:
            for issue in result.issues[:8]: st.error(issue.message)
        else:
            st.session_state[pending_key]=result.version.id
            st.success(f"已建立 v{result.version.version_no}，尚未設為啟用版。")
            st.rerun()
    if selected.id!=active.id:
        st.warning(f"v{selected.version_no} 尚未啟用；啟用只影響之後建立的新草稿，現有草稿不變。")
        confirmed=st.checkbox("我了解現有草稿不會自動換版",key=f"confirm-active-{selected.id}")
        if st.button("設為之後新貼文的啟用版",disabled=not confirmed,key=f"activate-template-{selected.id}"):
            template_editor_service.set_active_template_version(conn,theme.id,selected.id)
            st.success(f"v{selected.version_no} 已設為啟用版。")
            st.rerun()
    return TemplateManagementState(theme.id,selected.id,event.dirty)
