import sqlite3
from collections.abc import Callable

from daibu import db
from daibu.llm import prompt
from daibu.models import StoredIdea


def generate(
    conn: sqlite3.Connection,
    idea: StoredIdea,
    generate_text: Callable[[str], str],
) -> list[dict]:
    if not idea.company.strip():
        raise ValueError("這則題目沒有公司名，無法產生輪播草稿")

    prompt_text = prompt.build_carousel(
        idea.company,
        idea.title,
        idea.angle,
        idea.source_excerpt,
    )
    rows = prompt.parse_carousel(generate_text(prompt_text))
    db.save_carousel(conn, idea.id, rows)
    return rows
