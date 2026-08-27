import pytest

from daibu.cards.editor_payload import (
    apply_editor_values,
    draft_to_editor_payload,
    editable_values,
)
from tests.card_fixtures import carousel_draft


def test_editor_values_update_diagram_text_but_preserve_evidence():
    original = carousel_draft()
    values = dict(editable_values(original))
    values.update(
        {
            "page.problem.heading": "新的問題標題",
            "page.problem.diagram.0.title": "新的第一步",
            "page.problem.diagram.0.text": "新的節點說明",
            "page.problem.diagram.0.expression": "think",
        }
    )

    edited = apply_editor_values(original, values)
    problem = edited.pages[2]

    assert problem.heading == "新的問題標題"
    assert problem.diagram.nodes[0].title == "新的第一步"
    assert problem.diagram.nodes[0].text == "新的節點說明"
    assert problem.sections[0].source_ids == original.pages[2].sections[0].source_ids
    assert problem.sections[0].evidence_quotes == original.pages[2].sections[0].evidence_quotes


def test_unknown_editor_key_cannot_change_locked_structure():
    original = carousel_draft()
    values = dict(editable_values(original))
    values["page.problem.page_type"] = "cover"

    with pytest.raises(ValueError, match="內容欄位不存在"):
        apply_editor_values(original, values)


def test_editor_rebuild_keeps_section_and_diagram_counts():
    original = carousel_draft()
    edited = apply_editor_values(original, editable_values(original))

    assert [len(page.sections) for page in edited.pages] == [
        len(page.sections) for page in original.pages
    ]
    assert [len(page.diagram.nodes) if page.diagram else 0 for page in edited.pages] == [
        len(page.diagram.nodes) if page.diagram else 0 for page in original.pages
    ]


def test_fixed_cta_copy_is_not_exposed_as_an_editable_field():
    keys = editable_values(carousel_draft())

    assert "page.cta.section.0.text" not in keys


def test_payload_contains_six_pages_preview_fields_and_locked_evidence():
    draft = carousel_draft()
    previews = {
        page.page_type: f"<main>{page.page_type}</main>"
        for page in draft.pages
    }

    payload = draft_to_editor_payload(draft, previews, revision=7, idea_id=42)

    assert payload["revision"] == 7
    assert payload["ideaId"] == 42
    assert len(payload["pages"]) == 6
    assert payload["pages"][2]["previewHtml"] == "<main>problem</main>"
    assert any(
        field["key"] == "page.problem.diagram.0.expression"
        and field["options"] == ["concerned", "happy", "listen", "think"]
        for field in payload["pages"][2]["fields"]
    )
    locked = payload["pages"][2]["lockedEvidence"]
    assert locked[0]["sourceIds"]
    assert locked[0]["quotes"]
    assert all("<" not in quote for item in locked for quote in item["quotes"])
    assert set(payload["values"]) == set(editable_values(draft))
