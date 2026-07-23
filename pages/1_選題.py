import os
from datetime import date

import streamlit as st

from daibu import db, pipeline, selection
from daibu.llm import base
from daibu.ui import (
    DEFAULT_GATE_LINE,
    apply_styles,
    connect_app_db,
    page_header,
)

st.set_page_config(page_title="本週選題｜呆一布", page_icon="◉", layout="wide")
apply_styles()
page_header(
    "Radar",
    "本週選題",
    "讓 AI 從可信來源找題目；你保留最後的採用權。",
)

conn = connect_app_db()
themes = db.get_themes(conn)
sources = db.get_sources(conn)
today_themes = [theme for theme in themes if theme.weekday == date.today().weekday()]
gate_line = db.get_config(conn, "gate_line", DEFAULT_GATE_LINE)
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

if st.button("產生本週選題", type="primary", width="stretch"):
    if not today_themes:
        st.info("今天沒有排定主題；可到設定頁調整主題星期。")
    else:
        try:
            provider = base.get_provider(provider_config)
            with st.spinner("正在閱讀來源並整理候選…"):
                for theme in today_themes:
                    selection.generate_for_theme(
                        conn,
                        theme,
                        provider,
                        sources,
                        gate_line=gate_line,
                    )
            st.success("候選已產生。")
            st.rerun()
        except Exception as error:
            st.error(f"產生失敗：{error}")

st.subheader("候選題目")
candidates = db.get_ideas(conn, status="候選")
if not candidates:
    st.info("尚無候選。按上方按鈕，讓 AI 先替你整理一輪。")

for idea in candidates:
    with st.container(border=True):
        score_col, content_col = st.columns([1, 5])
        score_col.metric("守門線（滿分 100）", str(idea.gate_score))
        content_col.subheader(idea.title)
        content_col.write(idea.angle)
        content_col.caption(idea.gate_reason)
        if idea.source_url:
            content_col.link_button("查看來源", idea.source_url)
        with st.expander("微調標題與角度"):
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
        adopt_col, reject_col = st.columns(2)
        if adopt_col.button(
            "採用",
            key=f"adopt-{idea.id}",
            type="primary",
            width="stretch",
        ):
            pipeline.set_status(conn, idea.id, "採用")
            st.rerun()
        confirm_reject = reject_col.checkbox(
            "確認淘汰",
            key=f"confirm-reject-{idea.id}",
        )
        if reject_col.button(
            "淘汰",
            key=f"reject-{idea.id}",
            disabled=not confirm_reject,
            width="stretch",
        ):
            db.delete_idea(conn, idea.id)
            st.rerun()
