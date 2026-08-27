from dataclasses import asdict, dataclass, replace
from typing import Mapping

from daibu.cards import mascot, pages
from daibu.cards.schema import CarouselDraft


@dataclass(frozen=True)
class EditableField:
    key: str
    page_type: str
    label: str
    value: str
    input_kind: str
    recommended_chars: int
    hard_chars: int
    options: tuple[str, ...] = ()


@dataclass(frozen=True)
class LockedEvidence:
    label: str
    source_ids: tuple[str, ...]
    quotes: tuple[str, ...]


EXPRESSION_LABELS = {
    "listen": "聆聽",
    "think": "思考",
    "happy": "完成",
    "concerned": "注意",
}


def _field(
    key: str,
    page_type: str,
    label: str,
    value: str,
    *,
    kind: str = "text",
    hard_chars: int | None = None,
) -> EditableField:
    limits = {
        "heading": (18, pages.LIMITS["heading"]),
        "section": (72, 220),
        "diagram-title": (12, 24),
        "diagram-text": (20, 48),
        "expression": (0, 0),
    }
    recommended, hard = limits[kind]
    if hard_chars is not None:
        hard = hard_chars
        recommended = min(recommended, max(1, round(hard * 0.8)))
    return EditableField(
        key,
        page_type,
        label,
        value,
        "expression" if kind == "expression" else "text",
        recommended,
        hard,
        tuple(sorted(mascot.EXPRESSIONS)) if kind == "expression" else (),
    )


def editable_fields(draft: CarouselDraft) -> tuple[EditableField, ...]:
    fields = []
    for page in draft.pages:
        prefix = f"page.{page.page_type}"
        fields.append(
            _field(
                f"{prefix}.heading",
                page.page_type,
                "頁面標題",
                page.heading,
                kind="heading",
                hard_chars=pages.HEADING_HARD_LIMITS[page.page_type],
            )
        )
        for index, section in enumerate(page.sections):
            if page.page_type == "cta":
                continue
            fields.append(
                _field(
                    f"{prefix}.section.{index}.text",
                    page.page_type,
                    section.label,
                    section.text,
                    kind="section",
                    hard_chars=pages.SECTION_HARD_LIMITS[page.page_type][index],
                )
            )
        if page.diagram is not None:
            for index, node in enumerate(page.diagram.nodes):
                node_prefix = f"{prefix}.diagram.{index}"
                fields.extend(
                    (
                        _field(
                            f"{node_prefix}.title",
                            page.page_type,
                            f"圖解 {index + 1} 標題",
                            node.title,
                            kind="diagram-title",
                            hard_chars=pages.DIAGRAM_TITLE_HARD_LIMIT,
                        ),
                        _field(
                            f"{node_prefix}.text",
                            page.page_type,
                            f"圖解 {index + 1} 說明",
                            node.text,
                            kind="diagram-text",
                            hard_chars=pages.DIAGRAM_TEXT_HARD_LIMIT,
                        ),
                        _field(
                            f"{node_prefix}.expression",
                            page.page_type,
                            f"圖解 {index + 1} 表情",
                            node.expression,
                            kind="expression",
                        ),
                    )
                )
    return tuple(fields)


def editable_values(draft: CarouselDraft) -> dict[str, str]:
    return {field.key: field.value for field in editable_fields(draft)}


def apply_editor_values(
    saved_draft: CarouselDraft,
    values: Mapping[str, str],
) -> CarouselDraft:
    allowed = set(editable_values(saved_draft))
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise ValueError(f"內容欄位不存在：{unknown[0]}")
    if any(not isinstance(value, str) for value in values.values()):
        raise ValueError("內容欄位必須是文字")

    revised_pages = []
    for page in saved_draft.pages:
        prefix = f"page.{page.page_type}"
        heading = values.get(f"{prefix}.heading", page.heading)
        sections = tuple(
            replace(
                section,
                text=values.get(
                    f"{prefix}.section.{index}.text",
                    section.text,
                ),
            )
            for index, section in enumerate(page.sections)
        )
        diagram = page.diagram
        if diagram is not None:
            nodes = []
            for index, node in enumerate(diagram.nodes):
                node_prefix = f"{prefix}.diagram.{index}"
                expression = values.get(
                    f"{node_prefix}.expression",
                    node.expression,
                )
                if expression not in mascot.EXPRESSIONS:
                    raise ValueError("圖解表情不存在")
                nodes.append(
                    replace(
                        node,
                        title=values.get(f"{node_prefix}.title", node.title),
                        text=values.get(f"{node_prefix}.text", node.text),
                        expression=expression,
                    )
                )
            diagram = replace(diagram, nodes=tuple(nodes))
        revised_pages.append(
            replace(
                page,
                heading=heading,
                sections=sections,
                diagram=diagram,
            )
        )
    return replace(saved_draft, pages=tuple(revised_pages))


def _field_payload(field: EditableField) -> dict[str, object]:
    raw = asdict(field)
    return {
        "key": raw["key"],
        "pageType": raw["page_type"],
        "label": raw["label"],
        "value": raw["value"],
        "inputKind": raw["input_kind"],
        "recommendedChars": raw["recommended_chars"],
        "hardChars": raw["hard_chars"],
        "options": list(raw["options"]),
    }


def draft_to_editor_payload(
    draft: CarouselDraft,
    preview_html: Mapping[str, str],
    revision: int,
    *,
    idea_id: int,
) -> dict[str, object]:
    all_fields = editable_fields(draft)
    by_page = {
        page_type: tuple(
            field for field in all_fields if field.page_type == page_type
        )
        for page_type in pages.PAGE_TYPES
    }
    page_payloads = []
    for page in draft.pages:
        locked = tuple(
            LockedEvidence(
                section.label,
                section.source_ids,
                tuple(item.quote for item in section.evidence_quotes),
            )
            for section in page.sections
        )
        page_payloads.append(
            {
                "number": page.page_no,
                "pageType": page.page_type,
                "label": pages.label(page.page_type),
                "fields": [
                    _field_payload(field) for field in by_page[page.page_type]
                ],
                "lockedEvidence": [
                    {
                        "label": item.label,
                        "sourceIds": list(item.source_ids),
                        "quotes": list(item.quotes),
                    }
                    for item in locked
                ],
                "previewHtml": preview_html[page.page_type],
            }
        )
    values = editable_values(draft)
    return {
        "ideaId": idea_id,
        "revision": revision,
        "pages": page_payloads,
        "values": values,
        "fieldsByKey": {
            field.key: _field_payload(field) for field in all_fields
        },
        "expressionLabels": EXPRESSION_LABELS,
        "expressionPreviews": {
            expression: mascot.q_head_svg(expression)
            for expression in sorted(mascot.EXPRESSIONS)
        },
    }
