from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Mapping

from daibu.cards import pages
from daibu.cards.layout_registry import registry_for_schema
from daibu.cards.layout_schema import (
    LayoutDocument,
    layout_to_mapping,
    parse_layout,
)


@dataclass(frozen=True)
class TemplateField:
    element_id: str
    label: str
    kind: str
    editable_properties: tuple[str, ...]
    min_values: Mapping[str, float]
    max_values: Mapping[str, float]


_LAYOUT_ID = re.compile(
    r'<[^>]*\bdata-layout-id=["\u0027]([^"\u0027]+)["\u0027][^>]*>'
)


def _registry_fingerprint(
    schema_version: int,
    registry: Mapping[str, Mapping[str, object]],
) -> str:
    identity = {
        "schema_version": schema_version,
        "pages": {
            page_type: sorted(
                (
                    element_id,
                    getattr(rule, "text"),
                    getattr(rule, "collision"),
                    getattr(rule, "rendered"),
                )
                for element_id, rule in rules.items()
            )
            for page_type, rules in sorted(registry.items())
        },
    }
    encoded = json.dumps(
        identity,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def missing_preview_element_ids(
    preview_html: str,
    page_type: str,
    registry: Mapping[str, Mapping[str, object]],
) -> tuple[str, ...]:
    found = set(preview_layout_id_counts(preview_html))
    expected = {
        element_id
        for element_id, rule in registry[page_type].items()
        if getattr(rule, "rendered", True)
    }
    return tuple(sorted(expected - found))


def preview_layout_id_counts(preview_html: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for element_id in _LAYOUT_ID.findall(preview_html):
        counts[element_id] = counts.get(element_id, 0) + 1
    return counts


def apply_template_values(
    base: LayoutDocument,
    page_type: str,
    values: Mapping[str, Mapping[str, object]],
) -> LayoutDocument:
    if page_type not in base.pages:
        raise ValueError(f"未知頁型：{page_type}")
    expected = set(base.pages[page_type].elements)
    if set(values) != expected:
        raise ValueError("模板元素不完整或包含未知元素")
    registry = registry_for_schema(base.schema_version)
    raw = layout_to_mapping(base)
    raw_elements = raw["pages"][page_type]["elements"]
    for element_id, properties in values.items():
        rule = registry[page_type][element_id]
        allowed = {"x", "y", "w", "h"}
        if rule.text:
            allowed |= {"font_size", "text_align"}
        unknown = set(properties) - allowed
        if unknown:
            raise ValueError(f"{element_id} 含不允許的屬性：{sorted(unknown)[0]}")
        if set(properties) != allowed:
            raise ValueError(f"{element_id} 缺少必要屬性")
        raw_elements[element_id] = dict(properties)
    return parse_layout(raw)


def reset_layout_page(
    working: LayoutDocument,
    base: LayoutDocument,
    page_type: str,
) -> LayoutDocument:
    raw = layout_to_mapping(working)
    raw["pages"][page_type] = layout_to_mapping(base)["pages"][page_type]
    return parse_layout(raw)


def summarize_layout_diff(
    base: LayoutDocument,
    working: LayoutDocument,
) -> tuple[str, ...]:
    summaries = []
    for index, page_type in enumerate(pages.PAGE_TYPES, start=1):
        moved = resized = 0
        for element_id, original in base.pages[page_type].elements.items():
            edited = working.pages[page_type].elements[element_id]
            if (original.rect.x, original.rect.y) != (edited.rect.x, edited.rect.y):
                moved += 1
            if (
                (original.rect.w, original.rect.h, original.text_style)
                != (edited.rect.w, edited.rect.h, edited.text_style)
            ):
                resized += 1
        if moved or resized:
            summaries.append(
                f"第 {index} 頁：移動 {moved} 個元素、調整 {resized} 個文字框"
            )
    return tuple(summaries)


def template_editor_payload(
    theme,
    versions,
    selected_version,
    page_type: str,
    preview_html: str,
) -> dict[str, object]:
    layout = layout_to_mapping(selected_version.layout)
    schema_version = selected_version.layout.schema_version
    registry = registry_for_schema(schema_version)
    counts = preview_layout_id_counts(preview_html)
    missing = missing_preview_element_ids(preview_html, page_type, registry)
    duplicates = tuple(
        sorted(
            element_id
            for element_id, rule in registry[page_type].items()
            if rule.rendered and counts.get(element_id, 0) > 1
        )
    )
    if missing:
        sync_error = "預覽缺少版面元素：" + "、".join(missing)
    elif duplicates:
        sync_error = "預覽含重複版面元素：" + "、".join(duplicates)
    else:
        sync_error = ""
    elements = []
    for element_id, rule in registry[page_type].items():
        if not rule.rendered:
            continue
        properties = ("x", "y", "w", "h", "font_size", "text_align") if rule.text else ("x", "y", "w", "h")
        elements.append({
            "elementId": element_id,
            "label": rule.label,
            "kind": "text" if rule.text else "graphic",
            "collision": rule.collision,
            "editableProperties": list(properties),
            "minValues": {"w": rule.min_w, "h": rule.min_h, "font_size": rule.min_font_size},
            "maxValues": {"font_size": rule.max_font_size},
        })
    return {
        "themeId": theme.id,
        "themeName": theme.name,
        "versionId": selected_version.id,
        "versionNo": selected_version.version_no,
        "pageType": page_type,
        "pages": [{"pageType": value, "label": pages.label(value)} for value in pages.PAGE_TYPES],
        "elements": elements,
        "layout": layout,
        "layoutSchemaVersion": selected_version.layout.schema_version,
        "registryFingerprint": _registry_fingerprint(schema_version, registry),
        "previewHtml": preview_html,
        "previewSyncError": sync_error,
        "canvas": {"width": selected_version.layout.canvas_width, "height": selected_version.layout.canvas_height},
        "versions": [{"id": version.id, "versionNo": version.version_no, "createdAt": version.created_at} for version in versions],
    }
