from daibu import db
from daibu.cards.schema import BrandAsset
from daibu.llm.base import Idea
from daibu.models import Material, SourceSuggestion
import pytest


def test_research_finishes_before_one_model_call_and_saves_one_snapshot(
    tmp_path,
):
    from daibu.cards import research_draft
    from tests.card_fixtures import structured_llm_response, verified_sources

    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea("title", "angle", "", company="ElevenLabs"),
        status="採用",
    )
    db.save_idea_sources(conn, idea_id, verified_sources())
    idea = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    events = []

    def fake_search(_query, allowed_domains, limit=3):
        events.append("search")
        assert "elevenlabs.io" in allowed_domains
        return [
            Material(
                "ElevenLabs funding profile",
                "https://techcrunch.com/elevenlabs-funding",
                "ElevenLabs company profile",
            )
        ]

    def fake_fetch(url):
        return SourceSuggestion(
            "TechCrunch",
            "2026-07-30",
            url,
            "ElevenLabs raised funding for its AI voice platform.",
        )

    def fake_generate(_prompt):
        events.append("model")
        return structured_llm_response()

    result = research_draft.generate(
        conn,
        idea,
        ["techcrunch.com"],
        BrandAsset(
            "ElevenLabs",
            tmp_path / "logo.svg",
            "https://elevenlabs.io/about",
            "2026-07-30",
        ),
        fake_search,
        fake_fetch,
        fake_generate,
    )

    assert events.count("model") == 1
    assert events.index("model") > max(
        index for index, event in enumerate(events) if event == "search"
    )
    assert result.sources[-1].source_kind == "third_party"
    assert db.get_idea_sources(conn, idea_id) == result.sources
    assert db.get_carousel_draft(conn, idea_id) == result


def test_failed_new_model_response_keeps_the_previous_snapshot(tmp_path):
    from daibu.cards import research_draft
    from daibu.llm import base
    from tests.card_fixtures import carousel_draft

    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea("title", "angle", "", company="ElevenLabs"),
        status="採用",
    )
    original = carousel_draft()
    db.save_researched_draft(conn, idea_id, original)
    idea = next(item for item in db.get_ideas(conn) if item.id == idea_id)

    with pytest.raises(base.LLMResponseError):
        research_draft.generate(
            conn,
            idea,
            ["techcrunch.com"],
            None,
            lambda *_args, **_kwargs: [],
            lambda _url: None,
            lambda _prompt: "不是 JSON",
        )

    assert db.get_idea_sources(conn, idea_id) == original.sources
    assert db.get_carousel_draft(conn, idea_id) == original


def test_explicit_refresh_does_not_seed_research_with_the_old_snapshot(
    tmp_path,
    monkeypatch,
):
    from daibu.cards import research_draft
    from daibu.fetch.company_research import ResearchResult
    from tests.card_fixtures import carousel_draft, structured_llm_response

    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea("title", "angle", "", company="ElevenLabs"),
        status="採用",
    )
    original = carousel_draft()
    db.save_researched_draft(conn, idea_id, original)
    idea = next(item for item in db.get_ideas(conn) if item.id == idea_id)
    seen_seeds = []

    def fake_research(company, seed_sources, *_args, **_kwargs):
        assert company == "ElevenLabs"
        seen_seeds.append(seed_sources)
        return ResearchResult(original.sources, ())

    monkeypatch.setattr(
        research_draft.company_research,
        "research",
        fake_research,
    )

    research_draft.generate(
        conn,
        idea,
        (),
        None,
        None,
        None,
        lambda _prompt: structured_llm_response(),
        reuse_existing_sources=False,
    )

    assert seen_seeds == [()]
