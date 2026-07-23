import streamlit as st

from daibu import db, pipeline
from daibu.ui import apply_styles, connect_app_db, page_header

st.set_page_config(
    page_title="呆一布 選題大腦",
    page_icon="◉",
    layout="wide",
)
apply_styles()
page_header(
    "DiveAI Content Desk",
    "呆一布 選題大腦",
    "AI 當軍師，你當決策者。從可信來源找題目，沿著內容流水線一路走到成效回顧。",
)

conn = connect_app_db()
themes = db.get_themes(conn)
ideas = db.get_ideas(conn)

metric_columns = st.columns(3)
metric_columns[0].metric("主題", len(themes))
metric_columns[1].metric(
    "待決策候選",
    len([idea for idea in ideas if idea.status == "候選"]),
)
metric_columns[2].metric(
    "已發",
    len([idea for idea in ideas if idea.status == "已發"]),
)

st.subheader("接下來做什麼")
action_columns = st.columns(2)
with action_columns[0]:
    with st.container(border=True):
        st.markdown("### 先決定本週題目")
        st.write("讓 AI 整理候選，再由你採用值得做的內容。")
        st.page_link("pages/1_選題.py", label="前往本週選題")
with action_columns[1]:
    with st.container(border=True):
        st.markdown("### 繼續推進內容")
        st.write("編輯草稿、調整狀態，把採用題目送到已發。")
        st.page_link("pages/2_流水線.py", label="前往內容流水線")

st.subheader("目前流水線")
status_columns = st.columns(len(pipeline.STATUSES))
for status, column in zip(pipeline.STATUSES, status_columns, strict=True):
    column.metric(
        status,
        len([idea for idea in ideas if idea.status == status]),
    )

st.caption("資料只保存在這台電腦；API key 不寫入資料庫。")
