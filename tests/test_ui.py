import tomllib
from pathlib import Path

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


def test_brand_lockup_inlines_svg_not_img():
    html = ui.brand_lockup()

    assert "<svg" in html
    assert "<img" not in html
    assert "呆一布" in html
