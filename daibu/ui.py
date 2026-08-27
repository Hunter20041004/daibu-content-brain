import html
import os
import re
import sqlite3
from collections.abc import Callable, MutableMapping
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from daibu import db, pipeline, seeds, theme

DEFAULT_DB_PATH = "daibu.db"
PENDING_TOAST_KEY = "_pending_toast"
MASCOT_PATH = Path(__file__).resolve().parents[1] / "assets" / "mascot.svg"
MASCOT_POSE_DIR = Path(__file__).resolve().parents[1] / "assets" / "mascot"
MASCOT_POSES = frozenset(
    {"wave", "think", "happy", "note", "confused", "lost", "point"}
)
MASCOT_COACH_TONES = {
    "guide": "mascot-coach--guide",
    "success": "mascot-coach--success",
    "warning": "mascot-coach--warning",
}
THEME_PREFERENCE_KEY = "daibuColorMode-v1"
THEME_ICON_CLASSES = {
    "light": "theme-switcher__icon--moon",
    "dark": "theme-switcher__icon--sun",
}


def theme_switcher_html(mode: str) -> str:
    if mode not in {"light", "dark"}:
        raise ValueError(f"Unsupported theme mode: {mode}")
    is_dark = mode == "dark"
    current_label = "深色" if is_dark else "淺色"
    next_label = "淺色" if is_dark else "深色"
    current_native = "Dark" if is_dark else "Light"
    next_native = "Light" if is_dark else "Dark"
    icon_class = THEME_ICON_CLASSES[mode]
    return f"""
    <div class="theme-switcher" data-current-theme="{mode}">
      <p class="theme-switcher__eyebrow">目前：{current_label}模式</p>
      <button
        id="daibu-theme-switcher"
        class="theme-switcher__button"
        type="button"
        aria-label="切換成{next_label}模式"
        aria-pressed="{str(is_dark).lower()}"
      >
        <span class="theme-switcher__icon {icon_class}"
              aria-hidden="true"></span>
        <span>切換成{next_label}</span>
      </button>
      <p class="theme-switcher__status" aria-live="polite"></p>
    </div>
    <script>
    (() => {{
      const preferenceKey = "{THEME_PREFERENCE_KEY}";
      const currentTheme = "{current_native}";
      const nextTheme = "{next_native}";
      const activeKey = path => `stActiveTheme-${{path}}-v2`;
      const storeTheme = (path, value) =>
        window.localStorage.setItem(activeKey(path), JSON.stringify(value));
      const control = document.getElementById("daibu-theme-switcher");
      const status = document.querySelector(".theme-switcher__status");

      try {{
        const preferred = JSON.parse(
          window.localStorage.getItem(preferenceKey) || "null"
        );
        const storedHere = JSON.parse(
          window.localStorage.getItem(activeKey(window.location.pathname))
          || '"System"'
        );
        if (preferred && preferred !== storedHere) {{
          storeTheme(window.location.pathname, preferred);
          window.location.reload();
          return;
        }}

        control.addEventListener("click", () => {{
          control.disabled = true;
          status.textContent = "切換中…";
          const paths = new Set([
            window.location.pathname,
            ...Array.from(
              document.querySelectorAll('[data-testid="stSidebarNav"] a[href]')
            ).map(link => new URL(link.href).pathname),
          ]);
          window.localStorage.setItem(
            preferenceKey,
            JSON.stringify(nextTheme),
          );
          paths.forEach(path => storeTheme(path, nextTheme));
          window.requestAnimationFrame(() => window.location.reload());
        }});
      }} catch (error) {{
        control.disabled = true;
        status.textContent = "瀏覽器未允許儲存主題偏好。";
      }}
    }})();
    </script>
    """


def connect_app_db() -> sqlite3.Connection:
    load_dotenv()
    conn = db.connect(os.getenv("DAIBU_DB_PATH", DEFAULT_DB_PATH))
    db.init_schema(conn)
    seeds.load(conn)
    return conn


def save_body_draft(idea_id: int, body: str) -> None:
    conn = connect_app_db()
    try:
        pipeline.update_body(conn, idea_id, body)
    finally:
        conn.close()


def queue_toast(
    state: MutableMapping[str, object],
    message: str,
) -> None:
    state[PENDING_TOAST_KEY] = message


def show_queued_toast(
    state: MutableMapping[str, object],
    render: Callable[[str], object],
) -> None:
    message = state.pop(PENDING_TOAST_KEY, None)
    if isinstance(message, str):
        render(message)


def apply_styles() -> None:
    theme_mode = st.context.theme.type or "light"
    st.markdown(
        f"<style>{theme.css(theme_mode)}</style>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        brand_lockup(),
        unsafe_allow_html=True,
    )
    st.sidebar.html(
        theme_switcher_html(theme_mode),
        unsafe_allow_javascript=True,
    )


def mascot_svg(size: int = 44, pose: str | None = None) -> str:
    path = (
        MASCOT_POSE_DIR / f"{pose}.svg"
        if pose in MASCOT_POSES
        else MASCOT_PATH
    )
    svg = path.read_text(encoding="utf-8")
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.DOTALL)
    svg = re.sub(r">\s+<", "><", svg.strip())
    return svg.replace(
        "<svg ",
        f'<svg style="width: {size}px" ',
        1,
    )


def mascot_coach(
    pose: str,
    title: str,
    message: str,
    *,
    tone: str = "guide",
) -> str:
    tone_class = MASCOT_COACH_TONES.get(tone, MASCOT_COACH_TONES["guide"])
    safe_title = html.escape(title)
    safe_message = html.escape(message)
    return (
        '<aside class="mascot-coach '
        f'{tone_class}" role="status" '
        f'aria-label="{safe_title}">'
        '<div class="mascot-coach__figure" aria-hidden="true">'
        f"{mascot_svg(pose=pose)}"
        "</div>"
        '<div class="mascot-coach__copy">'
        f"<strong>{safe_title}</strong>"
        f"<p>{safe_message}</p>"
        "</div>"
        "</aside>"
    )


def brand_lockup(size: int = 44) -> str:
    return (
        '<div class="brand-lockup">'
        f"{mascot_svg(size)}"
        '<span class="brand-lockup__name">'
        "呆一布"
        '<span class="brand-lockup__meta">內容工作站</span>'
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
