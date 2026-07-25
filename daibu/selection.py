import sqlite3

from daibu import db
from daibu.fetch import collector
from daibu.llm.base import LLMProvider
from daibu.models import Source, Theme


def generate_for_theme(
    conn: sqlite3.Connection,
    theme: Theme,
    provider: LLMProvider,
    sources: list[Source],
) -> list[int]:
    materials = collector.collect(theme, sources)
    avoid_titles = db.get_rejected_titles(conn, theme.id)
    generated = provider.generate_ideas(
        theme.name,
        materials,
        theme.n_ideas,
        avoid_titles=avoid_titles,
    )
    return [
        db.add_idea(conn, theme.id, idea, status="候選")
        for idea in generated
    ]
