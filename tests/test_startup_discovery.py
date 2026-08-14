import logging
from pathlib import Path

from daibu import startup_discovery
from daibu.fetch import rss
from daibu.models import CompanyLead, Source


def configured_sources() -> list[Source]:
    return [
        Source(
            1,
            "YC Launches",
            "https://www.ycombinator.com/launches",
            "directory",
            True,
        ),
        Source(
            2,
            "YC Companies",
            "https://www.ycombinator.com/companies",
            "directory",
            True,
        ),
        Source(
            3,
            "a16z Speedrun Companies",
            "https://speedrun.a16z.com/companies",
            "directory",
            True,
        ),
        Source(
            4,
            "TechCrunch Startups",
            "https://techcrunch.com/category/startups/feed/",
            "rss",
            True,
        ),
    ]


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


def test_discovery_excludes_history_before_detail_and_news_calls(monkeypatch):
    detail_calls = []
    monkeypatch.setattr(
        startup_discovery.directories,
        "fetch_yc_launches",
        lambda *_args, **_kwargs: [
            CompanyLead(
                "SeenCo",
                "old",
                "https://yc.example/seen",
                profile_url="https://www.ycombinator.com/companies/seenco",
                source_name="YC Launches",
            ),
            CompanyLead(
                "NewCo",
                "new",
                "https://yc.example/new",
                profile_url="https://www.ycombinator.com/companies/newco",
                source_name="YC Launches",
            ),
        ],
    )
    monkeypatch.setattr(
        startup_discovery.directories,
        "fetch_speedrun_companies",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        startup_discovery.directories,
        "enrich_yc_company",
        lambda lead: detail_calls.append(lead.company) or lead,
    )
    monkeypatch.setattr(
        startup_discovery.rss,
        "fetch_tagged",
        lambda *_args, **_kwargs: [],
    )

    result = startup_discovery.discover(
        configured_sources(),
        {"seenco"},
        limit=3,
    )

    assert detail_calls == ["NewCo"]
    assert [lead.company for lead in result.leads] == ["NewCo"]


def test_discovery_enriches_up_to_requested_limit(monkeypatch):
    leads = [
        CompanyLead(
            f"Company{index}",
            "AI product",
            f"https://yc.example/{index}",
            profile_url=f"https://www.ycombinator.com/companies/company{index}",
            source_name="YC Launches",
        )
        for index in range(20)
    ]
    detail_calls = []
    monkeypatch.setattr(
        startup_discovery.directories,
        "fetch_yc_launches",
        lambda *_args, **_kwargs: leads,
    )
    monkeypatch.setattr(
        startup_discovery.directories,
        "fetch_speedrun_companies",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        startup_discovery.directories,
        "enrich_yc_company",
        lambda lead: detail_calls.append(lead.company) or lead,
    )
    monkeypatch.setattr(
        startup_discovery.rss,
        "fetch_tagged",
        lambda *_args, **_kwargs: [],
    )

    result = startup_discovery.discover(configured_sources(), set(), limit=15)

    assert len(result.leads) == 15
    assert detail_calls == [f"Company{index}" for index in range(15)]


def test_discovery_interleaves_directory_sources_before_limit(monkeypatch):
    yc_leads = [
        CompanyLead(
            f"YC{index}",
            "AI product",
            f"https://yc.example/{index}",
            profile_url=f"https://www.ycombinator.com/companies/yc{index}",
            source_name="YC Launches",
        )
        for index in range(20)
    ]
    speedrun_leads = [
        CompanyLead(
            f"Speedrun{index}",
            "AI product",
            f"https://speedrun.example/{index}",
            source_name="a16z Speedrun Companies",
        )
        for index in range(10)
    ]
    monkeypatch.setattr(
        startup_discovery.directories,
        "fetch_yc_launches",
        lambda *_args, **_kwargs: yc_leads,
    )
    monkeypatch.setattr(
        startup_discovery.directories,
        "fetch_speedrun_companies",
        lambda *_args, **_kwargs: speedrun_leads,
    )
    monkeypatch.setattr(
        startup_discovery.directories,
        "enrich_yc_company",
        lambda lead: lead,
    )
    monkeypatch.setattr(
        startup_discovery.rss,
        "fetch_tagged",
        lambda *_args, **_kwargs: [],
    )

    result = startup_discovery.discover(configured_sources(), set(), limit=6)

    assert [lead.company for lead in result.leads] == [
        "YC0",
        "Speedrun0",
        "YC1",
        "Speedrun1",
        "YC2",
        "Speedrun2",
    ]


def test_discovery_continues_when_one_directory_fails(monkeypatch):
    monkeypatch.setattr(
        startup_discovery.directories,
        "fetch_yc_launches",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("upstream details")
        ),
    )
    monkeypatch.setattr(
        startup_discovery.directories,
        "fetch_speedrun_companies",
        lambda *_args, **_kwargs: [
            CompanyLead(
                "Acceler8",
                "Workforce AI",
                "https://speedrun.a16z.com/companies/acceler8",
                source_name="a16z Speedrun Companies",
            )
        ],
    )
    monkeypatch.setattr(
        startup_discovery.rss,
        "fetch_tagged",
        lambda *_args, **_kwargs: [],
    )

    result = startup_discovery.discover(
        configured_sources(),
        set(),
    )

    assert [lead.company for lead in result.leads] == ["Acceler8"]
    assert result.warnings == (
        "YC Launches 暫時讀不到，已改用其他來源。",
    )
    assert "upstream details" not in " ".join(result.warnings)


def test_discovery_logs_failure_category_without_raw_secret(
    monkeypatch,
    caplog,
):
    monkeypatch.setattr(
        startup_discovery.directories,
        "fetch_yc_launches",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("TAVILY_API_KEY=secret-value")
        ),
    )
    monkeypatch.setattr(
        startup_discovery.directories,
        "fetch_speedrun_companies",
        lambda *_args, **_kwargs: [
            CompanyLead(
                "Acceler8",
                "Workforce AI",
                "https://speedrun.a16z.com/companies/acceler8",
                source_name="a16z Speedrun Companies",
            )
        ],
    )
    monkeypatch.setattr(
        startup_discovery.rss,
        "fetch_tagged",
        lambda *_args, **_kwargs: [],
    )

    with caplog.at_level(logging.INFO):
        startup_discovery.discover(configured_sources(), set())

    assert (
        "startup_source_failed source=YC Launches category=RuntimeError"
        in caplog.text
    )
    assert "secret-value" not in caplog.text
    assert "TAVILY_API_KEY" not in caplog.text
    assert "startup_discovery fetched=" in caplog.text


def test_discovery_keeps_directory_leads_when_news_fails(monkeypatch):
    monkeypatch.setattr(
        startup_discovery.directories,
        "fetch_yc_launches",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        startup_discovery.directories,
        "fetch_speedrun_companies",
        lambda *_args, **_kwargs: [
            CompanyLead(
                "Acceler8",
                "Workforce AI",
                "https://speedrun.a16z.com/companies/acceler8",
                source_name="a16z Speedrun Companies",
            )
        ],
    )
    monkeypatch.setattr(
        startup_discovery.rss,
        "fetch_tagged",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("feed secret")
        ),
    )

    result = startup_discovery.discover(configured_sources(), set())

    assert [lead.company for lead in result.leads] == ["Acceler8"]
    assert result.warnings == (
        "TechCrunch Startups 暫時讀不到，已使用公司目錄。",
    )
    assert "feed secret" not in " ".join(result.warnings)
