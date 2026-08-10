import pytest

from daibu import company_eligibility, db, selection
from daibu.llm.base import Idea
from daibu.models import CompanyEligibility, Material, StoredIdea, Theme


@pytest.fixture(autouse=True)
def qualify_unseen_test_companies(monkeypatch):
    def fake_evaluate(
        companies,
        search_fn,
        generate_text,
        *,
        current_year,
        checked_at=None,
    ):
        del search_fn, generate_text, current_year
        return {
            company.strip().casefold(): CompanyEligibility(
                company.strip().casefold(),
                company.strip(),
                "eligible",
                2022,
                "private_independent",
                "測試預設為合格",
                (),
                checked_at or "2026-08-10 13:00:00",
            )
            for company in companies
        }

    monkeypatch.setattr(company_eligibility, "evaluate_companies", fake_evaluate)


def _stored_idea(
    idea_id: int,
    company: str,
    created_at: str,
    title: str | None = None,
) -> StoredIdea:
    return StoredIdea(
        id=idea_id,
        theme_id=3,
        title=title or f"{company or '通用'}題目 {idea_id}",
        angle="角度",
        source_url="",
        status="候選",
        body="",
        created_at=created_at,
        published_at=None,
        company=company,
    )


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


def test_visible_company_profile_ideas_keeps_earliest_valid_company():
    later_railway = _stored_idea(
        12,
        " railway ",
        "2026-08-05 10:01:00",
        "後來的 Railway 題目",
    )
    moove = _stored_idea(11, "Moove", "2026-08-05 10:00:30")
    earliest_railway = _stored_idea(
        10,
        "Railway",
        "2026-08-05 10:00:00",
        "第一次 Railway 題目",
    )
    legacy = _stored_idea(8, "   ", "2026-07-25 09:00:00")
    ideas = [later_railway, moove, earliest_railway, legacy]

    visible = selection.visible_company_profile_ideas(ideas)

    assert [idea.id for idea in visible] == [moove.id, earliest_railway.id]
    assert ideas == [later_railway, moove, earliest_railway, legacy]


def test_visible_company_profiles_hide_explicitly_disallowed_companies():
    cloudflare = _stored_idea(1, "Cloudflare", "2026-08-01 09:00:00")
    railway = _stored_idea(2, "Railway", "2026-08-01 09:01:00")
    moove_without_cache = _stored_idea(3, "Moove", "2026-08-01 09:02:00")

    visible = selection.visible_company_profile_ideas(
        [cloudflare, railway, moove_without_cache],
        disallowed_company_keys={"cloudflare", "unknownco"},
    )

    assert [idea.company for idea in visible] == ["Railway", "Moove"]


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


def test_company_generation_rejects_seen_company_across_all_statuses(
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
        Idea(
            "雲端部署服務",
            "舊角度",
            "https://example.com/railway",
            company="Railway",
        ),
        status="採用",
    )
    materials = [
        Material(
            "Railway 更新",
            "https://example.com/railway-new",
            "Railway 推出新的部署功能。",
        ),
        Material(
            "Acme 更新",
            "https://example.com/acme",
            "Acme 幫團隊整理客服信件。",
        ),
    ]
    monkeypatch.setattr(
        selection.collector,
        "collect",
        lambda selected_theme, sources: materials,
    )

    class FakeProvider:
        def generate_ideas(self, *args, **kwargs):
            return [
                Idea(
                    "新的部署功能",
                    "新角度",
                    materials[0].url,
                    company=" railway ",
                    source_excerpt=materials[0].snippet,
                ),
                Idea(
                    "整理客服信件",
                    "現在值得看",
                    materials[1].url,
                    company="Acme",
                    source_excerpt=materials[1].snippet,
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
    assert [
        idea.company for idea in db.get_ideas(conn, status="候選")
    ] == ["Acme"]


def test_company_generation_rejects_seen_title_and_same_batch_duplicates(
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
            4,
            content_kind="company_profile",
        ),
    )
    db.add_idea(
        conn,
        theme_id,
        Idea("整理客服信件", "舊角度", "", company="OldCo"),
        status="已淘汰",
    )
    materials = [
        Material(
            f"{company} 更新",
            f"https://example.com/{index}",
            f"{company} 公布新的產品功能。",
        )
        for index, company in enumerate(
            ("NewCo", "Acme", "ACME", "Beta"),
            start=1,
        )
    ]
    monkeypatch.setattr(
        selection.collector,
        "collect",
        lambda selected_theme, sources: materials,
    )

    class FakeProvider:
        def generate_ideas(self, *args, **kwargs):
            return [
                Idea(
                    " 整理客服信件 ",
                    "新角度",
                    materials[0].url,
                    company="NewCo",
                    source_excerpt=materials[0].snippet,
                ),
                Idea(
                    "客服分類工具",
                    "角度",
                    materials[1].url,
                    company="Acme",
                    source_excerpt=materials[1].snippet,
                ),
                Idea(
                    "另一個客服工具",
                    "角度",
                    materials[2].url,
                    company=" acme ",
                    source_excerpt=materials[2].snippet,
                ),
                Idea(
                    "整理銷售線索",
                    "角度",
                    materials[3].url,
                    company="Beta",
                    source_excerpt=materials[3].snippet,
                ),
            ]

    ids = selection.generate_for_theme(
        conn,
        Theme(
            theme_id,
            "AI 新創介紹",
            4,
            [],
            4,
            content_kind="company_profile",
        ),
        FakeProvider(),
        [],
    )

    assert len(ids) == 2
    stored = db.get_ideas(conn, status="候選")
    assert {(idea.company, idea.title) for idea in stored} == {
        ("Acme", "客服分類工具"),
        ("Beta", "整理銷售線索"),
    }


def test_fully_duplicated_company_response_preserves_existing_rows(
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
            1,
            content_kind="company_profile",
        ),
    )
    existing_id = db.add_idea(
        conn,
        theme_id,
        Idea("部署服務", "舊角度", "", company="Railway"),
        status="候選",
    )
    material = Material(
        "Railway 更新",
        "https://example.com/railway",
        "Railway 推出新的部署功能。",
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
                    "新的部署功能",
                    "新角度",
                    material.url,
                    company="Railway",
                    source_excerpt=material.snippet,
                )
            ]

    with pytest.raises(
        selection.NoVerifiedCompanyCandidatesError,
        match="新的公司",
    ):
        selection.generate_for_theme(
            conn,
            Theme(
                theme_id,
                "AI 新創介紹",
                4,
                [],
                1,
                content_kind="company_profile",
            ),
            FakeProvider(),
            [],
        )

    assert [idea.id for idea in db.get_ideas(conn)] == [existing_id]


def test_company_generation_uses_cache_and_checks_only_unseen(
    tmp_path,
    monkeypatch,
):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme = Theme(
        None,
        "AI 新創介紹",
        4,
        [],
        4,
        content_kind="company_profile",
    )
    for company, verdict, status in [
        ("PublicCo", "ineligible", "public"),
        ("MysteryCo", "unknown", "unknown"),
        ("GoodCo", "eligible", "private_independent"),
    ]:
        db.save_company_eligibility(
            conn,
            CompanyEligibility(
                company.casefold(),
                company,
                verdict,
                2022 if verdict != "unknown" else None,
                status,
                "快取結果",
                (),
                "2026-08-10 13:00:00",
            ),
        )
    materials = [
        Material(
            company,
            f"https://example.com/{company.casefold()}",
            f"{company} 發表新產品。",
        )
        for company in ("PublicCo", "MysteryCo", "GoodCo", "NewCo")
    ]
    monkeypatch.setattr(
        selection.collector,
        "collect",
        lambda selected_theme, sources: materials,
    )
    evaluated: list[list[str]] = []

    def fake_evaluate(companies, *args, **kwargs):
        evaluated.append(companies)
        return {
            "newco": CompanyEligibility(
                "newco",
                "NewCo",
                "eligible",
                2024,
                "private_independent",
                "查核合格",
                (),
                "2026-08-10 13:10:00",
            )
        }

    monkeypatch.setattr(company_eligibility, "evaluate_companies", fake_evaluate)
    captured: dict[str, list[str]] = {}

    class FakeProvider:
        def generate_ideas(self, *args, **kwargs):
            captured["avoid_companies"] = kwargs["avoid_companies"]
            return [
                Idea(
                    f"{material.title} 在做什麼",
                    "值得看",
                    material.url,
                    company=material.title,
                    source_excerpt=material.snippet,
                )
                for material in materials
            ]

        def generate_text(self, prompt):
            raise AssertionError(f"fake evaluator should intercept: {prompt}")

    ids = selection.generate_for_theme(conn, theme, FakeProvider(), [])

    assert set(captured["avoid_companies"]) == {"PublicCo", "MysteryCo"}
    assert evaluated == [["NewCo"]]
    assert len(ids) == 2
    assert {idea.company for idea in db.get_ideas(conn)} == {"GoodCo", "NewCo"}


def test_company_generation_caches_every_fresh_verdict_and_persists_only_eligible(
    tmp_path,
    monkeypatch,
):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    companies = ("GoodCo", "PublicCo", "MysteryCo")
    materials = [
        Material(
            company,
            f"https://example.com/{company.casefold()}",
            f"{company} 最新消息。",
        )
        for company in companies
    ]
    monkeypatch.setattr(selection.collector, "collect", lambda *_: materials)

    def fake_evaluate(*args, **kwargs):
        del args, kwargs
        return {
            "goodco": CompanyEligibility(
                "goodco", "GoodCo", "eligible", 2023,
                "private_independent", "合格", (), "2026-08-10 13:00:00",
            ),
            "publicco": CompanyEligibility(
                "publicco", "PublicCo", "ineligible", 2020,
                "public", "已上市", (), "2026-08-10 13:00:00",
            ),
            "mysteryco": CompanyEligibility(
                "mysteryco", "MysteryCo", "unknown", None,
                "unknown", "資料不足", (), "2026-08-10 13:00:00",
            ),
        }

    monkeypatch.setattr(company_eligibility, "evaluate_companies", fake_evaluate)

    class FakeProvider:
        def generate_ideas(self, *args, **kwargs):
            return [
                Idea(
                    f"{item.title} 在做什麼",
                    "值得看",
                    item.url,
                    company=item.title,
                    source_excerpt=item.snippet,
                )
                for item in materials
            ]

    ids = selection.generate_for_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 3, "company_profile"),
        FakeProvider(),
        [],
    )

    assert len(ids) == 1
    assert [idea.company for idea in db.get_ideas(conn)] == ["GoodCo"]
    assert {
        key: record.verdict
        for key, record in db.get_company_eligibilities(conn).items()
    } == {
        "goodco": "eligible",
        "mysteryco": "unknown",
        "publicco": "ineligible",
    }


def test_eligibility_batch_failure_adds_no_ideas(tmp_path, monkeypatch):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    existing_id = db.add_idea(
        conn,
        None,
        Idea("原本題目", "原本角度", "https://example.com/old"),
        status="候選",
    )
    material = Material(
        "Acme",
        "https://example.com/acme",
        "Acme 發表新產品。",
    )
    monkeypatch.setattr(selection.collector, "collect", lambda *_: [material])

    def fail_evaluation(*args, **kwargs):
        raise company_eligibility.EligibilityResponseError("壞掉且含敏感內容")

    monkeypatch.setattr(
        company_eligibility,
        "evaluate_companies",
        fail_evaluation,
    )

    class FakeProvider:
        def generate_ideas(self, *args, **kwargs):
            return [
                Idea(
                    "Acme 在做什麼",
                    "值得看",
                    material.url,
                    company="Acme",
                    source_excerpt=material.snippet,
                )
            ]

    with pytest.raises(
        selection.CompanyEligibilityVerificationError,
        match="沒有新增候選",
    ) as error:
        selection.generate_for_theme(
            conn,
            Theme(None, "AI 新創介紹", 4, [], 3, "company_profile"),
            FakeProvider(),
            [],
        )

    assert "敏感內容" not in str(error.value)
    assert [idea.id for idea in db.get_ideas(conn)] == [existing_id]
    assert db.get_company_eligibilities(conn) == {}
