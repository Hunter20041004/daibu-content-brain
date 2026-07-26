import re
from datetime import date, timedelta
from pathlib import Path

from streamlit.testing.v1 import AppTest

from daibu import db, performance, pipeline, seeds, selection
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


def test_home_cta_targets_the_theme_with_candidates(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(conn, Theme(None, "沒有候選", 0, [], 1))
    target_theme_id = db.add_theme(
        conn,
        Theme(None, "有候選主題", 1, [], 1),
    )
    for index in range(2):
        db.add_idea(
            conn,
            target_theme_id,
            Idea(f"候選 {index}", "角度", ""),
        )

    app = AppTest.from_file(PROJECT_ROOT / "app.py")
    app.run()
    next(
        button for button in app.button
        if "有候選主題" in button.label
    ).click().run()

    assert any(
        subheader.value == "有候選主題工作區"
        for subheader in app.subheader
    )


def test_home_cta_names_target_theme_and_count(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 1, [], 3),
    )
    for index in range(3):
        db.add_idea(
            conn,
            theme_id,
            Idea(f"候選 {index}", "角度", ""),
        )

    app = AppTest.from_file(PROJECT_ROOT / "app.py")
    app.run()

    assert any(
        button.label == "去看「AI 新創介紹」的 3 則"
        for button in app.button
    )


def test_empty_candidate_state_points_at_the_right_button(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(conn, Theme(None, "等待產生", 0, [], 1))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    empty_state = " ".join(
        markdown.value for markdown in app.markdown
        if "尚無候選" in markdown.value
    )
    assert "左邊" not in empty_state
    assert "上方的「產生候選」" in empty_state


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


def test_home_counts_a_post_published_today(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "今天發布主題", 0, [], 1))
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("今天晚上發布", "角度", ""),
    )
    today_evening = f"{date.today().isoformat()} 20:09:00"
    monkeypatch.setattr(pipeline, "_now", lambda: today_evening)
    pipeline.set_status(conn, idea_id, "已發")

    app = AppTest.from_file(PROJECT_ROOT / "app.py")
    app.run()

    weekly_published = next(
        metric for metric in app.metric
        if metric.label == "本週已發"
    )
    assert weekly_published.value == "1"


def test_home_excludes_post_published_last_week(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "上週發布主題", 0, [], 1))
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("上週發布", "角度", ""),
    )
    previous_sunday = date.today() - timedelta(
        days=date.today().weekday() + 1,
    )
    last_week_evening = f"{previous_sunday.isoformat()} 20:09:00"
    monkeypatch.setattr(pipeline, "_now", lambda: last_week_evening)
    pipeline.set_status(conn, idea_id, "已發")

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


def test_rejecting_takes_a_single_click(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "淘汰流程", 0, [], 1))
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("一次淘汰這則", "不需要二次確認", ""),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()
    next(
        button for button in app.button
        if button.label == "淘汰"
    ).click().run()

    rejected = db.get_ideas(conn, status=pipeline.REJECTED)
    assert [idea.id for idea in rejected] == [idea_id]


def test_rejecting_offers_an_undo(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "可復原流程", 0, [], 1))
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("可以救回這則", "誤按也不怕", ""),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()
    next(
        button for button in app.button
        if button.label == "淘汰"
    ).click().run()
    undo = next(
        button for button in app.button
        if button.label == "復原剛剛淘汰的「可以救回這則」"
    )
    undo.click().run()

    restored = db.get_ideas(conn, status="候選")
    assert [idea.id for idea in restored] == [idea_id]


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


def test_source_library_shows_usage_count(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(
            None,
            "共用來源",
            "https://news.example.com/articles/ai",
            "rss",
            True,
        ),
    )
    db.add_theme(conn, Theme(None, "主題 A", 0, [source_id], 1))
    db.add_theme(conn, Theme(None, "主題 B", 1, [source_id], 1))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    visible_text = " ".join(
        element.value
        for elements in (app.markdown, app.caption)
        for element in elements
    )
    assert "共用來源" in visible_text
    assert "2 個主題在用" in visible_text


def test_source_library_summary_shows_domain_without_path(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_source(
        conn,
        Source(
            None,
            "精簡網址",
            "https://news.example.com/articles/ai",
            "search",
            True,
        ),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    source_summary = next(
        markdown.value for markdown in app.markdown
        if '<div class="source-row__summary">' in markdown.value
    )
    assert "news.example.com" in source_summary
    assert "/articles/ai" not in source_summary


def test_delete_source_warns_usage_count(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(None, "刪除前提醒", "https://example.com/feed", "rss", True),
    )
    db.add_theme(conn, Theme(None, "主題 A", 0, [source_id], 1))
    db.add_theme(conn, Theme(None, "主題 B", 1, [source_id], 1))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    warning_text = " ".join(warning.value for warning in app.warning)
    assert "這個來源正被 2 個主題使用" in warning_text


def test_delete_theme_warns_how_many_ideas_will_go(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "有內容主題", 0, [], 3))
    for index in range(2):
        db.add_idea(
            conn,
            theme_id,
            Idea(f"候選 {index}", "角度", ""),
        )
    db.add_idea(
        conn,
        theme_id,
        Idea("已發布", "角度", ""),
        status="已發",
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    warning_text = " ".join(warning.value for warning in app.warning)
    assert "2 則候選" in warning_text
    assert "1 則已發" in warning_text
    assert "無法復原" in warning_text


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


def test_adopted_idea_can_go_back_to_candidate(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "退回流程", 0, [], 1))
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("採用錯了這則", "可以退回", ""),
        status="採用",
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()
    next(
        button for button in app.button
        if button.label == "退回候選"
    ).click().run()

    candidates = db.get_ideas(conn, status="候選")
    assert [idea.id for idea in candidates] == [idea_id]
    assert any(
        "採用錯了這則" in markdown.value
        for markdown in app.markdown
    )


def test_published_idea_can_go_back_to_adopted(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "發布退回", 0, [], 1))
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("發布錯了這則", "退回繼續編輯", ""),
    )
    pipeline.set_status(conn, idea_id, "已發")

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()
    next(
        button for button in app.button
        if button.label == "退回已採用"
    ).click().run()

    adopted = db.get_ideas(conn, status="採用")
    assert [idea.id for idea in adopted] == [idea_id]
    assert adopted[0].published_at is None


def test_body_draft_survives_switching_themes(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    first_theme_id = db.add_theme(
        conn,
        Theme(None, "主題 A", 0, [], 1),
    )
    db.add_theme(conn, Theme(None, "主題 B", 1, [], 1))
    db.add_idea(
        conn,
        first_theme_id,
        Idea("準備寫正文", "採用角度", ""),
        status="採用",
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()
    app.text_area[0].set_value("切換主題也不能消失的正文")
    next(
        button for button in app.button
        if button.label == "主題 B"
    ).click().run()
    next(
        button for button in app.button
        if button.label == "主題 A"
    ).click().run()

    assert app.text_area[0].value == "切換主題也不能消失的正文"
    assert any(
        caption.value.startswith("已自動儲存於 ")
        for caption in app.caption
    )


def test_selected_theme_is_visually_marked(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(conn, Theme(None, "主題 A", 0, [], 1))
    db.add_theme(conn, Theme(None, "主題 B", 1, [], 1))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()
    next(
        button for button in app.button
        if button.label == "主題 B"
    ).click().run()

    theme_buttons = [
        button for button in app.button
        if button.label in {"主題 A", "主題 B"}
    ]
    assert [
        button.label for button in theme_buttons
        if button.proto.type == "primary"
    ] == ["主題 B"]


def test_adopting_shows_a_toast(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "採用主題", 0, [], 1),
    )
    db.add_idea(conn, theme_id, Idea("值得採用", "角度", ""))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()
    next(
        button for button in app.button
        if button.label == "採用"
    ).click().run()

    assert any(
        "已採用" in toast.value
        for toast in app.toast
    )


def test_success_messages_are_not_discarded_by_immediate_rerun():
    product_files = [
        *sorted((PROJECT_ROOT / "pages").glob("*.py")),
        PROJECT_ROOT / "daibu" / "overview.py",
    ]
    discarded_messages = []
    for path in product_files:
        source = path.read_text(encoding="utf-8")
        if re.search(r"st\.success\([^\n]*\)\s*\n\s*st\.rerun\(\)", source):
            discarded_messages.append(path.name)

    assert discarded_messages == []


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


def test_performance_form_clears_after_submit(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "成效表單", 0, [], 1))
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("要填成效這則", "角度", ""),
    )
    pipeline.set_status(conn, idea_id, "已發")

    app = AppTest.from_file(PROJECT_ROOT / "pages/2_成效.py")
    app.run()
    next(
        field for field in app.number_input
        if field.label == "讚"
    ).set_value(248)
    next(
        field for field in app.number_input
        if field.label == "觸及"
    ).set_value(5120)
    next(
        field for field in app.number_input
        if field.label == "互動"
    ).set_value(7.5)
    next(
        button for button in app.button
        if button.label == "儲存成效"
    ).click().run()

    values = {
        field.label: field.value
        for field in app.number_input
    }
    assert values == {"讚": 0, "觸及": 0, "互動": 0.0}


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
