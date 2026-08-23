from daibu import db
from daibu.cards import layout_repository, template_editor_service
from daibu.cards.layout_schema import layout_to_mapping, load_builtin_layout
from daibu.cards.template_stress import build_template_stress_cases
from daibu.models import Theme
from daibu.llm.base import Idea
from tests.card_fixtures import brand_asset, renderable_carousel_draft
from PIL import Image


def _setup(tmp_path):
    conn=db.connect(str(tmp_path/"template.db"));db.init_schema(conn)
    theme_id=db.add_theme(conn,Theme(None,"AI 新創介紹",4,[],1))
    version=layout_repository.ensure_default_version(conn,theme_id)
    return conn,theme_id,version


def test_unknown_template_property_does_not_create_version(tmp_path):
    conn,theme_id,version=_setup(tmp_path);raw=layout_to_mapping(version.layout)
    raw["pages"]["cover"]["elements"]["heading"]["rotate"]=10
    result=template_editor_service.save_template_version(conn,theme_id,version.id,raw,())
    assert result.version is None
    assert "不允許" in result.issues[0].message
    assert len(layout_repository.list_versions(conn,theme_id))==1


def test_success_creates_immutable_inactive_version(tmp_path):
    conn,theme_id,version=_setup(tmp_path);raw=layout_to_mapping(load_builtin_layout())
    result=template_editor_service.save_template_version(conn,theme_id,version.id,raw,build_template_stress_cases())
    assert not result.issues
    assert result.version.version_no==2
    assert layout_repository.get_active_version(conn,theme_id).id==version.id


def test_upgrade_changes_only_template_binding_and_revision(tmp_path):
    conn,theme_id,version=_setup(tmp_path)
    idea_id=db.add_idea(conn,theme_id,Idea("升級","角度","",company="ElevenLabs"),status="採用")
    draft=renderable_carousel_draft();db.save_carousel_draft(conn,idea_id,draft)
    target=layout_repository.create_version(conn,theme_id,load_builtin_layout())
    logo_path=tmp_path/"logo.png";Image.new("RGBA",(240,80),(47,124,135,255)).save(logo_path)
    before=db.get_carousel_draft_meta(conn,idea_id)
    result=template_editor_service.upgrade_draft_template(conn,idea_id,theme_id,draft,"ElevenLabs",brand_asset(logo_path),target.id)
    after=db.get_carousel_draft_meta(conn,idea_id)
    assert not result.issues
    assert after.template_version_id==target.id
    assert after.content_revision==before.content_revision+1
    assert db.get_carousel_draft(conn,idea_id)==draft
