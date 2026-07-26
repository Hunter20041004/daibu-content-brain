import html
import os
from datetime import date, datetime, timedelta

import streamlit as st

from daibu import db, performance, pipeline
from daibu.ui import apply_styles, connect_app_db, page_header

WEEKDAYS = ("週一", "週二", "週三", "週四", "週五", "週六", "週日")
CALENDAR_THEME_NAME_LIMIT = 7


def truncate_calendar_theme_name(name: str) -> str:
    if len(name) <= CALENDAR_THEME_NAME_LIMIT:
        return name
    return f"{name[:CALENDAR_THEME_NAME_LIMIT]}…"


def _published_this_week(published_at: str | None) -> bool:
    if not published_at:
        return False
    try:
        published_date = datetime.fromisoformat(published_at).date()
    except ValueError:
        return False
    week_start = date.today() - timedelta(days=date.today().weekday())
    return week_start <= published_date <= date.today()


def render() -> None:
    apply_styles()
    page_header(
        "Overview",
        "情況概覽",
        "先看下一步，再掌握本週排程、各主題進度與需要處理的提醒。",
    )

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
    candidate_counts = {
        theme.id: sum(
            idea.status == "候選" and idea.theme_id == theme.id
            for idea in ideas
        )
        for theme in themes
    }
    candidate_target = max(
        themes,
        key=lambda theme: candidate_counts[theme.id],
        default=None,
    )
    candidate_target_count = (
        candidate_counts[candidate_target.id]
        if candidate_target
        else 0
    )
    blank_adopted = [
        idea for idea in ideas
        if idea.status == "採用" and not idea.body.strip()
    ]
    theme_ids_with_ideas = {
        idea.theme_id for idea in ideas
        if idea.theme_id is not None
    }
    today_unstarted = [
        theme for theme in today_themes
        if theme.id not in theme_ids_with_ideas
    ]
    published_this_week = sum(
        idea.status == "已發" and _published_this_week(idea.published_at)
        for idea in ideas
    )

    if status_counts["候選"]:
        next_action = f"你有 {status_counts['候選']} 則候選等你決定"
    elif blank_adopted:
        next_action = f"{len(blank_adopted)} 則已採用還沒寫正文"
    elif today_unstarted:
        next_action = f"今天排的是「{today_unstarted[0].name}」，還沒產候選"
    elif themes:
        next_theme = min(
            themes,
            key=lambda theme: (
                (theme.weekday - date.today().weekday()) % 7 or 7
            ),
        )
        next_action = (
            "目前沒有待辦；下一個排定的是"
            f"{WEEKDAYS[next_theme.weekday]}的「{next_theme.name}」"
        )
    else:
        next_action = "目前沒有待辦；先建立第一個主題"

    cta_label = (
        f"去看「{candidate_target.name}」的 {candidate_target_count} 則"
        if candidate_target and candidate_target_count
        else "前往選題工作台"
    )
    with st.container(key="next-action-card"):
        st.markdown(
            '<div class="suggestion-card">'
            '<span class="suggestion-card__label">下一步</span>'
            '<p class="suggestion-card__message">'
            f"{html.escape(next_action)}</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button(cta_label, type="primary"):
            if candidate_target and candidate_target_count:
                st.session_state.selected_theme_id = candidate_target.id
            st.switch_page("pages/1_選題.py")

    st.subheader("待辦數字")
    focus_columns = st.columns(3)
    focus_items = (
        ("待你決策", status_counts["候選"]),
        ("已採用待寫", len(blank_adopted)),
        ("本週已發", published_this_week),
    )
    for column, (label, value) in zip(
        focus_columns,
        focus_items,
        strict=True,
    ):
        column.metric(label, value)

    st.subheader("本週主題行事曆")
    schedule_columns = st.columns(7)
    for weekday, column in enumerate(schedule_columns):
        scheduled_names = [
            theme.name for theme in themes
            if theme.weekday == weekday
        ]
        schedule_text = (
            "、".join(
                truncate_calendar_theme_name(name)
                for name in scheduled_names
            )
            if scheduled_names
            else "空檔"
        )
        schedule_title = (
            "、".join(scheduled_names)
            if scheduled_names
            else "空檔"
        )
        calendar_classes = ["daibu-card", "calendar-card"]
        if not scheduled_names:
            calendar_classes.append("calendar-card--empty")
        if weekday == date.today().weekday():
            calendar_classes.append("calendar-card--today")
        with column:
            st.markdown(
                f'<div class="{" ".join(calendar_classes)}">'
                f"<strong>{WEEKDAYS[weekday]}</strong>"
                f'<p title="{html.escape(schedule_title, quote=True)}">'
                f"{html.escape(schedule_text)}</p>"
                "</div>",
                unsafe_allow_html=True,
            )

    performance_by_theme = {
        str(row["theme"]): row["avg_engagement"]
        for row in performance.summary_by_theme(conn)
    }
    theme_status_rows = [
        {
            "主題": theme.name,
            "星期": WEEKDAYS[theme.weekday],
            "來源數": len(theme.source_ids),
            "候選": sum(
                idea.theme_id == theme.id and idea.status == "候選"
                for idea in ideas
            ),
            "已發": sum(
                idea.theme_id == theme.id and idea.status == "已發"
                for idea in ideas
            ),
            "平均互動": (
                f"{float(performance_by_theme[theme.name]):.1f}"
                if theme.name in performance_by_theme
                else "—"
            ),
        }
        for theme in themes
    ]
    st.subheader("各主題近況")
    st.dataframe(
        theme_status_rows,
        width="stretch",
        hide_index=True,
    )

    themes_without_sources = [
        theme.name for theme in themes
        if not theme.source_ids
    ]
    configured_provider = db.get_config(
        conn,
        "llm_provider",
        os.getenv("LLM_PROVIDER", "gemini"),
    ).lower()
    provider_key_name = (
        "GROQ_API_KEY"
        if configured_provider == "groq"
        else "GEMINI_API_KEY"
    )
    if themes_without_sources or not os.getenv(provider_key_name):
        st.subheader("需要處理的提醒")
        if themes_without_sources:
            st.warning(
                f"{'、'.join(themes_without_sources)} 未綁來源；"
                "生成時會只靠主題名發想。"
            )
        if not os.getenv(provider_key_name):
            st.warning(
                f"尚未設定 {provider_key_name}，"
                "產生候選前請到設定頁補上。"
            )

    st.caption("資料只保存在這台電腦；API key 不寫入資料庫。")
