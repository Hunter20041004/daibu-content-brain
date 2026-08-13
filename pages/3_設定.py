import os

import streamlit as st

from daibu import db
from daibu.llm import base
from daibu.ui import apply_styles, connect_app_db, page_header

st.set_page_config(page_title="設定｜呆一布", page_icon="◉", layout="wide")
apply_styles()
page_header(
    "System",
    "設定",
    "管理 AI 與搜尋服務；內容主題和來源請回到選題工作台調整。",
)

conn = connect_app_db()

settings_panel = st.container(key="settings-form")
settings_panel.subheader("系統設定")
with settings_panel.form("system-config"):
    provider_options = ["gemini", "groq"]
    current_provider = db.get_config(conn, "llm_provider", "gemini")
    provider = st.selectbox(
        "AI 服務商",
        provider_options,
        index=provider_options.index(current_provider)
        if current_provider in provider_options
        else 0,
        format_func=lambda value: (
            "Google AI（Gemma＋Gemini）"
            if value == "gemini"
            else "Groq"
        ),
    )
    idea_model = ""
    if provider == "gemini":
        idea_model = st.text_input(
            "選題主要模型",
            value=db.get_config(
                conn,
                "llm_idea_model",
                base.DEFAULT_GOOGLE_IDEA_MODEL,
            ),
        )
        model = st.text_input(
            "正文、備援與輪播模型",
            value=db.get_config(
                conn,
                "llm_model",
                base.DEFAULT_GOOGLE_FALLBACK_MODEL,
            ),
        )
        st.caption(
            "選題與必要資格查核先用 Gemma；正文與輪播使用 Gemini，"
            "Gemma 暫時錯誤或選題格式失敗時會自動改用 Gemini。"
        )
    else:
        model = st.text_input(
            "模型",
            value=db.get_config(
                conn,
                "llm_model",
                "llama-3.3-70b-versatile",
            ),
        )
    search_provider = "tavily"
    st.markdown("搜尋服務：Tavily")
    st.caption("API key 只放在本次執行環境，不寫入 SQLite，也不會進 Git。")
    gemini_key = ""
    groq_key = ""
    if provider == "gemini":
        gemini_key = st.text_input(
            "Gemini 金鑰",
            type="password",
            placeholder="已設環境變數時可留空",
        )
        st.caption(
            "Gemini 金鑰："
            f"{'已設定' if os.getenv('GEMINI_API_KEY') else '尚未設定'}"
        )
    else:
        groq_key = st.text_input(
            "Groq 金鑰",
            type="password",
            placeholder="已設環境變數時可留空",
        )
        st.caption(
            "Groq 金鑰："
            f"{'已設定' if os.getenv('GROQ_API_KEY') else '尚未設定'}"
        )
    tavily_key = st.text_input(
        "Tavily 金鑰",
        type="password",
        placeholder="已設環境變數時可留空",
    )
    st.caption(
        "Tavily 金鑰："
        f"{'已設定' if os.getenv('TAVILY_API_KEY') else '尚未設定'}"
    )
    if st.form_submit_button("儲存系統設定", type="primary"):
        db.set_config(conn, "llm_provider", provider)
        db.set_config(conn, "llm_model", model)
        if provider == "gemini":
            db.set_config(conn, "llm_idea_model", idea_model)
        db.set_config(conn, "search_provider", search_provider)
        if gemini_key:
            os.environ["GEMINI_API_KEY"] = gemini_key
        if groq_key:
            os.environ["GROQ_API_KEY"] = groq_key
        if tavily_key:
            os.environ["TAVILY_API_KEY"] = tavily_key
        st.success("設定已儲存；新輸入的 key 只在本次 App 執行期間有效。")
