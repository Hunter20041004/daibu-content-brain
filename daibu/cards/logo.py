import base64
from datetime import date
from io import BytesIO
import re
from urllib.parse import urlparse
from xml.etree import ElementTree

from PIL import Image

from daibu.cards.schema import BrandAsset


_URL_REFERENCE = re.compile(r"""url\(\s*(['"]?)(.*?)\1\s*\)""", re.IGNORECASE)
_ALLOWED_SVG_TAGS = {
    "svg",
    "g",
    "defs",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "lineargradient",
    "radialgradient",
    "stop",
    "clippath",
    "mask",
    "pattern",
    "marker",
    "symbol",
    "use",
    "title",
    "desc",
    "text",
    "tspan",
}
_ALLOWED_SVG_ATTRIBUTES = {
    "id",
    "class",
    "version",
    "x",
    "y",
    "x1",
    "y1",
    "x2",
    "y2",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "width",
    "height",
    "viewbox",
    "preserveaspectratio",
    "d",
    "points",
    "transform",
    "fill",
    "fill-opacity",
    "fill-rule",
    "stroke",
    "stroke-width",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-miterlimit",
    "stroke-dasharray",
    "stroke-dashoffset",
    "stroke-opacity",
    "opacity",
    "offset",
    "stop-color",
    "stop-opacity",
    "gradientunits",
    "gradienttransform",
    "spreadmethod",
    "clip-path",
    "clip-rule",
    "mask",
    "maskunits",
    "maskcontentunits",
    "patternunits",
    "patterncontentunits",
    "patterntransform",
    "marker-start",
    "marker-mid",
    "marker-end",
    "markerwidth",
    "markerheight",
    "refx",
    "refy",
    "orient",
    "href",
    "role",
    "aria-label",
    "aria-hidden",
    "focusable",
    "vector-effect",
    "font-family",
    "font-size",
    "font-weight",
    "letter-spacing",
    "text-anchor",
    "dominant-baseline",
}


class BrandAssetRequired(ValueError):
    pass


class InvalidBrandAsset(ValueError):
    pass


def _local_name(value: str) -> str:
    return value.rsplit("}", maxsplit=1)[-1].lower()


def _validate_svg(data: bytes) -> None:
    if b"<!doctype" in data.lower() or b"<!entity" in data.lower():
        raise InvalidBrandAsset("SVG Logo 含不安全宣告")
    try:
        if next(
            ElementTree.iterparse(BytesIO(data), events=("pi",)),
            None,
        ):
            raise InvalidBrandAsset("SVG Logo 含不安全處理指令")
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        raise InvalidBrandAsset("SVG Logo 無法解析") from error
    if _local_name(root.tag) != "svg":
        raise InvalidBrandAsset("SVG Logo 根節點必須是 svg")

    for element in root.iter():
        if _local_name(element.tag) not in _ALLOWED_SVG_TAGS:
            raise InvalidBrandAsset("SVG Logo 含不安全內容")
        for name, value in element.attrib.items():
            local_name = _local_name(name)
            normalized = value.strip().casefold()
            if local_name not in _ALLOWED_SVG_ATTRIBUTES:
                raise InvalidBrandAsset("SVG Logo 含不安全屬性")
            if local_name in {"href", "src"} and not normalized.startswith("#"):
                raise InvalidBrandAsset("SVG Logo 不可載入外部資源")
            references = _URL_REFERENCE.findall(normalized)
            if "url(" in normalized and (
                not references
                or any(not target.strip().startswith("#") for _, target in references)
            ):
                raise InvalidBrandAsset("SVG Logo 不可載入外部資源")


def _validate_png(data: bytes) -> None:
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format != "PNG":
                raise InvalidBrandAsset("PNG Logo 檔案格式不正確")
            has_transparency = (
                "A" in image.getbands() or "transparency" in image.info
            )
            image.verify()
    except (OSError, SyntaxError, ValueError) as error:
        raise InvalidBrandAsset("PNG Logo 檔案格式不正確") from error
    if not has_transparency:
        raise InvalidBrandAsset("PNG Logo 必須保留透明色版")


def _validate_metadata(asset: BrandAsset, company: str) -> None:
    if asset.company.strip().casefold() != company.strip().casefold():
        raise InvalidBrandAsset("Logo 公司名稱與輪播公司不符")
    source = urlparse(asset.official_source_url)
    if source.scheme != "https" or not source.netloc:
        raise InvalidBrandAsset("Logo 必須保留官方 https 來源網址")
    try:
        date.fromisoformat(asset.verified_at)
    except ValueError as error:
        raise InvalidBrandAsset("Logo 確認日期必須是 YYYY-MM-DD") from error
    if not asset.local_path.is_file():
        raise InvalidBrandAsset("找不到已確認的 Logo 檔案")


def logo_data_uri(
    asset: BrandAsset | None,
    company: str,
) -> str:
    if asset is None:
        raise BrandAssetRequired("請提供或確認官方 Logo")
    _validate_metadata(asset, company)
    suffix = asset.local_path.suffix.lower()
    data = asset.local_path.read_bytes()
    if suffix == ".png":
        _validate_png(data)
        mime = "image/png"
    elif suffix == ".svg":
        _validate_svg(data)
        mime = "image/svg+xml"
    else:
        raise InvalidBrandAsset("Logo 只接受 SVG 或透明 PNG")
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"
