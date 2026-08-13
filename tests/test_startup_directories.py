from pathlib import Path

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
