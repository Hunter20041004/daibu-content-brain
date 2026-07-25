from pathlib import Path

from streamlit.testing.v1 import AppTest

from daibu import db, performance, seeds, selection
from daibu.llm import base
from daibu.llm.base import Idea
from daibu.models import Source, Theme

PROJECT_ROOT = Path(__file__).parents[1]


def test_app_entry_loads_without_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "app.py")
    app.run()

    assert not app.exception


def test_home_leads_with_the_next_action(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "待決策主題", 0, [], 1))
    db.add_idea(conn, theme_id, Idea("待決策候選", "角度", ""))

    app = AppTest.from_file(PROJECT_ROOT / "app.py")
    app.run()

    visible_text = " ".join(markdown.value for markdown in app.markdown)
    assert "1 則候選等你決定" in visible_text


def test_home_next_action_falls_back_when_nothing_pending(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setattr(seeds, "load", lambda conn: None)

    app = AppTest.from_file(PROJECT_ROOT / "app.py")
    app.run()

    visible_text = " ".join(markdown.value for markdown in app.markdown)
    assert "目前沒有待辦" in visible_text


def test_home_shows_the_week_schedule(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "app.py")
    app.run()

    visible_markdown = " ".join(markdown.value for markdown in app.markdown)
    for weekday in ("週一", "週二", "週三", "週四", "週五", "週六", "週日"):
        assert weekday in visible_markdown


def test_home_lists_each_theme_status(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(None, "近況來源", "https://example.com/feed", "rss", True),
    )
    theme_id = db.add_theme(
        conn,
        Theme(None, "近況主題", 2, [source_id], 1),
    )
    db.add_idea(
        conn,
        theme_id,
        Idea("已發布", "角度", ""),
        status="已發",
    )

    app = AppTest.from_file(PROJECT_ROOT / "app.py")
    app.run()

    status_rows = app.dataframe[0].value.to_dict("records")
    row = next(item for item in status_rows if item["主題"] == "近況主題")
    assert row["來源數"] == 1
    assert row["已發"] == 1


def test_home_does_not_count_unknown_publish_time_as_this_week(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "舊資料主題", 0, [], 1))
    db.add_idea(
        conn,
        theme_id,
        Idea("沒有發布時間的舊貼文", "角度", ""),
        status="已發",
    )

    app = AppTest.from_file(PROJECT_ROOT / "app.py")
    app.run()

    weekly_published = next(
        metric for metric in app.metric
        if metric.label == "本週已發"
    )
    assert weekly_published.value == "0"


def test_home_flags_themes_without_sources(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(conn, Theme(None, "需要來源的主題", 1, [], 1))

    app = AppTest.from_file(PROJECT_ROOT / "app.py")
    app.run()

    warning_text = " ".join(warning.value for warning in app.warning)
    assert "需要來源的主題" in warning_text
    assert "未綁來源" in warning_text


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


def test_selection_page_loads_without_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    assert not app.exception


def test_selection_lists_my_themes_in_the_left_column(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    for weekday, name in enumerate(("主題甲", "主題乙", "主題丙")):
        db.add_theme(conn, Theme(None, name, weekday, [], 1))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    button_labels = {button.label for button in app.button}
    assert {"主題甲", "主題乙", "主題丙"}.issubset(button_labels)


def test_selection_shows_the_selected_theme_workspace(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(None, "指定來源", "https://example.com/feed", "rss", True),
    )
    db.add_theme(conn, Theme(None, "第一個主題", 0, [source_id], 2))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    assert any(
        subheader.value == "第一個主題工作區"
        for subheader in app.subheader
    )
    source_checkbox = next(
        checkbox for checkbox in app.checkbox
        if checkbox.label == "指定來源"
    )
    assert source_checkbox.value is True


def test_selection_generates_for_the_selected_theme_only(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    first_id = db.add_theme(conn, Theme(None, "只產這個", 0, [], 1))
    db.add_theme(conn, Theme(None, "不要產這個", 1, [], 1))
    generated_theme_ids = []
    monkeypatch.setattr(base, "get_provider", lambda config: object())
    monkeypatch.setattr(
        selection,
        "generate_for_theme",
        lambda conn, theme, provider, sources: generated_theme_ids.append(
            theme.id
        ) or [],
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()
    next(
        button for button in app.button
        if button.label == "產生候選"
    ).click().run()

    assert generated_theme_ids == [first_id]


def test_selection_only_shows_candidates_of_the_selected_theme(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    first_id = db.add_theme(conn, Theme(None, "主題一", 0, [], 1))
    second_id = db.add_theme(conn, Theme(None, "主題二", 1, [], 1))
    db.add_idea(conn, first_id, Idea("只看這則", "角度一", ""))
    db.add_idea(conn, second_id, Idea("不該出現", "角度二", ""))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    visible_markdown = " ".join(markdown.value for markdown in app.markdown)
    assert "只看這則" in visible_markdown
    assert "不該出現" not in visible_markdown


def test_selection_warns_when_theme_has_no_sources(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(conn, Theme(None, "無來源主題", 0, [], 1))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    assert any(
        "只靠主題名發想" in warning.value
        for warning in app.warning
    )


def test_selection_lists_adopted_ideas_with_body_editor(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "寫作主題", 0, [], 1))
    db.add_idea(
        conn,
        theme_id,
        Idea("準備寫正文", "採用角度", ""),
        status="採用",
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    assert any("準備寫正文" in expander.label for expander in app.expander)
    assert any(
        text_area.label == "正文｜準備寫正文"
        for text_area in app.text_area
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
            0,
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
        if button.label == "產生候選"
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


def test_no_pipeline_page_exists():
    assert not any("流水線" in page.name for page in (PROJECT_ROOT / "pages").iterdir())


def test_performance_page_loads_without_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "pages/2_成效.py")
    app.run()

    assert not app.exception


def test_performance_shows_recommendation_before_chart(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "成效主題", 0, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("已發貼文", "切入角度", ""),
        status="已發",
    )
    performance.record(conn, idea_id, "Instagram", 10, 100, 5.0)

    app = AppTest.from_file(PROJECT_ROOT / "pages/2_成效.py")
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
