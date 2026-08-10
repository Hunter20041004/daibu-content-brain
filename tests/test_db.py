import sqlite3

import pytest

from daibu import db, performance, pipeline
from daibu.llm.base import Idea
from daibu.models import (
    CompanyEligibility,
    EligibilityEvidence,
    Source,
    Theme,
)


def test_add_and_get_theme(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    theme_id = db.add_theme(
        conn,
        Theme(
            None,
            "AI 近期大事",
            weekday=0,
            source_ids=[],
            n_ideas=3,
        ),
    )

    themes = db.get_themes(conn)
    assert len(themes) == 1
    assert themes[0].id == theme_id and themes[0].name == "AI 近期大事"
    assert themes[0].source_ids == []


def test_add_and_get_theme_keeps_its_bound_sources(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_a = db.add_source(
        conn,
        Source(None, "來源 A", "https://a.example", "rss", True),
    )
    source_b = db.add_source(
        conn,
        Source(None, "來源 B", "https://b.example", "search", True),
    )

    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 近期大事", 0, [source_a, source_b], 3),
    )

    theme = db.get_themes(conn)[0]
    assert theme.id == theme_id
    assert theme.source_ids == [source_a, source_b]


def test_update_theme_replaces_its_bound_sources(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_a = db.add_source(
        conn,
        Source(None, "來源 A", "https://a.example", "rss", True),
    )
    source_b = db.add_source(
        conn,
        Source(None, "來源 B", "https://b.example", "rss", True),
    )
    theme_id = db.add_theme(
        conn,
        Theme(None, "主題", 0, [source_a], 2),
    )

    db.update_theme(
        conn,
        Theme(theme_id, "主題", 0, [source_b], 2),
    )

    assert db.get_themes(conn)[0].source_ids == [source_b]


def test_theme_content_kind_defaults_and_survives_rename(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    general_id = db.add_theme(conn, Theme(None, "一般系列", 0, [], 2))
    company_id = db.add_theme(
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

    themes = {theme.id: theme for theme in db.get_themes(conn)}
    assert themes[general_id].content_kind == "general"
    company_theme = themes[company_id]
    assert company_theme.content_kind == "company_profile"

    db.update_theme(
        conn,
        Theme(
            company_theme.id,
            "改過名字的公司系列",
            company_theme.weekday,
            company_theme.source_ids,
            company_theme.n_ideas,
            content_kind=company_theme.content_kind,
        ),
    )

    renamed = {theme.id: theme for theme in db.get_themes(conn)}[company_id]
    assert renamed.name == "改過名字的公司系列"
    assert renamed.content_kind == "company_profile"


def test_add_and_get_sources_without_layers(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    db.add_source(
        conn,
        Source(
            None,
            "TechCrunch",
            "https://techcrunch.com/feed/",
            "rss",
            True,
        ),
    )
    db.add_source(
        conn,
        Source(None, "a16z", "https://a16z.com/feed/", "rss", True),
    )

    assert [source.name for source in db.get_sources(conn)] == [
        "TechCrunch",
        "a16z",
    ]


def test_count_themes_using_source(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(None, "共用來源", "https://example.com/feed", "rss", True),
    )
    db.add_theme(conn, Theme(None, "主題 A", 0, [source_id], 1))
    db.add_theme(conn, Theme(None, "主題 B", 1, [source_id], 1))
    db.add_theme(conn, Theme(None, "未使用", 2, [], 1))

    assert db.count_themes_using_source(conn, source_id) == 2


def test_get_ideas_returns_newest_first(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "排序主題", 0, [], 1),
    )
    older_id = db.add_idea(
        conn,
        theme_id,
        Idea("較早候選", "角度", ""),
    )
    newer_id = db.add_idea(
        conn,
        theme_id,
        Idea("最新候選", "角度", ""),
    )
    conn.execute(
        "UPDATE ideas SET created_at = ? WHERE id = ?",
        ("2026-07-25 09:00:00", older_id),
    )
    conn.execute(
        "UPDATE ideas SET created_at = ? WHERE id = ?",
        ("2026-07-25 10:00:00", newer_id),
    )
    conn.commit()

    assert [
        idea.id for idea in db.get_ideas(conn, status="候選")
    ] == [newer_id, older_id]


def test_get_idea_exclusions_includes_every_status_and_skips_blank_companies(
    tmp_path,
):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "公司介紹", 0, [], 3))
    other_theme_id = db.add_theme(conn, Theme(None, "其他系列", 1, [], 1))
    rows = (
        ("候選題", "Railway", "候選"),
        ("採用題", "Cloudflare", "採用"),
        ("已發題", "Moove", "已發"),
        ("淘汰題", "Acme", "已淘汰"),
        ("空白公司題", "   ", "候選"),
    )
    for title, company, status in rows:
        db.add_idea(
            conn,
            theme_id,
            Idea(title, "角度", "", company=company),
            status=status,
        )
    db.add_idea(
        conn,
        other_theme_id,
        Idea("別的系列題", "角度", "", company="Other"),
        status="候選",
    )

    titles, companies = db.get_idea_exclusions(conn, theme_id)

    assert titles == [title for title, _, _ in rows]
    assert companies == ["Railway", "Cloudflare", "Moove", "Acme"]


def test_init_schema_creates_all_product_tables(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    table_names = {row["name"] for row in rows}

    assert {
        "themes",
        "sources",
        "theme_sources",
        "config",
        "ideas",
        "performance",
    } <= table_names


def test_init_schema_creates_company_eligibility_audit_table(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(company_eligibility)")
    }

    assert columns == {
        "company_key",
        "company",
        "verdict",
        "founded_year",
        "ownership_status",
        "reason",
        "evidence_json",
        "checked_at",
    }


def test_company_eligibility_round_trip_preserves_evidence_and_null_year(
    tmp_path,
):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    record = CompanyEligibility(
        company_key="cloudflare",
        company="Cloudflare",
        verdict="ineligible",
        founded_year=None,
        ownership_status="public",
        reason="已公開上市",
        evidence=(
            EligibilityEvidence(
                "public",
                "https://example.com/ipo",
                "Cloudflare became publicly traded in 2019.",
            ),
            EligibilityEvidence(
                "founded",
                "https://example.com/about",
                "Cloudflare was founded in 2009.",
            ),
        ),
        checked_at="2026-08-10 13:00:00",
    )

    db.save_company_eligibility(conn, record)

    assert db.get_company_eligibility(conn, "cloudflare") == record
    assert db.get_company_eligibilities(conn) == {
        "cloudflare": record,
    }


def test_saving_company_eligibility_does_not_change_ideas(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "公司介紹", 0, [], 1))
    db.add_idea(
        conn,
        theme_id,
        Idea(
            "候選題",
            "角度",
            "https://example.com/story",
            company="Cloudflare",
            source_excerpt="來源引文",
        ),
        status="候選",
    )
    before = [dict(row) for row in conn.execute("SELECT * FROM ideas")]

    db.save_company_eligibility(
        conn,
        CompanyEligibility(
            company_key="cloudflare",
            company="Cloudflare",
            verdict="ineligible",
            founded_year=2009,
            ownership_status="public",
            reason="已公開上市",
            evidence=(),
            checked_at="2026-08-10 13:00:00",
        ),
    )

    after = [dict(row) for row in conn.execute("SELECT * FROM ideas")]
    assert after == before


def test_add_and_get_candidate_idea(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "AI 大事", 0, [], 2),
    )

    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea("標題", "角度", "https://example.com/a"),
        status="候選",
    )

    ideas = db.get_ideas(conn, status="候選")
    assert len(ideas) == 1
    assert ideas[0].id == idea_id
    assert ideas[0].theme_id == theme_id
    assert ideas[0].source_url == "https://example.com/a"
    assert not hasattr(ideas[0], "gate_score")
    assert ideas[0].status == "候選"


def test_add_and_get_idea_keeps_company_and_excerpt(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea = Idea(
        title="讓文字開口說話",
        angle="語音合成的成本結構被改寫",
        source_url="https://example.com/a",
        company="ElevenLabs",
        source_excerpt="ElevenLabs 於 2022 年在倫敦成立。",
    )

    idea_id = db.add_idea(conn, None, idea)
    stored = [item for item in db.get_ideas(conn) if item.id == idea_id][0]

    assert stored.company == "ElevenLabs"
    assert stored.source_excerpt == "ElevenLabs 於 2022 年在倫敦成立。"
    conn.close()


def test_set_idea_company_updates_only_company(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea(
            "保留標題",
            "保留角度",
            "https://example.com/source",
            source_excerpt="保留引文",
        ),
    )

    db.set_idea_company(conn, idea_id, " ElevenLabs ")

    stored = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    assert stored.company == "ElevenLabs"
    assert stored.title == "保留標題"
    assert stored.source_excerpt == "保留引文"


def test_idea_source_pack_round_trip_and_cascade_delete(tmp_path):
    from tests.card_fixtures import verified_sources

    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(conn, None, Idea("t", "a", ""))
    expected = verified_sources()

    db.save_idea_sources(conn, idea_id, expected)

    assert db.get_idea_sources(conn, idea_id) == expected
    assert db.get_idea_sources(conn, idea_id + 999) == ()

    db.save_idea_sources(conn, idea_id, expected[:1])
    assert db.get_idea_sources(conn, idea_id) == expected[:1]

    db.delete_idea(conn, idea_id)
    assert conn.execute(
        "SELECT COUNT(*) FROM idea_sources"
    ).fetchone()[0] == 0


def test_save_copy_draft_replaces_body_and_sources_together(tmp_path):
    from tests.card_fixtures import verified_sources

    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea("t", "a", "", company="ElevenLabs"),
        status="採用",
    )
    pipeline.update_body(conn, idea_id, "舊正文")
    db.save_idea_sources(conn, idea_id, verified_sources()[:1])

    db.save_copy_draft(
        conn,
        idea_id,
        verified_sources()[1:],
        "新正文" * 120,
    )

    stored = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    assert stored.body == "新正文" * 120
    assert db.get_idea_sources(conn, idea_id) == verified_sources()[1:]


def test_save_copy_draft_rolls_back_sources_when_body_write_fails(tmp_path):
    from tests.card_fixtures import verified_sources

    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea("t", "a", "", company="ElevenLabs"),
        status="採用",
    )
    original_sources = verified_sources()[:1]
    pipeline.update_body(conn, idea_id, "舊正文")
    db.save_idea_sources(conn, idea_id, original_sources)
    conn.execute(
        """
        CREATE TRIGGER reject_copy_body
        BEFORE UPDATE OF body ON ideas
        WHEN NEW.body = '觸發失敗'
        BEGIN
            SELECT RAISE(ABORT, '模擬正文寫入失敗');
        END
        """
    )
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        db.save_copy_draft(
            conn,
            idea_id,
            verified_sources()[1:],
            "觸發失敗",
        )

    stored = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    assert stored.body == "舊正文"
    assert db.get_idea_sources(conn, idea_id) == original_sources


def test_source_kind_round_trips_through_pack_and_snapshot(tmp_path):
    from dataclasses import replace

    from daibu.cards.schema import CarouselDraft
    from tests.card_fixtures import carousel_draft

    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(conn, None, Idea("t", "a", ""))
    original = carousel_draft()
    official = replace(original.sources[0], source_kind="official")
    third_party = replace(original.sources[1], source_kind="third_party")
    sources = (official, third_party, *original.sources[2:])
    grounded = CarouselDraft(sources, original.pages)

    db.save_idea_sources(conn, idea_id, sources)
    db.save_carousel_draft(conn, idea_id, grounded)

    assert db.get_idea_sources(conn, idea_id) == sources
    assert db.get_carousel_draft(conn, idea_id).sources == sources


def test_invalid_researched_draft_preserves_existing_sources_and_pages(tmp_path):
    from dataclasses import replace

    from tests.card_fixtures import carousel_draft

    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(conn, None, Idea("t", "a", ""))
    original = carousel_draft()
    db.save_idea_sources(conn, idea_id, original.sources)
    db.save_carousel_draft(conn, idea_id, original)

    with pytest.raises(ValueError):
        db.save_researched_draft(
            conn,
            idea_id,
            replace(original, pages=original.pages[:-1]),
        )

    assert db.get_idea_sources(conn, idea_id) == original.sources
    assert db.get_carousel_draft(conn, idea_id) == original


def test_add_idea_records_local_created_time(monkeypatch, tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    local_time = "2031-02-03 20:09:10"
    monkeypatch.setattr(db, "_now", lambda: local_time, raising=False)

    db.add_idea(conn, None, Idea("本機時間題目", "角度", ""))

    idea = db.get_ideas(conn)[0]
    assert idea.created_at == local_time


def test_ideas_table_has_no_gate_columns(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(ideas)")
    }

    assert "gate_score" not in columns
    assert "gate_reason" not in columns


def test_update_theme_replaces_editable_fields(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(None, "舊名稱", 0, [], 2),
    )

    db.update_theme(
        conn,
        Theme(theme_id, "新名稱", 3, [], 4),
    )

    theme = db.get_themes(conn)[0]
    assert theme.name == "新名稱"
    assert theme.weekday == 3
    assert theme.source_ids == []
    assert theme.n_ideas == 4


def test_delete_theme_removes_it(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(None, "來源", "https://example.com", "rss", True),
    )
    theme_id = db.add_theme(
        conn,
        Theme(None, "待刪除", 0, [source_id], 2),
    )

    db.delete_theme(conn, theme_id)

    assert db.get_themes(conn) == []
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM theme_sources WHERE theme_id = ?",
            (theme_id,),
        ).fetchone()[0]
        == 0
    )


def test_delete_theme_also_deletes_its_ideas(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "連內容刪除", 0, [], 3))
    for status in ("候選", "採用", "已發"):
        idea_id = db.add_idea(
            conn,
            theme_id,
            Idea(f"{status}題目", "角度", ""),
            status=status,
        )
    performance.record(conn, idea_id, "Threads", 1, 10, 2.0)

    db.delete_theme(conn, theme_id)

    assert db.get_ideas(conn) == []
    assert conn.execute("SELECT COUNT(*) FROM performance").fetchone()[0] == 0


def test_delete_theme_leaves_other_themes_ideas_untouched(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    deleted_theme_id = db.add_theme(
        conn,
        Theme(None, "刪除這個", 0, [], 1),
    )
    kept_theme_id = db.add_theme(
        conn,
        Theme(None, "保留這個", 1, [], 1),
    )
    db.add_idea(conn, deleted_theme_id, Idea("一起刪除", "角度", ""))
    kept_idea_id = db.add_idea(
        conn,
        kept_theme_id,
        Idea("必須保留", "角度", ""),
    )

    db.delete_theme(conn, deleted_theme_id)

    assert [idea.id for idea in db.get_ideas(conn)] == [kept_idea_id]


def test_count_theme_content_reports_what_will_be_deleted(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(conn, Theme(None, "刪除預覽", 0, [], 9))
    other_theme_id = db.add_theme(
        conn,
        Theme(None, "不列入預覽", 1, [], 1),
    )
    candidate_ids = [
        db.add_idea(
            conn,
            theme_id,
            Idea(f"候選 {index}", "角度", ""),
        )
        for index in range(8)
    ]
    db.save_carousel(conn, candidate_ids[0], _seven_rows())
    db.save_carousel(conn, candidate_ids[1], _seven_rows())
    db.add_idea(
        conn,
        theme_id,
        Idea("已發布", "角度", ""),
        status="已發",
    )
    other_idea_id = db.add_idea(
        conn,
        other_theme_id,
        Idea("別的主題", "角度", ""),
    )
    db.save_carousel(conn, other_idea_id, _seven_rows())

    counts = db.count_theme_content(conn, theme_id)

    assert counts == {
        "候選": 8,
        "採用": 0,
        "已發": 1,
        "輪播草稿": 2,
    }


def test_update_source_replaces_editable_fields(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(None, "舊來源", "https://old.example", "rss", True),
    )

    db.update_source(
        conn,
        Source(
            source_id,
            "新來源",
            "https://new.example",
            "search",
            False,
        ),
    )

    source = db.get_sources(conn)[0]
    assert source.name == "新來源"
    assert source.url == "https://new.example"
    assert source.fetch_type == "search"
    assert source.enabled is False


def test_delete_source_removes_it(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(None, "待刪除", "https://example.com", "rss", True),
    )

    db.delete_source(conn, source_id)

    assert db.get_sources(conn) == []


def test_deleting_a_source_unbinds_it_from_themes(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    source_id = db.add_source(
        conn,
        Source(None, "待刪除", "https://example.com", "rss", True),
    )
    theme_id = db.add_theme(
        conn,
        Theme(None, "主題", 0, [source_id], 2),
    )

    db.delete_source(conn, source_id)

    theme = next(
        theme for theme in db.get_themes(conn) if theme.id == theme_id
    )
    assert theme.source_ids == []


def test_set_config_upserts_value(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    db.set_config(conn, "gate_line", "第一版")
    db.set_config(conn, "gate_line", "第二版")

    assert db.get_config(conn, "gate_line") == "第二版"
    assert db.get_config(conn, "missing", default="預設") == "預設"


def test_update_idea_content_saves_tweaked_title_and_angle(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea("舊標題", "舊角度", ""),
    )

    db.update_idea_content(conn, idea_id, "新標題", "新角度")

    idea = db.get_ideas(conn)[0]
    assert idea.title == "新標題"
    assert idea.angle == "新角度"


def test_delete_idea_removes_rejected_candidate(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea("淘汰題目", "角度", ""),
    )

    db.delete_idea(conn, idea_id)

    assert db.get_ideas(conn) == []


def _seven_rows():
    from daibu.cards import pages

    return [
        {
            "page_no": index + 1,
            "page_type": page_type,
            "heading": f"標題{index}",
            "body": f"內文{index}",
            "grounding": "source" if index < 3 else "model",
            "source_quote": "原文" if index < 3 else "",
        }
        for index, page_type in enumerate(pages.PAGE_TYPES)
    ]


def test_save_and_get_carousel(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea(title="t", angle="a", source_url=""),
    )

    db.save_carousel(conn, idea_id, _seven_rows())
    got = db.get_carousel(conn, idea_id)

    assert [row["page_no"] for row in got] == [1, 2, 3, 4, 5, 6, 7]
    assert got[0]["page_type"] == "cover"
    assert got[6]["grounding"] == "model"
    conn.close()


def test_save_carousel_overwrites_previous_draft(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea(title="t", angle="a", source_url=""),
    )

    db.save_carousel(conn, idea_id, _seven_rows())
    db.save_carousel(conn, idea_id, _seven_rows())

    assert len(db.get_carousel(conn, idea_id)) == 7
    conn.close()


def test_structured_carousel_round_trip(tmp_path):
    from tests.card_fixtures import carousel_draft

    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(conn, None, Idea("t", "a", ""))
    expected = carousel_draft()

    db.save_carousel_draft(conn, idea_id, expected)

    assert db.get_carousel_draft(conn, idea_id) == expected
    conn.close()


def test_structured_carousel_preserves_verified_source_order(tmp_path):
    from dataclasses import replace

    from tests.card_fixtures import carousel_draft

    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(conn, None, Idea("t", "a", ""))
    original = carousel_draft()
    expected = replace(original, sources=tuple(reversed(original.sources)))

    db.save_carousel_draft(conn, idea_id, expected)

    assert db.get_carousel_draft(conn, idea_id) == expected
    conn.close()


def test_deleting_idea_removes_its_structured_carousel_sources(tmp_path):
    from tests.card_fixtures import carousel_draft

    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(conn, None, Idea("t", "a", ""))
    db.save_carousel_draft(conn, idea_id, carousel_draft())

    db.delete_idea(conn, idea_id)

    assert conn.execute(
        "SELECT COUNT(*) FROM carousel_sources"
    ).fetchone()[0] == 0
    conn.close()


def test_update_single_carousel_page(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea(title="t", angle="a", source_url=""),
    )
    db.save_carousel(conn, idea_id, _seven_rows())
    page_id = db.get_carousel(conn, idea_id)[0]["id"]

    db.update_carousel_page(conn, page_id, "新標題", "新內文")

    assert db.get_carousel(conn, idea_id)[0]["heading"] == "新標題"
    conn.close()


def test_rejecting_idea_keeps_its_carousel(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea(title="t", angle="a", source_url=""),
    )
    db.save_carousel(conn, idea_id, _seven_rows())

    pipeline.set_status(conn, idea_id, "已淘汰")

    assert len(db.get_carousel(conn, idea_id)) == 7
    conn.close()


def test_deleting_idea_removes_its_carousel(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea(title="t", angle="a", source_url=""),
    )
    db.save_carousel(conn, idea_id, _seven_rows())

    db.delete_idea(conn, idea_id)

    orphans = conn.execute(
        "SELECT COUNT(*) AS n FROM carousel_pages"
    ).fetchone()
    assert orphans["n"] == 0
    conn.close()


def test_deleting_theme_removes_carousels_of_its_ideas(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(id=None, name="X", weekday=1, source_ids=[], n_ideas=3),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(title="t", angle="a", source_url=""),
    )
    db.save_carousel(conn, idea_id, _seven_rows())

    db.delete_theme(conn, theme_id)

    orphans = conn.execute(
        "SELECT COUNT(*) AS n FROM carousel_pages"
    ).fetchone()
    assert orphans["n"] == 0
    conn.close()


def test_deleting_theme_removes_structured_carousel_sources(tmp_path):
    from tests.card_fixtures import carousel_draft

    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    theme_id = db.add_theme(
        conn,
        Theme(id=None, name="X", weekday=1, source_ids=[], n_ideas=3),
    )
    idea_id = db.add_idea(
        conn,
        theme_id,
        Idea(title="t", angle="a", source_url=""),
    )
    db.save_carousel_draft(conn, idea_id, carousel_draft())

    db.delete_theme(conn, theme_id)

    assert conn.execute(
        "SELECT COUNT(*) FROM carousel_sources"
    ).fetchone()[0] == 0
    conn.close()
