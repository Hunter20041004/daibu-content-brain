import streamlit as st

from daibu import db, pipeline
from daibu.ui import apply_styles, connect_app_db, page_header

EDITOR_STATE_KEY = "pipeline_editor_idea_id"

st.set_page_config(page_title="內容流水線｜呆一布", page_icon="◉", layout="wide")
apply_styles()
page_header(
    "Pipeline",
    "內容流水線",
    "從候選到已發，每張卡只放在一個清楚的位置。",
)

conn = connect_app_db()
ideas = db.get_ideas(conn)
themes = {theme.id: theme.name for theme in db.get_themes(conn)}


def close_editor() -> None:
    st.session_state.pop(EDITOR_STATE_KEY, None)


@st.dialog(
    "編輯內容",
    width="large",
    on_dismiss=close_editor,
)
def edit_idea(idea) -> None:
    st.subheader(idea.title)
    st.caption(
        f"{themes.get(idea.theme_id, '未分類')} · "
        f"守門線 {idea.gate_score}",
    )
    with st.form(f"pipeline-editor-{idea.id}"):
        new_status = st.selectbox(
            "狀態",
            pipeline.STATUSES,
            index=pipeline.STATUSES.index(idea.status),
            key=f"pipeline-status-{idea.id}",
        )
        body = st.text_area(
            "內容",
            value=idea.body,
            placeholder="在這裡整理貼文草稿…",
            key=f"pipeline-body-{idea.id}",
            height=280,
        )
        if st.form_submit_button("儲存", type="primary"):
            pipeline.set_status(conn, idea.id, new_status)
            pipeline.update_body(conn, idea.id, body)
            close_editor()
            st.success("內容已儲存。")
            st.rerun(scope="app")


columns = st.columns(len(pipeline.STATUSES))
for status, column in zip(pipeline.STATUSES, columns, strict=True):
    status_ideas = [idea for idea in ideas if idea.status == status]
    with column:
        st.subheader(status)
        st.markdown(
            f'<span class="status-chip">{len(status_ideas)} 則</span>',
            unsafe_allow_html=True,
        )
        if not status_ideas:
            st.markdown(
                '<div class="empty-state">目前沒有內容</div>',
                unsafe_allow_html=True,
            )
        for idea in status_ideas:
            with st.container(border=True):
                if st.button(
                    idea.title,
                    key=f"open-pipeline-editor-{idea.id}",
                    width="stretch",
                ):
                    st.session_state[EDITOR_STATE_KEY] = idea.id
                    st.rerun()
                st.caption(
                    f"{themes.get(idea.theme_id, '未分類')} · "
                    f"守門線 {idea.gate_score}",
                )

selected_idea_id = st.session_state.get(EDITOR_STATE_KEY)
selected_idea = next(
    (idea for idea in ideas if idea.id == selected_idea_id),
    None,
)
if selected_idea is not None:
    edit_idea(selected_idea)
elif selected_idea_id is not None:
    close_editor()
