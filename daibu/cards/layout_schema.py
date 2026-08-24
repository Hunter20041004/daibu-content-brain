from dataclasses import dataclass
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from daibu.cards.layout_registry import registry_for_schema
from daibu.cards.layout_upgrade import normalize_layout_mapping


CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1350


class LayoutValidationError(ValueError):
    def __init__(self, element_id: str | None, message: str) -> None:
        self.element_id = element_id
        super().__init__(message)


@dataclass(frozen=True)
class LayoutRect:
    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class TextStyle:
    font_size: float
    text_align: str


@dataclass(frozen=True)
class LayoutElement:
    rect: LayoutRect
    text_style: TextStyle | None = None


@dataclass(frozen=True)
class LayoutPage:
    elements: Mapping[str, LayoutElement]


@dataclass(frozen=True)
class LayoutDocument:
    schema_version: int
    canvas_width: int
    canvas_height: int
    pages: Mapping[str, LayoutPage]


def load_builtin_layout() -> LayoutDocument:
    layout_path = Path(__file__).with_name("layouts") / "editorial-v15-1.json"
    return parse_layout(json.loads(layout_path.read_text(encoding="utf-8")))


def layout_to_mapping(document: LayoutDocument) -> dict[str, object]:
    pages: dict[str, object] = {}
    for page_type, page in document.pages.items():
        elements: dict[str, object] = {}
        for element_id, element in page.elements.items():
            raw_element: dict[str, object] = {
                "x": element.rect.x,
                "y": element.rect.y,
                "w": element.rect.w,
                "h": element.rect.h,
            }
            if element.text_style is not None:
                raw_element.update(
                    {
                        "font_size": element.text_style.font_size,
                        "text_align": element.text_style.text_align,
                    }
                )
            elements[element_id] = raw_element
        pages[page_type] = {"elements": elements}
    return {
        "schema_version": document.schema_version,
        "canvas": {
            "width": document.canvas_width,
            "height": document.canvas_height,
        },
        "pages": pages,
    }


def replace_element(
    document: LayoutDocument,
    page_type: str,
    element_id: str,
    **changes: object,
) -> LayoutDocument:
    raw_layout = layout_to_mapping(document)
    raw_pages = raw_layout["pages"]
    assert isinstance(raw_pages, dict)
    if page_type not in raw_pages:
        raise LayoutValidationError(None, f"未知頁型：{page_type}")
    raw_page = raw_pages[page_type]
    assert isinstance(raw_page, dict)
    raw_elements = raw_page["elements"]
    assert isinstance(raw_elements, dict)
    if element_id not in raw_elements:
        raise LayoutValidationError(element_id, f"未知版面元素：{element_id}")
    raw_element = raw_elements[element_id]
    assert isinstance(raw_element, dict)
    raw_element.update(changes)
    return parse_layout(raw_layout)


def _finite_number(value: object, element_id: str, field: str) -> float:
    if isinstance(value, bool):
        raise LayoutValidationError(element_id, f"{element_id} {field} 必須是有限數字")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise LayoutValidationError(
            element_id,
            f"{element_id} {field} 必須是有限數字",
        ) from error
    if not math.isfinite(number):
        raise LayoutValidationError(element_id, f"{element_id} {field} 必須是有限數字")
    return number


def parse_layout(value: Mapping[str, object]) -> LayoutDocument:
    value = normalize_layout_mapping(value)
    unknown_properties = set(value) - {"schema_version", "canvas", "pages"}
    if unknown_properties:
        unknown = sorted(str(item) for item in unknown_properties)[0]
        raise LayoutValidationError(None, f"版面含不允許的屬性：{unknown}")
    schema_version = value.get("schema_version")
    if schema_version not in {1, 2}:
        raise LayoutValidationError(None, "不支援的 schema_version")
    registry = registry_for_schema(int(schema_version))
    raw_canvas = value.get("canvas")
    if not isinstance(raw_canvas, Mapping):
        raise LayoutValidationError(None, "版面缺少 canvas")
    unknown_canvas_properties = set(raw_canvas) - {"width", "height"}
    if unknown_canvas_properties:
        unknown = sorted(str(item) for item in unknown_canvas_properties)[0]
        raise LayoutValidationError(None, f"canvas 含不允許的屬性：{unknown}")
    if (
        raw_canvas.get("width") != CANVAS_WIDTH
        or raw_canvas.get("height") != CANVAS_HEIGHT
    ):
        raise LayoutValidationError(None, "版面畫布必須是 1080×1350")

    raw_pages = value.get("pages")
    if not isinstance(raw_pages, Mapping):
        raise LayoutValidationError(None, "版面缺少 pages")

    parsed_pages: dict[str, LayoutPage] = {}
    for page_type, raw_page in raw_pages.items():
        if not isinstance(page_type, str) or page_type not in registry:
            raise LayoutValidationError(None, f"未知頁型：{page_type}")
        if not isinstance(raw_page, Mapping):
            raise LayoutValidationError(None, f"{page_type} 頁版面必須是物件")
        unknown_page_properties = set(raw_page) - {"elements"}
        if unknown_page_properties:
            unknown = sorted(str(item) for item in unknown_page_properties)[0]
            raise LayoutValidationError(
                None,
                f"{page_type} 頁含不允許的屬性：{unknown}",
            )
        raw_elements = raw_page.get("elements")
        if not isinstance(raw_elements, Mapping):
            raise LayoutValidationError(None, f"{page_type} 頁缺少 elements")

        parsed_elements: dict[str, LayoutElement] = {}
        for element_id, raw_element in raw_elements.items():
            if not isinstance(element_id, str) or element_id not in registry[page_type]:
                raise LayoutValidationError(
                    element_id if isinstance(element_id, str) else None,
                    f"未知版面元素：{element_id}",
                )
            if not isinstance(raw_element, Mapping):
                raise LayoutValidationError(element_id, f"{element_id} 必須是物件")
            rule = registry[page_type][element_id]
            allowed_properties = {"x", "y", "w", "h"}
            if rule.text:
                allowed_properties.update({"font_size", "text_align"})
            unknown_properties = set(raw_element) - allowed_properties
            if unknown_properties:
                unknown = sorted(str(item) for item in unknown_properties)[0]
                raise LayoutValidationError(
                    element_id,
                    f"{element_id} 含不允許的屬性：{unknown}",
                )
            rect = LayoutRect(
                _finite_number(raw_element.get("x"), element_id, "x"),
                _finite_number(raw_element.get("y"), element_id, "y"),
                _finite_number(raw_element.get("w"), element_id, "w"),
                _finite_number(raw_element.get("h"), element_id, "h"),
            )
            if rect.w <= 0 or rect.h <= 0:
                raise LayoutValidationError(element_id, f"{element_id} 尺寸必須大於 0")
            if rect.w < rule.min_w or rect.h < rule.min_h:
                raise LayoutValidationError(
                    element_id,
                    f"{element_id} 小於登錄的最小尺寸",
                )
            if (
                rect.x < 0
                or rect.y < 0
                or rect.x + rect.w > CANVAS_WIDTH
                or rect.y + rect.h > CANVAS_HEIGHT
            ):
                raise LayoutValidationError(element_id, f"{element_id} 必須完整留在畫布內")
            text_style = (
                TextStyle(
                    _finite_number(
                        raw_element.get("font_size", rule.min_font_size),
                        element_id,
                        "font_size",
                    ),
                    str(raw_element.get("text_align", "left")),
                )
                if rule.text
                else None
            )
            if text_style is not None and text_style.text_align not in {
                "left",
                "center",
                "right",
            }:
                raise LayoutValidationError(element_id, f"{element_id} 對齊方式不受支援")
            if text_style is not None and text_style.font_size < rule.min_font_size:
                raise LayoutValidationError(element_id, f"{element_id} 字級小於可讀下限")
            if text_style is not None and text_style.font_size > rule.max_font_size:
                raise LayoutValidationError(element_id, f"{element_id} 字級超過安全上限")
            parsed_elements[element_id] = LayoutElement(rect, text_style)

        missing_elements = sorted(
            set(registry[page_type]) - set(parsed_elements)
        )
        if missing_elements:
            raise LayoutValidationError(
                missing_elements[0],
                f"{page_type} 頁缺少必要元素：{', '.join(missing_elements)}",
            )
        parsed_pages[page_type] = LayoutPage(MappingProxyType(parsed_elements))

    missing_pages = sorted(set(registry) - set(parsed_pages))
    if missing_pages:
        raise LayoutValidationError(
            None,
            f"版面缺少必要頁型：{', '.join(missing_pages)}",
        )

    return LayoutDocument(
        int(value.get("schema_version", 0)),
        int(raw_canvas.get("width", 0)),
        int(raw_canvas.get("height", 0)),
        MappingProxyType(parsed_pages),
    )
