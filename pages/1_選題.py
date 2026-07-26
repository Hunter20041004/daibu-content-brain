import html
import os

import streamlit as st

from daibu import clock, db, pipeline, selection
from daibu.llm import base
from daibu.models import Source, Theme
from daibu.ui import (
    apply_styles,
    connect_app_db,
    page_header,
)

WEEKDAYS = ("週一", "週二", "週三", "週四", "週五", "週六", "週日")

st.set_page_config(page_title="選題｜呆一布", page_icon="◉", layout="wide")
apply_styles()
page_header(
    "Radar",
    "選題工作台",
    "以主題為中心管理來源、產生候選，並把採用內容一路寫到發布。",
)

conn = connect_app_db()


def save_body_draft(idea_id: int, body_key: str) -> None:
    pipeline.update_body(conn, idea_id, st.session_state[body_key])
    st.session_state[f"body-saved-at-{idea_id}"] = clock.now()[11:16]


themes = db.get_themes(conn)
sources = db.get_sources(conn)
candidates = db.get_ideas(conn, status="候選")
adopted_ideas = db.get_ideas(conn, status="採用")
published_ideas = db.get_ideas(conn, status="已發")
provider_config = dict(os.environ)
provider_config["LLM_PROVIDER"] = db.get_config(
    conn,
    "llm_provider",
    provider_config.get("LLM_PROVIDER", "gemini"),
)
provider_config["LLM_MODEL"] = db.get_config(
    conn,
    "llm_model",
    provider_config.get("LLM_MODEL", ""),
)

context_column, candidate_column = st.columns([1, 2], gap="medium")

with context_column:
    st.subheader("我的主題")
    if themes and st.session_state.get("selected_theme_id") not in {
        theme.id for theme in themes
    }:
        st.session_state.selected_theme_id = themes[0].id
    for theme in themes:
        theme_candidates = sum(
            idea.theme_id == theme.id for idea in candidates
        )
        with st.container(key=f"theme-item-{theme.id}"):
            if st.button(
                theme.name,
                key=f"select-theme-{theme.id}",
                type=(
                    "primary"
                    if theme.id == st.session_state.selected_theme_id
                    else "secondary"
                ),
                width="stretch",
            ):
                st.session_state.selected_theme_id = theme.id
                st.rerun()
            st.markdown(
                '<p class="theme-item__meta">'
                f"{WEEKDAYS[theme.weekday]} · "
                f"{len(theme.source_ids)} 來源 · {theme_candidates} 候選"
                "</p>",
                unsafe_allow_html=True,
            )

    with st.popover("＋ 新增主題", width="stretch"):
        with st.form("new-theme"):
            new_theme_name = st.text_input("主題名稱")
            new_theme_weekday = st.selectbox("提醒星期", WEEKDAYS)
            new_theme_count = st.number_input(
                "每次產生幾則",
                min_value=1,
                max_value=12,
                value=3,
            )
            if st.form_submit_button("建立主題", type="primary"):
                if not new_theme_name.strip():
                    st.error("請輸入主題名稱。")
                else:
                    theme_id = db.add_theme(
                        conn,
                        Theme(
                            None,
                            new_theme_name.strip(),
                            WEEKDAYS.index(new_theme_weekday),
                            [],
                            int(new_theme_count),
                        ),
                    )
                    st.session_state.selected_theme_id = theme_id
                    st.rerun()

    with st.expander("來源庫"):
        st.caption("來源可被多個主題共用；停用後不會再抓取。")
        with st.form("new-source"):
            new_source_name = st.text_input("新來源名稱")
            new_source_url = st.text_input("新來源網址")
            new_source_type = st.selectbox(
                "新來源抓取方式",
                ("rss", "search"),
            )
            if st.form_submit_button("新增來源"):
                if not new_source_name.strip() or not new_source_url.strip():
                    st.error("來源名稱與網址都要填寫。")
                else:
                    db.add_source(
                        conn,
                        Source(
                            None,
                            new_source_name.strip(),
                            new_source_url.strip(),
                            new_source_type,
                            True,
                        ),
                    )
                    st.rerun()

        for source in sources:
            st.markdown(f"**{source.name}**")
            st.caption(f"{source.fetch_type} · {source.url}")
            with st.popover(
                f"編輯 {source.name}",
                width="stretch",
            ):
                with st.form(f"edit-source-{source.id}"):
                    edited_source_name = st.text_input(
                        "來源名稱",
                        value=source.name,
                    )
                    edited_source_url = st.text_input(
                        "來源網址",
                        value=source.url,
                    )
                    edited_source_type = st.selectbox(
                        "抓取方式",
                        ("rss", "search"),
                        index=("rss", "search").index(source.fetch_type),
                    )
                    edited_source_enabled = st.checkbox(
                        "啟用",
                        value=source.enabled,
                    )
                    if st.form_submit_button("儲存來源"):
                        db.update_source(
                            conn,
                            Source(
                                source.id,
                                edited_source_name.strip(),
                                edited_source_url.strip(),
                                edited_source_type,
                                edited_source_enabled,
                            ),
                        )
                        st.rerun()
                confirm_delete_source = st.checkbox(
                    "確認從來源庫刪除",
                    key=f"confirm-delete-source-{source.id}",
                )
                if st.button(
                    "刪除來源",
                    key=f"delete-source-{source.id}",
                    disabled=not confirm_delete_source,
                    width="stretch",
                ):
                    db.delete_source(conn, source.id)
                    st.rerun()

with candidate_column:
    selected_theme = next(
        (
            theme for theme in themes
            if theme.id == st.session_state.get("selected_theme_id")
        ),
        None,
    )
    if selected_theme:
        st.subheader(f"{selected_theme.name}工作區")

        with st.expander("主題設定"):
            with st.form(f"theme-settings-{selected_theme.id}"):
                edited_theme_name = st.text_input(
                    "主題名稱",
                    value=selected_theme.name,
                )
                edited_theme_weekday = st.selectbox(
                    "提醒星期",
                    WEEKDAYS,
                    index=selected_theme.weekday,
                )
                edited_theme_count = st.number_input(
                    "每次產生幾則",
                    min_value=1,
                    max_value=12,
                    value=selected_theme.n_ideas,
                )
                if st.form_submit_button("儲存主題設定"):
                    db.update_theme(
                        conn,
                        Theme(
                            selected_theme.id,
                            edited_theme_name.strip(),
                            WEEKDAYS.index(edited_theme_weekday),
                            selected_theme.source_ids,
                            int(edited_theme_count),
                        ),
                    )
                    st.rerun()
            content_counts = db.count_theme_content(
                conn,
                selected_theme.id,
            )
            content_summary = "、".join(
                f"{count} 則{status}"
                for status, count in content_counts.items()
                if count
            )
            warning_message = (
                f"這會一併刪掉 {content_summary}，且無法復原。"
                if content_summary
                else "這會刪除主題，且無法復原。"
            )
            st.warning(warning_message)
            confirm_delete_theme = st.checkbox(
                "確認刪除這個主題",
                key=f"confirm-delete-theme-{selected_theme.id}",
            )
            if st.button(
                "刪除主題",
                key=f"delete-theme-{selected_theme.id}",
                disabled=not confirm_delete_theme,
            ):
                db.delete_theme(conn, selected_theme.id)
                st.session_state.pop("selected_theme_id", None)
                st.rerun()

        with st.expander("這個主題抓哪些來源"):
            with st.form(f"theme-sources-{selected_theme.id}"):
                selected_source_ids = []
                for source in sources:
                    source_label = (
                        source.name
                        if source.enabled
                        else f"{source.name}（已停用）"
                    )
                    if st.checkbox(
                        source_label,
                        value=source.id in selected_theme.source_ids,
                        key=f"theme-source-{selected_theme.id}-{source.id}",
                    ):
                        selected_source_ids.append(source.id)
                if st.form_submit_button("儲存來源綁定"):
                    db.update_theme(
                        conn,
                        Theme(
                            selected_theme.id,
                            selected_theme.name,
                            selected_theme.weekday,
                            selected_source_ids,
                            selected_theme.n_ideas,
                        ),
                    )
                    st.success("來源綁定已儲存。")
                    st.rerun()
        if not selected_theme.source_ids:
            st.warning("這個主題沒綁來源，AI 會只靠主題名發想。")

        if st.button(
            "產生候選",
            type="primary",
            width="stretch",
        ):
            try:
                provider = base.get_provider(provider_config)
                with st.spinner("正在閱讀來源並整理候選…"):
                    selection.generate_for_theme(
                        conn,
                        selected_theme,
                        provider,
                        sources,
                    )
                st.success("候選已產生。")
                st.rerun()
            except Exception as error:
                st.error(f"產生失敗：{error}")
    else:
        st.markdown(
            '<div class="empty-state">'
            "先在左欄新增一個主題，再開始建立選題。"
            "</div>",
            unsafe_allow_html=True,
        )

    selected_candidates = [
        idea for idea in candidates
        if selected_theme and idea.theme_id == selected_theme.id
    ]
    st.subheader(f"候選（{len(selected_candidates)}）")
    if not selected_candidates:
        st.markdown(
            '<div class="empty-state">'
            "<p>這個主題尚無候選，按左邊的按鈕讓 AI 先整理一輪。</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    for idea in selected_candidates:
        with st.container(border=True):
            st.markdown(
                '<h3 class="candidate-card__title">'
                f"{html.escape(idea.title)}"
                "</h3>",
                unsafe_allow_html=True,
            )
            st.write(idea.angle)
            if idea.source_url:
                st.link_button("查看來源", idea.source_url)

            adopt_column, tweak_column, reject_column = st.columns(3)
            if adopt_column.button(
                "採用",
                key=f"adopt-{idea.id}",
                type="primary",
                width="stretch",
            ):
                pipeline.set_status(conn, idea.id, "採用")
                st.rerun()

            with tweak_column.popover("微調", width="stretch"):
                with st.form(f"tweak-{idea.id}"):
                    tweaked_title = st.text_input(
                        "標題",
                        value=idea.title,
                        key=f"tweak-title-{idea.id}",
                    )
                    tweaked_angle = st.text_area(
                        "切入角度",
                        value=idea.angle,
                        key=f"tweak-angle-{idea.id}",
                    )
                    if st.form_submit_button("儲存微調"):
                        db.update_idea_content(
                            conn,
                            idea.id,
                            tweaked_title.strip(),
                            tweaked_angle.strip(),
                        )
                        st.success("微調已儲存。")
                        st.rerun()

            with reject_column.popover("淘汰", width="stretch"):
                confirm_reject = st.checkbox(
                    "我確認要淘汰這則候選",
                    key=f"confirm-reject-{idea.id}",
                )
                if st.button(
                    "確認淘汰",
                    key=f"reject-{idea.id}",
                    disabled=not confirm_reject,
                    width="stretch",
                ):
                    pipeline.set_status(conn, idea.id, pipeline.REJECTED)
                    st.rerun()

    selected_adopted = [
        idea for idea in adopted_ideas
        if selected_theme and idea.theme_id == selected_theme.id
    ]
    st.subheader(f"已採用（{len(selected_adopted)}）")
    if not selected_adopted:
        st.caption("這個主題還沒有已採用的題目。")
    for idea in selected_adopted:
        with st.expander(idea.title):
            st.caption(idea.angle)
            body_key = f"body-{idea.id}"
            body = st.text_area(
                f"正文｜{idea.title}",
                value=idea.body,
                key=body_key,
                on_change=save_body_draft,
                args=(idea.id, body_key),
            )
            saved_at = st.session_state.get(f"body-saved-at-{idea.id}")
            if saved_at:
                st.caption(f"已自動儲存於 {saved_at}")
            save_column, publish_column = st.columns(2)
            if save_column.button(
                "儲存正文",
                key=f"save-body-{idea.id}",
                width="stretch",
            ):
                save_body_draft(idea.id, body_key)
                st.success("正文已儲存。")
                st.rerun()
            if publish_column.button(
                "標記已發",
                key=f"publish-{idea.id}",
                type="primary",
                width="stretch",
            ):
                pipeline.update_body(conn, idea.id, body)
                pipeline.set_status(conn, idea.id, "已發")
                st.success("已標記為已發。")
                st.rerun()

    selected_published = [
        idea for idea in published_ideas
        if selected_theme and idea.theme_id == selected_theme.id
    ]
    if selected_published:
        with st.expander(f"已發（{len(selected_published)}）"):
            for idea in selected_published:
                st.markdown(f"**{idea.title}**")
                st.caption(idea.published_at or "發布時間未知")
