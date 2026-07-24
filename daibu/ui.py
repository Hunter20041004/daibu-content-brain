import os
import sqlite3

import streamlit as st
from dotenv import load_dotenv

from daibu import db, seeds, theme

DEFAULT_DB_PATH = "daibu.db"
DEFAULT_GATE_LINE = (
    "一個怕 AI 的文組同學看完這則，會不會覺得"
    "「原來我也可以，而且我更會想事情了」？"
)


def connect_app_db() -> sqlite3.Connection:
    load_dotenv()
    conn = db.connect(os.getenv("DAIBU_DB_PATH", DEFAULT_DB_PATH))
    db.init_schema(conn)
    seeds.load(conn)
    return conn


def apply_styles() -> None:
    st.markdown(
        f"<style>{theme.css()}</style>",
        unsafe_allow_html=True,
    )


def page_header(kicker: str, title: str, description: str) -> None:
    st.markdown(f'<p class="page-kicker">{kicker}</p>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(
        f'<p class="page-deck">{description}</p>',
        unsafe_allow_html=True,
    )
