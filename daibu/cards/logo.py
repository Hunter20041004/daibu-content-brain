import base64
from datetime import date
from urllib.parse import urlparse
from xml.etree import ElementTree

from daibu.cards.schema import BrandAsset


class BrandAssetRequired(ValueError):
    pass


class InvalidBrandAsset(ValueError):
    pass


def _local_name(value: str) -> str:
    return value.rsplit("}", maxsplit=1)[-1].lower()


def _validate_svg(data: bytes) -> None:
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        raise InvalidBrandAsset("SVG Logo 無法解析") from error
    if _local_name(root.tag) != "svg":
        raise InvalidBrandAsset("SVG Logo 根節點必須是 svg")

    blocked_tags = {"script", "foreignobject", "iframe", "object", "embed"}
    for element in root.iter():
        if _local_name(element.tag) in blocked_tags:
            raise InvalidBrandAsset("SVG Logo 含不安全內容")
        for name, value in element.attrib.items():
            local_name = _local_name(name)
            if local_name.startswith("on"):
                raise InvalidBrandAsset("SVG Logo 含不安全事件")
            if local_name in {"href", "src"} and (
                value.startswith("http:") or value.startswith("https:")
            ):
                raise InvalidBrandAsset("SVG Logo 不可載入外部資源")


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
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise InvalidBrandAsset("PNG Logo 檔案格式不正確")
        mime = "image/png"
    elif suffix == ".svg":
        _validate_svg(data)
        mime = "image/svg+xml"
    else:
        raise InvalidBrandAsset("Logo 只接受 SVG 或透明 PNG")
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"
