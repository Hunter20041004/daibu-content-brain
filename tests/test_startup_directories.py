from pathlib import Path

import pytest

from daibu.fetch import startup_directories
from daibu.models import CompanyLead


def test_yc_launches_maps_only_ai_companies(monkeypatch):
    payload = Path("tests/fixtures/yc_launches.json").read_text()
    calls = []
    monkeypatch.setattr(
        startup_directories,
        "_get_text",
        lambda url: calls.append(url) or payload,
    )

    leads = startup_directories.fetch_yc_launches(
        "https://www.ycombinator.com/launches",
        pages=1,
    )

    assert calls == ["https://www.ycombinator.com/launches?page=0"]
    assert [(lead.company, lead.batch_or_cohort) for lead in leads] == [
        ("Almanac", "Summer 2026")
    ]
    assert leads[0].tags == ("Generative AI", "AI", "AI Assistant")
    assert leads[0].source_name == "YC Launches"
    assert leads[0].profile_url == (
        "https://www.ycombinator.com/companies/almanac"
    )


def test_yc_company_enrichment_reads_status_and_founding_year(monkeypatch):
    html_text = Path("tests/fixtures/yc_company_active.html").read_text()
    monkeypatch.setattr(
        startup_directories,
        "_get_text",
        lambda _url: html_text,
    )
    lead = CompanyLead(
        "Almanac",
        "Agent with a company brain",
        "https://www.ycombinator.com/launches/almanac",
        profile_url="https://www.ycombinator.com/companies/almanac",
        batch_or_cohort="Summer 2026",
        source_name="YC Launches",
    )

    enriched = startup_directories.enrich_yc_company(lead)

    assert enriched.founded_year == 2026
    assert enriched.ownership_status == "active"
    assert enriched.official_url == "https://usealmanac.com"


def test_public_yc_company_is_an_early_rejection(monkeypatch):
    html_text = Path("tests/fixtures/yc_company_public.html").read_text()
    monkeypatch.setattr(
        startup_directories,
        "_get_text",
        lambda _url: html_text,
    )
    lead = CompanyLead(
        "Groww",
        "Investing",
        "https://www.ycombinator.com/launches/groww",
        profile_url="https://www.ycombinator.com/companies/groww",
    )

    enriched = startup_directories.enrich_yc_company(lead)

    assert enriched.ownership_status == "public"


def test_speedrun_keeps_ai_categories_and_newest_cohort(monkeypatch):
    html_text = Path("tests/fixtures/speedrun_companies.html").read_text()
    cohort_json = Path("tests/fixtures/speedrun_cohort.json").read_text()
    responses = iter((html_text, cohort_json))
    calls = []
    monkeypatch.setattr(
        startup_directories,
        "_get_text",
        lambda url: calls.append(url) or next(responses),
    )

    leads = startup_directories.fetch_speedrun_companies(
        "https://speedrun.a16z.com/companies"
    )

    assert calls == [
        "https://speedrun.a16z.com/companies",
        "https://speedrun-be.a16z.com/api/companies/companies/"
        "?limit=100&cohort=SR006",
    ]
    assert [lead.company for lead in leads] == ["Acceler8"]
    assert leads[0].batch_or_cohort == "SR006"
    assert "AI Agents" in leads[0].tags
    assert leads[0].founded_year == 2025
    assert leads[0].official_url == "https://useacceler8.com"


def test_speedrun_rejects_an_unapproved_api_host(monkeypatch):
    html_text = Path("tests/fixtures/speedrun_companies.html").read_text()
    html_text = html_text.replace(
        "speedrun-be.a16z.com",
        "evil.example",
    )
    calls = []
    monkeypatch.setattr(
        startup_directories,
        "_get_text",
        lambda url: calls.append(url) or html_text,
    )

    with pytest.raises(ValueError, match="Speedrun API 網址不合法"):
        startup_directories.fetch_speedrun_companies(
            "https://speedrun.a16z.com/companies"
        )

    assert calls == ["https://speedrun.a16z.com/companies"]


@pytest.mark.contract
def test_real_yc_launches_returns_ai_company_fields():
    leads = startup_directories.fetch_yc_launches(
        "https://www.ycombinator.com/launches",
        pages=1,
    )

    assert leads
    assert all(
        lead.company and lead.discovery_url.startswith("https://")
        for lead in leads
    )
    assert all(lead.profile_url.startswith(
        "https://www.ycombinator.com/companies/"
    ) for lead in leads)
    assert all(lead.tags for lead in leads)


@pytest.mark.contract
def test_real_yc_company_exposes_public_status_and_founding_year():
    lead = CompanyLead(
        "Groww",
        "Investing platform",
        "https://www.ycombinator.com/launches/groww",
        profile_url="https://www.ycombinator.com/companies/groww",
        source_name="YC Launches",
    )

    enriched = startup_directories.enrich_yc_company(lead)

    assert enriched.founded_year == 2016
    assert enriched.ownership_status == "public"
    assert enriched.official_url.startswith("https://")


@pytest.mark.contract
def test_real_speedrun_returns_latest_cohort_ai_company_fields():
    leads = startup_directories.fetch_speedrun_companies(
        "https://speedrun.a16z.com/companies"
    )

    assert leads
    assert all(lead.company and lead.batch_or_cohort for lead in leads)
    assert all(lead.discovery_url.startswith(
        "https://speedrun.a16z.com/companies/"
    ) for lead in leads)
    assert all(lead.official_url.startswith("https://") for lead in leads)
    assert all(lead.founded_year is not None for lead in leads)
    assert all(
        startup_directories.SPEEDRUN_AI_TAGS.intersection(lead.tags)
        for lead in leads
    )
