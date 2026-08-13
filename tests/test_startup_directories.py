from pathlib import Path

from daibu.fetch import startup_directories


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
