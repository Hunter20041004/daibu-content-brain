"""Find a logo candidate only through pages on a possible official website."""

import json
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
from daibu.cards.official_site import OfficialSite
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
    official_site_url: str = ""
    source_kind: str = "official_site"
    logo_kind: str = "logo"
    theme: str = "unknown"
    confidence: str = "high"
    reasons: tuple[str, ...] = ()


class _OfficialPageParser(HTMLParser):
    def __init__(self, page_url: str, company: str) -> None:
        super().__init__()
        self.page_url = page_url
        self.company = company
        self.logo_urls: list[tuple[int, str, str]] = []
        self.inline_logos: list[tuple[int, str]] = []
        self.brand_page_urls: list[str] = []
        self._inline_parts: list[str] | None = None
        self._inline_depth = 0
        self._inline_score = 0
        self._json_ld_parts: list[str] | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {name.casefold(): value or "" for name, value in attrs}
        if tag == "script" and values.get("type").casefold() == "application/ld+json":
            self._json_ld_parts = []
            return
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
        if tag == "img" and (values.get("src") or values.get("srcset")):
            description = " ".join(
                values.get(name, "")
                for name in (
                    "alt",
                    "title",
                    "class",
                    "id",
                    "src",
                    "srcset",
                )
            )
            if "logo" in description.casefold() or _normalized(
                self.company
            ) in _normalized(description):
                source = values.get("src", "")
                if values.get("srcset"):
                    variants = [
                        item.strip().split()[0]
                        for item in values["srcset"].split(",")
                        if item.strip()
                    ]
                    if variants:
                        source = variants[-1]
                self.logo_urls.append(
                    (
                        _logo_score(description),
                        urljoin(self.page_url, source),
                        description,
                    )
                )
        style = values.get("style", "")
        description = " ".join(
            values.get(name, "")
            for name in ("aria-label", "title", "class", "id")
        )
        background = re.search(
            r"background(?:-image)?\s*:\s*url\(\s*['\"]?([^'\")]+)",
            style,
            flags=re.IGNORECASE,
        )
        if background and (
            "logo" in description.casefold()
            or "brand" in description.casefold()
            or _normalized(self.company) in _normalized(description)
        ):
            self.logo_urls.append(
                (
                    _logo_score(description),
                    urljoin(self.page_url, background.group(1)),
                    description,
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
        if tag == "script" and self._json_ld_parts is not None:
            try:
                payload = json.loads("".join(self._json_ld_parts))
            except (json.JSONDecodeError, TypeError, ValueError):
                payload = None
            self._json_ld_parts = None
            if isinstance(payload, dict) and payload.get("logo"):
                description = "Organization.logo company logo"
                self.logo_urls.append(
                    (
                        _logo_score(description),
                        urljoin(self.page_url, str(payload["logo"])),
                        description,
                    )
                )
            return
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
        if self._json_ld_parts is not None:
            self._json_ld_parts.append(data)
            return
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


def _logo_kind(description: str) -> str:
    descriptor = description.casefold()
    if "symbol" in descriptor or "brand-mark" in descriptor:
        return "symbol"
    if "icon" in descriptor or "app" in descriptor:
        return "icon"
    return "logo"


def _logo_theme(description: str) -> str:
    descriptor = description.casefold()
    if "white" in descriptor or "light" in descriptor:
        return "light"
    if "dark" in descriptor:
        return "dark"
    return "unknown"


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


def extract_candidates(
    site: OfficialSite,
    *,
    html_fetch_fn: Callable[[str], str] | None = None,
    asset_fetch_fn: Callable[[str], tuple[bytes, str]] | None = None,
    excluded_asset_urls: Iterable[str] = (),
) -> tuple[LogoCandidate, ...]:
    """Collect up to three distinct, safe Logo forms from one official site."""
    fetch_html = html_fetch_fn or _download_html
    fetch_asset = asset_fetch_fn or _download_asset
    excluded = set(excluded_asset_urls)
    page_urls = [site.website_url]
    visited: set[str] = set()
    seen_assets: set[str] = set()
    candidates: list[tuple[int, LogoCandidate]] = []

    while page_urls and len(visited) < MAX_OFFICIAL_PAGES:
        page_url = page_urls.pop(0)
        if page_url in visited or not _same_site(page_url, site.website_url):
            continue
        visited.add(page_url)
        try:
            parser = _parse_page(page_url, site.company, fetch_html(page_url))
        except (OSError, UnicodeError, ValueError):
            continue
        page_urls.extend(
            url
            for url in parser.brand_page_urls
            if url not in visited and _same_site(url, site.website_url)
        )
        for index, (score, raw_svg) in enumerate(
            sorted(
                parser.inline_logos,
                key=lambda item: item[0],
                reverse=True,
            ),
            start=1,
        ):
            page_base_url = page_url.split("#", maxsplit=1)[0]
            asset_url = f"{page_base_url}#inline-logo-{index}"
            if asset_url in excluded or asset_url in seen_assets:
                continue
            seen_assets.add(asset_url)
            try:
                data, filename = _safe_inline_svg(raw_svg, site.company)
            except ValueError:
                continue
            candidates.append(
                (
                    score,
                    LogoCandidate(
                        site.company,
                        filename,
                        data,
                        page_url,
                        asset_url,
                        site.website_url,
                        "official_site",
                        "logo",
                        "unknown",
                        "high",
                        ("官網內嵌 SVG",),
                    ),
                )
            )
        for score, asset_url, description in sorted(
            parser.logo_urls,
            key=lambda item: item[0],
            reverse=True,
        ):
            if asset_url in excluded or asset_url in seen_assets:
                continue
            seen_assets.add(asset_url)
            parsed = urlparse(asset_url)
            if parsed.scheme != "https" or not parsed.netloc:
                continue
            try:
                data, content_type = fetch_asset(asset_url)
                filename = _filename(asset_url, content_type, site.company)
                logo.validate_upload(data, filename)
            except (OSError, ValueError):
                continue
            kind = _logo_kind(description)
            candidates.append(
                (
                    score,
                    LogoCandidate(
                        site.company,
                        filename,
                        data,
                        page_url,
                        asset_url,
                        site.website_url,
                        "official_site",
                        kind,
                        _logo_theme(description),
                        "high",
                        (
                            "Organization.logo"
                            if "organization.logo" in description.casefold()
                            else "官網頁面直接引用",
                        ),
                    ),
                )
            )

    best_by_kind: dict[str, tuple[int, LogoCandidate]] = {}
    for item in candidates:
        kind = item[1].logo_kind
        if kind not in best_by_kind or item[0] > best_by_kind[kind][0]:
            best_by_kind[kind] = item
    return tuple(
        best_by_kind[kind][1]
        for kind in ("logo", "symbol", "icon")
        if kind in best_by_kind
    )[:3]


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
            for _, asset_url, _description in sorted(
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
