import html

import streamlit as st

from daibu import db, performance
from daibu.ui import apply_styles, connect_app_db, page_header

st.set_page_config(page_title="成效｜呆一布", page_icon="◉", layout="wide")
apply_styles()
page_header(
    "Performance",
    "成效回顧",
    "用少量可解釋的數字，看見哪個主題值得延續、哪個需要補強。",
)

conn = connect_app_db()
published = db.get_ideas(conn, status="已發")
summary = performance.summary_by_theme(conn)
recommendation = performance.suggest(summary)

results_column, entry_column = st.columns([2, 1], gap="large")

with results_column:
    st.markdown(
        '<div class="suggestion-card">'
        "<strong>下週建議</strong>"
        f"<p>{html.escape(recommendation)}</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.subheader("各主題表現")
    if not summary:
        st.markdown(
            '<div class="empty-state">'
            "還沒有足夠資料畫圖；回填第一則成效後，"
            "這裡會顯示主題比較。"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.bar_chart(summary, x="theme", y="avg_engagement")
        st.caption("圖表指標：每個主題的平均互動。")
        st.dataframe(
            summary,
            width="stretch",
            hide_index=True,
            column_config={
                "theme": "主題",
                "posts": "貼文數",
                "avg_likes": "平均讚",
                "avg_reach": "平均觸及",
                "avg_engagement": "平均互動",
            },
        )

with entry_column:
    st.subheader("回填已發貼文")
    if not published:
        st.markdown(
            '<div class="empty-state">'
            "尚無「已發」內容；先到流水線把一張卡移到已發。"
            "</div>",
            unsafe_allow_html=True,
        )

    with st.form("performance-entry"):
        idea = st.selectbox(
            "貼文",
            published,
            format_func=lambda item: item.title,
            disabled=not published,
        )
        platform = st.selectbox(
            "平台",
            ["Instagram", "Facebook", "Threads", "LinkedIn", "其他"],
        )
        likes = st.number_input("讚", min_value=0, value=0, step=1)
        reach = st.number_input("觸及", min_value=0, value=0, step=1)
        engagement = st.number_input(
            "互動",
            min_value=0.0,
            value=0.0,
            step=0.1,
            help="填入平台提供的互動數值；不同平台請維持同一口徑再比較。",
        )
        if st.form_submit_button(
            "儲存成效",
            type="primary",
            disabled=not published,
        ):
            performance.record(
                conn,
                idea.id,
                platform,
                int(likes),
                int(reach),
                float(engagement),
            )
            st.success("成效已記錄。")
            st.rerun()
