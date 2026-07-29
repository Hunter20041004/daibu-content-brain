import sqlite3
from collections.abc import Callable

from daibu import db
from daibu.llm import prompt
from daibu.models import StoredIdea


MIN_EXCERPT_CHARS = 60


def generate(
    conn: sqlite3.Connection,
    idea: StoredIdea,
    generate_text: Callable[[str], str],
) -> list[dict]:
    if not idea.company.strip():
        raise ValueError("這則題目沒有公司名，無法產生輪播草稿")
    excerpt_length = len(idea.source_excerpt.strip())
    if excerpt_length < MIN_EXCERPT_CHARS:
        raise ValueError(
            f"來源引文只有 {excerpt_length} 字，"
            f"不足以當依據（至少要 {MIN_EXCERPT_CHARS} 字），"
            "建議換一則候選，或先在微調裡補上引文"
        )

    prompt_text = prompt.build_carousel(
        idea.company,
        idea.title,
        idea.angle,
        idea.source_excerpt,
    )
    rows = prompt.parse_carousel(generate_text(prompt_text))
    db.save_carousel(conn, idea.id, rows)
    return rows
