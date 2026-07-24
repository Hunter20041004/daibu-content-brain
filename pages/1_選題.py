import html
import os
from datetime import date

import streamlit as st

from daibu import db, pipeline, selection
from daibu.llm import base
from daibu.ui import (
    DEFAULT_GATE_LINE,
    apply_styles,
    connect_app_db,
    mascot_svg,
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
candidates = db.get_ideas(conn, status="候選")
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

context_column, candidate_column = st.columns([1, 2], gap="large")

with context_column:
    st.subheader("今天的題目範圍")
    if today_themes:
        theme_chips = "".join(
            f'<span class="status-chip">{html.escape(theme.name)}</span>'
            for theme in today_themes
        )
        st.markdown(
            f'<div class="pipeline-legend">{theme_chips}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="empty-state">'
            "今天沒有排定主題；可到設定頁調整主題星期。"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("#### 目前守門線")
    st.markdown(
        '<div class="daibu-card">'
        f"{html.escape(gate_line)}"
        "</div>",
        unsafe_allow_html=True,
    )

    if st.button("產生本週選題", type="primary", width="stretch"):
        if not today_themes:
            st.warning("今天沒有排定主題；先到設定頁調整主題星期。")
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

    if candidates:
        last_generated = max(idea.created_at for idea in candidates)
        st.caption(f"最近一批候選：{last_generated}")
    else:
        st.caption("尚未產生候選")

with candidate_column:
    st.subheader("候選題目")
    if not candidates:
        st.markdown(
            '<div class="empty-state">'
            f"{mascot_svg(72)}"
            "<p>尚無候選，按左邊的按鈕讓 AI 先整理一輪。</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    for idea in candidates:
        with st.container(border=True):
            score_column, content_column = st.columns(
                [1, 5],
                vertical_alignment="top",
            )
            score_class = (
                "score-badge score-badge--review"
                if idea.gate_score < 70
                else "score-badge"
            )
            score_column.markdown(
                f'<div class="{score_class}">'
                f"{idea.gate_score}"
                "<small>守門線</small>"
                "</div>",
                unsafe_allow_html=True,
            )
            with content_column:
                st.markdown(
                    '<h3 class="candidate-card__title">'
                    f"{html.escape(idea.title)}"
                    "</h3>",
                    unsafe_allow_html=True,
                )
                st.write(idea.angle)
                st.caption(idea.gate_reason)
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
                    db.delete_idea(conn, idea.id)
                    st.rerun()
