import sqlite3
from dataclasses import dataclass

from daibu import db
from daibu.models import Source, Theme


@dataclass(frozen=True)
class ThemeSeed:
    name: str
    weekday: int
    n_ideas: int
    source_names: list[str]
    content_kind: str = "general"


DEFAULT_THEMES = [
    ThemeSeed(
        "AI 新創介紹",
        4,
        3,
        [
            "YC Launches",
            "YC Companies",
            "a16z Speedrun Companies",
            "TechCrunch Startups",
        ],
        content_kind="company_profile",
    ),
]

DEFAULT_SOURCES = [
    Source(None, "TechCrunch", "https://techcrunch.com/feed/", "rss", True),
    Source(
        None,
        "TechCrunch Startups",
        "https://techcrunch.com/category/startups/feed/",
        "rss",
        True,
    ),
    Source(None, "iThome AI", "https://www.ithome.com.tw/tags/ai", "search", True),
    Source(None, "科技新報 TechNews", "https://technews.tw/category/ai/", "search", True),
    Source(None, "OpenAI News", "https://openai.com/news/", "search", True),
    Source(None, "Anthropic News", "https://www.anthropic.com/news", "search", True),
    Source(
        None,
        "Google DeepMind Blog",
        "https://deepmind.google/discover/blog/",
        "search",
        True,
    ),
    Source(
        None,
        "Y Combinator Blog",
        "https://www.ycombinator.com/blog/rss",
        "rss",
        True,
    ),
    Source(
        None,
        "YC Launches",
        "https://www.ycombinator.com/launches",
        "directory",
        True,
    ),
    Source(
        None,
        "YC Companies",
        "https://www.ycombinator.com/companies",
        "directory",
        True,
    ),
    Source(
        None,
        "Anthropic Skills Releases",
        "https://github.com/anthropics/skills/releases",
        "search",
        True,
    ),
    Source(None, "Hacker News", "https://hnrss.org/frontpage", "rss", True),
    Source(None, "GitHub", "https://github.com/", "search", True),
    Source(None, "Product Hunt AI", "https://www.producthunt.com/feed", "rss", True),
    Source(
        None,
        "Reddit r/ClaudeAI",
        "https://www.reddit.com/r/ClaudeAI/.rss",
        "rss",
        True,
    ),
    Source(
        None,
        "Reddit r/LocalLLaMA",
        "https://www.reddit.com/r/LocalLLaMA/.rss",
        "rss",
        True,
    ),
    Source(None, "a16z", "https://a16z.com/feed/", "rss", False),
    Source(
        None,
        "a16z Speedrun Companies",
        "https://speedrun.a16z.com/companies",
        "directory",
        True,
    ),
    Source(
        None,
        "VentureBeat AI",
        "https://venturebeat.com/category/ai/feed/",
        "rss",
        True,
    ),
    Source(None, "INSIDE", "https://www.inside.com.tw/feed/rss", "rss", True),
]


def load(conn: sqlite3.Connection) -> None:
    if db.get_config(conn, "seeds_loaded") == "1":
        return

    existing_source_names = {source.name for source in db.get_sources(conn)}
    for source in DEFAULT_SOURCES:
        if source.name not in existing_source_names:
            db.add_source(conn, source)

    source_ids_by_name = {
        source.name: source.id
        for source in db.get_sources(conn)
        if source.id is not None
    }
    existing_theme_names = {theme.name for theme in db.get_themes(conn)}
    for seed in DEFAULT_THEMES:
        if seed.name not in existing_theme_names:
            db.add_theme(
                conn,
                Theme(
                    None,
                    seed.name,
                    seed.weekday,
                    [
                        source_ids_by_name[name]
                        for name in seed.source_names
                    ],
                    seed.n_ideas,
                    content_kind=seed.content_kind,
                ),
            )
    db.set_config(conn, "seeds_loaded", "1")
