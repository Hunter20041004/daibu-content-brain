import sqlite3


def record(
    conn: sqlite3.Connection,
    idea_id: int,
    platform: str,
    likes: int,
    reach: int,
    engagement: float,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO performance (
            idea_id, platform, likes, reach, engagement
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (idea_id, platform, likes, reach, engagement),
    )
    conn.commit()
    return cursor.lastrowid


def summary_by_theme(conn: sqlite3.Connection) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT
            themes.name AS theme,
            COUNT(performance.id) AS posts,
            AVG(performance.likes) AS avg_likes,
            AVG(performance.reach) AS avg_reach,
            AVG(performance.engagement) AS avg_engagement
        FROM themes
        JOIN ideas ON ideas.theme_id = themes.id
        JOIN performance ON performance.idea_id = ideas.id
        GROUP BY themes.id, themes.name
        ORDER BY avg_engagement DESC, themes.name
        """
    ).fetchall()
    return [dict(row) for row in rows]


def suggest(summary: list[dict[str, object]]) -> str:
    if not summary:
        return "尚無成效資料；請先回填至少一則已發貼文。"

    ranked = sorted(
        summary,
        key=lambda row: float(row["avg_engagement"]),
        reverse=True,
    )
    strongest = str(ranked[0]["theme"])
    if len(ranked) == 1:
        return f"目前表現最好的是「{strongest}」；累積更多主題後再比較。"

    weakest = str(ranked[-1]["theme"])
    return (
        f"目前表現最好的是「{strongest}」；"
        f"下週可優先補強「{weakest}」，再觀察互動是否改善。"
    )
