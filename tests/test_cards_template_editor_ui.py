from daibu import db
from daibu.cards import template_editor_component, template_editor_ui
from daibu.models import Theme


def test_template_management_builds_seven_page_payload(tmp_path,monkeypatch):
    conn=db.connect(str(tmp_path/"ui.db"));db.init_schema(conn)
    db.add_theme(conn,Theme(None,"AI 新創介紹",4,[],1))
    captured={}
    def mount(payload,*,key): captured.update(payload);return template_editor_component.TemplateEditorEvent(False,None)
    monkeypatch.setattr(template_editor_ui,"mount_template_editor",mount)
    template_editor_ui.render_template_management(conn)
    assert len(captured["pages"])==7
    assert captured["previewHtml"]
    assert "layout" in captured
