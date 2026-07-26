import os
import re
import sqlite3
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from daibu import db, seeds, theme

DEFAULT_DB_PATH = "daibu.db"
MASCOT_PATH = Path(__file__).resolve().parents[1] / "assets" / "mascot.svg"
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
    theme_mode = st.context.theme.type
    st.markdown(
        f"<style>{theme.css(theme_mode)}</style>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        brand_lockup(),
        unsafe_allow_html=True,
    )


def mascot_svg(size: int = 44) -> str:
    svg = MASCOT_PATH.read_text(encoding="utf-8")
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.DOTALL)
    svg = re.sub(r">\s+<", "><", svg.strip())
    return svg.replace(
        "<svg ",
        f'<svg style="width: {size}px" ',
        1,
    )


def brand_lockup(size: int = 44) -> str:
    return (
        '<div class="brand-lockup">'
        f"{mascot_svg(size)}"
        '<span class="brand-lockup__name">'
        "呆一布"
        '<span class="brand-lockup__meta">選題大腦</span>'
        "</span>"
        "</div>"
    )


def page_header(kicker: str, title: str, description: str) -> None:
    st.markdown(f'<p class="page-kicker">{kicker}</p>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(
        f'<p class="page-deck">{description}</p>',
        unsafe_allow_html=True,
    )
