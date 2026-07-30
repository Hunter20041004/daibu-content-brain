import base64
from datetime import date
from io import BytesIO
from pathlib import Path
import re
import warnings
from urllib.parse import urlparse
from xml.etree import ElementTree

from PIL import Image

from daibu.cards.schema import BrandAsset

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_EDGE_PX = 4096
MAX_TOTAL_PX = 8_000_000
MIN_EDGE_PX = 64
Image.MAX_IMAGE_PIXELS = MAX_TOTAL_PX


_LOCAL_FRAGMENT = re.compile(r"#[A-Za-z0-9_.:-]+")
_LOCAL_URL_REFERENCE = re.compile(
    r"""url\(\s*(['"]?)#[A-Za-z0-9_.:-]+\1\s*\)""",
    re.IGNORECASE,
)
_SAFE_COLOR_FUNCTION = re.compile(
    r"(?:rgb|rgba|hsl|hsla)\([0-9.,%\s+-]+\)",
    re.IGNORECASE,
)
_URL_CAPABLE_ATTRIBUTES = {
    "fill",
    "stroke",
    "clip-path",
    "mask",
    "marker-start",
    "marker-mid",
    "marker-end",
}
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


def validate_upload(data: bytes, filename: str) -> None:
    if len(data) > MAX_FILE_BYTES:
        size_mb = len(data) / (1024 * 1024)
        raise InvalidBrandAsset(
            f"這個檔案 {size_mb:.1f} MB，超過 2 MB 上限。"
            "請改用官方品牌素材包裡的 SVG 或去背 PNG。"
        )
    suffix = Path(filename).suffix.lower()
    if suffix not in {".png", ".svg"}:
        raise InvalidBrandAsset(
            "只接受 SVG 或去背 PNG。JPG 沒有透明背景，"
            "貼上會出現白色方塊。"
        )
    if suffix == ".png":
        try:
            with warnings.catch_warnings():
                warnings.simplefilter(
                    "ignore",
                    Image.DecompressionBombWarning,
                )
                with Image.open(BytesIO(data)) as image:
                    width, height = image.size
        except Image.DecompressionBombError as error:
            raise InvalidBrandAsset(
                "圖片總像素超過 800 萬，解開後會佔用太多記憶體。"
                "請改用官方素材包裡較小的版本。"
            ) from error
        except (OSError, SyntaxError, ValueError) as error:
            raise InvalidBrandAsset("PNG Logo 檔案格式不正確") from error
        if max(width, height) > MAX_EDGE_PX:
            raise InvalidBrandAsset(
                f"圖片解析度 {width}×{height}，超過 4096 px 上限。"
                "請用官方素材包裡較小的版本，或先縮到 2048 px 以內。"
            )
        if width * height > MAX_TOTAL_PX:
            raise InvalidBrandAsset(
                "圖片總像素超過 800 萬，解開後會佔用太多記憶體。"
                "請改用官方素材包裡較小的版本。"
            )
        if min(width, height) < MIN_EDGE_PX:
            raise InvalidBrandAsset(
                f"圖片只有 {width}×{height}，看起來是網站小圖示。"
                "請上傳至少 64 px 的官方 Logo。"
            )
        _validate_png(data)
    else:
        _validate_svg(data)
        root = ElementTree.fromstring(data)
        attributes = {
            _local_name(name): value
            for name, value in root.attrib.items()
        }
        has_box = bool(attributes.get("viewbox", "").strip())
        has_dimensions = bool(attributes.get("width", "").strip()) and bool(
            attributes.get("height", "").strip()
        )
        if not has_box and not has_dimensions:
            raise InvalidBrandAsset(
                "這個 SVG 沒有 viewBox 或寬高，排版時會變形。"
                "請用官方素材包裡的完整版本。"
            )


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
            if "\\" in normalized or "/*" in normalized or "*/" in normalized:
                raise InvalidBrandAsset("SVG Logo 含不安全編碼")
            if local_name == "href" and not _LOCAL_FRAGMENT.fullmatch(normalized):
                raise InvalidBrandAsset("SVG Logo 不可載入外部資源")
            if "url" in normalized and not _LOCAL_URL_REFERENCE.fullmatch(
                normalized
            ):
                raise InvalidBrandAsset("SVG Logo 不可載入外部資源")
            if (
                local_name in _URL_CAPABLE_ATTRIBUTES
                and ("(" in normalized or ")" in normalized)
                and not _LOCAL_URL_REFERENCE.fullmatch(normalized)
                and not (
                    local_name in {"fill", "stroke"}
                    and _SAFE_COLOR_FUNCTION.fullmatch(normalized)
                )
            ):
                raise InvalidBrandAsset("SVG Logo 含不安全屬性值")


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
    validate_source_metadata(asset.official_source_url, asset.verified_at)
    if not asset.local_path.is_file():
        raise InvalidBrandAsset("找不到已確認的 Logo 檔案")


def validate_source_metadata(
    official_source_url: str,
    verified_at: str,
) -> None:
    source = urlparse(official_source_url)
    if source.scheme != "https" or not source.netloc:
        raise InvalidBrandAsset("Logo 必須保留官方 https 來源網址")
    try:
        date.fromisoformat(verified_at)
    except ValueError as error:
        raise InvalidBrandAsset("Logo 確認日期必須是 YYYY-MM-DD") from error


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
