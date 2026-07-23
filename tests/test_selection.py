from daibu import db, selection
from daibu.llm.base import Idea
from daibu.models import Theme


def test_generate_persists_candidates(tmp_path, monkeypatch):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme = Theme(None, "大事", 0, "timely", ["L1"], 2)
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
                    80,
                    "理由",
                    "https://example.com/a",
                )
            ]

    ids = selection.generate_for_theme(
        conn,
        theme,
        FakeProvider(),
        [],
        gate_line="守門線",
    )

    rows = db.get_ideas(conn, status="候選")
    assert len(ids) == 1
    assert len(rows) == 1
    assert rows[0].gate_score == 80
