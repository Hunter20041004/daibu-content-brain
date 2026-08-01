from dataclasses import replace

import pytest

from daibu import copywriting, db
from daibu.fetch.company_research import ResearchResult
from daibu.llm.base import Idea
from daibu.models import StoredIdea
from tests.card_fixtures import verified_sources


def adopted_company() -> StoredIdea:
    return StoredIdea(
        id=1,
        theme_id=3,
        title="用 AI 保留聲音的語氣與節奏",
        angle="聲音製作流程正在改變",
        source_url="https://elevenlabs.io/about",
        status="採用",
        body="",
        created_at="2026-07-31 10:00:00",
        published_at=None,
        company="ElevenLabs",
        source_excerpt="公司開發能保留語氣、節奏與情緒的語音模型。",
    )


def test_copy_prompt_uses_only_the_verified_research_pack():
    idea = adopted_company()
    sources = verified_sources()

    text = copywriting.build_prompt(idea, sources)

    assert idea.company in text
    assert idea.title in text
    assert "350–500" in text
    assert "繁體中文" in text
    assert "純文字" in text
    assert "只能根據下列已驗證來源" in text
    for source in sources:
        assert source.url in text
        assert source.excerpt in text


def test_copy_generation_retries_once_after_invalid_length():
    responses = iter(["太短", "文" * 350])
    prompts = []

    def fake_generate(prompt_text):
        prompts.append(prompt_text)
        return next(responses)

    result = copywriting.generate_draft(
        adopted_company(),
        verified_sources(),
        fake_generate,
    )

    assert result == "文" * 350
    assert len(prompts) == 2
    assert prompts[0] == prompts[1]


def test_copy_generation_stops_after_two_invalid_responses():
    responses = iter(["   ", "文" * 501])
    calls = []

    with pytest.raises(copywriting.CopyDraftError, match="原文沒有變更"):
        copywriting.generate_draft(
            adopted_company(),
            verified_sources(),
            lambda prompt_text: (
                calls.append(prompt_text) or next(responses)
            ),
        )

    assert len(calls) == 2


def test_copy_service_researches_then_saves_one_complete_snapshot(
    tmp_path,
    monkeypatch,
):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        3,
        Idea(
            adopted_company().title,
            adopted_company().angle,
            adopted_company().source_url,
            company=adopted_company().company,
        ),
        status="採用",
    )
    idea = replace(adopted_company(), id=idea_id)
    events = []

    def fake_research(
        company,
        seed_sources,
        configured_domains,
        official_domains,
        **_kwargs,
    ):
        events.append("research")
        assert company == "ElevenLabs"
        assert seed_sources == ()
        assert tuple(configured_domains) == ("techcrunch.com",)
        assert tuple(official_domains) == ("elevenlabs.io",)
        return ResearchResult(verified_sources(), ())

    monkeypatch.setattr(
        copywriting.company_research,
        "research",
        fake_research,
    )

    body = copywriting.generate(
        conn,
        idea,
        ("techcrunch.com",),
        lambda _prompt: events.append("model") or "文" * 350,
        official_domains=("elevenlabs.io",),
    )

    assert events == ["research", "model"]
    assert body == "文" * 350
    stored = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    assert stored.body == body
    assert db.get_idea_sources(conn, idea_id) == verified_sources()


def test_copy_service_research_failure_keeps_body_and_sources(
    tmp_path,
    monkeypatch,
):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea("原標題", "原角度", "", company="ElevenLabs"),
        status="採用",
    )
    db.save_copy_draft(
        conn,
        idea_id,
        verified_sources()[:1],
        "舊正文",
    )
    idea = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    model_calls = []

    monkeypatch.setattr(
        copywriting.company_research,
        "research",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("找不到可信資料")
        ),
    )

    with pytest.raises(ValueError, match="找不到可信資料"):
        copywriting.generate(
            conn,
            idea,
            (),
            lambda prompt: model_calls.append(prompt) or "文" * 350,
        )

    stored = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    assert model_calls == []
    assert stored.body == "舊正文"
    assert db.get_idea_sources(conn, idea_id) == verified_sources()[:1]


def test_copy_service_generation_failure_keeps_body_and_sources(
    tmp_path,
    monkeypatch,
):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea("原標題", "原角度", "", company="ElevenLabs"),
        status="採用",
    )
    original_sources = verified_sources()[:1]
    db.save_copy_draft(conn, idea_id, original_sources, "舊正文")
    idea = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    monkeypatch.setattr(
        copywriting.company_research,
        "research",
        lambda *_args, **_kwargs: ResearchResult(
            verified_sources()[1:],
            (),
        ),
    )
    model_calls = []

    with pytest.raises(copywriting.CopyDraftError):
        copywriting.generate(
            conn,
            idea,
            (),
            lambda prompt: model_calls.append(prompt) or "太短",
        )

    stored = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    assert len(model_calls) == 2
    assert stored.body == "舊正文"
    assert db.get_idea_sources(conn, idea_id) == original_sources
