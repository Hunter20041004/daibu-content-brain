from types import SimpleNamespace

from daibu import workspace


def _idea(
    status: str,
    body: str = "",
    theme_id: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(status=status, body=body, theme_id=theme_id)


def test_candidates_make_decide_the_current_step():
    state = workspace.derive_workflow([_idea("候選")])

    assert state.current == "decide"
    assert state.completed == ("research",)
    assert state.candidate_count == 1


def test_adopted_idea_without_body_moves_to_write():
    state = workspace.derive_workflow([_idea("採用")])

    assert state.current == "write"
    assert state.completed == ("research", "decide")


def test_adopted_idea_with_body_moves_to_carousel():
    state = workspace.derive_workflow([_idea("採用", "正文完成")])

    assert state.current == "carousel"
    assert state.completed == ("research", "decide", "write")


def test_next_mission_names_the_series_with_candidates():
    themes = [SimpleNamespace(id=7, name="AI 新創介紹", weekday=4)]

    mission = workspace.next_mission(
        themes,
        [_idea("候選", theme_id=7)],
        today_weekday=4,
    )

    assert mission.theme_id == 7
    assert mission.step == "decide"
    assert mission.label == "挑選「AI 新創介紹」的 1 則候選"


def test_next_mission_prioritizes_unfinished_adopted_copy():
    themes = [SimpleNamespace(id=7, name="AI 新創介紹", weekday=4)]
    mission = workspace.next_mission(
        themes,
        [_idea("候選", theme_id=7), _idea("採用", theme_id=7)],
        today_weekday=4,
    )
    assert mission.step == "write"
    assert mission.label == "完成「AI 新創介紹」的貼文內容"


def test_next_mission_continues_to_carousel_after_copy_is_ready():
    themes = [SimpleNamespace(id=7, name="AI 新創介紹", weekday=4)]
    mission = workspace.next_mission(
        themes, [_idea("採用", "正文完成", theme_id=7)], today_weekday=4
    )
    assert mission.step == "carousel"
    assert mission.label == "完成「AI 新創介紹」的輪播圖片"


def test_next_mission_starts_research_for_the_scheduled_series():
    themes = [
        SimpleNamespace(id=3, name="產品觀察", weekday=2),
        SimpleNamespace(id=7, name="AI 新創介紹", weekday=4),
    ]
    mission = workspace.next_mission(themes, [], today_weekday=4)
    assert mission.theme_id == 7
    assert mission.step == "research"
    assert mission.label == "替「AI 新創介紹」找題材"


def test_carousel_checklist_is_linear_and_blocks_later_requirements():
    items = workspace.carousel_checklist(
        has_company=True,
        source_count=0,
        has_logo=False,
        has_draft=False,
        has_pngs=False,
    )
    assert [item.label for item in items] == [
        "公司名稱",
        "這篇內容的查證證據",
        "官方 Logo",
        "六頁草稿",
        "六張圖片",
    ]
    assert [item.state for item in items] == [
        "complete",
        "current",
        "blocked",
        "blocked",
        "blocked",
    ]
