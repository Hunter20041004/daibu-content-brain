from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse

from daibu.cards import pages


@dataclass(frozen=True)
class VerifiedSource:
    source_id: str
    publisher: str
    published_at: str
    url: str
    excerpt: str


@dataclass(frozen=True)
class ContentSection:
    label: str
    text: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class DiagramNode:
    title: str
    text: str
    expression: str = ""


@dataclass(frozen=True)
class DiagramSpec:
    kind: str
    nodes: tuple[DiagramNode, ...]


@dataclass(frozen=True)
class CarouselPage:
    page_no: int
    page_type: str
    heading: str
    sections: tuple[ContentSection, ...]
    diagram: DiagramSpec | None
    source_label: str


@dataclass(frozen=True)
class CarouselDraft:
    sources: tuple[VerifiedSource, ...]
    pages: tuple[CarouselPage, ...]


@dataclass(frozen=True)
class BrandAsset:
    company: str
    local_path: Path
    official_source_url: str
    verified_at: str


def narrative_chars(page: CarouselPage) -> int:
    return sum(len("".join(section.text.split())) for section in page.sections)


def _source_label(
    sections: tuple[ContentSection, ...],
    sources: tuple[VerifiedSource, ...],
) -> str:
    used = {item for section in sections for item in section.source_ids}
    entries = []
    for source in sources:
        if source.source_id in used:
            label = f"{source.publisher} · {source.published_at}"
            if label not in entries:
                entries.append(label)
    return "來源：" + "；".join(entries)


def page_from_mapping(
    value: Mapping[str, object],
    sources: tuple[VerifiedSource, ...],
) -> CarouselPage:
    sections = tuple(
        ContentSection(
            str(item["label"]),
            str(item["text"]),
            tuple(str(source_id) for source_id in item.get("source_ids", [])),
        )
        for item in value.get("sections", [])
    )
    raw_diagram = value.get("diagram")
    diagram = None
    if isinstance(raw_diagram, Mapping):
        diagram = DiagramSpec(
            str(raw_diagram.get("kind", "")),
            tuple(
                DiagramNode(
                    str(node.get("title", "")),
                    str(node.get("text", "")),
                    str(node.get("expression", "")),
                )
                for node in raw_diagram.get("nodes", [])
                if isinstance(node, Mapping)
            ),
        )
    return CarouselPage(
        int(value["page_no"]),
        str(value["page_type"]),
        str(value["heading"]),
        sections,
        diagram,
        _source_label(sections, sources),
    )


def validate_draft(draft: CarouselDraft) -> None:
    """Validate a structured carousel draft."""
    source_ids = [source.source_id for source in draft.sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("來源 ID 不可重複")

    for source in draft.sources:
        values = (
            source.source_id,
            source.publisher,
            source.published_at,
            source.url,
            source.excerpt,
        )
        if not all(value.strip() for value in values):
            raise ValueError("來源資料不完整")
        parsed = urlparse(source.url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("來源網址必須是 https")
        try:
            date.fromisoformat(source.published_at)
        except ValueError as error:
            raise ValueError("來源日期必須是 YYYY-MM-DD") from error

    expected = list(enumerate(pages.PAGE_TYPES, start=1))
    actual = [(page.page_no, page.page_type) for page in draft.pages]
    if actual != expected:
        raise ValueError("輪播必須依固定順序包含七頁")

    known_sources = {source.source_id for source in draft.sources}
    for page in draft.pages:
        labels = {section.label for section in page.sections}
        missing = pages.REQUIRED_SECTIONS[page.page_type] - labels
        if missing:
            raise ValueError(
                f"{page.page_type} 缺少 section：{', '.join(sorted(missing))}"
            )

        if page.page_type in pages.DIAGRAM_FOR:
            if page.diagram is None:
                raise ValueError(f"{page.page_type} 缺少品牌圖解")
            if page.diagram.kind not in pages.DIAGRAM_FOR[page.page_type]:
                raise ValueError(f"{page.page_type} 使用了不相容的圖解")
        elif page.diagram is not None:
            raise ValueError(f"{page.page_type} 不應放主圖解")

        if page.page_type in pages.PAGE_TYPES[1:6]:
            count = narrative_chars(page)
            if not pages.LIMITS["inner_min"] <= count <= pages.LIMITS["inner_max"]:
                raise ValueError(
                    f"{page.page_type} 文字需為 "
                    f"{pages.LIMITS['inner_min']}–{pages.LIMITS['inner_max']} 字，"
                    f"目前 {count} 字"
                )

        for section in page.sections:
            unknown = set(section.source_ids) - known_sources
            if unknown:
                raise ValueError(f"引用不存在的來源：{', '.join(sorted(unknown))}")
            may_be_unsourced = section.label in {"互動邀請", "證據限制"}
            if not section.source_ids and not may_be_unsourced:
                raise ValueError(f"{section.label} 是事實區塊，必須附來源")

    cta = " ".join(section.text for section in draft.pages[-1].sections)
    if any(word in cta for word in ("試用", "註冊", "下載", "投資", "官網看看")):
        raise ValueError("第 7 頁只能邀請按讚或追蹤")
