import os

import pytest
from dotenv import load_dotenv

from daibu.llm import base
from daibu.models import Material

load_dotenv()


@pytest.mark.contract
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY") and not os.getenv("GROQ_API_KEY"),
    reason="無 LLM key",
)
def test_real_llm_returns_parsable_ideas():
    provider = base.get_provider_from_env()

    ideas = provider.generate_ideas(
        "AI 近期大事",
        [
            Material(
                "AI 實驗室發表新模型",
                "https://example.com/public-ai-update",
                "公開資料摘要",
            )
        ],
        n=2,
    )

    assert len(ideas) >= 1
    assert all(idea.title and idea.angle for idea in ideas)


@pytest.mark.contract
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY") and not os.getenv("GROQ_API_KEY"),
    reason="無 LLM key",
)
def test_real_llm_returns_valid_sourced_carousel(tmp_path):
    from daibu import db
    from daibu.cards import draft
    from daibu.llm.base import Idea
    from tests.card_fixtures import verified_sources

    provider = base.get_provider_from_env()
    sources = verified_sources()
    conn = db.connect(str(tmp_path / "contract.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea(
            title="生成式語音",
            angle="理解工作改變",
            source_url="https://elevenlabs.io/about",
            company="ElevenLabs",
        ),
    )
    idea = next(item for item in db.get_ideas(conn) if item.id == idea_id)

    result = draft.generate(
        conn,
        idea,
        sources,
        provider.generate_text,
    )

    assert len(result.pages) == 7
    assert all(page.sections for page in result.pages)
    assert db.get_carousel_draft(conn, idea_id) == result
    conn.close()
