from daibu import db, seeds
from daibu.models import Source


KEEP = {"Product Hunt AI", "Y Combinator Blog", "a16z", "TechCrunch", "INSIDE"}
FIXED_KEEP = {
    "Product Hunt AI",
    "Y Combinator Blog",
    "VentureBeat AI",
    "TechCrunch",
    "INSIDE",
}


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
    assert len(sources) == len(seeds.DEFAULT_SOURCES)
    assert [theme.name for theme in themes] == ["AI 新創介紹"]

    seeds.load(conn)

    assert len(db.get_sources(conn)) == len(sources)
    assert len(db.get_themes(conn)) == len(themes)


def test_ai_startup_seed_is_a_company_profile_series(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    seeds.load(conn)

    themes = {theme.name: theme for theme in db.get_themes(conn)}
    assert themes["AI 新創介紹"].content_kind == "company_profile"


def test_load_seeds_only_when_database_is_brand_new(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    seeds.load(conn)
    deleted_theme_id = db.get_themes(conn)[0].id
    deleted_source_id = db.get_sources(conn)[0].id
    assert deleted_theme_id is not None
    assert deleted_source_id is not None

    db.delete_theme(conn, deleted_theme_id)
    db.delete_source(conn, deleted_source_id)
    seeds.load(conn)

    assert len(db.get_themes(conn)) == len(seeds.DEFAULT_THEMES) - 1
    assert len(db.get_sources(conn)) == len(seeds.DEFAULT_SOURCES) - 1


def test_startup_theme_sources_are_pruned_once(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    seeds.load(conn)

    theme = [
        theme
        for theme in db.get_themes(conn)
        if theme.name == "AI 新創介紹"
    ][0]
    conn.executemany(
        """
        INSERT OR IGNORE INTO theme_sources (theme_id, source_id)
        VALUES (?, ?)
        """,
        [
            (theme.id, source.id)
            for source in db.get_sources(conn)
            if source.id is not None
        ],
    )
    conn.execute(
        "DELETE FROM config WHERE key = 'startup_sources_pruned'"
    )
    conn.commit()

    db.init_schema(conn)

    theme = [
        theme
        for theme in db.get_themes(conn)
        if theme.name == "AI 新創介紹"
    ][0]
    names = {
        source.name
        for source in db.get_sources(conn)
        if source.id in set(theme.source_ids)
    }
    assert names == KEEP
    assert len(db.get_sources(conn)) == len(seeds.DEFAULT_SOURCES)

    # 使用者自己加回一個之後，再跑一次 init_schema 不可以又被刪掉
    other = [
        source
        for source in db.get_sources(conn)
        if source.name == "Hacker News"
    ][0]
    conn.execute(
        "INSERT INTO theme_sources (theme_id, source_id) VALUES (?, ?)",
        (theme.id, other.id),
    )
    conn.commit()

    db.init_schema(conn)

    theme = [
        theme
        for theme in db.get_themes(conn)
        if theme.name == "AI 新創介紹"
    ][0]
    names = {
        source.name
        for source in db.get_sources(conn)
        if source.id in set(theme.source_ids)
    }
    assert "Hacker News" in names
    conn.close()


def test_broken_sources_are_fixed_once(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    seeds.load(conn)

    by_name = {source.name: source for source in db.get_sources(conn)}
    assert by_name["Y Combinator Blog"].fetch_type == "rss"
    assert by_name["Y Combinator Blog"].url.endswith("/blog/rss")
    assert by_name["INSIDE"].fetch_type == "rss"
    assert by_name["INSIDE"].url.endswith("/feed/rss")

    theme = [
        theme
        for theme in db.get_themes(conn)
        if theme.name == "AI 新創介紹"
    ][0]
    names = {
        source.name
        for source in db.get_sources(conn)
        if source.id in set(theme.source_ids)
    }
    assert names == FIXED_KEEP
    # a16z 只是解除綁定，不可從來源庫消失
    assert "a16z" in by_name

    # 使用者自己把 YC 改回 search 之後，再跑一次不可以又被改掉
    yc = by_name["Y Combinator Blog"]
    db.update_source(
        conn,
        Source(
            yc.id,
            yc.name,
            "https://www.ycombinator.com/blog",
            "search",
            True,
        ),
    )
    db.init_schema(conn)

    again = {source.name: source for source in db.get_sources(conn)}
    assert again["Y Combinator Blog"].fetch_type == "search"
    conn.close()
