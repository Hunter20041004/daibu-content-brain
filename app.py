import streamlit as st

from daibu.overview import render as render_overview

st.set_page_config(
    page_title="呆一布 內容工作站",
    page_icon="◉",
    layout="wide",
)

navigation = st.navigation(
    [
        st.Page(render_overview, title="工作台", default=True),
        st.Page("pages/1_選題.py", title="內容製作"),
        st.Page("pages/2_成效.py", title="成效"),
        st.Page("pages/3_設定.py", title="系統設定"),
    ],
)
navigation.run()
