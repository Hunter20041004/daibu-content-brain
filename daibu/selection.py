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
    gate_line: str,
) -> list[int]:
    materials = collector.collect(theme, sources)
    generated = provider.generate_ideas(
        theme.name,
        theme.kind,
        materials,
        gate_line,
        theme.n_ideas,
    )
    return [
        db.add_idea(conn, theme.id, idea, status="候選")
        for idea in generated
    ]
