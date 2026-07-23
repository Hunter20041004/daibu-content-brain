import streamlit as st

from daibu import db, pipeline
from daibu.ui import apply_styles, connect_app_db, page_header

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

columns = st.columns(len(pipeline.STATUSES))
for status, column in zip(pipeline.STATUSES, columns, strict=True):
    status_ideas = [idea for idea in ideas if idea.status == status]
    with column:
        st.subheader(status)
        st.caption(f"{len(status_ideas)} 則")
        if not status_ideas:
            st.info("目前沒有內容")
        for idea in status_ideas:
            with st.container(border=True):
                st.markdown(f"**{idea.title}**")
                st.caption(
                    f"{themes.get(idea.theme_id, '未分類')} · "
                    f"守門線 {idea.gate_score}"
                )
                with st.form(f"pipeline-card-{idea.id}"):
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
                    )
                    if st.form_submit_button("儲存"):
                        pipeline.set_status(conn, idea.id, new_status)
                        pipeline.update_body(conn, idea.id, body)
                        st.success("內容已儲存。")
                        st.rerun()
