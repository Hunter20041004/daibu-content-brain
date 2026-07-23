import tomllib
from pathlib import Path

from daibu import ui


ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_pages_use_current_width_argument():
    page_paths = [
        ROOT / "app.py",
        *(ROOT / "pages").glob("*.py"),
    ]
    source_texts = [path.read_text() for path in page_paths]

    assert all("use_container_width" not in source for source in source_texts)


def test_streamlit_theme_is_light_and_readable():
    with (ROOT / ".streamlit" / "config.toml").open("rb") as config_file:
        theme = tomllib.load(config_file)["theme"]

    assert theme["base"] == "light"
    assert theme["backgroundColor"] == "#f7f3ec"
    assert theme["secondaryBackgroundColor"] == "#fffdf9"
    assert theme["textColor"] == "#171513"


def test_connect_app_db_loads_dotenv(monkeypatch, tmp_path):
    loaded = []
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setattr(ui, "load_dotenv", lambda: loaded.append(True))

    conn = ui.connect_app_db()
    conn.close()

    assert loaded == [True]


def test_metric_text_uses_readable_colors(monkeypatch):
    rendered = []
    monkeypatch.setattr(
        ui.st,
        "markdown",
        lambda body, **kwargs: rendered.append(body),
    )

    ui.apply_styles()

    styles = rendered[0]
    assert '[data-testid="stMetricLabel"] *' in styles
    assert '[data-testid="stMetricValue"] *' in styles
    assert "color: var(--muted)" in styles
    assert "color: var(--ink)" in styles
