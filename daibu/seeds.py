import sqlite3

from daibu import db
from daibu.models import Source, Theme

DEFAULT_THEMES = [
    Theme(None, "AI 近期大事", 0, "timely", ["L1", "L2", "L3", "L4"], 3),
    Theme(
        None,
        "本週熱門 Claude/Codex Skill",
        2,
        "timely",
        ["L2", "L4"],
        3,
    ),
    Theme(
        None,
        "AI 新創介紹",
        4,
        "evergreen",
        ["L1", "L2", "L4", "L5"],
        3,
    ),
]

DEFAULT_SOURCES = [
    Source(None, "TechCrunch", "https://techcrunch.com/feed/", "L1", "rss", True),
    Source(None, "iThome AI", "https://www.ithome.com.tw/tags/ai", "L1", "search", True),
    Source(None, "科技新報 TechNews", "https://technews.tw/category/ai/", "L1", "search", True),
    Source(None, "OpenAI News", "https://openai.com/news/", "L2", "search", True),
    Source(None, "Anthropic News", "https://www.anthropic.com/news", "L2", "search", True),
    Source(
        None,
        "Google DeepMind Blog",
        "https://deepmind.google/discover/blog/",
        "L2",
        "search",
        True,
    ),
    Source(None, "Y Combinator Blog", "https://www.ycombinator.com/blog", "L2", "search", True),
    Source(
        None,
        "Anthropic Skills Releases",
        "https://github.com/anthropics/skills/releases",
        "L2",
        "search",
        True,
    ),
    # TODO(需澄清): 電子報沒有穩定公開 RSS；v1 先列為手動來源。
    Source(None, "TLDR AI", "https://tldr.tech/ai", "L3", "manual", True),
    Source(None, "Ben's Bites", "https://www.bensbites.com/", "L3", "manual", True),
    Source(None, "Hacker News", "https://hnrss.org/frontpage", "L4", "rss", True),
    Source(None, "GitHub", "https://github.com/", "L4", "search", True),
    Source(None, "Product Hunt AI", "https://www.producthunt.com/feed", "L4", "rss", True),
    Source(
        None,
        "Reddit r/ClaudeAI",
        "https://www.reddit.com/r/ClaudeAI/.rss",
        "L4",
        "rss",
        True,
    ),
    Source(
        None,
        "Reddit r/LocalLLaMA",
        "https://www.reddit.com/r/LocalLLaMA/.rss",
        "L4",
        "rss",
        True,
    ),
    # TODO(需澄清): Skill 生態無穩定排行榜；保留人工補來源後備。
    Source(
        None,
        "Awesome Claude Code",
        "https://github.com/hesreallyhim/awesome-claude-code",
        "L4",
        "manual",
        True,
    ),
    Source(None, "a16z", "https://a16z.com/feed/", "L5", "rss", True),
    Source(None, "INSIDE", "https://www.inside.com.tw/tag/AI", "L5", "search", True),
]


def load(conn: sqlite3.Connection) -> None:
    existing_theme_names = {theme.name for theme in db.get_themes(conn)}
    for theme in DEFAULT_THEMES:
        if theme.name not in existing_theme_names:
            db.add_theme(conn, theme)

    existing_source_names = {source.name for source in db.get_sources(conn)}
    for source in DEFAULT_SOURCES:
        if source.name not in existing_source_names:
            db.add_source(conn, source)
