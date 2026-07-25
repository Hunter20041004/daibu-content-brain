from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest

from daibu import db, performance, pipeline, selection
from daibu.llm import base
from daibu.llm.base import Idea
from daibu.models import Theme

PROJECT_ROOT = Path(__file__).parents[1]


def test_app_entry_loads_without_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "app.py")
    app.run()

    assert not app.exception


def test_home_shows_single_primary_action(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "app.py")
    app.run()

    assert not app.exception
    primary_actions = [
        button for button in app.button
        if button.proto.type == "primary"
    ]
    assert len(primary_actions) == 1


def test_home_renders_mascot_without_code_block(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "app.py")
    app.run()

    assert not app.exception
    assert len(app.code) == 0


def test_selection_page_loads_without_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    assert not app.exception


def test_selection_score_stays_readable_in_narrow_card(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_idea(
        conn,
        None,
        Idea("候選標題", "切入角度", 88, "守門理由", ""),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    score_badges = [
        markdown.value
        for markdown in app.markdown
        if "score-badge" in markdown.value
    ]
    assert any("88" in badge for badge in score_badges)
    assert len(app.metric) == 0


def test_selection_uses_configured_gate_line(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(
        conn,
        Theme(
            None,
            "今天主題",
            date.today().weekday(),
            "evergreen",
            [],
            1,
        ),
    )
    db.set_config(conn, "gate_line", "自訂守門線")
    received_gate_lines = []
    monkeypatch.setattr(base, "get_provider", lambda config: object())
    monkeypatch.setattr(
        selection,
        "generate_for_theme",
        lambda conn, theme, provider, sources, gate_line: (
            received_gate_lines.append(gate_line) or []
        ),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()
    next(
        button
        for button in app.button
        if button.label == "產生本週選題"
    ).click().run()

    assert received_gate_lines
    assert set(received_gate_lines) == {"自訂守門線"}


def test_selection_shows_configured_gate_line(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.set_config(conn, "gate_line", "畫面上的自訂守門線")

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    assert any(
        "畫面上的自訂守門線" in markdown.value
        for markdown in app.markdown
    )


def test_selection_uses_configured_llm_provider(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(
        conn,
        Theme(
            None,
            "今天主題",
            date.today().weekday(),
            "evergreen",
            [],
            1,
        ),
    )
    db.set_config(conn, "llm_provider", "groq")
    db.set_config(conn, "llm_model", "custom-model")
    received_configs = []
    monkeypatch.setattr(base, "get_provider_from_env", lambda: object())
    monkeypatch.setattr(
        base,
        "get_provider",
        lambda config: received_configs.append(config.copy()) or object(),
    )
    monkeypatch.setattr(
        selection,
        "generate_for_theme",
        lambda *args, **kwargs: [],
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()
    next(
        button
        for button in app.button
        if button.label == "產生本週選題"
    ).click().run()

    assert received_configs[0]["LLM_PROVIDER"] == "groq"
    assert received_configs[0]["LLM_MODEL"] == "custom-model"


def test_settings_page_loads_without_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "pages/3_設定.py")
    app.run()

    assert not app.exception


def test_settings_page_only_keeps_system_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "pages/3_設定.py")
    app.run()

    visible_text = " ".join(
        element.value
        for elements in (
            app.title,
            app.subheader,
            app.markdown,
            app.caption,
        )
        for element in elements
    )
    assert "守門線" not in visible_text
    assert "大主題" not in visible_text
    assert "來源白名單" not in visible_text


def test_pipeline_page_loads_without_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "pages/2_流水線.py")
    app.run()

    assert not app.exception


def test_pipeline_shows_five_statuses_without_inline_editor(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_idea(
        conn,
        None,
        Idea("看板卡片", "切入角度", 80, "守門理由", ""),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/2_流水線.py")
    app.run()

    subheaders = {subheader.value for subheader in app.subheader}
    assert set(pipeline.STATUSES).issubset(subheaders)
    assert len(app.text_area) == 0


def test_pipeline_opens_editor_only_after_card_click(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_idea(
        conn,
        None,
        Idea("點我編輯", "切入角度", 80, "守門理由", ""),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/2_流水線.py")
    app.run()
    next(button for button in app.button if button.label == "點我編輯").click().run()

    assert not app.exception
    assert len(app.text_area) == 1


def test_performance_page_loads_without_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "pages/3_成效.py")
    app.run()

    assert not app.exception


def test_performance_shows_recommendation_before_chart(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "成效主題", 0, "evergreen", [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("已發貼文", "切入角度", 80, "守門理由", ""),
        status="已發",
    )
    performance.record(conn, idea_id, "Instagram", 10, 100, 5.0)

    app = AppTest.from_file(PROJECT_ROOT / "pages/3_成效.py")
    app.run()

    def walk(block):
        for child in block.children.values():
            yield child
            if hasattr(child, "children"):
                yield from walk(child)

    elements = list(walk(app._tree[0]))
    recommendation_index = next(
        index
        for index, element in enumerate(elements)
        if element.type == "markdown"
        and '<div class="suggestion-card">' in element.value
    )
    chart_index = next(
        index
        for index, element in enumerate(elements)
        if element.type == "vega_lite_chart"
    )

    assert not app.exception
    assert recommendation_index < chart_index
