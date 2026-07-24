from datetime import date

import streamlit as st

from daibu import db, pipeline
from daibu.ui import apply_styles, connect_app_db, mascot_svg

st.set_page_config(
    page_title="呆一布 選題大腦",
    page_icon="◉",
    layout="wide",
)
apply_styles()

conn = connect_app_db()
themes = db.get_themes(conn)
ideas = db.get_ideas(conn)
today_themes = [
    theme for theme in themes
    if theme.weekday == date.today().weekday()
]
status_counts = {
    status: len([idea for idea in ideas if idea.status == status])
    for status in pipeline.STATUSES
}

hero_visual, hero_content = st.columns(
    [1, 4],
    vertical_alignment="center",
)
with hero_visual:
    st.markdown(
        f'<div class="hero-lockup__visual">{mascot_svg(160)}</div>',
        unsafe_allow_html=True,
    )
with hero_content:
    st.markdown(
        '<p class="page-kicker">DiveAI Content Desk</p>',
        unsafe_allow_html=True,
    )
    st.title("今天，先決定值得做的題目")
    st.markdown(
        '<p class="page-deck">'
        "AI 先整理可信來源與候選，你保留最後的採用權，"
        "再沿著流水線把想法推進到發布。"
        "</p>",
        unsafe_allow_html=True,
    )
    if st.button(
        "前往本週選題",
        type="primary",
        width="stretch",
    ):
        st.switch_page("pages/1_選題.py")

st.subheader("今日焦點")
focus_columns = st.columns(3)
focus_items = (
    ("今天排定主題", len(today_themes), False),
    ("待你決策候選", status_counts["候選"], status_counts["候選"] > 0),
    ("已發內容", status_counts["已發"], False),
)
for column, (label, value, needs_attention) in zip(
    focus_columns,
    focus_items,
    strict=True,
):
    value_class = "attention-chip" if needs_attention else "today-stat__value"
    with column:
        st.markdown(
            '<div class="daibu-card today-stat">'
            f'<div class="today-stat__label">{label}</div>'
            f'<div class="{value_class}">{value}</div>'
            "</div>",
            unsafe_allow_html=True,
        )

st.subheader("流水線縮影")
total_ideas = sum(status_counts.values())
segments = "".join(
    (
        '<span class="pipeline-bar__segment" '
        f'style="width: {(count / total_ideas * 100) if total_ideas else 0:.2f}%">'
        "</span>"
    )
    for count in status_counts.values()
)
legend = "".join(
    f"<span>{status} {status_counts[status]}</span>"
    for status in pipeline.STATUSES
)
st.markdown(
    f'<div class="pipeline-bar" aria-label="內容流水線分布">{segments}</div>'
    f'<div class="pipeline-legend">{legend}</div>',
    unsafe_allow_html=True,
)

st.caption("資料只保存在這台電腦；API key 不寫入資料庫。")
