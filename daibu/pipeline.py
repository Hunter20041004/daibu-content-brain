import sqlite3

from daibu.clock import now as _now

STATUSES = ["候選", "採用", "已發"]
REJECTED = "已淘汰"
ALL_STATUSES = STATUSES + [REJECTED]


def set_status(
    conn: sqlite3.Connection,
    idea_id: int,
    new_status: str,
) -> None:
    if new_status not in ALL_STATUSES:
        raise ValueError(f"不合法的流水線狀態：{new_status}")

    if new_status == "已發":
        conn.execute(
            """
            UPDATE ideas
            SET status = ?, published_at = ?
            WHERE id = ?
            """,
            (new_status, _now(), idea_id),
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
