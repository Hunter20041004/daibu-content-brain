import sqlite3

STATUSES = ["候選", "採用", "草稿", "已排程", "已發"]


def set_status(
    conn: sqlite3.Connection,
    idea_id: int,
    new_status: str,
) -> None:
    if new_status not in STATUSES:
        raise ValueError(f"不合法的流水線狀態：{new_status}")

    if new_status == "已發":
        conn.execute(
            """
            UPDATE ideas
            SET status = ?, published_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_status, idea_id),
        )
    else:
        conn.execute(
            """
            UPDATE ideas
            SET status = ?, published_at = NULL
            WHERE id = ?
            """,
            (new_status, idea_id),
        )
    conn.commit()


def update_body(
    conn: sqlite3.Connection,
    idea_id: int,
    body: str,
) -> None:
    conn.execute(
        "UPDATE ideas SET body = ? WHERE id = ?",
        (body, idea_id),
    )
    conn.commit()
