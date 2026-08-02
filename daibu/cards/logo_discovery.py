"""Find a logo candidate only through pages on a possible official website."""

import re
import ssl
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

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
        self.brand_page_urls: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {name.casefold(): value or "" for name, value in attrs}
        if tag == "img" and values.get("src"):
            description = " ".join(
                values.get(name, "")
                for name in ("alt", "title", "class", "id", "src")
            )
            if "logo" in description.casefold() or _normalized(
                self.company
            ) in _normalized(description):
                descriptor = description.casefold()
                score = 0
                if "white" in descriptor or "logo-light" in descriptor:
                    score -= 2
                if "dark" in descriptor or "logo-dark" in descriptor:
                    score += 1
                self.logo_urls.append(
                    (score, urljoin(self.page_url, values["src"]))
                )
        if tag == "a" and values.get("href"):
            target = urljoin(self.page_url, values["href"])
            path = urlparse(target).path.casefold()
            if any(marker in path for marker in _BRAND_MARKERS):
                self.brand_page_urls.append(target)


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9一-鿿]+", "", value.casefold())


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
    haystack = _normalized(
        f"{material.title} {material.snippet} {_hostname(material.url)}"
    )
    return bool(needle and needle in haystack)


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
