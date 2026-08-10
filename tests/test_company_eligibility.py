import json

import pytest

from daibu import company_eligibility
from daibu.models import Material


def test_matching_founded_and_private_evidence_is_eligible_at_ten_year_boundary():
    materials = {
        "acme": [
            Material(
                "About Acme",
                "https://acme.example/about",
                "Acme was founded in 2016 and remains a privately held, "
                "independent company.",
            )
        ]
    }
    raw = json.dumps(
        [
            {
                "company": "Acme",
                "founded_year": 2016,
                "ownership_status": "private_independent",
                "reason": "成立十年且仍為私人獨立公司",
                "evidence": [
                    {
                        "claim": "founded",
                        "source_url": "https://acme.example/about",
                        "quote": "Acme was founded in 2016",
                    },
                    {
                        "claim": "private_independent",
                        "source_url": "https://acme.example/about",
                        "quote": "privately held, independent company",
                    },
                ],
            }
        ]
    )

    records = company_eligibility.verify_response(
        raw,
        ["Acme"],
        materials,
        current_year=2026,
        checked_at="2026-08-10 13:00:00",
    )

    record = records["acme"]
    assert record.verdict == "eligible"
    assert record.founded_year == 2016
    assert record.ownership_status == "private_independent"
    assert len(record.evidence) == 2


def test_private_company_older_than_ten_years_is_ineligible():
    snippet = (
        "LegacyCo was founded in 2015 and remains a privately held, "
        "independent company."
    )
    materials = {
        "legacyco": [
            Material("About", "https://legacy.example/about", snippet)
        ]
    }
    raw = json.dumps(
        [
            {
                "company": "LegacyCo",
                "founded_year": 2015,
                "ownership_status": "private_independent",
                "reason": "成立超過十年",
                "evidence": [
                    {
                        "claim": "founded",
                        "source_url": "https://legacy.example/about",
                        "quote": "LegacyCo was founded in 2015",
                    },
                    {
                        "claim": "private_independent",
                        "source_url": "https://legacy.example/about",
                        "quote": "privately held, independent company",
                    },
                ],
            }
        ]
    )

    record = company_eligibility.verify_response(
        raw,
        ["LegacyCo"],
        materials,
        current_year=2026,
        checked_at="2026-08-10 13:00:00",
    )["legacyco"]

    assert record.verdict == "ineligible"
    assert record.founded_year == 2015
    assert record.reason == "成立超過十年"


def test_public_and_acquired_companies_are_ineligible():
    materials = {
        "listedco": [
            Material(
                "IPO",
                "https://listed.example/ipo",
                "ListedCo became publicly traded on NYSE in 2024.",
            )
        ],
        "boughtco": [
            Material(
                "Acquisition",
                "https://buyer.example/news",
                "Buyer completed its acquisition of BoughtCo in 2025.",
            )
        ],
    }
    raw = json.dumps(
        [
            {
                "company": "ListedCo",
                "founded_year": 2020,
                "ownership_status": "public",
                "reason": "已公開上市",
                "evidence": [
                    {
                        "claim": "public",
                        "source_url": "https://listed.example/ipo",
                        "quote": "publicly traded on NYSE in 2024",
                    }
                ],
            },
            {
                "company": "BoughtCo",
                "founded_year": 2021,
                "ownership_status": "acquired",
                "reason": "已被收購",
                "evidence": [
                    {
                        "claim": "acquired",
                        "source_url": "https://buyer.example/news",
                        "quote": "acquisition of BoughtCo in 2025",
                    }
                ],
            },
        ]
    )

    records = company_eligibility.verify_response(
        raw,
        ["ListedCo", "BoughtCo"],
        materials,
        current_year=2026,
        checked_at="2026-08-10 13:00:00",
    )

    assert records["listedco"].verdict == "ineligible"
    assert records["listedco"].ownership_status == "public"
    assert records["boughtco"].verdict == "ineligible"
    assert records["boughtco"].ownership_status == "acquired"


def test_evidence_from_a_different_url_cannot_make_company_eligible():
    materials = {
        "acme": [
            Material(
                "About",
                "https://acme.example/about",
                "Acme was founded in 2021 and remains privately held.",
            )
        ]
    }
    raw = json.dumps(
        [
            {
                "company": "Acme",
                "founded_year": 2021,
                "ownership_status": "private_independent",
                "evidence": [
                    {
                        "claim": "founded",
                        "source_url": "https://invented.example/about",
                        "quote": "Acme was founded in 2021",
                    },
                    {
                        "claim": "private_independent",
                        "source_url": "https://invented.example/about",
                        "quote": "remains privately held",
                    },
                ],
            }
        ]
    )

    record = company_eligibility.verify_response(
        raw,
        ["Acme"],
        materials,
        current_year=2026,
        checked_at="2026-08-10 13:00:00",
    )["acme"]

    assert record.verdict == "unknown"
    assert record.evidence == ()


def test_quote_not_present_in_search_material_cannot_make_company_eligible():
    materials = {
        "acme": [
            Material(
                "About",
                "https://acme.example/about",
                "Acme builds tools for finance teams.",
            )
        ]
    }
    raw = json.dumps(
        [
            {
                "company": "Acme",
                "founded_year": 2021,
                "ownership_status": "private_independent",
                "evidence": [
                    {
                        "claim": "founded",
                        "source_url": "https://acme.example/about",
                        "quote": "Acme was founded in 2021",
                    },
                    {
                        "claim": "private_independent",
                        "source_url": "https://acme.example/about",
                        "quote": "Acme remains privately held",
                    },
                ],
            }
        ]
    )

    record = company_eligibility.verify_response(
        raw,
        ["Acme"],
        materials,
        current_year=2026,
        checked_at="2026-08-10 13:00:00",
    )["acme"]

    assert record.verdict == "unknown"
    assert record.evidence == ()


def test_contradictory_private_and_public_evidence_becomes_unknown():
    snippet = (
        "Acme was founded in 2021 and is privately held. "
        "Acme also became publicly traded in 2024."
    )
    materials = {
        "acme": [Material("Company", "https://acme.example/company", snippet)]
    }
    raw = json.dumps(
        [
            {
                "company": "Acme",
                "founded_year": 2021,
                "ownership_status": "private_independent",
                "evidence": [
                    {
                        "claim": "founded",
                        "source_url": "https://acme.example/company",
                        "quote": "Acme was founded in 2021",
                    },
                    {
                        "claim": "private_independent",
                        "source_url": "https://acme.example/company",
                        "quote": "is privately held",
                    },
                    {
                        "claim": "public",
                        "source_url": "https://acme.example/company",
                        "quote": "became publicly traded in 2024",
                    },
                ],
            }
        ]
    )

    record = company_eligibility.verify_response(
        raw,
        ["Acme"],
        materials,
        current_year=2026,
        checked_at="2026-08-10 13:00:00",
    )["acme"]

    assert record.verdict == "unknown"


def test_founding_evidence_without_private_evidence_becomes_unknown():
    materials = {
        "acme": [
            Material(
                "About",
                "https://acme.example/about",
                "Acme was founded in 2021.",
            )
        ]
    }
    raw = json.dumps(
        [
            {
                "company": "Acme",
                "founded_year": 2021,
                "ownership_status": "private_independent",
                "evidence": [
                    {
                        "claim": "founded",
                        "source_url": "https://acme.example/about",
                        "quote": "Acme was founded in 2021",
                    }
                ],
            }
        ]
    )

    record = company_eligibility.verify_response(
        raw,
        ["Acme"],
        materials,
        current_year=2026,
        checked_at="2026-08-10 13:00:00",
    )["acme"]

    assert record.verdict == "unknown"


def test_malformed_batch_json_raises_a_clear_error():
    with pytest.raises(
        company_eligibility.EligibilityResponseError,
        match="JSON 無法解析",
    ):
        company_eligibility.verify_response(
            "Here is the answer: [{broken]",
            ["Acme"],
            {"acme": []},
            current_year=2026,
            checked_at="2026-08-10 13:00:00",
        )
