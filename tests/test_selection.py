from daibu import db, selection
from daibu.llm.base import Idea
from daibu.models import Theme


def test_generate_persists_candidates(tmp_path, monkeypatch):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme = Theme(None, "大事", 0, [], 2)
    monkeypatch.setattr(
        selection.collector,
        "collect",
        lambda selected_theme, sources: [],
    )

    class FakeProvider:
        def generate_ideas(self, *args, **kwargs):
            return [
                Idea(
                    "標題",
                    "角度",
                    "https://example.com/a",
                )
            ]

    ids = selection.generate_for_theme(
        conn,
        theme,
        FakeProvider(),
        [],
    )

    rows = db.get_ideas(conn, status="候選")
    assert len(ids) == 1
    assert len(rows) == 1
    assert rows[0].source_url == "https://example.com/a"


def test_generate_passes_rejected_titles_of_that_theme(
    tmp_path,
    monkeypatch,
):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "主題 A", 0, [], 2),
    )
    other_theme_id = db.add_theme(
        conn,
        Theme(None, "主題 B", 1, [], 2),
    )
    db.add_idea(
        conn,
        theme_id,
        Idea("同主題舊題", "角度", ""),
        status="已淘汰",
    )
    db.add_idea(
        conn,
        other_theme_id,
        Idea("別的主題舊題", "角度", ""),
        status="已淘汰",
    )
    monkeypatch.setattr(
        selection.collector,
        "collect",
        lambda selected_theme, sources: [],
    )
    captured = {}

    class FakeProvider:
        def generate_ideas(
            self,
            theme_name,
            materials,
            n,
            avoid_titles=None,
        ):
            captured["avoid_titles"] = avoid_titles
            return []

    selection.generate_for_theme(
        conn,
        Theme(theme_id, "主題 A", 0, [], 2),
        FakeProvider(),
        [],
    )

    assert captured["avoid_titles"] == ["同主題舊題"]
