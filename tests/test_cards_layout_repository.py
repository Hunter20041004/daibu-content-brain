import pytest

from daibu import db
from daibu.cards import layout_repository
from daibu.cards.layout_schema import replace_element
from daibu.models import Theme


def test_new_template_version_is_immutable_and_not_activated_implicitly(
    tmp_path,
):
    conn = db.connect(str(tmp_path / "test.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "一布懂 AI 新創", 4, [], 5),
    )

    first = layout_repository.ensure_default_version(conn, theme_id)
    changed = replace_element(first.layout, "cover", "company-name", x=120)
    second = layout_repository.create_version(conn, theme_id, changed)

    assert second.version_no == 2
    assert layout_repository.get_active_version(conn, theme_id).id == first.id
    assert layout_repository.get_version(conn, first.id).layout != second.layout


def test_template_version_cannot_be_activated_for_another_theme(tmp_path):
    conn = db.connect(str(tmp_path / "ownership.db"))
    db.init_schema(conn)
    first_theme_id = db.add_theme(
        conn,
        Theme(None, "系列 A", 1, [], 5),
    )
    second_theme_id = db.add_theme(
        conn,
        Theme(None, "系列 B", 2, [], 5),
    )
    first_active = layout_repository.ensure_default_version(
        conn,
        first_theme_id,
    )
    other_version = layout_repository.ensure_default_version(
        conn,
        second_theme_id,
    )

    with pytest.raises(ValueError, match="不屬於這個內容系列"):
        layout_repository.set_active_version(
            conn,
            first_theme_id,
            other_version.id,
        )

    assert (
        layout_repository.get_active_version(conn, first_theme_id).id
        == first_active.id
    )


def test_startup_removes_legacy_version_and_replaces_it_with_v3(tmp_path):
    conn = db.connect(str(tmp_path / "legacy.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "舊版系列", 1, [], 5),
    )
    with conn:
        cursor = conn.execute(
            "INSERT INTO carousel_template_versions "
            "(theme_id, version_no, schema_version, layout_json) "
            "VALUES (?, 1, 1, '{\"schema_version\":1}')",
            (theme_id,),
        )
    legacy_id = int(cursor.lastrowid)

    db.init_schema(conn)

    assert conn.execute(
        "SELECT 1 FROM carousel_template_versions WHERE id = ?", (legacy_id,)
    ).fetchone() is None
    active = layout_repository.get_active_version(conn, theme_id)
    assert active.layout.schema_version == 3
    assert "reason" in active.layout.pages["who"].elements
