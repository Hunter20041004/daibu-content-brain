from types import SimpleNamespace
from pathlib import Path

from daibu.cards import workbench
from daibu.cards.schema import BrandAsset
from tests.card_fixtures import verified_sources


def test_missing_requirements_reports_company_and_source_gaps():
    unnamed = SimpleNamespace(company="")
    named = SimpleNamespace(company="ElevenLabs")
    pack = verified_sources()

    assert workbench.missing_requirements(unnamed, pack, None) == (
        "這則題目還沒有公司名",
    )
    assert workbench.missing_requirements(named, (), None) == (
        "還沒有任何已查證來源",
    )
    assert workbench.missing_requirements(unnamed, (), None) == (
        "這則題目還沒有公司名",
        "還沒有任何已查證來源",
    )
    assert workbench.missing_requirements(named, pack, None) == ()


def test_rendering_requires_complete_inputs_and_a_logo():
    named = SimpleNamespace(company="ElevenLabs")
    unnamed = SimpleNamespace(company="")
    pack = verified_sources()
    asset = BrandAsset(
        "ElevenLabs",
        Path("logo.png"),
        "https://elevenlabs.io/about",
        "2026-07-30",
    )

    assert not workbench.can_render(named, pack, None)
    assert not workbench.can_render(unnamed, pack, asset)
    assert workbench.can_render(named, pack, asset)
