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
        "timely",
        [
            Material(
                "AI 實驗室發表新模型",
                "https://example.com/public-ai-update",
                "公開資料摘要",
            )
        ],
        gate_line="怕 AI 的文組同學看完會不會覺得我也可以？",
        n=2,
    )

    assert len(ideas) >= 1
    assert all(0 <= idea.gate_score <= 100 for idea in ideas)
    assert all(idea.title and idea.angle for idea in ideas)
