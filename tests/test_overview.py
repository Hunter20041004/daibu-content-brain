from daibu import overview


def test_calendar_truncates_long_theme_names():
    assert overview.truncate_calendar_theme_name("AI 新創") == "AI 新創"
    assert (
        overview.truncate_calendar_theme_name("本週熱門 Claude/Codex Skill")
        == "本週熱門 Cl…"
    )
