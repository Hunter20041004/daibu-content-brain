import tomllib
from pathlib import Path
from types import SimpleNamespace

from daibu import theme, ui


ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_pages_use_current_width_argument():
    page_paths = [
        ROOT / "app.py",
        *(ROOT / "pages").glob("*.py"),
    ]
    source_texts = [path.read_text() for path in page_paths]

    assert all("use_container_width" not in source for source in source_texts)


def test_streamlit_theme_supports_brand_light_and_dark_palettes():
    with (ROOT / ".streamlit" / "config.toml").open("rb") as config_file:
        config = tomllib.load(config_file)["theme"]

    assert config["light"]["backgroundColor"].upper() == theme.LIGHT["CANVAS"]
    assert config["light"]["textColor"].upper() == theme.LIGHT["INK"]
    assert config["dark"]["backgroundColor"].upper() == theme.DARK["CANVAS"]
    assert config["dark"]["textColor"].upper() == theme.DARK["INK"]


def test_toolbar_mode_is_minimal():
    with (ROOT / ".streamlit" / "config.toml").open("rb") as config_file:
        config = tomllib.load(config_file)

    assert config["client"]["toolbarMode"] == "minimal"


def test_ui_has_no_retired_gate_line_default():
    assert not hasattr(ui, "DEFAULT_GATE_LINE")


def test_connect_app_db_loads_dotenv(monkeypatch, tmp_path):
    loaded = []
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setattr(ui, "load_dotenv", lambda: loaded.append(True))

    conn = ui.connect_app_db()
    conn.close()

    assert loaded == [True]


def test_apply_styles_injects_brand_theme(monkeypatch):
    rendered = []
    monkeypatch.setattr(
        ui.st,
        "markdown",
        lambda body, **kwargs: rendered.append(body),
    )

    ui.apply_styles()

    styles = rendered[0]
    assert "--brand-primary" in styles
    assert "prefers-reduced-motion" in styles
    assert "color: var(--ink)" in styles


def test_carousel_workbench_uses_branded_hierarchy_styles():
    styles = theme.css("light")

    assert ".carousel-status" in styles
    assert ".verified-source" in styles
    assert ".carousel-page-heading" in styles
    assert "background: var(--surface)" in styles
    assert "border: 1px solid var(--border)" in styles


def test_apply_styles_uses_current_streamlit_theme(monkeypatch):
    received_modes = []
    monkeypatch.setattr(
        ui.st,
        "context",
        SimpleNamespace(theme=SimpleNamespace(type="dark")),
    )
    monkeypatch.setattr(
        ui.theme,
        "css",
        lambda mode: received_modes.append(mode) or "",
    )
    monkeypatch.setattr(ui.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        ui.st.sidebar,
        "markdown",
        lambda *args, **kwargs: None,
    )

    ui.apply_styles()

    assert received_modes == ["dark"]


def test_brand_lockup_inlines_svg_not_img():
    html = ui.brand_lockup()

    assert "<svg" in html
    assert "<img" not in html
    assert "呆一布" in html


def test_mascot_svg_is_compact_for_streamlit_markdown():
    svg = ui.mascot_svg()

    assert "\n" not in svg


def test_apply_styles_places_brand_in_sidebar(monkeypatch):
    rendered = []
    monkeypatch.setattr(ui.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        ui.st.sidebar,
        "markdown",
        lambda body, **kwargs: rendered.append(body),
    )

    ui.apply_styles()

    assert "呆一布" in rendered[0]


def test_queued_toast_is_shown_once_on_the_next_run():
    state = {}
    rendered = []

    ui.queue_toast(state, "操作成功")
    ui.show_queued_toast(state, rendered.append)
    ui.show_queued_toast(state, rendered.append)

    assert rendered == ["操作成功"]
