"""Find a logo candidate only through pages on a possible official website."""

import re
import ssl
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from html import escape as html_escape
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

import certifi

from daibu.cards import logo
from daibu.fetch import company_research, search
from daibu.models import Material

MAX_OFFICIAL_PAGES = 3
MAX_HTML_BYTES = 1_048_576
_BRAND_MARKERS = ("brand", "press", "media", "asset")
_BLOCKED_DOMAINS = (
    *company_research.TRUSTED_EDITORIAL_DOMAINS,
    "crunchbase.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "wikipedia.org",
    "x.com",
    "youtube.com",
)


class LogoDiscoveryError(ValueError):
    pass


@dataclass(frozen=True)
class LogoCandidate:
    company: str
    filename: str
    data: bytes
    official_page_url: str
    asset_url: str


class _OfficialPageParser(HTMLParser):
    def __init__(self, page_url: str, company: str) -> None:
        super().__init__()
        self.page_url = page_url
        self.company = company
        self.logo_urls: list[tuple[int, str]] = []
        self.inline_logos: list[tuple[int, str]] = []
        self.brand_page_urls: list[str] = []
        self._inline_parts: list[str] | None = None
        self._inline_depth = 0
        self._inline_score = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {name.casefold(): value or "" for name, value in attrs}
        if self._inline_parts is not None:
            self._inline_parts.append(self.get_starttag_text() or f"<{tag}>")
            if tag == "svg":
                self._inline_depth += 1
            return
        if tag == "svg":
            description = " ".join(
                values.get(name, "")
                for name in (
                    "aria-label",
                    "title",
                    "class",
                    "id",
                    "data-testid",
                )
            )
            normalized_description = _normalized(description)
            if (
                "logo" in description.casefold()
                or _normalized(self.company) in normalized_description
            ):
                self._inline_score = _logo_score(description)
                self._inline_parts = [
                    self.get_starttag_text() or "<svg>"
                ]
                self._inline_depth = 1
                return
        if tag == "img" and values.get("src"):
            description = " ".join(
                values.get(name, "")
                for name in ("alt", "title", "class", "id", "src")
            )
            if "logo" in description.casefold() or _normalized(
                self.company
            ) in _normalized(description):
                self.logo_urls.append(
                    (
                        _logo_score(description),
                        urljoin(self.page_url, values["src"]),
                    )
                )
        if tag == "a" and values.get("href"):
            target = urljoin(self.page_url, values["href"])
            path = urlparse(target).path.casefold()
            if any(marker in path for marker in _BRAND_MARKERS):
                self.brand_page_urls.append(target)

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if self._inline_parts is not None:
            self._inline_parts.append(self.get_starttag_text() or f"<{tag}/>")
            return
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if self._inline_parts is None:
            return
        self._inline_parts.append(f"</{tag}>")
        if tag == "svg":
            self._inline_depth -= 1
            if self._inline_depth == 0:
                self.inline_logos.append(
                    (self._inline_score, "".join(self._inline_parts))
                )
                self._inline_parts = None

    def handle_data(self, data: str) -> None:
        if self._inline_parts is not None:
            self._inline_parts.append(html_escape(data))

    def handle_entityref(self, name: str) -> None:
        if self._inline_parts is not None:
            self._inline_parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._inline_parts is not None:
            self._inline_parts.append(f"&#{name};")


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9一-鿿]+", "", value.casefold())


def _logo_score(description: str) -> int:
    descriptor = description.casefold()
    score = 0
    if "white" in descriptor or "logo-light" in descriptor:
        score -= 2
    if "dark" in descriptor or "logo-dark" in descriptor:
        score += 1
    return score


def _hostname(value: str) -> str:
    return (urlparse(value).hostname or "").casefold().removeprefix("www.")


def _same_site(first: str, second: str) -> bool:
    return _hostname(first) == _hostname(second)


def _is_blocked(value: str) -> bool:
    hostname = _hostname(value)
    return any(
        hostname == blocked or hostname.endswith(f".{blocked}")
        for blocked in _BLOCKED_DOMAINS
    )


def _looks_like_company_site(company: str, material: Material) -> bool:
    needle = _normalized(company)
    hostname_labels = {
        _normalized(label) for label in _hostname(material.url).split(".")
    }
    return bool(needle and needle in hostname_labels)


def _request(url: str) -> Request:
    return Request(url, headers={"User-Agent": "daibu-content-brain/1.0"})


def _download_html(url: str) -> str:
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(_request(url), timeout=15, context=context) as response:
        return response.read(MAX_HTML_BYTES).decode("utf-8", errors="replace")


def _download_asset(url: str) -> tuple[bytes, str]:
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(_request(url), timeout=15, context=context) as response:
        content_type = response.headers.get_content_type()
        return response.read(logo.MAX_FILE_BYTES + 1), content_type


def _filename(asset_url: str, content_type: str, company: str) -> str:
    name = PurePosixPath(urlparse(asset_url).path).name
    suffix = PurePosixPath(name).suffix.casefold()
    if suffix not in {".svg", ".png"}:
        suffix = {
            "image/svg+xml": ".svg",
            "image/png": ".png",
        }.get(content_type, "")
    if not suffix:
        raise logo.InvalidBrandAsset("Logo 只接受 SVG 或透明 PNG")
    stem = PurePosixPath(name).stem or f"{_normalized(company)}-logo"
    return f"{stem}{suffix}"


def _parse_page(
    page_url: str,
    company: str,
    html: str,
) -> _OfficialPageParser:
    parser = _OfficialPageParser(page_url, company)
    parser.feed(html)
    return parser


def _safe_inline_svg(raw_svg: str, company: str) -> tuple[bytes, str]:
    try:
        root = ElementTree.fromstring(raw_svg)
    except ElementTree.ParseError as error:
        raise logo.InvalidBrandAsset("內嵌 SVG 無法解析") from error
    for element in root.iter():
        if logo._local_name(element.tag) not in logo._ALLOWED_SVG_TAGS:
            raise logo.InvalidBrandAsset("SVG Logo 含不安全內容")
        for name in tuple(element.attrib):
            if logo._local_name(name) not in logo._ALLOWED_SVG_ATTRIBUTES:
                del element.attrib[name]
    if not root.tag.startswith("{"):
        root.set("xmlns", "http://www.w3.org/2000/svg")
    data = ElementTree.tostring(root, encoding="utf-8")
    filename = f"{_normalized(company) or 'company'}-inline-logo.svg"
    logo.validate_upload(data, filename)
    return data, filename


def discover(
    company: str,
    *,
    search_fn: Callable[[str, int], list[Material]] | None = None,
    html_fetch_fn: Callable[[str], str] | None = None,
    asset_fetch_fn: Callable[[str], tuple[bytes, str]] | None = None,
    excluded_asset_urls: Iterable[str] = (),
) -> LogoCandidate:
    """Return one unconfirmed candidate; never persist it."""
    if not company.strip():
        raise LogoDiscoveryError("沒有公司名稱，無法搜尋官方 Logo。")
    do_search = search_fn or search.search_web
    fetch_html = html_fetch_fn or _download_html
    fetch_asset = asset_fetch_fn or _download_asset
    excluded = set(excluded_asset_urls)
    query = f'"{company}" official website logo brand assets'

    try:
        results = do_search(query, 5)
        if not results:
            results = do_search(f'"{company}" official website', 5)
    except (OSError, RuntimeError, ValueError) as error:
        raise LogoDiscoveryError(str(error)) from error

    failures: list[str] = []
    for material in results:
        parsed = urlparse(material.url)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or _is_blocked(material.url)
            or not _looks_like_company_site(company, material)
        ):
            continue
        page_urls = [material.url]
        visited: set[str] = set()
        while page_urls and len(visited) < MAX_OFFICIAL_PAGES:
            page_url = page_urls.pop(0)
            if page_url in visited or not _same_site(page_url, material.url):
                continue
            visited.add(page_url)
            try:
                parser = _parse_page(
                    page_url,
                    company,
                    fetch_html(page_url),
                )
            except (OSError, UnicodeError, ValueError) as error:
                failures.append(f"{page_url}：{error}")
                continue
            page_urls.extend(
                url
                for url in parser.brand_page_urls
                if url not in visited and _same_site(url, material.url)
            )
            for index, (_, raw_svg) in enumerate(
                sorted(
                    parser.inline_logos,
                    key=lambda candidate: candidate[0],
                    reverse=True,
                ),
                start=1,
            ):
                page_base_url = page_url.split("#", maxsplit=1)[0]
                asset_url = f"{page_base_url}#inline-logo-{index}"
                if asset_url in excluded:
                    continue
                try:
                    data, filename = _safe_inline_svg(raw_svg, company)
                except ValueError as error:
                    failures.append(f"{asset_url}：{error}")
                    continue
                return LogoCandidate(
                    company.strip(),
                    filename,
                    data,
                    page_url,
                    asset_url,
                )
            for _, asset_url in sorted(
                parser.logo_urls,
                key=lambda candidate: candidate[0],
                reverse=True,
            ):
                asset = urlparse(asset_url)
                if (
                    asset_url in excluded
                    or asset.scheme != "https"
                    or not asset.netloc
                ):
                    continue
                try:
                    data, content_type = fetch_asset(asset_url)
                    filename = _filename(asset_url, content_type, company)
                    logo.validate_upload(data, filename)
                except (OSError, ValueError) as error:
                    failures.append(f"{asset_url}：{error}")
                    continue
                return LogoCandidate(
                    company.strip(),
                    filename,
                    data,
                    page_url,
                    asset_url,
                )
    detail = f"（{failures[-1]}）" if failures else ""
    raise LogoDiscoveryError(
        "找不到可安全預覽的官方 SVG 或透明 PNG。"
        "你仍可從公司官網下載後手動上傳。"
        f"{detail}"
    )
