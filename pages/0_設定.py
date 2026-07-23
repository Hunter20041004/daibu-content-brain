import os

import streamlit as st

from daibu import db
from daibu.models import Source, Theme
from daibu.ui import (
    DEFAULT_GATE_LINE,
    apply_styles,
    connect_app_db,
    page_header,
)

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
LAYERS = ["L1", "L2", "L3", "L4", "L5"]
KINDS = {"常青": "evergreen", "時效": "timely"}
FETCH_TYPES = ["rss", "search", "manual"]

st.set_page_config(page_title="設定｜呆一布", page_icon="◉", layout="wide")
apply_styles()
page_header(
    "Settings",
    "設定",
    "決定每週談什麼、信任哪些來源，以及 AI 應守住哪條線。",
)

conn = connect_app_db()

st.subheader("守門線與 AI")
with st.form("product-config"):
    gate_line = st.text_area(
        "守門線",
        value=db.get_config(conn, "gate_line", DEFAULT_GATE_LINE),
        help="這段文字會原封不動交給 AI，作為每則候選的評分標準。",
    )
    provider_options = ["gemini", "groq"]
    current_provider = db.get_config(conn, "llm_provider", "gemini")
    provider = st.selectbox(
        "LLM provider",
        provider_options,
        index=provider_options.index(current_provider)
        if current_provider in provider_options
        else 0,
    )
    default_model = (
        "gemini-2.5-flash"
        if provider == "gemini"
        else "llama-3.3-70b-versatile"
    )
    model = st.text_input(
        "模型",
        value=db.get_config(conn, "llm_model", default_model),
    )
    search_provider = st.selectbox(
        "搜尋 provider",
        ["tavily"],
        help="v1 固定使用 Tavily 免費層。",
    )
    st.caption("API key 只放在目前執行環境，不寫入 SQLite，也不會進 Git。")
    gemini_key = st.text_input(
        "Gemini API key",
        type="password",
        placeholder="已設環境變數時可留空",
    )
    groq_key = st.text_input(
        "Groq API key",
        type="password",
        placeholder="已設環境變數時可留空",
    )
    tavily_key = st.text_input(
        "Tavily API key",
        type="password",
        placeholder="已設環境變數時可留空",
    )
    if st.form_submit_button("儲存產品設定", type="primary"):
        db.set_config(conn, "gate_line", gate_line)
        db.set_config(conn, "llm_provider", provider)
        db.set_config(conn, "llm_model", model)
        db.set_config(conn, "search_provider", search_provider)
        if gemini_key:
            os.environ["GEMINI_API_KEY"] = gemini_key
        if groq_key:
            os.environ["GROQ_API_KEY"] = groq_key
        if tavily_key:
            os.environ["TAVILY_API_KEY"] = tavily_key
        st.success("設定已儲存；新輸入的 key 只在本次 App 執行期間有效。")

st.divider()
st.subheader("大主題")
with st.form("add-theme", clear_on_submit=True):
    name = st.text_input("主題名稱 *")
    weekday = st.selectbox("星期", WEEKDAYS)
    kind_label = st.radio("類型", list(KINDS), horizontal=True)
    source_layers = st.multiselect("使用來源層", LAYERS, default=["L1"])
    n_ideas = st.number_input("每次產幾則", min_value=1, max_value=10, value=3)
    if st.form_submit_button("新增主題", type="primary"):
        if not name.strip():
            st.error("請填主題名稱。")
        else:
            db.add_theme(
                conn,
                Theme(
                    None,
                    name.strip(),
                    WEEKDAYS.index(weekday),
                    KINDS[kind_label],
                    source_layers,
                    int(n_ideas),
                ),
            )
            st.success("主題已新增。")
            st.rerun()

for theme in db.get_themes(conn):
    with st.expander(f"{WEEKDAYS[theme.weekday]} · {theme.name}"):
        with st.form(f"edit-theme-{theme.id}"):
            edited_name = st.text_input(
                "主題名稱",
                value=theme.name,
                key=f"theme-name-{theme.id}",
            )
            edited_weekday = st.selectbox(
                "星期",
                WEEKDAYS,
                index=theme.weekday,
                key=f"theme-weekday-{theme.id}",
            )
            kind_labels = list(KINDS)
            edited_kind = st.radio(
                "類型",
                kind_labels,
                index=list(KINDS.values()).index(theme.kind),
                horizontal=True,
                key=f"theme-kind-{theme.id}",
            )
            edited_layers = st.multiselect(
                "使用來源層",
                LAYERS,
                default=theme.source_layers,
                key=f"theme-layers-{theme.id}",
            )
            edited_n = st.number_input(
                "每次產幾則",
                min_value=1,
                max_value=10,
                value=theme.n_ideas,
                key=f"theme-count-{theme.id}",
            )
            if st.form_submit_button("儲存主題"):
                db.update_theme(
                    conn,
                    Theme(
                        theme.id,
                        edited_name.strip(),
                        WEEKDAYS.index(edited_weekday),
                        KINDS[edited_kind],
                        edited_layers,
                        int(edited_n),
                    ),
                )
                st.success("主題已更新。")
                st.rerun()
        confirm = st.checkbox(
            "我確認要刪除這個主題",
            key=f"confirm-theme-delete-{theme.id}",
        )
        if st.button(
            "刪除主題",
            key=f"delete-theme-{theme.id}",
            disabled=not confirm,
        ):
            db.delete_theme(conn, theme.id)
            st.rerun()

st.divider()
st.subheader("來源白名單")
with st.form("add-source", clear_on_submit=True):
    source_name = st.text_input("來源名稱 *")
    source_url = st.text_input("網址 *")
    layer = st.selectbox("層級", LAYERS)
    fetch_type = st.selectbox("抓取方式", FETCH_TYPES)
    enabled = st.checkbox("啟用", value=True)
    if st.form_submit_button("新增來源", type="primary"):
        if not source_name.strip() or not source_url.strip():
            st.error("來源名稱與網址都必填。")
        else:
            db.add_source(
                conn,
                Source(
                    None,
                    source_name.strip(),
                    source_url.strip(),
                    layer,
                    fetch_type,
                    enabled,
                ),
            )
            st.success("來源已新增。")
            st.rerun()

for source in db.get_sources(conn):
    with st.expander(f"{source.layer} · {source.name}"):
        with st.form(f"edit-source-{source.id}"):
            edited_source_name = st.text_input(
                "來源名稱",
                value=source.name,
                key=f"source-name-{source.id}",
            )
            edited_url = st.text_input(
                "網址",
                value=source.url,
                key=f"source-url-{source.id}",
            )
            edited_layer = st.selectbox(
                "層級",
                LAYERS,
                index=LAYERS.index(source.layer),
                key=f"source-layer-{source.id}",
            )
            edited_fetch_type = st.selectbox(
                "抓取方式",
                FETCH_TYPES,
                index=FETCH_TYPES.index(source.fetch_type),
                key=f"source-fetch-{source.id}",
            )
            edited_enabled = st.checkbox(
                "啟用",
                value=source.enabled,
                key=f"source-enabled-{source.id}",
            )
            if st.form_submit_button("儲存來源"):
                db.update_source(
                    conn,
                    Source(
                        source.id,
                        edited_source_name.strip(),
                        edited_url.strip(),
                        edited_layer,
                        edited_fetch_type,
                        edited_enabled,
                    ),
                )
                st.success("來源已更新。")
                st.rerun()
        confirm = st.checkbox(
            "我確認要刪除這個來源",
            key=f"confirm-source-delete-{source.id}",
        )
        if st.button(
            "刪除來源",
            key=f"delete-source-{source.id}",
            disabled=not confirm,
        ):
            db.delete_source(conn, source.id)
            st.rerun()
