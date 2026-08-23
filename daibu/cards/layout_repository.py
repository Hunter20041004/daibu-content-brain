from __future__ import annotations

from dataclasses import dataclass
import json
import sqlite3

from daibu.cards.layout_schema import (
    LayoutDocument,
    layout_to_mapping,
    load_builtin_layout,
    parse_layout,
)


@dataclass(frozen=True)
class TemplateVersion:
    id: int
    theme_id: int
    version_no: int
    layout: LayoutDocument
    created_at: str


def _canonical_layout_json(layout: LayoutDocument) -> str:
    validated = parse_layout(layout_to_mapping(layout))
    return json.dumps(
        layout_to_mapping(validated),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _row_to_version(row: sqlite3.Row) -> TemplateVersion:
    return TemplateVersion(
        id=int(row["id"]),
        theme_id=int(row["theme_id"]),
        version_no=int(row["version_no"]),
        layout=parse_layout(json.loads(row["layout_json"])),
        created_at=str(row["created_at"]),
    )


def get_version(conn: sqlite3.Connection, version_id: int) -> TemplateVersion:
    row = conn.execute(
        "SELECT * FROM carousel_template_versions WHERE id = ?",
        (version_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"找不到模板版本：{version_id}")
    return _row_to_version(row)


def list_versions(conn: sqlite3.Connection, theme_id: int) -> tuple[TemplateVersion, ...]:
    rows = conn.execute(
        "SELECT * FROM carousel_template_versions WHERE theme_id = ? ORDER BY version_no DESC",
        (theme_id,),
    ).fetchall()
    return tuple(_row_to_version(row) for row in rows)


def ensure_default_version(
    conn: sqlite3.Connection,
    theme_id: int,
) -> TemplateVersion:
    active_row = conn.execute(
        """
        SELECT versions.*
        FROM carousel_template_settings AS settings
        JOIN carousel_template_versions AS versions
          ON versions.id = settings.active_version_id
        WHERE settings.theme_id = ?
        """,
        (theme_id,),
    ).fetchone()
    if active_row is not None:
        return _row_to_version(active_row)

    with conn:
        version_row = conn.execute(
            """
            SELECT * FROM carousel_template_versions
            WHERE theme_id = ?
            ORDER BY version_no
            LIMIT 1
            """,
            (theme_id,),
        ).fetchone()
        if version_row is None:
            layout = load_builtin_layout()
            cursor = conn.execute(
                """
                INSERT INTO carousel_template_versions (
                    theme_id, version_no, schema_version, layout_json
                ) VALUES (?, 1, ?, ?)
                """,
                (
                    theme_id,
                    layout.schema_version,
                    _canonical_layout_json(layout),
                ),
            )
            version_id = int(cursor.lastrowid)
        else:
            version_id = int(version_row["id"])
        conn.execute(
            """
            INSERT INTO carousel_template_settings (theme_id, active_version_id)
            VALUES (?, ?)
            """,
            (theme_id, version_id),
        )
    return get_version(conn, version_id)


def get_active_version(
    conn: sqlite3.Connection,
    theme_id: int,
) -> TemplateVersion:
    row = conn.execute(
        """
        SELECT versions.*
        FROM carousel_template_settings AS settings
        JOIN carousel_template_versions AS versions
          ON versions.id = settings.active_version_id
        WHERE settings.theme_id = ?
        """,
        (theme_id,),
    ).fetchone()
    if row is None:
        return ensure_default_version(conn, theme_id)
    return _row_to_version(row)


def create_version(
    conn: sqlite3.Connection,
    theme_id: int,
    layout: LayoutDocument,
) -> TemplateVersion:
    canonical_json = _canonical_layout_json(layout)
    with conn:
        row = conn.execute(
            """
            SELECT COALESCE(MAX(version_no), 0) + 1 AS next_version
            FROM carousel_template_versions
            WHERE theme_id = ?
            """,
            (theme_id,),
        ).fetchone()
        version_no = int(row["next_version"])
        cursor = conn.execute(
            """
            INSERT INTO carousel_template_versions (
                theme_id, version_no, schema_version, layout_json
            ) VALUES (?, ?, ?, ?)
            """,
            (
                theme_id,
                version_no,
                layout.schema_version,
                canonical_json,
            ),
        )
        version_id = int(cursor.lastrowid)
    return get_version(conn, version_id)


def set_active_version(
    conn: sqlite3.Connection,
    theme_id: int,
    version_id: int,
) -> None:
    version = get_version(conn, version_id)
    if version.theme_id != theme_id:
        raise ValueError("模板版本不屬於這個內容系列")
    with conn:
        conn.execute(
            """
            INSERT INTO carousel_template_settings (theme_id, active_version_id)
            VALUES (?, ?)
            ON CONFLICT(theme_id) DO UPDATE SET
                active_version_id = excluded.active_version_id
            """,
            (theme_id, version_id),
        )
