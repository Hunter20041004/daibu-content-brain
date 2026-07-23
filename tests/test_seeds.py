from daibu import db, seeds


def test_load_seeds_all_layers_and_themes_without_duplicates(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    seeds.load(conn)

    sources = db.get_sources(conn)
    themes = db.get_themes(conn)
    assert {source.layer for source in sources} == {
        "L1",
        "L2",
        "L3",
        "L4",
        "L5",
    }
    assert any("AI 近期大事" in theme.name for theme in themes)
    assert any("Skill" in theme.name for theme in themes)
    assert any("AI 新創介紹" in theme.name for theme in themes)

    seeds.load(conn)

    assert len(db.get_sources(conn)) == len(sources)
    assert len(db.get_themes(conn)) == len(themes)
