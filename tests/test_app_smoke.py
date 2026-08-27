import json
import logging
import re
from datetime import date, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from daibu import (
    copywriting,
    db,
    performance,
    pipeline,
    seeds,
    selection,
    startup_discovery,
)
from daibu.fetch import page as page_fetch
from daibu.llm import base
from daibu.llm.base import Idea
from daibu.models import CompanyEligibility, Source, SourceSuggestion, Theme

PROJECT_ROOT = Path(__file__).parents[1]


def test_app_entry_loads_without_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "app.py")
    app.run()

    assert not app.exception


def test_settings_exposes_series_template_management(monkeypatch,tmp_path):
    from daibu.cards import template_editor_component,template_editor_ui
    database_path=tmp_path/"settings.db";monkeypatch.setenv("DAIBU_DB_PATH",str(database_path))
    conn=db.connect(str(database_path));db.init_schema(conn);db.add_theme(conn,Theme(None,"AI 新創介紹",4,[],1))
    monkeypatch.setattr(template_editor_ui,"mount_template_editor",lambda payload,*,key:template_editor_component.TemplateEditorEvent(False,None))
    app=AppTest.from_file(PROJECT_ROOT/"pages/3_設定.py").run()
    text=" ".join(item.value for item in [*app.subheader,*app.caption])
    assert not app.exception
    assert "系統設定" in text and "系列模板管理" in text


def test_home_is_a_guided_multi_series_workstation(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "app.py")
    app.run()

    visible_text = " ".join(
        element.value
        for element in [*app.markdown, *app.title, *app.subheader]
    )
    assert "今日下一步" in visible_text
    assert "我的內容系列" in visible_text
    assert "情況概覽" not in visible_text


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
    assert "目前沒有內容系列" in visible_text


def test_home_empty_series_points_to_project_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setattr(seeds, "load", lambda conn: None)

    app = AppTest.from_file(PROJECT_ROOT / "app.py").run()

    visible_text = " ".join(
        element.value for elements in (app.markdown, app.info)
        for element in elements
    )
    assert "目前沒有內容系列；到內容製作頁用「新增內容系列」建立第一個。" in visible_text
    assert "先建立第一個內容系列" not in visible_text


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
    assert "上方的「開始找題材」" in empty_state


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
    row = next(
        item for item in status_rows if item["內容系列"] == "近況主題"
    )
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


def test_candidate_comparison_shows_one_detail_at_a_time(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "AI 新創介紹", 0, [], 2))
    db.add_idea(conn, theme_id, Idea("候選甲", "角度甲", ""))
    db.add_idea(conn, theme_id, Idea("候選乙", "角度乙", ""))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run(timeout=10)

    candidate_details = [
        markdown.value
        for markdown in app.markdown
        if markdown.value.startswith('<h3 class="candidate-card__title">')
    ]
    assert len(candidate_details) == 1
    candidate_buttons = {
        button.label
        for button in app.button
        if button.label.startswith("查看｜")
    }
    assert candidate_buttons == {"查看｜候選甲", "查看｜候選乙"}


def test_candidate_stage_has_one_primary_decision(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "決策系列", 0, [], 1))
    db.add_idea(conn, theme_id, Idea("只判斷這則", "角度", ""))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()

    assert [
        button.label
        for button in app.button
        if button.proto.type == "primary"
    ] == ["採用並繼續寫內容"]


def test_content_workstation_names_the_four_step_journey(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()

    visible_text = " ".join(
        element.value
        for elements in (app.markdown, app.title, app.subheader)
        for element in elements
    )
    visible_text += " " + " ".join(expander.label for expander in app.expander)
    for step in ("找題材", "選一則", "寫內容", "做輪播"):
        assert step in visible_text
    assert "我的內容系列" in visible_text
    assert "素材來源庫" in visible_text
    assert "選題工作台" not in visible_text


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


def test_selection_hides_manual_series_creation_but_lists_code_added_series(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(conn, Theme(None, "程式新增系列", 2, [], 2))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()

    button_labels = {button.label for button in app.button}
    assert "程式新增系列" in button_labels
    assert "＋ 新增內容系列" not in button_labels
    assert "建立內容系列" not in button_labels


def test_selection_empty_series_points_at_the_form_on_this_page(
    monkeypatch,
    tmp_path,
):
    """在內容製作頁上，空狀態要指向同一頁的表單，不是叫使用者去別頁。"""
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setattr(seeds, "load", lambda conn: None)

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()

    visible_text = " ".join(markdown.value for markdown in app.markdown)
    assert "目前沒有內容系列；用左邊的「新增內容系列」建立第一個。" in visible_text
    assert "到內容製作頁" not in visible_text, "已經在這一頁了，不該叫使用者再過來"


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


def test_company_series_keeps_its_internal_kind_after_settings_save(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(
            None,
            "AI 新創介紹",
            4,
            [],
            3,
            content_kind="company_profile",
        ),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        button for button in app.button
        if button.label == "儲存內容系列設定"
    ).click().run()

    stored = {theme.id: theme for theme in db.get_themes(conn)}[theme_id]
    assert stored.name == "AI 新創介紹"
    assert stored.content_kind == "company_profile"


def test_selecting_theme_requests_scroll_to_its_workspace(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(conn, Theme(None, "第一個主題", 0, [], 1))
    db.add_theme(conn, Theme(None, "第二個主題", 1, [], 1))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()
    next(
        button for button in app.button
        if button.label == "第二個主題"
    ).click().run()

    scroll_markup = " ".join(
        markdown.value for markdown in app.markdown
        if "theme-workspace" in markdown.value
    )
    assert 'id="theme-workspace"' in scroll_markup
    assert 'data-scroll-requested="true"' in scroll_markup


def test_selecting_theme_uses_the_supported_iframe_api(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(conn, Theme(None, "第一個主題", 0, [], 1))
    db.add_theme(conn, Theme(None, "第二個主題", 1, [], 1))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()
    next(
        button for button in app.button
        if button.label == "第二個主題"
    ).click().run()

    assert not app.exception


def test_workspace_scroll_iframe_has_a_body_for_auto_sizing():
    page_source = (
        PROJECT_ROOT / "pages/1_選題.py"
    ).read_text(encoding="utf-8")

    assert "<body>" in page_source
    assert "</body>" in page_source


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
        lambda conn, theme, provider, sources, **_kwargs: generated_theme_ids.append(
            theme.id
        ) or [],
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()
    next(
        button for button in app.button
        if button.label == "開始找題材"
    ).click().run()

    assert generated_theme_ids == [first_id]


def test_generated_candidates_get_a_mascot_completion_state(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "完成提示", 0, [], 1))
    monkeypatch.setattr(base, "get_provider", lambda config: object())

    def generate(conn, theme, provider, sources, **_kwargs):
        return [db.add_idea(conn, theme.id, Idea("整理完成", "角度", ""))]

    monkeypatch.setattr(selection, "generate_for_theme", generate)

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        button for button in app.button if button.label == "開始找題材"
    ).click().run()

    success_coach = " ".join(
        markdown.value
        for markdown in app.markdown
        if "mascot-coach--success" in markdown.value
    )
    assert "候選整理好了" in success_coach


def test_generation_error_uses_mascot_recovery_state(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(conn, Theme(None, "失敗提示", 0, [], 1))
    monkeypatch.setattr(base, "get_provider", lambda config: object())
    monkeypatch.setattr(
        selection,
        "generate_for_theme",
        lambda *args: (_ for _ in ()).throw(RuntimeError("暫時連不上")),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        button for button in app.button if button.label == "開始找題材"
    ).click().run()

    recovery = " ".join(
        markdown.value
        for markdown in app.markdown
        if "mascot-coach--warning" in markdown.value
    )
    rendered = " ".join(markdown.value for markdown in app.markdown)
    assert "這次沒有成功，但原本內容都還在" in recovery
    assert "呆一布正在讀資料" not in rendered


def _render_generation_error(monkeypatch, tmp_path, error):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1, "company_profile"),
    )
    monkeypatch.setattr(base, "get_provider", lambda _config: object())

    def raise_product_error(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(
        selection,
        "generate_for_theme",
        raise_product_error,
    )
    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        button for button in app.button if button.label == "開始找題材"
    ).click().run()

    return " ".join(item.value for item in app.error)


def test_generation_shows_precise_no_source_error(monkeypatch, tmp_path):
    rendered = _render_generation_error(
        monkeypatch,
        tmp_path,
        startup_discovery.NoAvailableStartupSourcesError("raw detail"),
    )

    assert "目前沒有可用的公司來源" in rendered
    assert "產生失敗：" not in rendered
    assert "raw detail" not in rendered


def test_ai_startup_rerun_button_says_five(monkeypatch, tmp_path):
    database_path = tmp_path / "five-button.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    seeds.load(conn)
    theme = db.get_themes(conn)[0]
    db.add_idea(
        conn,
        theme.id,
        Idea(
            "Existing company",
            "Existing angle",
            "https://example.com/existing",
            company="ExistingCo",
            source_excerpt="Existing company evidence",
        ),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()

    assert any(button.label == "再產生 5 則" for button in app.button)


def test_generation_shows_precise_repeated_company_error(
    monkeypatch,
    tmp_path,
):
    rendered = _render_generation_error(
        monkeypatch,
        tmp_path,
        startup_discovery.AllStartupCompaniesRepeatedError("raw detail"),
    )

    assert "這批來源裡的公司都介紹過了" in rendered
    assert "raw detail" not in rendered


def test_generation_shows_precise_ineligible_company_error(
    monkeypatch,
    tmp_path,
):
    rendered = _render_generation_error(
        monkeypatch,
        tmp_path,
        selection.NoVerifiedCompanyCandidatesError("raw detail"),
    )

    assert "找到公司，但沒有符合本系列資格的公司" in rendered
    assert "raw detail" not in rendered


def test_generation_shows_precise_company_classification_error(
    monkeypatch,
    tmp_path,
):
    rendered = _render_generation_error(
        monkeypatch,
        tmp_path,
        selection.CompanyClassificationError("raw detail"),
    )

    assert "公司主類別分類暫時失敗" in rendered
    assert "原本內容都還在" in rendered
    assert "raw detail" not in rendered


def test_generation_shows_company_diversity_shortage_details(
    monkeypatch,
    tmp_path,
):
    message = (
        "已檢查 40 家；目前可用分類：AI 基礎建設 9 家、"
        "企業／產業應用 2 家。無法湊出 5 家且至少 3 類，"
        "這次沒有新增候選。"
    )
    rendered = _render_generation_error(
        monkeypatch,
        tmp_path,
        selection.InsufficientCompanyDiversityError(message),
    )

    assert "已檢查 40 家" in rendered
    assert "AI 基礎建設 9 家" in rendered
    assert "無法湊出 5 家且至少 3 類" in rendered


def test_generation_shows_precise_gemini_unavailable_error(
    monkeypatch,
    tmp_path,
):
    rendered = _render_generation_error(
        monkeypatch,
        tmp_path,
        base.LLMUnavailableError("raw detail"),
    )

    assert "Gemini 暫時繁忙" in rendered
    assert "raw detail" not in rendered


def test_generation_shows_precise_gemini_quota_error(monkeypatch, tmp_path):
    rendered = _render_generation_error(
        monkeypatch,
        tmp_path,
        base.LLMQuotaError("raw quota detail"),
    )

    assert "Gemini 免費額度已用完" in rendered
    assert "可以切換 Groq" in rendered
    assert "raw quota detail" not in rendered


def test_generation_shows_precise_gemini_timeout_error(monkeypatch, tmp_path):
    rendered = _render_generation_error(
        monkeypatch,
        tmp_path,
        base.LLMTimeoutError("raw timeout detail"),
    )

    assert "Gemini 回應超時" in rendered
    assert "raw timeout detail" not in rendered


def test_generation_shows_precise_eligibility_service_error(
    monkeypatch,
    tmp_path,
):
    rendered = _render_generation_error(
        monkeypatch,
        tmp_path,
        selection.CompanyEligibilityVerificationError(
            "raw eligibility detail"
        ),
    )

    assert "公司資格查核暫時失敗" in rendered
    assert "這次沒有新增候選" in rendered
    assert "raw eligibility detail" not in rendered


def test_generation_shows_precise_model_response_error(monkeypatch, tmp_path):
    rendered = _render_generation_error(
        monkeypatch,
        tmp_path,
        base.LLMResponseError("raw model response"),
    )

    assert "模型回覆格式不完整" in rendered
    assert "原本內容都還在" in rendered
    assert "raw model response" not in rendered


def test_unknown_generation_error_logs_only_safe_error_types(
    monkeypatch,
    tmp_path,
    caplog,
):
    error = RuntimeError("raw outer secret")
    error.__cause__ = ValueError("raw cause secret")
    caplog.set_level(logging.WARNING)

    rendered = _render_generation_error(monkeypatch, tmp_path, error)
    messages = " ".join(record.getMessage() for record in caplog.records)

    assert "這次沒有完成" in rendered
    assert "generation_failed" in messages
    assert "error_type=RuntimeError" in messages
    assert "cause_type=ValueError" in messages
    assert "raw outer secret" not in messages
    assert "raw cause secret" not in messages


def test_directory_source_rejects_an_unapproved_url(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        field for field in app.text_input if field.label == "新來源名稱"
    ).set_value("Unknown Directory")
    next(
        field for field in app.text_input if field.label == "新來源網址"
    ).set_value("https://evil.example/companies")
    next(
        field
        for field in app.selectbox
        if field.label == "新來源抓取方式"
    ).set_value("directory")
    next(
        button for button in app.button if button.label == "新增來源"
    ).click().run()

    assert any(
        "公司目錄只支援已核可的三個網址" in item.value
        for item in app.error
    )
    conn = db.connect(str(database_path))
    assert "Unknown Directory" not in {
        source.name for source in db.get_sources(conn)
    }


def test_generation_renders_safe_source_warning(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1, "company_profile"),
    )
    monkeypatch.setattr(base, "get_provider", lambda _config: object())

    def warn_then_fail(*_args, warning_sink=None, **_kwargs):
        assert warning_sink is not None
        warning_sink("YC Launches 暫時讀不到，已改用其他來源。")
        raise startup_discovery.NoAvailableStartupSourcesError("raw detail")

    monkeypatch.setattr(selection, "generate_for_theme", warn_then_fail)
    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        button for button in app.button if button.label == "開始找題材"
    ).click().run()

    assert any(
        "YC Launches 暫時讀不到" in item.value
        for item in app.warning
    )


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
        "只依系列名稱發想" in warning.value
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
    assert "2 個內容系列在用" in visible_text


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
    assert "這個來源正被 2 個內容系列使用" in warning_text


def test_home_empty_state_points_at_a_real_entry_point(monkeypatch, tmp_path):
    """空狀態不能把使用者指去一個沒有這個功能的頁面。"""
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.set_config(conn, "seeds_loaded", "1")

    for page in ("app.py", "pages/1_選題.py"):
        app = AppTest.from_file(PROJECT_ROOT / page)
        app.run()

        visible_text = " ".join(
            element.value
            for element in [
                *app.markdown,
                *app.title,
                *app.subheader,
                *app.info,
                *app.warning,
                *app.caption,
            ]
        )
        assert "專案設定" not in visible_text, (
            f"{page} 把使用者指去設定頁，但那裡沒有新增內容系列的功能"
        )
        assert "新增內容系列" in visible_text, f"{page} 沒有給出真正能用的入口"


def test_selection_can_create_a_series_when_none_are_left(monkeypatch, tmp_path):
    """使用者可以把內容系列全部刪掉，而種子資料只會載入一次。

    沒有新增入口的話，刪光之後這個工具從介面上就再也回不來了。
    """
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.set_config(conn, "seeds_loaded", "1")

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    assert not app.exception
    assert not db.get_themes(conn), "前置條件：這個測試要從零個系列開始"

    app.text_input(key="new-theme-name").set_value("AI 工具週報")
    next(
        button for button in app.button
        if "建立內容系列" in button.label
    ).click().run()

    assert [theme.name for theme in db.get_themes(conn)] == ["AI 工具週報"]


def test_delete_theme_warns_how_many_ideas_will_go(monkeypatch, tmp_path):
    from daibu.cards import layout_repository

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
    layout_repository.ensure_default_version(conn, theme_id)

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    warning_text = " ".join(warning.value for warning in app.warning)
    assert "2 則候選" in warning_text
    assert "1 則已發" in warning_text
    assert "1 個模板版本" in warning_text
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
        text_area.label == "正文"
        for text_area in app.text_area
    )
    assert not any(
        button.label == "AI 幫我寫初稿" for button in app.button
    )


def test_blank_adopted_company_shows_primary_ai_copy_button(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(
            None,
            "AI 新創介紹",
            4,
            [],
            1,
            content_kind="company_profile",
        ),
    )
    db.add_idea(
        conn,
        theme_id,
        Idea(
            "用 AI 整理客服信件",
            "工作流程正在改變",
            "https://example.com/acme",
            company="Acme",
        ),
        status="採用",
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()

    ai_button = next(
        button for button in app.button
        if button.label == "AI 幫我寫初稿"
    )
    save_button = next(
        button for button in app.button
        if button.label == "儲存並繼續做輪播"
    )
    assert ai_button.disabled is False
    assert ai_button.proto.type == "primary"
    assert save_button.proto.type == "secondary"


def test_ai_copy_generation_loads_and_saves_the_new_draft(
    monkeypatch,
    tmp_path,
):
    from tests.card_fixtures import verified_sources

    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(
            None,
            "TechCrunch",
            "https://techcrunch.com/feed",
            "rss",
            True,
        ),
    )
    theme_id = db.add_theme(
        conn,
        Theme(
            None,
            "AI 新創介紹",
            4,
            [source_id],
            1,
            content_kind="company_profile",
        ),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            "用 AI 整理客服信件",
            "工作流程正在改變",
            "https://example.com/acme",
            company="Acme",
        ),
        status="採用",
    )
    calls = []

    def fake_generate(
        service_conn,
        idea,
        configured_domains,
        generate_text,
        **kwargs,
    ):
        calls.append((tuple(configured_domains), kwargs))
        assert callable(generate_text)
        body = "文" * 350
        db.save_copy_draft(
            service_conn,
            idea.id,
            verified_sources(),
            body,
        )
        return body

    monkeypatch.setattr(copywriting, "generate", fake_generate)
    monkeypatch.setattr(
        base,
        "get_provider",
        lambda _config: type(
            "Provider",
            (),
            {"generate_text": lambda self, _prompt: "文" * 350},
        )(),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        button for button in app.button
        if button.label == "AI 幫我寫初稿"
    ).click().run(timeout=20)

    stored = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    assert calls == [
        (
            (
                "www.ycombinator.com",
                "speedrun.a16z.com",
                "techcrunch.com",
            ),
            {"official_domains": ()},
        )
    ]
    assert stored.body == "文" * 350
    assert next(area for area in app.text_area if area.label == "正文").value == (
        "文" * 350
    )
    rendered = " ".join(block.value for block in app.markdown)
    assert "初稿準備好了" in rendered


def test_body_editor_refreshes_when_copy_changes_outside_current_session(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "寫作主題", 0, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("跨頁更新正文", "採用角度", ""),
        status="採用",
    )
    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run(timeout=10)
    body_editor = next(
        area for area in app.text_area if area.label == "正文"
    )
    assert body_editor.value == ""

    pipeline.update_body(conn, idea_id, "另一個流程剛產生的新正文")
    app.run(timeout=10)

    refreshed_editor = next(
        area for area in app.text_area if area.label == "正文"
    )
    assert refreshed_editor.value == "另一個流程剛產生的新正文"


def test_ai_copy_error_keeps_current_data_and_shows_recovery(
    monkeypatch,
    tmp_path,
):
    from tests.card_fixtures import verified_sources

    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(
            None,
            "AI 新創介紹",
            4,
            [],
            1,
            content_kind="company_profile",
        ),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("公司定位", "角度", "", company="Acme"),
        status="採用",
    )
    original_sources = verified_sources()[:1]
    db.save_idea_sources(conn, idea_id, original_sources)
    monkeypatch.setattr(
        copywriting,
        "generate",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("可信網域沒有資料")
        ),
    )
    monkeypatch.setattr(
        base,
        "get_provider",
        lambda _config: type(
            "Provider",
            (),
            {"generate_text": lambda self, _prompt: ""},
        )(),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        button for button in app.button
        if button.label == "AI 幫我寫初稿"
    ).click().run()

    stored = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    assert stored.body == ""
    assert db.get_idea_sources(conn, idea_id) == original_sources
    assert any("可信網域沒有資料" in error.value for error in app.error)
    rendered = " ".join(block.value for block in app.markdown)
    assert "這次沒有寫進去" in rendered


def test_existing_copy_requires_confirmation_before_regeneration(
    monkeypatch,
    tmp_path,
):
    from tests.card_fixtures import verified_sources

    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(
            None,
            "AI 新創介紹",
            4,
            [],
            1,
            content_kind="company_profile",
        ),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("公司定位", "角度", "", company="Acme"),
        status="採用",
    )
    pipeline.update_body(conn, idea_id, "原本正文")
    calls = []

    def fake_generate(
        service_conn,
        idea,
        configured_domains,
        generate_text,
        **kwargs,
    ):
        del configured_domains, generate_text, kwargs
        calls.append(idea.id)
        body = "新" * 350
        db.save_copy_draft(
            service_conn,
            idea.id,
            verified_sources(),
            body,
        )
        return body

    monkeypatch.setattr(copywriting, "generate", fake_generate)
    monkeypatch.setattr(
        base,
        "get_provider",
        lambda _config: type(
            "Provider",
            (),
            {"generate_text": lambda self, _prompt: "新" * 350},
        )(),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run(timeout=10)

    assert not any(
        button.label == "AI 幫我寫初稿" for button in app.button
    )
    assert "重新產生初稿" in {
        expander.label for expander in app.expander
    }
    confirm = next(
        checkbox for checkbox in app.checkbox
        if checkbox.label.startswith("我知道會覆蓋目前正文")
    )
    regenerate = next(
        button for button in app.button
        if button.label == "確認重新產生初稿"
    )
    assert regenerate.disabled
    assert calls == []

    confirm.set_value(True).run()
    assert calls == []
    next(
        button for button in app.button
        if button.label == "確認重新產生初稿"
    ).click().run()

    stored = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    assert calls == [idea_id]
    assert stored.body == "新" * 350


def test_writing_workspace_opens_one_adopted_idea_at_a_time(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "寫作系列", 0, [], 2))
    db.add_idea(
        conn, theme_id, Idea("正文甲", "角度甲", ""), status="採用"
    )
    db.add_idea(
        conn, theme_id, Idea("正文乙", "角度乙", ""), status="採用"
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()

    assert len([area for area in app.text_area if area.label == "正文"]) == 1
    writing_labels = {
        button.label
        for button in app.button
        if "編輯｜" in button.label
    }
    assert {
        label.replace("正在編輯｜", "編輯｜")
        for label in writing_labels
    } == {"編輯｜正文甲", "編輯｜正文乙"}
    assert sum(label.startswith("正在編輯｜") for label in writing_labels) == 1


def test_selecting_adopted_idea_marks_it_and_requests_editor_scroll(
    monkeypatch,
    tmp_path,
):
    import streamlit as st

    iframe_calls = []
    original_iframe = st.iframe

    def capture_iframe(*args, **kwargs):
        iframe_calls.append(kwargs)
        return original_iframe(*args, **kwargs)

    monkeypatch.setattr(st, "iframe", capture_iframe)
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "寫作系列", 0, [], 2))
    first_id = db.add_idea(
        conn, theme_id, Idea("正文甲", "角度甲", ""), status="採用"
    )
    second_id = db.add_idea(
        conn, theme_id, Idea("正文乙", "角度乙", ""), status="採用"
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    edit_button = next(
        button for button in app.button
        if button.label.startswith("編輯｜")
    )
    selected_title = edit_button.label.removeprefix("編輯｜")
    selected_id = first_id if selected_title == "正文甲" else second_id
    edit_button.click().run()

    assert any(
        button.label == f"正在編輯｜{selected_title}"
        for button in app.button
    )
    scroll_markup = " ".join(
        markdown.value for markdown in app.markdown
        if f"adopted-editor-{selected_id}" in markdown.value
    )
    assert f'id="adopted-editor-{selected_id}"' in scroll_markup
    assert 'data-scroll-requested="true"' in scroll_markup
    assert iframe_calls[-1]["height"] == 1


def test_writing_stage_hides_earlier_research_and_candidate_tools(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "連續寫作", 0, [], 2))
    db.add_idea(conn, theme_id, Idea("稍後再選", "角度", ""))
    db.add_idea(
        conn, theme_id, Idea("現在寫這則", "角度", ""), status="採用"
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()

    assert not any(
        button.label.startswith(("查看｜", "再產生", "開始找題材"))
        for button in app.button
    )
    assert any(area.label == "正文" for area in app.text_area)


def test_carousel_prerequisites_are_one_linear_checklist(
    monkeypatch,
    tmp_path,
):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "輪播系列", 0, [], 1))
    db.add_idea(
        conn, theme_id, Idea("準備輪播", "角度", ""), status="採用"
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()

    checklist = next(
        markdown.value
        for markdown in app.markdown
        if 'class="carousel-checklist"' in markdown.value
    )
    for label in (
        "公司名稱",
        "這篇內容的查證證據",
        "官方 Logo",
            "六頁草稿",
            "六張圖片",
    ):
        assert label in checklist
    assert checklist.count("carousel-checklist__item--current") == 1


def test_publish_is_disabled_when_body_is_empty(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "空白正文主題", 0, [], 1),
    )
    db.add_idea(
        conn,
        theme_id,
        Idea("還不能發布", "採用角度", ""),
        status="採用",
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    publish_button = next(
        button for button in app.button
        if button.label == "標記已發"
    )
    assert publish_button.disabled


def test_save_and_continue_is_the_primary_editor_action(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "正文動作主題", 0, [], 1),
    )
    db.add_idea(
        conn,
        theme_id,
        Idea("安全儲存優先", "採用角度", ""),
        status="採用",
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    save_button = next(
        button for button in app.button
        if button.label == "儲存並繼續做輪播"
    )
    publish_button = next(
        button for button in app.button
        if button.label == "標記已發"
    )
    assert save_button.proto.type == "primary"
    assert publish_button.proto.type == "secondary"


def test_body_editor_shows_character_count(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "字數主題", 0, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("檢查平台長度", "採用角度", ""),
        status="採用",
    )
    pipeline.update_body(conn, idea_id, "文" * 128)

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()

    visible_captions = " ".join(
        caption.value for caption in app.caption
    )
    assert "128 字 · Threads 還可寫 372" in visible_captions


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

    current_marker = " ".join(
        markdown.value
        for markdown in app.markdown
        if "theme-item__current" in markdown.value
    )
    assert "目前 · 主題 B" in current_marker


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
        if button.label == "採用並繼續寫內容"
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
            if button.label == "開始找題材"
    ).click().run()

    assert received_configs[0]["LLM_PROVIDER"] == "groq"
    assert received_configs[0]["LLM_MODEL"] == "custom-model"


def test_newly_generated_candidates_are_marked(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    db.add_theme(
        conn,
        Theme(None, "新候選主題", 0, [], 1),
    )
    monkeypatch.setattr(base, "get_provider", lambda config: object())

    def generate_candidate(
        conn,
        selected_theme,
        provider,
        sources,
        **_kwargs,
    ):
        return [
            db.add_idea(
                conn,
                selected_theme.id,
                Idea("剛生成的候選", "新角度", ""),
            ),
        ]

    monkeypatch.setattr(
        selection,
        "generate_for_theme",
        generate_candidate,
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py")
    app.run()
    next(
        button for button in app.button
        if button.label == "開始找題材"
    ).click().run()

    assert any(
        '<span class="candidate-card__new">新</span>'
        in markdown.value
        for markdown in app.markdown
    )


def test_settings_page_loads_without_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "pages/3_設定.py")
    app.run()

    assert not app.exception


def test_settings_separates_gemma_ideas_from_gemini_carousels(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "pages/3_設定.py")
    app.run()

    idea_model_field = next(
        field for field in app.text_input
        if field.label == "選題主要模型"
    )
    fallback_model_field = next(
        field for field in app.text_input
        if field.label == "正文、備援與輪播模型"
    )
    assert idea_model_field.value == "gemma-4-26b-a4b-it"
    assert fallback_model_field.value == "gemini-3.5-flash-lite"


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


def test_settings_reports_key_status(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    for key_name in (
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "TAVILY_API_KEY",
    ):
        monkeypatch.delenv(key_name, raising=False)

    unset_app = AppTest.from_file(PROJECT_ROOT / "pages/3_設定.py")
    unset_app.run()
    unset_text = " ".join(
        caption.value for caption in unset_app.caption
    )

    assert "Gemini 金鑰：尚未設定" in unset_text
    assert "Tavily 金鑰：尚未設定" in unset_text

    monkeypatch.setenv("GEMINI_API_KEY", "do-not-display-this-secret")
    monkeypatch.setenv("TAVILY_API_KEY", "also-secret")
    configured_app = AppTest.from_file(PROJECT_ROOT / "pages/3_設定.py")
    configured_app.run()
    configured_text = " ".join(
        caption.value for caption in configured_app.caption
    )

    assert "Gemini 金鑰：已設定" in configured_text
    assert "Tavily 金鑰：已設定" in configured_text
    assert "do-not-display-this-secret" not in configured_text
    assert "also-secret" not in configured_text


def test_settings_has_no_third_party_logo_service(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))
    app = AppTest.from_file(PROJECT_ROOT / "pages/3_設定.py").run()
    removed_name = "Brand" + "fetch"

    visible = " ".join(
        element.value
        for elements in (app.markdown, app.caption)
        for element in elements
    )
    assert removed_name not in visible
    assert all(
        removed_name not in field.label
        for field in app.text_input
    )


def test_removed_logo_provider_has_no_runtime_surface():
    removed = "brand" + "fetch"
    runtime_files = [
        PROJECT_ROOT / "daibu/cards" / f"{removed}.py",
        PROJECT_ROOT / "tests" / f"test_cards_{removed}.py",
    ]
    assert not any(path.exists() for path in runtime_files)

    checked = [
        PROJECT_ROOT / ".env.example",
        PROJECT_ROOT / "pages/1_選題.py",
        PROJECT_ROOT / "pages/3_設定.py",
        PROJECT_ROOT / "daibu/cards/logo_search.py",
    ]
    assert all(
        removed not in path.read_text(encoding="utf-8").casefold()
        for path in checked
    )


def test_settings_only_shows_the_active_provider_key(monkeypatch, tmp_path):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "pages/3_設定.py")
    app.run()

    field_labels = [field.label for field in app.text_input]
    assert "Gemini 金鑰" in field_labels
    assert "Groq 金鑰" not in field_labels


def test_settings_uses_chinese_labels_and_static_search_service(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("DAIBU_DB_PATH", str(tmp_path / "app.db"))

    app = AppTest.from_file(PROJECT_ROOT / "pages/3_設定.py")
    app.run()

    assert [field.label for field in app.selectbox] == [
        "AI 服務商",
        "內容系列",
        "模板版本",
    ]
    visible_text = " ".join(
        element.value
        for elements in (app.markdown, app.caption)
        for element in elements
    )
    assert "搜尋服務：Tavily" in visible_text


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
        ).click().run(timeout=10)

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
    comparison_theme_id = db.add_theme(
        conn,
        Theme(None, "比較主題", 1, [], 1),
    )
    comparison_idea_id = db.add_idea(
        conn,
        comparison_theme_id,
        Idea("比較貼文", "另一個角度", ""),
        status="已發",
    )
    performance.record(
        conn,
        comparison_idea_id,
        "Threads",
        8,
        80,
        4.0,
    )

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


def test_performance_hides_chart_when_data_is_thin(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "單一成效主題", 0, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("唯一已發貼文", "切入角度", ""),
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

    assert not any(
        element.type == "vega_lite_chart"
        for element in walk(app._tree[0])
    )
    assert app.dataframe


def test_performance_chart_axes_are_chinese(monkeypatch, tmp_path):
    database_path = tmp_path / "app.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(database_path))
    conn = db.connect(str(database_path))
    db.init_schema(conn)
    for weekday, name in enumerate(("主題甲", "主題乙")):
        theme_id = db.add_theme(
            conn,
            Theme(None, name, weekday, [], 1),
        )
        idea_id = db.add_idea(
            conn,
            theme_id,
            Idea(f"{name}貼文", "切入角度", ""),
            status="已發",
        )
        performance.record(
            conn,
            idea_id,
            "Threads",
            10,
            100,
            float(weekday + 1),
        )

    app = AppTest.from_file(PROJECT_ROOT / "pages/2_成效.py")
    app.run()

    def walk(block):
        for child in block.children.values():
            yield child
            if hasattr(child, "children"):
                yield from walk(child)

    chart = next(
        element
        for element in walk(app._tree[0])
        if element.type == "vega_lite_chart"
    )
    spec = json.loads(chart.proto.spec)

    assert spec["encoding"]["x"]["title"] == "主題"
    assert spec["encoding"]["x"]["axis"]["labelAngle"] == 0
    assert spec["encoding"]["y"]["title"] == "平均互動"


def test_company_candidate_decision_view_shows_only_company_and_description(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(
            id=None,
            name="AI 新創介紹",
            weekday=4,
            source_ids=[],
            n_ideas=3,
            content_kind="company_profile",
        ),
    )
    db.add_idea(
        conn,
        theme_id,
        Idea(
            title="讓文字開口說話",
            angle="配音成本被改寫",
            source_url="https://example.com/a",
            company="ElevenLabs",
            source_excerpt="2022 年於倫敦成立。",
        ),
    )
    conn.close()

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    rendered = " ".join(block.value for block in app.markdown)
    button_labels = {button.label for button in app.button}

    assert "ElevenLabs" in rendered
    assert "讓文字開口說話" in rendered
    assert "配音成本被改寫" not in rendered
    assert "未指定公司" not in rendered
    assert "ElevenLabs｜讓文字開口說話" in button_labels
    assert {"採用並繼續寫內容", "淘汰"} <= button_labels


def test_company_candidate_view_hides_legacy_and_later_duplicate_rows(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(
            None,
            "AI 新創介紹",
            4,
            [],
            3,
            content_kind="company_profile",
        ),
    )
    legacy_id = db.add_idea(
        conn,
        theme_id,
        Idea("通用觀點文", "角度", ""),
    )
    railway_first_id = db.add_idea(
        conn,
        theme_id,
        Idea("第一次 Railway 題目", "角度", "", company="Railway"),
    )
    railway_later_id = db.add_idea(
        conn,
        theme_id,
        Idea("後來的 Railway 題目", "角度", "", company=" railway "),
    )
    cloudflare_id = db.add_idea(
        conn,
        theme_id,
        Idea("Cloudflare 題目", "角度", "", company="Cloudflare"),
    )
    moove_id = db.add_idea(
        conn,
        theme_id,
        Idea("Moove 題目", "角度", "", company="Moove"),
    )
    db.save_company_eligibility(
        conn,
        CompanyEligibility(
            "cloudflare",
            "Cloudflare",
            "ineligible",
            2009,
            "public",
            "已上市",
            (),
            "2026-08-10 13:00:00",
        ),
    )
    for idea_id, created_at in (
        (legacy_id, "2026-07-25 09:00:00"),
        (railway_first_id, "2026-08-05 10:00:00"),
        (railway_later_id, "2026-08-05 10:01:00"),
        (cloudflare_id, "2026-08-05 10:02:00"),
        (moove_id, "2026-08-05 10:03:00"),
    ):
        conn.execute(
            "UPDATE ideas SET created_at = ? WHERE id = ?",
            (created_at, idea_id),
        )
    conn.commit()

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()

    button_labels = {button.label for button in app.button}
    subheaders = {item.value for item in app.subheader}
    captions = {item.value for item in app.caption}
    assert "候選（2）" in subheaders
    assert "先瀏覽公司與它在做什麼，再一次專心判斷一則。" in captions
    assert "Railway｜第一次 Railway 題目" in button_labels
    assert "Moove｜Moove 題目" in button_labels
    assert "Cloudflare｜Cloudflare 題目" not in button_labels
    assert not any(label.startswith("比較｜") for label in button_labels)
    assert "後來的 Railway 題目" not in " ".join(button_labels)
    assert "通用觀點文" not in " ".join(button_labels)
    assert len(db.get_ideas(conn, status="候選")) == 5


def test_general_candidate_view_keeps_title_and_angle(tmp_path, monkeypatch):
    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(
            id=None,
            name="一般系列",
            weekday=4,
            source_ids=[],
            n_ideas=3,
        ),
    )
    db.add_idea(
        conn,
        theme_id,
        Idea(title="舊題目", angle="舊切角", source_url=""),
    )
    conn.close()

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    rendered = " ".join(block.value for block in app.markdown)

    assert "舊題目" in rendered
    assert "舊切角" in rendered
    assert "未指定公司" in rendered


def test_adopted_idea_carousel_reports_missing_company(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    db.add_idea(
        conn,
        theme_id,
        Idea("待補公司", "採用角度", ""),
        status="採用",
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    rendered = " ".join(block.value for block in app.markdown)

    assert not app.exception
    assert "公司名稱" in rendered
    assert "carousel-checklist__item--current" in rendered


def test_adopted_idea_carousel_can_save_company_name(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("待補公司", "採用角度", ""),
        status="採用",
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        field for field in app.text_input
        if field.label == "公司名稱"
    ).set_value("ElevenLabs")
    next(
        button for button in app.button
        if button.label == "儲存公司名"
    ).click().run()

    stored = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    assert stored.company == "ElevenLabs"


def test_adopted_idea_carousel_can_add_a_verified_source(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            "來源測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        field for field in app.text_input
        if field.key == f"carousel-source-url-{idea_id}"
    ).set_value("https://elevenlabs.io/about")
    next(
        field for field in app.text_input
        if field.label == "出版方"
    ).set_value("ElevenLabs")
    next(
        field for field in app.text_input
        if field.label == "發布日期"
    ).set_value("2026-07-30")
    next(
        field for field in app.text_area
        if field.label == "查證引文"
    ).set_value("官方說明公司提供生成式語音與內容製作工具。")
    next(
        button for button in app.button
        if button.label == "加入來源"
    ).click().run()

    stored = db.get_idea_sources(conn, idea_id)
    assert len(stored) == 1
    assert stored[0].source_id == "S1"
    assert stored[0].publisher == "ElevenLabs"


def test_adopted_idea_carousel_can_prefill_source_from_url(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    db.add_idea(
        conn,
        theme_id,
        Idea(
            "抓取測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )
    monkeypatch.setattr(
        page_fetch,
        "fetch_suggestion",
        lambda url: SourceSuggestion(
            "Example News",
            "2026-07-20",
            url,
            "官方說明這個模型能保留語氣與節奏，並提供內容製作工具。",
        ),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        field for field in app.text_input
        if field.label == "來源網址"
    ).set_value("https://news.example/story")
    next(
        button for button in app.button
        if button.label == "抓取內容"
    ).click().run()

    assert next(
        field.value for field in app.text_input
        if field.label == "出版方"
    ) == "Example News"
    assert next(
        field.value for field in app.text_input
        if field.label == "發布日期"
    ) == "2026-07-20"
    assert next(
        field.value for field in app.text_area
        if field.label == "查證引文"
    ).startswith("官方說明")


def test_source_fetch_error_keeps_existing_form_values(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    db.add_idea(
        conn,
        theme_id,
        Idea(
            "抓取失敗測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )

    def fail(_url):
        raise ValueError("抓不到這個網址，請直接手動填寫。")

    monkeypatch.setattr(page_fetch, "fetch_suggestion", fail)
    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        field for field in app.text_input
        if field.label == "來源網址"
    ).set_value("https://news.example/private")
    next(
        field for field in app.text_input
        if field.label == "出版方"
    ).set_value("我已填的出版方")
    next(
        button for button in app.button
        if button.label == "抓取內容"
    ).click().run()

    assert not app.exception
    assert any("抓不到這個網址" in error.value for error in app.error)
    assert next(
        field.value for field in app.text_input
        if field.label == "出版方"
    ) == "我已填的出版方"


def test_adopted_idea_carousel_can_remove_a_source(
    tmp_path,
    monkeypatch,
):
    from tests.card_fixtures import verified_sources

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            "刪來源測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )
    db.save_idea_sources(conn, idea_id, verified_sources())

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        button for button in app.button
        if button.label == "刪除 S2"
    ).click().run()

    assert [
        source.source_id
        for source in db.get_idea_sources(conn, idea_id)
    ] == ["S1", "S3"]


def test_adopted_idea_can_generate_a_carousel_draft(
    tmp_path,
    monkeypatch,
):
    from tests.card_fixtures import structured_llm_response, verified_sources

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            "草稿生成測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )
    db.save_idea_sources(conn, idea_id, verified_sources())

    class Provider:
        def generate_carousel_text(self, _prompt):
            return structured_llm_response()

    monkeypatch.setattr(base, "get_provider", lambda _config: Provider())
    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run(timeout=10)
    next(
        button for button in app.button
        if button.label == "產生輪播草稿"
    ).click().run(timeout=10)

    stored = db.get_carousel_draft(conn, idea_id)
    assert not app.exception
    assert stored is not None
    assert len(stored.pages) == 6


def test_failed_carousel_generation_closes_research_status(
    tmp_path,
    monkeypatch,
):
    from daibu.cards import research_draft
    from tests.card_fixtures import verified_sources

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            "錯誤狀態測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )
    db.save_idea_sources(conn, idea_id, verified_sources())

    class Provider:
        def generate_carousel_text(self, _prompt):
            return ""

    def fail(*_args, **_kwargs):
        raise base.LLMResponseError("bad response")

    monkeypatch.setattr(base, "get_provider", lambda _config: Provider())
    monkeypatch.setattr(research_draft, "generate", fail)
    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        button for button in app.button
        if button.label == "產生輪播草稿"
    ).click().run()

    assert any(
        status.label == "公司資料查證未完成" for status in app.status
    )
    failed_status = next(
        status for status in app.status
        if status.label == "公司資料查證未完成"
    )
    assert failed_status.icon == ":material/error:"
    assert failed_status.proto.expanded is False


def test_company_research_can_generate_without_a_manual_source_pack(
    tmp_path,
    monkeypatch,
):
    from daibu.cards import research_draft
    from tests.card_fixtures import carousel_draft

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(
            None,
            "TechCrunch",
            "https://techcrunch.com/feed",
            "rss",
            True,
        ),
    )
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [source_id], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            "自動研究測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )
    calls = []

    def fake_generate(
        service_conn,
        idea,
        configured_domains,
        brand_asset,
        search_fn,
        fetch_fn,
        generate_text,
    ):
        del brand_asset, search_fn, fetch_fn, generate_text
        calls.append(tuple(configured_domains))
        result = carousel_draft()
        db.save_researched_draft(service_conn, idea.id, result)
        return result

    monkeypatch.setattr(research_draft, "generate", fake_generate)
    provider = type(
        "Provider",
        (),
        {"generate_carousel_text": lambda self, _prompt: ""},
    )()
    monkeypatch.setattr(base, "get_provider", lambda _config: provider)

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    generate_button = next(
        button for button in app.button
        if button.label == "產生輪播草稿"
    )
    assert generate_button.disabled is False
    generate_button.click().run()

    assert calls == [
        (
            "www.ycombinator.com",
            "speedrun.a16z.com",
            "techcrunch.com",
        )
    ]
    assert db.get_carousel_draft(conn, idea_id) is not None
    rendered = " ".join(block.value for block in app.markdown)
    assert "官方說法" in rendered
    assert "第三方報導" in rendered
    assert any(
        section.evidence_quotes
        for page in db.get_carousel_draft(conn, idea_id).pages
        for section in page.sections
    )


def test_saved_carousel_draft_shows_six_editable_pages(
    tmp_path,
    monkeypatch,
):
    from daibu.cards import assets, editor_component, editor_ui
    from tests.card_fixtures import carousel_draft, solid_png

    captured = {}

    def capture_editor(payload, *, key):
        captured["payload"] = payload
        captured["key"] = key
        return editor_component.ContentEditorEvent(False, None)

    monkeypatch.setattr(editor_ui, "mount_content_editor", capture_editor)

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            "草稿顯示測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )
    db.save_idea_sources(conn, idea_id, carousel_draft().sources)
    db.save_carousel_draft(conn, idea_id, carousel_draft())
    assets.store_logo(
        conn,
        "ElevenLabs",
        "official.png",
        solid_png(240, 80),
        "https://elevenlabs.io/about",
        "2026-08-23",
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    rendered = " ".join(block.value for block in app.markdown)

    assert not app.exception
    assert len(captured["payload"]["pages"]) == 6
    assert all(page["previewHtml"] for page in captured["payload"]["pages"])
    assert any(
        ".diagram." in field["key"]
        for page in captured["payload"]["pages"]
        for field in page["fields"]
    )
    assert any(
        page["lockedEvidence"]
        for page in captured["payload"]["pages"]
    )
    assert "儲存草稿" not in [button.label for button in app.button]
    assert "六頁內容編輯器" in rendered


def test_invalid_carousel_edit_keeps_widgets_and_database_unchanged(
    tmp_path,
    monkeypatch,
):
    from daibu.cards import assets, editor_component, editor_ui
    from daibu.cards.editor_payload import editable_values
    from tests.card_fixtures import carousel_draft, solid_png

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            "草稿驗證測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )
    original = carousel_draft()
    db.save_idea_sources(conn, idea_id, original.sources)
    db.save_carousel_draft(conn, idea_id, original)
    assets.store_logo(
        conn,
        "ElevenLabs",
        "official.png",
        solid_png(240, 80),
        "https://elevenlabs.io/about",
        "2026-08-23",
    )
    metadata = db.get_carousel_draft_meta(conn, idea_id)
    values = editable_values(original)
    values["page.who.section.0.text"] += "補" * 221
    monkeypatch.setattr(
        editor_ui,
        "mount_content_editor",
        lambda _payload, *, key: editor_component.ContentEditorEvent(
            True,
            {"revision": metadata.content_revision, "values": values},
        ),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()

    assert any("220" in error.value for error in app.error)
    assert db.get_carousel_draft(conn, idea_id) == original
    assert any("先儲存六頁變更" in item.value for item in app.caption)


def test_carousel_editor_save_action_updates_database(tmp_path, monkeypatch):
    from daibu.cards import assets, editor_component, editor_ui
    from daibu.cards.editor_payload import editable_values
    from tests.card_fixtures import renderable_carousel_draft, solid_png

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "AI 新創介紹", 4, [], 1))
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("編輯器保存測試", "採用角度", "", company="ElevenLabs"),
        status="採用",
    )
    original = renderable_carousel_draft()
    db.save_idea_sources(conn, idea_id, original.sources)
    db.save_carousel_draft(conn, idea_id, original)
    assets.store_logo(
        conn,
        "ElevenLabs",
        "official.png",
        solid_png(240, 80),
        "https://elevenlabs.io/about",
        "2026-08-23",
    )
    before = db.get_carousel_draft_meta(conn, idea_id)
    values = editable_values(original)
    values["page.who.heading"] = "重新認識 ElevenLabs"
    calls = 0

    def save_once(_payload, *, key):
        nonlocal calls
        calls += 1
        if calls == 1:
            return editor_component.ContentEditorEvent(
                True,
                {"revision": before.content_revision, "values": values},
            )
        return editor_component.ContentEditorEvent(False, None)

    monkeypatch.setattr(editor_ui, "mount_content_editor", save_once)

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run(timeout=20)

    saved = db.get_carousel_draft(conn, idea_id)
    after = db.get_carousel_draft_meta(conn, idea_id)
    assert not app.exception
    assert saved.pages[1].heading == "重新認識 ElevenLabs"
    assert after.content_revision == before.content_revision + 1


def test_unsaved_carousel_editor_disables_image_generation(tmp_path, monkeypatch):
    from daibu.cards import editor_component, editor_ui
    from tests.card_fixtures import carousel_draft

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "AI 新創介紹", 4, [], 1))
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("未存內容測試", "採用角度", "", company="ElevenLabs"),
        status="採用",
    )
    original = carousel_draft()
    db.save_carousel_draft(conn, idea_id, original)
    monkeypatch.setattr(
        editor_ui,
        "mount_content_editor",
        lambda _payload, *, key: editor_component.ContentEditorEvent(True, None),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()

    render_button = next(
        button for button in app.button if button.label == "產生六張圖"
    )
    assert render_button.disabled is True
    assert any("先儲存六頁變更" in item.value for item in app.caption)
    assert db.get_carousel_draft(conn, idea_id) == original


def test_regenerating_a_carousel_requires_explicit_confirmation(
    tmp_path,
    monkeypatch,
):
    from tests.card_fixtures import carousel_draft

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            "重新產生測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )
    db.save_idea_sources(conn, idea_id, carousel_draft().sources)
    db.save_carousel_draft(conn, idea_id, carousel_draft())

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()

    assert any(
        button.label == "確認重新產生"
        for button in app.button
    )
    assert any(
        "會覆蓋目前的六頁內容，且無法復原" in caption.value
        for caption in app.caption
    )


def test_regeneration_uses_the_saved_snapshot_without_new_research(
    tmp_path,
    monkeypatch,
):
    from daibu.cards import draft as draft_service
    from tests.card_fixtures import carousel_draft

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "AI 新創介紹", 4, [], 1))
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("快照重生", "採用角度", "", company="ElevenLabs"),
        status="採用",
    )
    original = carousel_draft()
    db.save_carousel_draft(conn, idea_id, original)
    db.save_idea_sources(conn, idea_id, original.sources[:1])
    seen_sources = []

    def fake_generate(_conn, _idea, sources, _generate_text):
        seen_sources.append(sources)
        return original

    provider = type(
        "Provider",
        (),
        {"generate_carousel_text": lambda self, _prompt: ""},
    )()
    monkeypatch.setattr(draft_service, "generate", fake_generate)
    monkeypatch.setattr(base, "get_provider", lambda _config: provider)

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        button for button in app.button
        if button.label == "確認重新產生"
    ).click().run()

    assert seen_sources == [original.sources]


def test_explicit_research_refreshes_instead_of_reusing_the_snapshot(
    tmp_path,
    monkeypatch,
):
    from daibu.cards import research_draft
    from tests.card_fixtures import carousel_draft

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "AI 新創介紹", 4, [], 1))
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("重新研究", "採用角度", "", company="ElevenLabs"),
        status="採用",
    )
    original = carousel_draft()
    db.save_researched_draft(conn, idea_id, original)
    seen_reuse = []

    def fake_generate(
        service_conn,
        idea,
        configured_domains,
        brand_asset,
        search_fn,
        fetch_fn,
        generate_text,
        *,
        reuse_existing_sources=True,
    ):
        del configured_domains, brand_asset, search_fn, fetch_fn, generate_text
        seen_reuse.append(reuse_existing_sources)
        db.save_researched_draft(service_conn, idea.id, original)
        return original

    provider = type(
        "Provider",
        (),
        {"generate_carousel_text": lambda self, _prompt: ""},
    )()
    monkeypatch.setattr(research_draft, "generate", fake_generate)
    monkeypatch.setattr(base, "get_provider", lambda _config: provider)

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        button for button in app.button
        if button.label == "確認重新搜尋"
    ).click().run()

    assert seen_reuse == [False]


def test_carousel_logo_block_explains_missing_asset_and_disables_render(
    tmp_path,
    monkeypatch,
):
    from tests.card_fixtures import carousel_draft

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            "Logo 缺件測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )
    db.save_idea_sources(conn, idea_id, carousel_draft().sources)
    db.save_carousel_draft(conn, idea_id, carousel_draft())

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    rendered = " ".join(block.value for block in app.markdown)
    render_button = next(
        button for button in app.button
        if button.label == "產生六張圖"
    )

    assert not app.exception
    assert "還沒有 ElevenLabs 的官方 Logo" in rendered
    assert len(app.file_uploader) == 1
    assert render_button.disabled


def test_three_logo_candidates_show_identity_evidence_without_persisting(
    tmp_path,
    monkeypatch,
):
    import streamlit as st

    from daibu.cards import logo_discovery, logo_search, official_site

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    monkeypatch.setenv("DAIBU_LOGO_DIR", str(tmp_path / "logos"))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            "Logo 自動搜尋測試",
            "採用角度",
            "",
            company="Acme",
        ),
        status="採用",
    )
    pipeline.update_body(
        conn,
        idea_id,
        "已有正文，所以可以開始找官方 Logo。",
    )
    site = official_site.OfficialSite(
        company="Acme",
        website_url="https://acme.example",
        domain="acme.example",
        confidence="high",
        evidence=(),
    )
    candidates = tuple(
        logo_discovery.LogoCandidate(
            "Acme",
            f"acme-{kind}.svg",
            b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"/>',
            "https://acme.example/brand",
            f"https://acme.example/assets/acme-{kind}.svg?secret=hidden",
            official_site_url="https://acme.example",
            source_kind=source,
            logo_kind=kind,
            confidence=confidence,
            reasons=(reason,),
        )
        for kind, source, confidence, reason in (
            ("logo", "official_site", "high", "官網品牌頁引用"),
            ("symbol", "official_site", "high", "官網頁首引用"),
            ("icon", "official_site", "high", "官網動態頁面引用"),
        )
    )
    monkeypatch.setattr(
        logo_search,
        "find_candidates",
        lambda *_args, **_kwargs: logo_search.LogoSearchResult(
            site,
            candidates,
        ),
    )
    preview_values = []

    def capture_preview(value, *args, **kwargs):
        del args, kwargs
        preview_values.append(value)

    monkeypatch.setattr(st, "image", capture_preview)

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run(timeout=10)
    rendered = " ".join(block.value for block in app.markdown)

    assert not app.exception
    assert "找到 3 張 Logo 候選" in rendered
    assert "待你確認" in rendered
    assert "acme.example" in rendered
    assert "官網" in rendered
    assert "完整 Logo" in rendered
    assert "品牌符號" in rendered
    assert "網站圖示" in rendered
    assert "高信心" in rendered
    assert "secret=hidden" not in rendered
    assert len(preview_values) == 3
    assert sum(
        button.label == "確認這是官方 Logo"
        for button in app.button
    ) == 3
    assert db.get_brand_asset(conn, "Acme") is None
    assert not (tmp_path / "logos").exists()


def test_logo_search_receives_the_full_idea_context(
    tmp_path,
    monkeypatch,
):
    from daibu.cards import logo_discovery, logo_search, official_site
    from tests.card_fixtures import carousel_draft

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            "SUN 用 AI 找出適合的患者",
            "從醫療配對切入",
            "",
            company="SUN",
        ),
        status="採用",
    )
    pipeline.update_body(conn, idea_id, "SUN 協助病患找到臨床試驗。")
    source_pack = carousel_draft().sources
    db.save_idea_sources(conn, idea_id, source_pack)
    seen = []

    def fake_find_candidates(context, **kwargs):
        seen.append((context, kwargs))
        site = official_site.OfficialSite(
            company="SUN",
            website_url="https://sun.example",
            domain="sun.example",
            confidence="high",
            evidence=(),
        )
        candidate = logo_discovery.LogoCandidate(
            "SUN",
            "sun.svg",
            b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"/>',
            "https://sun.example/brand",
            "https://sun.example/sun.svg",
        )
        return logo_search.LogoSearchResult(site, (candidate,))

    monkeypatch.setattr(logo_search, "find_candidates", fake_find_candidates)

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run(timeout=10)

    assert not app.exception
    assert len(seen) == 1
    context, kwargs = seen[0]
    assert context.company == "SUN"
    assert context.title == "SUN 用 AI 找出適合的患者"
    assert context.angle == "從醫療配對切入"
    assert context.body == "SUN 協助病患找到臨床試驗。"
    assert context.sources == source_pack
    assert kwargs == {}


def test_confirming_second_logo_candidate_persists_only_that_candidate(
    tmp_path,
    monkeypatch,
):
    from daibu.cards import logo_discovery, logo_search, official_site

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    monkeypatch.setenv("DAIBU_LOGO_DIR", str(tmp_path / "logos"))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("Logo 確認測試", "採用角度", "", company="Acme"),
        status="採用",
    )
    pipeline.update_body(conn, idea_id, "已有正文。")
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 80">'
        b'<path fill="#111" d="M0 0h240v80H0z"/></svg>'
    )
    site = official_site.OfficialSite(
        "Acme",
        "https://acme.example",
        "acme.example",
        "high",
        (),
    )
    candidates = tuple(
        logo_discovery.LogoCandidate(
            "Acme",
            f"acme-{index}.svg",
            svg.replace(b"240", str(240 + index).encode(), 1),
            "https://acme.example/brand",
            f"https://acme.example/assets/acme-{index}.svg",
        )
        for index in range(1, 4)
    )
    monkeypatch.setattr(
        logo_search,
        "find_candidates",
        lambda *_args, **_kwargs: logo_search.LogoSearchResult(
            site,
            candidates,
        ),
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    confirmation_buttons = [
        button for button in app.button
        if button.label == "確認這是官方 Logo"
    ]
    confirmation_buttons[1].click().run()

    stored = db.get_brand_asset(conn, "Acme")
    count = conn.execute(
        "SELECT COUNT(*) FROM brand_assets WHERE company = ?",
        ("Acme",),
    ).fetchone()[0]
    assert not app.exception
    assert stored is not None
    assert stored.local_path.is_file()
    assert stored.local_path.read_bytes() == candidates[1].data
    assert stored.official_source_url == "https://acme.example/brand"
    assert count == 1
    assert f"logo-search-result-{idea_id}" not in app.session_state


def test_rejecting_first_logo_candidate_keeps_other_two_without_searching_again(
    tmp_path,
    monkeypatch,
):
    from daibu.cards import logo_discovery, logo_search, official_site

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    monkeypatch.setenv("DAIBU_LOGO_DIR", str(tmp_path / "logos"))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("Logo 拒絕測試", "採用角度", "", company="Acme"),
        status="採用",
    )
    pipeline.update_body(conn, idea_id, "已有正文。")
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 80">'
        b'<path fill="#111" d="M0 0h240v80H0z"/></svg>'
    )
    calls = []
    site = official_site.OfficialSite(
        "Acme",
        "https://acme.example",
        "acme.example",
        "high",
        (),
    )
    candidates = tuple(
        logo_discovery.LogoCandidate(
            "Acme",
            f"acme-{index}.svg",
            svg,
            "https://acme.example/brand",
            f"https://acme.example/assets/acme-{index}.svg",
        )
        for index in range(1, 4)
    )

    def fake_find_candidates(*args, **kwargs):
        calls.append((args, kwargs))
        return logo_search.LogoSearchResult(site, candidates)

    monkeypatch.setattr(logo_search, "find_candidates", fake_find_candidates)
    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()

    first_reject = next(
        button for button in app.button
        if button.label == "不是這個品牌的 Logo"
    )
    first_reject.click().run()

    assert db.get_brand_asset(conn, "Acme") is None
    assert not (tmp_path / "logos").exists()
    assert len(app.file_uploader) == 1
    assert not app.exception
    assert len(calls) == 1
    assert sum(
        button.label == "確認這是官方 Logo"
        for button in app.button
    ) == 2
    assert not any(
        button.label == "重新搜尋官方 Logo"
        for button in app.button
    )


@pytest.mark.parametrize(
    ("stage", "expected_heading"),
    (
        ("official_site", "無法確認官方網站"),
        ("official_assets", "官網找不到可核對的 Logo 候選"),
        ("service", "Logo 搜尋服務暫時中斷"),
    ),
)
def test_logo_search_errors_explain_the_failed_stage_without_blocking_draft(
    tmp_path,
    monkeypatch,
    stage,
    expected_heading,
):
    from daibu.cards import logo_search

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("Logo 錯誤復原", "採用角度", "", company="Acme"),
        status="採用",
    )
    pipeline.update_body(conn, idea_id, "已有正文。")

    def fail_search(*_args, **_kwargs):
        raise logo_search.LogoSearchError(stage, "可安全顯示的錯誤細節。")

    monkeypatch.setattr(logo_search, "find_candidates", fail_search)

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    warning_text = " ".join(warning.value for warning in app.warning)
    draft_button = next(
        button for button in app.button
        if button.label == "產生輪播草稿"
    )

    assert not app.exception
    assert expected_heading in warning_text
    assert "可安全顯示的錯誤細節" in warning_text
    assert len(app.file_uploader) == 1
    assert not draft_button.disabled
    assert any(
        button.label == "重新搜尋官方 Logo"
        for button in app.button
    )
    assert db.get_brand_asset(conn, "Acme") is None


def test_carousel_logo_can_be_uploaded_and_reused(
    tmp_path,
    monkeypatch,
):
    from tests.card_fixtures import solid_png

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    monkeypatch.setenv("DAIBU_LOGO_DIR", str(tmp_path / "logos"))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    db.add_idea(
        conn,
        theme_id,
        Idea(
            "Logo 上傳測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    app.file_uploader[0].upload(
        "official.png",
        solid_png(240, 80),
        "image/png",
    )
    next(
        field for field in app.text_input
        if field.label == "Logo 官方來源網址"
    ).set_value("https://elevenlabs.io/about")
    next(
        button for button in app.button
        if button.label == "儲存 Logo"
    ).click().run()

    stored = db.get_brand_asset(conn, "ElevenLabs")
    rendered = " ".join(block.value for block in app.markdown)
    captions = " ".join(caption.value for caption in app.caption)
    assert not app.exception
    assert stored is not None
    assert stored.local_path.is_file()
    assert "ElevenLabs 官方 Logo" in rendered
    assert date.today().isoformat() in captions
    assert any(button.label == "換一張" for button in app.button)


def test_carousel_logo_submit_explains_when_file_is_missing(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    monkeypatch.setenv("DAIBU_LOGO_DIR", str(tmp_path / "logos"))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    db.add_idea(
        conn,
        theme_id,
        Idea(
            "Logo 缺檔測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    save_button = next(
        button for button in app.button
        if button.label == "儲存 Logo"
    )

    assert not save_button.disabled
    save_button.click().run()

    assert not app.exception
    assert any("請先上傳" in error.value for error in app.error)


def test_rejected_carousel_logo_upload_keeps_page_running(
    tmp_path,
    monkeypatch,
):
    from tests.card_fixtures import solid_png

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    monkeypatch.setenv("DAIBU_LOGO_DIR", str(tmp_path / "logos"))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    db.add_idea(
        conn,
        theme_id,
        Idea(
            "Logo 擋錯測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    app.file_uploader[0].upload(
        "oversized.png",
        solid_png(4200, 120),
        "image/png",
    )
    next(
        field for field in app.text_input
        if field.label == "Logo 官方來源網址"
    ).set_value("https://elevenlabs.io/about")
    next(
        button for button in app.button
        if button.label == "儲存 Logo"
    ).click().run()

    assert not app.exception
    assert any("超過 4096 px" in error.value for error in app.error)
    assert db.get_brand_asset(conn, "ElevenLabs") is None
    assert not (tmp_path / "logos").exists()


def test_complete_carousel_can_render_and_download_six_pngs(
    tmp_path,
    monkeypatch,
):
    import zipfile
    from io import BytesIO

    from daibu.cards import assets, bundle, workbench
    from tests.card_fixtures import renderable_carousel_draft, solid_png

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    monkeypatch.setenv("DAIBU_LOGO_DIR", str(tmp_path / "logos"))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            "完整出圖測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )
    draft = renderable_carousel_draft()
    db.save_idea_sources(conn, idea_id, draft.sources)
    db.save_carousel_draft(conn, idea_id, draft)
    assets.store_logo(
        conn,
        "ElevenLabs",
        "official.png",
        solid_png(240, 80),
        "https://elevenlabs.io/about",
        "2026-07-30",
    )

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        button for button in app.button
        if button.label == "產生六張圖"
    ).click().run(timeout=20)

    pngs = workbench.cached_pngs(
        app.session_state,
        idea_id,
        draft,
        db.get_carousel_draft_meta(conn, idea_id).template_version_id,
        db.get_carousel_draft_meta(conn, idea_id).content_revision,
    )
    archive = bundle.carousel_zip(pngs)
    with zipfile.ZipFile(BytesIO(archive)) as packaged:
        assert packaged.namelist() == list(bundle.PAGE_FILENAMES)
        assert all(
            packaged.read(filename).startswith(b"\x89PNG")
            for filename in bundle.PAGE_FILENAMES
        )
    assert not app.exception
    assert pngs is not None
    assert len(app.download_button) == 1


def test_saving_carousel_edits_invalidates_the_old_download(
    tmp_path,
    monkeypatch,
):
    from daibu.cards import assets, editor_component, editor_ui
    from daibu.cards.editor_payload import editable_values
    from tests.card_fixtures import renderable_carousel_draft, solid_png

    path = tmp_path / "t.db"
    monkeypatch.setenv("DAIBU_DB_PATH", str(path))
    monkeypatch.setenv("DAIBU_LOGO_DIR", str(tmp_path / "logos"))
    conn = db.connect(str(path))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 1),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(
            "快取失效測試",
            "採用角度",
            "",
            company="ElevenLabs",
        ),
        status="採用",
    )
    draft = renderable_carousel_draft()
    db.save_idea_sources(conn, idea_id, draft.sources)
    db.save_carousel_draft(conn, idea_id, draft)
    assets.store_logo(
        conn,
        "ElevenLabs",
        "official.png",
        solid_png(240, 80),
        "https://elevenlabs.io/about",
        "2026-07-30",
    )
    before = db.get_carousel_draft_meta(conn, idea_id)
    values = editable_values(draft)
    values["page.who.section.0.text"] += "補"
    should_save = False

    def editor_event(_payload, *, key):
        nonlocal should_save
        if should_save:
            should_save = False
            return editor_component.ContentEditorEvent(
                True,
                {"revision": before.content_revision, "values": values},
            )
        return editor_component.ContentEditorEvent(False, None)

    monkeypatch.setattr(editor_ui, "mount_content_editor", editor_event)

    app = AppTest.from_file(PROJECT_ROOT / "pages/1_選題.py").run()
    next(
        button for button in app.button
        if button.label == "產生六張圖"
    ).click().run(timeout=20)
    assert len(app.download_button) == 1

    should_save = True
    app.run(timeout=20)

    assert not app.exception
    assert len(app.download_button) == 0
