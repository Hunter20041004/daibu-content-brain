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


def test_main_navigation_uses_product_language():
    app_source = (ROOT / "app.py").read_text()

    for label in ("工作台", "內容製作", "成效", "系統設定"):
        assert f'title="{label}"' in app_source
    assert 'title="概覽"' not in app_source
    assert 'title="選題"' not in app_source


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


def test_carousel_checklist_replaces_decorative_side_stripes():
    styles = theme.css("light")

    assert ".carousel-checklist" in styles
    assert ".carousel-checklist__item--current" in styles
    assert "border-left: 4px solid var(--highlight)" not in styles
    assert "border-left: 3px solid var(--brand-primary)" not in styles


def test_carousel_preview_uses_one_responsive_ordered_grid():
    page_source = (ROOT / "pages" / "1_選題.py").read_text()
    styles = theme.css("light")

    assert "preview_columns[index % 2]" not in page_source
    assert "carousel-preview-grid-" in page_source
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in styles
    assert "grid-template-columns: minmax(0, 1fr)" in styles


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


def test_mascot_coach_uses_pose_and_accessible_status_copy():
    coach = ui.mascot_coach(
        "point",
        "今天先做這一步",
        "挑一則候選，其他工具先不用管。",
    )

    assert "mascot-coach" in coach
    assert "今天先做這一步" in coach
    assert "挑一則候選" in coach
    assert "aria-label=" in coach
    assert ui.mascot_svg(pose="point") in coach


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
