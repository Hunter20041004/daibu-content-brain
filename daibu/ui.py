import os
import sqlite3

import streamlit as st
from dotenv import load_dotenv

from daibu import db, seeds

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
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,600;6..72,700&family=Noto+Sans+TC:wght@400;500;600;700&display=swap');
        :root {
            --ink: #171513;
            --paper: #f7f3ec;
            --surface: #fffdf9;
            --muted: #665f57;
            --line: #ded7ce;
            --accent: #b94235;
            --accent-dark: #913228;
            --success: #246b4a;
            --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
        }
        .stApp {
            background:
                radial-gradient(circle at 90% 2%, rgba(185,66,53,.08), transparent 28rem),
                var(--paper);
            color: var(--ink);
            font-family: "Noto Sans TC", sans-serif;
        }
        h1, h2, h3 {
            color: var(--ink);
            font-family: "Newsreader", "Noto Serif TC", serif;
            letter-spacing: -0.02em;
        }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"] { border-right: 1px solid var(--line); }
        [data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 1rem;
        }
        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] * { color: var(--muted); }
        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] * { color: var(--ink); }
        .stButton > button {
            min-height: 44px;
            border-radius: 10px;
            transition:
                transform 160ms var(--ease-out),
                border-color 160ms ease,
                background-color 160ms ease;
        }
        .stButton > button:active { transform: scale(.97); }
        .stButton > button[kind="primary"] {
            background: var(--accent);
            border-color: var(--accent);
        }
        .stButton > button[kind="primary"]:hover {
            background: var(--accent-dark);
            border-color: var(--accent-dark);
        }
        .page-kicker {
            color: var(--accent);
            font-size: .78rem;
            font-weight: 700;
            letter-spacing: .12em;
            margin-bottom: .35rem;
            text-transform: uppercase;
        }
        .page-deck {
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.7;
            max-width: 68ch;
        }
        @media (prefers-reduced-motion: reduce) {
            .stButton > button { transition: none; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(kicker: str, title: str, description: str) -> None:
    st.markdown(f'<p class="page-kicker">{kicker}</p>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(
        f'<p class="page-deck">{description}</p>',
        unsafe_allow_html=True,
    )
