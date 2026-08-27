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
    source_kind: str = "manual"


@dataclass(frozen=True)
class EvidenceQuote:
    source_id: str
    quote: str


@dataclass(frozen=True)
class ContentSection:
    label: str
    text: str
    source_ids: tuple[str, ...]
    evidence_quotes: tuple[EvidenceQuote, ...] = ()


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


class DraftValidationError(ValueError):
    def __init__(
        self,
        draft: CarouselDraft,
        issues: tuple[tuple[str | None, str], ...],
    ) -> None:
        self.draft = draft
        self.issues = issues
        self.page_types = frozenset(
            page_type
            for page_type, _message in issues
            if page_type is not None
        )
        self.has_global_issues = any(
            page_type is None for page_type, _message in issues
        )
        super().__init__(
            "\n".join(f"- {message}" for _page_type, message in issues)
        )


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
    if not used:
        return ""
    dates_by_publisher: dict[str, list[str]] = {}
    for source in sorted(sources, key=lambda item: item.source_id):
        if source.source_id in used:
            dates = dates_by_publisher.setdefault(source.publisher, [])
            if source.published_at not in dates:
                dates.append(source.published_at)
    entries = (
        f"{publisher} · {'、'.join(dates)}"
        for publisher, dates in dates_by_publisher.items()
    )
    return "來源：" + "；".join(entries)


def page_from_mapping(
    value: Mapping[str, object],
    sources: tuple[VerifiedSource, ...],
) -> CarouselPage:
    for field in ("page_no", "page_type", "heading"):
        if field not in value:
            raise ValueError(f"輪播頁缺少必要欄位：{field}")
    page_no = value["page_no"]
    if not isinstance(page_no, int) or isinstance(page_no, bool):
        raise ValueError("輪播頁 page_no 必須是整數")
    for field in ("page_type", "heading"):
        if not isinstance(value[field], str):
            raise ValueError(f"輪播頁 {field} 必須是字串")
    raw_sections = value.get("sections", [])
    if not isinstance(raw_sections, (list, tuple)):
        raise ValueError("輪播頁 sections 必須是陣列")
    parsed_sections = []
    for item in raw_sections:
        if not isinstance(item, Mapping):
            raise ValueError("輪播頁 section 必須是物件")
        for field in ("label", "text"):
            if field not in item:
                raise ValueError(
                    f"輪播頁 section 缺少必要欄位：{field}"
                )
        for field in ("label", "text"):
            if not isinstance(item[field], str):
                raise ValueError(
                    f"輪播頁 section.{field} 必須是字串"
                )
        raw_evidence = item.get("evidence_quotes")
        evidence_quotes: tuple[EvidenceQuote, ...] = ()
        if raw_evidence is not None:
            if not isinstance(raw_evidence, (list, tuple)):
                raise ValueError(
                    "輪播頁 section.evidence_quotes 必須是陣列"
                )
            parsed_evidence = []
            for evidence in raw_evidence:
                if not isinstance(evidence, Mapping):
                    raise ValueError("輪播頁查證引文必須是物件")
                source_id = evidence.get("source_id")
                quote = evidence.get("quote")
                if not isinstance(source_id, str) or not source_id.strip():
                    raise ValueError("查證引文 source_id 必須是非空字串")
                if not isinstance(quote, str) or not quote.strip():
                    raise ValueError("查證引文 quote 必須是非空字串")
                parsed_evidence.append(EvidenceQuote(source_id, quote))
            evidence_quotes = tuple(parsed_evidence)
            raw_source_ids = list(
                dict.fromkeys(
                    evidence.source_id for evidence in evidence_quotes
                )
            )
        else:
            if "source_ids" not in item:
                raise ValueError(
                    "輪播頁 section 缺少必要欄位：source_ids"
                )
            raw_source_ids = item["source_ids"]
        if not isinstance(raw_source_ids, (list, tuple)):
            raise ValueError("輪播頁 section.source_ids 必須是陣列")
        if any(
            not isinstance(source_id, str) or not source_id.strip()
            for source_id in raw_source_ids
        ):
            raise ValueError(
                "輪播頁 section.source_ids 每一項都必須是非空字串"
            )
        parsed_sections.append(
            ContentSection(
                item["label"],
                item["text"],
                tuple(raw_source_ids),
                evidence_quotes,
            )
        )
    sections = tuple(parsed_sections)
    raw_diagram = value.get("diagram")
    if raw_diagram is not None and not isinstance(raw_diagram, Mapping):
        raise ValueError("輪播頁 diagram 必須是物件或 null")
    diagram = None
    if isinstance(raw_diagram, Mapping):
        raw_nodes = raw_diagram.get("nodes", [])
        if not isinstance(raw_nodes, (list, tuple)):
            raise ValueError("輪播頁 diagram.nodes 必須是陣列")
        parsed_nodes = []
        for node in raw_nodes:
            if not isinstance(node, Mapping):
                raise ValueError("輪播頁 diagram node 必須是物件")
            for field in ("title", "text"):
                if not isinstance(node.get(field), str):
                    raise ValueError(
                        f"輪播頁 diagram node.{field} 必須是字串"
                    )
            expression = node.get("expression", "")
            if not isinstance(expression, str):
                raise ValueError(
                    "輪播頁 diagram node.expression 必須是字串"
                )
            parsed_nodes.append(
                DiagramNode(
                    node["title"],
                    node["text"],
                    expression,
                )
            )
        diagram = DiagramSpec(
            str(raw_diagram.get("kind", "")),
            tuple(parsed_nodes),
        )
    return CarouselPage(
        page_no,
        value["page_type"],
        value["heading"],
        sections,
        diagram,
        _source_label(sections, sources),
    )


def _source_validation_errors(
    sources: tuple[VerifiedSource, ...],
) -> tuple[str, ...]:
    errors: list[str] = []

    def record(message: str) -> None:
        if message not in errors:
            errors.append(message)

    source_ids = [source.source_id for source in sources]
    if len(source_ids) != len(set(source_ids)):
        record("來源 ID 不可重複")

    for source in sources:
        values = (
            source.source_id,
            source.publisher,
            source.published_at,
            source.url,
            source.excerpt,
        )
        if not all(
            isinstance(value, str) and value.strip()
            for value in values
        ):
            record("來源資料不完整")
        parsed = (
            urlparse(source.url)
            if isinstance(source.url, str)
            else None
        )
        if parsed is None or parsed.scheme != "https" or not parsed.netloc:
            record("來源網址必須是 https")
        try:
            if not isinstance(source.published_at, str):
                raise ValueError
            date.fromisoformat(source.published_at)
        except ValueError:
            record("來源日期必須是 YYYY-MM-DD")
        if source.source_kind not in {"official", "third_party", "manual"}:
            record("來源類別無效")
    return tuple(errors)


def validate_sources(sources: tuple[VerifiedSource, ...]) -> None:
    errors = _source_validation_errors(sources)
    if errors:
        raise ValueError("\n".join(f"- {message}" for message in errors))


def validate_draft(draft: CarouselDraft) -> None:
    """Validate a structured carousel draft."""
    errors: list[tuple[str | None, str]] = []

    def record(message: str, page_type: str | None = None) -> None:
        issue = (page_type, message)
        if issue not in errors:
            errors.append(issue)

    for source_error in _source_validation_errors(draft.sources):
        record(source_error)

    expected = list(enumerate(pages.PAGE_TYPES, start=1))
    actual = [(page.page_no, page.page_type) for page in draft.pages]
    if actual != expected:
        record("輪播必須依固定順序包含六頁")

    known_sources = {source.source_id for source in draft.sources}
    for page in draft.pages:
        if not page.heading.strip():
            record(f"{page.page_type} 標題不可空白", page.page_type)
        heading_chars = len("".join(page.heading.split()))
        heading_limit = pages.HEADING_HARD_LIMITS.get(
            page.page_type,
            pages.LIMITS["heading"],
        )
        if heading_chars > heading_limit:
            record(
                f"{page.page_type} 標題最多 {heading_limit} 字，"
                f"目前 {heading_chars} 字",
                page.page_type,
            )
        expected_source_label = _source_label(page.sections, draft.sources)
        if page.source_label != expected_source_label:
            record(
                f"{page.page_type} 來源標示必須由程式產生",
                page.page_type,
            )
        ordered_labels = tuple(section.label for section in page.sections)
        labels = set(ordered_labels)
        required = pages.REQUIRED_SECTIONS.get(page.page_type)
        if required is not None:
            missing = required - labels
            if missing:
                record(
                    f"{page.page_type} 缺少 section："
                    f"{', '.join(sorted(missing))}",
                    page.page_type,
                )
            if ordered_labels not in pages.SECTION_LABEL_SEQUENCES[page.page_type]:
                record(
                    f"{page.page_type} section 必須依固定順序完整提供",
                    page.page_type,
                )

        if page.page_type in pages.DIAGRAM_FOR:
            if page.diagram is None:
                record(f"{page.page_type} 缺少品牌圖解", page.page_type)
            elif page.diagram.kind not in pages.DIAGRAM_FOR[page.page_type]:
                record(f"{page.page_type} 使用了不相容的圖解", page.page_type)
            elif len(page.diagram.nodes) != 3:
                record(
                    f"{page.page_type} 圖解必須有 3 個節點",
                    page.page_type,
                )
            elif any(
                not node.title.strip() or not node.text.strip()
                for node in page.diagram.nodes
            ):
                record(
                    f"{page.page_type} 圖解節點不可空白",
                    page.page_type,
                )
            else:
                for node_index, node in enumerate(page.diagram.nodes, start=1):
                    title_chars = len("".join(node.title.split()))
                    text_chars = len("".join(node.text.split()))
                    if title_chars > pages.DIAGRAM_TITLE_HARD_LIMIT:
                        record(
                            f"{page.page_type} 圖解 {node_index} 標題最多 "
                            f"{pages.DIAGRAM_TITLE_HARD_LIMIT} 字，"
                            f"目前 {title_chars} 字",
                            page.page_type,
                        )
                    if text_chars > pages.DIAGRAM_TEXT_HARD_LIMIT:
                        record(
                            f"{page.page_type} 圖解 {node_index} 說明最多 "
                            f"{pages.DIAGRAM_TEXT_HARD_LIMIT} 字，"
                            f"目前 {text_chars} 字",
                            page.page_type,
                        )
        elif page.page_type in pages.PAGE_TYPES and page.diagram is not None:
            record(f"{page.page_type} 不應放主圖解", page.page_type)

        if page.page_type in pages.PAGE_TYPES[1:5]:
            count = narrative_chars(page)
            if count > pages.LIMITS["inner_max"]:
                record(
                    f"{page.page_type} 文字最多 "
                    f"{pages.LIMITS['inner_max']} 字，"
                    f"目前 {count} 字",
                    page.page_type,
                )

        for section_index, section in enumerate(page.sections):
            if not section.text.strip():
                record(
                    f"{page.page_type} {section.label} 內容不可空白",
                    page.page_type,
                )
            hard_limits = pages.SECTION_HARD_LIMITS.get(page.page_type, ())
            if section_index < len(hard_limits):
                hard_limit = hard_limits[section_index]
                section_chars = len("".join(section.text.split()))
                if section_chars > hard_limit:
                    record(
                        f"{page.page_type} {section.label} 最多 {hard_limit} 字，"
                        f"目前 {section_chars} 字",
                        page.page_type,
                    )
            unknown = set(section.source_ids) - known_sources
            if unknown:
                record(
                    f"引用不存在的來源：{', '.join(sorted(unknown))}",
                    page.page_type,
                )
            may_be_unsourced = section.label == "互動邀請"
            if not section.source_ids and not may_be_unsourced:
                record(
                    f"{section.label} 是事實區塊，必須附來源",
                    page.page_type,
                )

    cta_page = next(
        (page for page in draft.pages if page.page_type == "cta"),
        None,
    )
    if cta_page is not None:
        cta = "\n".join(section.text for section in cta_page.sections)
        if cta != pages.CTA_TEXT:
            record("第 6 頁必須使用固定品牌文案", "cta")
        if any(
            word in cta
            for word in ("試用", "註冊", "下載", "投資", "官網看看")
        ):
            record("第 6 頁只能邀請按讚或追蹤", "cta")

    if errors:
        raise DraftValidationError(draft, tuple(errors))


def validate_grounded_draft(draft: CarouselDraft) -> None:
    """Require every factual section to cite a verbatim source excerpt."""
    validate_draft(draft)
    sources = {source.source_id: source for source in draft.sources}
    errors: list[tuple[str | None, str]] = []
    may_be_unsourced = {"互動邀請"}

    for page in draft.pages:
        for section in page.sections:
            if section.label not in may_be_unsourced and not section.evidence_quotes:
                errors.append(
                    (
                        page.page_type,
                        f"{section.label} 是事實區塊，必須附查證引文",
                    )
                )
                continue
            evidence_ids = tuple(
                dict.fromkeys(item.source_id for item in section.evidence_quotes)
            )
            if section.evidence_quotes and section.source_ids != evidence_ids:
                errors.append(
                    (
                        page.page_type,
                        f"{section.label} 的來源 ID 必須由查證引文產生",
                    )
                )
            for evidence in section.evidence_quotes:
                source = sources.get(evidence.source_id)
                if source is None:
                    errors.append(
                        (
                            page.page_type,
                            f"引用不存在的來源：{evidence.source_id}",
                        )
                    )
                elif not evidence.quote.strip():
                    errors.append(
                        (
                            page.page_type,
                            f"{evidence.source_id} 查證引文不可空白",
                        )
                    )
                elif evidence.quote not in source.excerpt:
                    errors.append(
                        (
                            page.page_type,
                            f"查證引文不在 {evidence.source_id} 原文",
                        )
                    )

    if errors:
        raise DraftValidationError(draft, tuple(errors))
