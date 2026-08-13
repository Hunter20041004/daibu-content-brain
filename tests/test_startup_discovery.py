from pathlib import Path

from daibu import startup_discovery
from daibu.fetch import rss
from daibu.models import CompanyLead


def test_recent_ai_news_enriches_one_known_company_only(monkeypatch):
    raw = Path("tests/fixtures/techcrunch_startups.xml").read_text()
    monkeypatch.setattr(rss, "_download", lambda _url: raw)
    leads = (
        CompanyLead(
            "Cognition",
            "AI coding",
            "https://yc.example/cognition",
            source_name="YC Launches",
        ),
        CompanyLead(
            "Almanac",
            "Agent",
            "https://yc.example/almanac",
            source_name="YC Launches",
        ),
        CompanyLead(
            "Acceler8",
            "Workforce AI",
            "https://speedrun.example/acceler8",
            source_name="a16z Speedrun Companies",
        ),
    )
    news = rss.fetch_tagged("fixture://techcrunch")

    mixed = startup_discovery.mix_leads(leads, news, limit=3)

    assert [lead.company for lead in mixed] == [
        "Cognition",
        "Almanac",
        "Acceler8",
    ]
    assert mixed[0].source_name == "TechCrunch Startups"
    assert sum(
        lead.source_name == "TechCrunch Startups" for lead in mixed
    ) == 1


def test_ipo_news_does_not_replace_a_directory_lead(monkeypatch):
    raw = Path("tests/fixtures/techcrunch_startups.xml").read_text()
    monkeypatch.setattr(rss, "_download", lambda _url: raw)
    lead = CompanyLead(
        "PublicCo",
        "AI infrastructure",
        "https://yc.example/publicco",
        source_name="YC Launches",
    )

    mixed = startup_discovery.mix_leads(
        (lead,),
        rss.fetch_tagged("fixture://techcrunch"),
    )

    assert mixed == (lead,)
