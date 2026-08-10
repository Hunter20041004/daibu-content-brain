import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from daibu import company_eligibility
from daibu.fetch import search
from daibu.llm import base


@pytest.mark.contract
def test_real_search_and_llm_classify_known_company_examples():
    env_path = Path(os.getenv("DAIBU_ENV_FILE", ".env"))
    load_dotenv(env_path)
    if not os.getenv("TAVILY_API_KEY") or not os.getenv("GEMINI_API_KEY"):
        pytest.skip("需要真實 Tavily 與 Gemini API key")

    provider = base.get_provider_from_env()
    records = company_eligibility.evaluate_companies(
        ["Cloudflare", "Moove", "Railway"],
        search.search_web,
        provider.generate_text,
        current_year=2026,
    )

    assert records["cloudflare"].verdict == "ineligible"
    assert records["cloudflare"].ownership_status == "public"
    for company_key in ("moove", "railway"):
        record = records[company_key]
        assert record.verdict == "eligible", record.reason
        assert {item.claim for item in record.evidence} >= {
            "founded",
            "private_independent",
        }
