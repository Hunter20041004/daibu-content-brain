import pytest

from daibu import db, selection
from daibu.llm.base import Idea
from daibu.models import Material, Theme


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
            content_kind="general",
        ):
            captured["avoid_titles"] = avoid_titles
            captured["content_kind"] = content_kind
            return []

    selection.generate_for_theme(
        conn,
        Theme(theme_id, "主題 A", 0, [], 2),
        FakeProvider(),
        [],
    )

    assert captured["avoid_titles"] == ["同主題舊題"]
    assert captured["content_kind"] == "general"


def test_company_profiles_require_company_and_plain_description(
    tmp_path,
    monkeypatch,
):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(
            None,
            "AI 新創介紹",
            4,
            [],
            3,
            content_kind="company_profile",
        ),
    )
    material = Material(
        "Acme 發表產品",
        "https://example.com/acme",
        "Acme 幫團隊整理客服信件。",
    )
    monkeypatch.setattr(
        selection.collector,
        "collect",
        lambda selected_theme, sources: [material],
    )

    class FakeProvider:
        def generate_ideas(self, *args, **kwargs):
            return [
                Idea(
                    "幫團隊整理客服信件",
                    "現在值得看",
                    material.url,
                    company="",
                    source_excerpt=material.snippet,
                ),
                Idea(
                    "   ",
                    "現在值得看",
                    material.url,
                    company="Acme",
                    source_excerpt=material.snippet,
                ),
                Idea(
                    "幫團隊整理客服信件",
                    "現在值得看",
                    material.url,
                    company="Acme",
                    source_excerpt=material.snippet,
                ),
            ]

    ids = selection.generate_for_theme(
        conn,
        Theme(
            theme_id,
            "AI 新創介紹",
            4,
            [],
            3,
            content_kind="company_profile",
        ),
        FakeProvider(),
        [],
    )

    assert len(ids) == 1
    rows = [
        row
        for row in db.get_ideas(conn, status="候選")
        if row.theme_id == theme_id
    ]
    assert [(row.company, row.title) for row in rows] == [
        ("Acme", "幫團隊整理客服信件")
    ]


def test_company_profile_evidence_must_match_collected_material(
    tmp_path,
    monkeypatch,
):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    material = Material(
        "Acme 發表產品",
        "https://example.com/acme",
        "Acme 幫團隊整理客服信件，並標出需要人工回覆的案件。",
    )
    theme = Theme(
        None,
        "AI 新創介紹",
        4,
        [],
        5,
        content_kind="company_profile",
    )
    monkeypatch.setattr(
        selection.collector,
        "collect",
        lambda selected_theme, sources: [material],
    )

    def candidate(url, excerpt):
        return Idea(
            "幫團隊整理客服信件",
            "現在值得看",
            url,
            company="Acme",
            source_excerpt=excerpt,
        )

    class FakeProvider:
        def generate_ideas(self, *args, **kwargs):
            return [
                candidate("http://example.com/acme", "Acme 幫團隊整理客服信件"),
                candidate("https://other.example/acme", "Acme 幫團隊整理客服信件"),
                candidate(material.url, ""),
                candidate(material.url, "素材裡沒有的改寫句子"),
                candidate(material.url, "Acme 幫團隊整理客服信件"),
            ]

    ids = selection.generate_for_theme(
        conn,
        theme,
        FakeProvider(),
        [],
    )

    assert len(ids) == 1
    stored = db.get_ideas(conn, status="候選")
    assert [idea.source_excerpt for idea in stored] == [
        "Acme 幫團隊整理客服信件"
    ]


def test_no_verified_company_candidates_preserves_existing_rows(
    tmp_path,
    monkeypatch,
):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(
            None,
            "AI 新創介紹",
            4,
            [],
            3,
            content_kind="company_profile",
        ),
    )
    db.add_idea(
        conn,
        theme_id,
        Idea("既有公司", "既有角度", "https://example.com/old"),
        status="候選",
    )
    material = Material(
        "Acme 發表產品",
        "https://example.com/acme",
        "Acme 幫團隊整理客服信件。",
    )
    monkeypatch.setattr(
        selection.collector,
        "collect",
        lambda selected_theme, sources: [material],
    )

    class FakeProvider:
        def generate_ideas(self, *args, **kwargs):
            return [
                Idea(
                    "空泛候選",
                    "角度",
                    material.url,
                    company="",
                    source_excerpt=material.snippet,
                )
            ]

    with pytest.raises(
        selection.NoVerifiedCompanyCandidatesError,
        match="沒有找到可核對的公司",
    ):
        selection.generate_for_theme(
            conn,
            Theme(
                theme_id,
                "AI 新創介紹",
                4,
                [],
                3,
                content_kind="company_profile",
            ),
            FakeProvider(),
            [],
        )

    stored = db.get_ideas(conn, status="候選")
    assert [idea.title for idea in stored] == ["既有公司"]
