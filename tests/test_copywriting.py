import pytest

from daibu import copywriting
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
