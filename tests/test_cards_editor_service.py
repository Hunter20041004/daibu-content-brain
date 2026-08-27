from pathlib import Path

from PIL import Image

from daibu import db
from daibu.cards import editor_service, layout_repository
from daibu.cards.editor_payload import editable_values
from daibu.cards.layout_schema import load_builtin_layout, replace_element
from daibu.llm.base import Idea
from daibu.models import Theme
from tests.card_fixtures import brand_asset, renderable_carousel_draft


def _saved_editor(tmp_path: Path):
    conn = db.connect(str(tmp_path / "editor.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "AI 新創介紹", 4, [], 1))
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("內容編輯", "角度", "", company="ElevenLabs"),
        status="採用",
    )
    draft = renderable_carousel_draft()
    db.save_carousel_draft(conn, idea_id, draft)
    logo_path = tmp_path / "logo.png"
    Image.new("RGBA", (240, 80), (47, 124, 135, 255)).save(logo_path)
    return conn, theme_id, idea_id, draft, brand_asset(logo_path)


def test_layout_failure_rolls_back_all_seven_pages(tmp_path):
    conn, theme_id, idea_id, draft, asset = _saved_editor(tmp_path)
    bad_layout = replace_element(
        load_builtin_layout(),
        "cover",
        "heading",
        h=24,
    )
    version = layout_repository.create_version(conn, theme_id, bad_layout)
    db.upgrade_carousel_template(conn, idea_id, version.id)
    before_meta = db.get_carousel_draft_meta(conn, idea_id)
    values = editable_values(draft)
    values["page.cover.heading"] = "新封面標題"

    result = editor_service.save_editor_payload(
        conn,
        idea_id,
        draft,
        {"revision": before_meta.content_revision, "values": values},
        "ElevenLabs",
        asset,
    )

    assert db.get_carousel_draft(conn, idea_id) == draft
    assert db.get_carousel_draft_meta(conn, idea_id) == before_meta
    assert result.issues[0].page_type == "cover"
    assert result.issues[0].field_key == "page.cover.heading"


def test_success_saves_all_changes_and_increments_revision(tmp_path):
    conn, _theme_id, idea_id, draft, asset = _saved_editor(tmp_path)
    before = db.get_carousel_draft_meta(conn, idea_id)
    values = editable_values(draft)
    values["page.who.heading"] = "認識 ElevenLabs"
    values["page.problem.diagram.0.title"] = "內容需求"

    result = editor_service.save_editor_payload(
        conn,
        idea_id,
        draft,
        {"revision": before.content_revision, "values": values},
        "ElevenLabs",
        asset,
    )

    after = db.get_carousel_draft_meta(conn, idea_id)
    saved = db.get_carousel_draft(conn, idea_id)
    assert not result.issues
    assert after.content_revision == before.content_revision + 1
    assert after.template_version_id == before.template_version_id
    assert saved.pages[1].heading == "認識 ElevenLabs"
    assert saved.pages[2].diagram.nodes[0].title == "內容需求"


def test_stale_revision_preserves_database(tmp_path):
    conn, _theme_id, idea_id, draft, asset = _saved_editor(tmp_path)

    result = editor_service.save_editor_payload(
        conn,
        idea_id,
        draft,
        {"revision": 0, "values": editable_values(draft)},
        "ElevenLabs",
        asset,
    )

    assert "其他畫面更新" in result.issues[0].message
    assert db.get_carousel_draft(conn, idea_id) == draft


def test_save_accepts_a_concise_inner_heading(tmp_path):
    conn, _theme_id, idea_id, draft, asset = _saved_editor(tmp_path)
    metadata = db.get_carousel_draft_meta(conn, idea_id)
    values = editable_values(draft)
    values["page.how-ai.heading"] = "如何處理內容"

    result = editor_service.save_editor_payload(
        conn,
        idea_id,
        draft,
        {"revision": metadata.content_revision, "values": values},
        "ElevenLabs",
        asset,
    )

    assert not result.issues
    assert db.get_carousel_draft(conn, idea_id).pages[3].heading == "如何處理內容"
