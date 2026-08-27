import os

import pytest
from dotenv import load_dotenv

from daibu.llm import base
from daibu.llm.gemini import GeminiProvider
from daibu import company_diversity
from daibu.models import CompanyLead, Material

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
                "ElevenLabs 發表新版語音模型",
                "https://example.com/public-ai-update",
                "ElevenLabs 公開新版語音模型，支援內容製作者調整語氣。",
            )
        ],
        n=2,
    )

    assert len(ideas) >= 1
    assert all(idea.title and idea.angle for idea in ideas)


@pytest.mark.contract
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="無 Google AI Studio key",
)
def test_real_gemma_returns_parsable_traditional_chinese_idea():
    provider = GeminiProvider(
        api_key=os.environ["GEMINI_API_KEY"],
        model=base.DEFAULT_GOOGLE_IDEA_MODEL,
    )

    ideas = provider.generate_ideas(
        "AI 新創介紹",
        [
            Material(
                "Feldy",
                "https://www.ycombinator.com/companies/feldy",
                "Feldy | Founded 2024 | Winter 2024 | AI meal planning",
            )
        ],
        n=1,
        content_kind="company_profile",
    )

    assert len(ideas) == 1
    assert ideas[0].company == "Feldy"
    assert ideas[0].title and ideas[0].angle
    assert any("\u4e00" <= char <= "\u9fff" for char in ideas[0].title)


@pytest.mark.contract
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="無 Google AI Studio key",
)
def test_real_gemma_returns_parsable_company_categories():
    leads = [
        CompanyLead(
            "InfraGrid",
            "Model serving and GPU orchestration platform for AI developers.",
            "https://example.com/infragrid",
        ),
        CompanyLead(
            "WorkFlow AI",
            "AI workflow assistant sold to finance operations teams.",
            "https://example.com/workflow",
        ),
        CompanyLead(
            "CreatorPal",
            "Personal video editing assistant for individual creators.",
            "https://example.com/creatorpal",
        ),
        CompanyLead(
            "RobotFarm",
            "Autonomous robots that move goods inside warehouses.",
            "https://example.com/robotfarm",
        ),
        CompanyLead(
            "BioProbe",
            "AI drug discovery tools for biotech research laboratories.",
            "https://example.com/bioprobe",
        ),
        CompanyLead(
            "Risklytics",
            "AI governance and regulatory risk analysis for organizations.",
            "https://example.com/risklytics",
        ),
    ]
    provider = GeminiProvider(
        api_key=os.environ["GEMINI_API_KEY"],
        model=base.DEFAULT_GOOGLE_IDEA_MODEL,
    )

    raw = provider.generate_text(
        company_diversity.build_classification_prompt(leads)
    )
    classified = company_diversity.parse_classifications(raw, leads)

    assert len(classified) == 6
    assert {item.category for item in classified} == set(
        company_diversity.CATEGORIES
    )


@pytest.mark.contract
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY") and not os.getenv("GROQ_API_KEY"),
    reason="無 LLM key",
)
def test_real_llm_returns_valid_sourced_carousel(tmp_path):
    from daibu import db
    from daibu.cards import draft, pages
    from daibu.cards.schema import validate_grounded_draft
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
        provider.generate_carousel_text,
    )

    assert len(result.pages) == 6
    assert all(page.sections for page in result.pages)
    assert result.pages[-1].sections[0].text == pages.CTA_TEXT
    validate_grounded_draft(result)
    assert db.get_carousel_draft(conn, idea_id) == result
    conn.close()
