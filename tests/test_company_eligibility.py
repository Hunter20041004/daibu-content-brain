import json

import pytest

from daibu import company_eligibility, db
from daibu.llm.base import Idea
from daibu.models import Material, Theme


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


def test_evaluate_searches_each_company_once_and_generates_one_batch():
    search_calls: list[tuple[str, int]] = []
    generated_prompts: list[str] = []

    def fake_search(query: str, limit: int) -> list[Material]:
        search_calls.append((query, limit))
        company = next(
            name for name in ["Acme", "Beta", "Gamma"] if name in query
        )
        return [
            Material(
                f"About {company}",
                f"https://{company.lower()}.example/about",
                f"{company} was founded in 2020 and remains privately held.",
            )
        ]

    def fake_generate(prompt: str) -> str:
        generated_prompts.append(prompt)
        return json.dumps(
            [
                {
                    "company": company,
                    "founded_year": 2020,
                    "ownership_status": "private_independent",
                    "reason": "符合條件",
                    "evidence": [
                        {
                            "claim": "founded",
                            "source_url": f"https://{company.lower()}.example/about",
                            "quote": f"{company} was founded in 2020",
                        },
                        {
                            "claim": "private_independent",
                            "source_url": f"https://{company.lower()}.example/about",
                            "quote": "remains privately held",
                        },
                    ],
                }
                for company in ["Acme", "Beta", "Gamma"]
            ]
        )

    records = company_eligibility.evaluate_companies(
        ["Acme", "Beta", "Gamma"],
        fake_search,
        fake_generate,
        current_year=2026,
        checked_at="2026-08-10 13:00:00",
    )

    assert len(search_calls) == 3
    assert all(limit == 5 for _, limit in search_calls)
    assert len(generated_prompts) == 1
    assert all(name in generated_prompts[0] for name in ["Acme", "Beta", "Gamma"])
    assert all(records[key].verdict == "eligible" for key in records)


def test_one_search_failure_becomes_unknown_without_losing_other_company():
    def fake_search(query: str, limit: int) -> list[Material]:
        assert limit == 5
        if "Broken" in query:
            raise RuntimeError("secret-key-should-not-escape")
        return [
            Material(
                "About Good",
                "https://good.example/about",
                "Good was founded in 2022 and remains privately held.",
            )
        ]

    def fake_generate(_prompt: str) -> str:
        return json.dumps(
            [
                {
                    "company": "Good",
                    "founded_year": 2022,
                    "ownership_status": "private_independent",
                    "evidence": [
                        {
                            "claim": "founded",
                            "source_url": "https://good.example/about",
                            "quote": "Good was founded in 2022",
                        },
                        {
                            "claim": "private_independent",
                            "source_url": "https://good.example/about",
                            "quote": "remains privately held",
                        },
                    ],
                }
            ]
        )

    records = company_eligibility.evaluate_companies(
        ["Broken", "Good"],
        fake_search,
        fake_generate,
        current_year=2026,
        checked_at="2026-08-10 13:00:00",
    )

    assert records["broken"].verdict == "unknown"
    assert "secret-key" not in records["broken"].reason
    assert records["good"].verdict == "eligible"


def test_company_missing_from_batch_response_is_filled_as_unknown():
    calls: list[str] = []

    def fake_search(query: str, limit: int) -> list[Material]:
        calls.append(query)
        assert limit == 5
        return []

    records = company_eligibility.evaluate_companies(
        ["Acme", " acme ", "Missing"],
        fake_search,
        lambda _prompt: "[]",
        current_year=2026,
        checked_at="2026-08-10 13:00:00",
    )

    assert len(calls) == 2
    assert set(records) == {"acme", "missing"}
    assert all(record.verdict == "unknown" for record in records.values())


def test_backfill_checks_unique_profile_companies_without_changing_ideas(
    tmp_path,
):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    profile_id = db.add_theme(
        conn,
        Theme(None, "AI 新創介紹", 4, [], 3, "company_profile"),
    )
    general_id = db.add_theme(conn, Theme(None, "一般系列", 1, [], 1))
    db.add_idea(
        conn,
        profile_id,
        Idea("Railway 一", "角度", "https://example.com/r1", company="Railway"),
    )
    db.add_idea(
        conn,
        profile_id,
        Idea("Railway 二", "角度", "https://example.com/r2", company=" railway "),
    )
    db.add_idea(
        conn,
        profile_id,
        Idea("Cloudflare", "角度", "https://example.com/c", company="Cloudflare"),
    )
    db.add_idea(
        conn,
        general_id,
        Idea("GeneralCo", "角度", "https://example.com/g", company="GeneralCo"),
    )
    before = [tuple(row) for row in conn.execute("SELECT * FROM ideas ORDER BY id")]
    search_calls: list[str] = []
    generation_calls: list[str] = []

    def fake_search(query: str, limit: int) -> list[Material]:
        search_calls.append(query)
        assert limit == 5
        company = "Railway" if "Railway" in query else "Cloudflare"
        return [
            Material(
                company,
                f"https://example.com/{company.casefold()}",
                f"{company} was founded in 2020 and remains privately held.",
            )
        ]

    class FakeProvider:
        def generate_text(self, _prompt: str) -> str:
            generation_calls.append(_prompt)
            return json.dumps(
                [
                    {
                        "company": company,
                        "founded_year": 2020,
                        "ownership_status": "private_independent",
                        "evidence": [
                            {
                                "claim": "founded",
                                "source_url": f"https://example.com/{company.casefold()}",
                                "quote": f"{company} was founded in 2020",
                            },
                            {
                                "claim": "private_independent",
                                "source_url": f"https://example.com/{company.casefold()}",
                                "quote": "remains privately held",
                            },
                        ],
                    }
                    for company in ("Railway", "Cloudflare")
                ]
            )

    records = company_eligibility.backfill_existing(
        conn,
        FakeProvider(),
        fake_search,
        current_year=2026,
    )

    after = [tuple(row) for row in conn.execute("SELECT * FROM ideas ORDER BY id")]
    assert len(search_calls) == 2
    assert set(records) == {"railway", "cloudflare"}
    assert set(db.get_company_eligibilities(conn)) == {"railway", "cloudflare"}
    assert after == before

    search_calls.clear()
    second = company_eligibility.backfill_existing(
        conn,
        FakeProvider(),
        fake_search,
        current_year=2026,
    )

    assert second == {}
    assert search_calls == []
    assert len(generation_calls) == 1
