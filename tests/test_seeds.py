from daibu import db, seeds


def test_seed_sources_have_no_manual_fetch_type():
    assert {
        source.fetch_type for source in seeds.DEFAULT_SOURCES
    } <= {"rss", "search"}


def test_seed_themes_are_bound_to_named_sources(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    seeds.load(conn)

    sources_by_id = {
        source.id: source.name for source in db.get_sources(conn)
    }
    themes_by_name = {
        theme.name: theme for theme in db.get_themes(conn)
    }
    for seed in seeds.DEFAULT_THEMES:
        theme = themes_by_name[seed.name]
        bound_names = {
            sources_by_id[source_id] for source_id in theme.source_ids
        }
        assert theme.source_ids
        assert bound_names == set(seed.source_names)


def test_load_seeds_themes_without_duplicates(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    seeds.load(conn)

    sources = db.get_sources(conn)
    themes = db.get_themes(conn)
    assert len(sources) == 15
    assert any("AI 近期大事" in theme.name for theme in themes)
    assert any("Skill" in theme.name for theme in themes)
    assert any("AI 新創介紹" in theme.name for theme in themes)

    seeds.load(conn)

    assert len(db.get_sources(conn)) == len(sources)
    assert len(db.get_themes(conn)) == len(themes)
