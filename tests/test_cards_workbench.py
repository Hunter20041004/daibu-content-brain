from types import SimpleNamespace
from pathlib import Path
from dataclasses import replace

from daibu.cards import workbench
from daibu.cards.schema import BrandAsset
from tests.card_fixtures import carousel_draft, verified_sources


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


def test_cached_pngs_are_invalidated_when_draft_content_changes():
    draft = carousel_draft()
    assert workbench.draft_fingerprint(draft) == (
        workbench.draft_fingerprint(draft)
    )
    changed_section = replace(
        draft.pages[1].sections[0],
        text=draft.pages[1].sections[0].text + "改",
    )
    changed_page = replace(
        draft.pages[1],
        sections=(changed_section,) + draft.pages[1].sections[1:],
    )
    changed = replace(
        draft,
        pages=(draft.pages[0], changed_page) + draft.pages[2:],
    )
    assert workbench.draft_fingerprint(changed) != (
        workbench.draft_fingerprint(draft)
    )

    state = {
        "carousel-png-42": (
            workbench.draft_fingerprint(draft),
            [b"png"] * 7,
        )
    }
    assert workbench.cached_pngs(state, 42, draft) == [b"png"] * 7
    assert workbench.cached_pngs(state, 42, changed) is None
