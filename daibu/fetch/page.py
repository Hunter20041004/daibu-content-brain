"""Extract editable source suggestions from a public article page.

This local single-user tool does not block private network addresses.
"""

import ssl
from datetime import date
from html.parser import HTMLParser
from typing import Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import certifi
from daibu.models import SourceSuggestion

_SKIPPED_ELEMENTS = {
    "script",
    "style",
    "nav",
    "footer",
    "aside",
    "form",
    "button",
    "noscript",
    "svg",
}
_SENTENCE_ENDINGS = ("。", "！", "？", ".", "!", "?")


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.publisher = ""
        self.published_at = ""
        self.parts: list[str] = []
        self.main_parts: list[str] = []
        self.article_parts: list[str] = []
        self._skip_depth = 0
        self._main_depth = 0
        self._article_depth = 0
        self._heading_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = dict(attrs)
        if tag in _SKIPPED_ELEMENTS:
            self._skip_depth += 1
        if tag == "main":
            self._main_depth += 1
        if tag == "article":
            self._article_depth += 1
        if tag == "h1":
            self._heading_depth += 1
        if tag == "meta":
            property_name = values.get("property", "")
            if property_name == "og:site_name":
                self.publisher = values.get("content", "") or ""
            elif property_name == "article:published_time":
                self.published_at = values.get("content", "") or ""
        elif tag == "time" and not self.published_at:
            self.published_at = values.get("datetime", "") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED_ELEMENTS and self._skip_depth:
            self._skip_depth -= 1
        if tag == "h1" and self._heading_depth:
            self._heading_depth -= 1
        if tag == "article" and self._article_depth:
            self._article_depth -= 1
        if tag == "main" and self._main_depth:
            self._main_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth and not self._heading_depth:
            self.parts.append(data)
            if self._main_depth:
                self.main_parts.append(data)
            if self._article_depth:
                self.article_parts.append(data)


def _complete_sentence(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    candidate = normalized[:limit]
    sentence_end = max(candidate.rfind(mark) for mark in _SENTENCE_ENDINGS)
    if sentence_end >= 0:
        return candidate[:sentence_end + 1].strip()
    return candidate.rsplit(" ", 1)[0].strip()


def _article_text(parser: _PageParser, limit: int) -> str:
    selected = parser.article_parts or parser.main_parts or parser.parts
    return _complete_sentence("".join(selected), limit)


def extract_article(html: str, limit: int = 1200) -> str:
    parser = _PageParser()
    parser.feed(html)
    return _article_text(parser, limit)


def _valid_date(value: str) -> str:
    candidate = value[:10]
    try:
        date.fromisoformat(candidate)
    except ValueError:
        return ""
    return candidate


def _download(url: str) -> str:
    request = Request(url, headers={"User-Agent": "daibu-content-brain/1.0"})
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=15, context=ssl_context) as response:
        return response.read(1_048_576).decode("utf-8", errors="replace")


def fetch_suggestion(
    url: str,
    download: Callable[[str], str] | None = None,
) -> SourceSuggestion:
    parsed_url = urlparse(url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError("來源網址必須是 https")
    try:
        html = (download or _download)(url)
    except (OSError, UnicodeError) as exc:
        raise ValueError(
            "抓不到這個網址，請確認它公開可讀，或直接手動填寫。"
        ) from exc
    parser = _PageParser()
    parser.feed(html)
    domain = parsed_url.hostname or ""
    if domain.startswith("www."):
        domain = domain[4:]
    return SourceSuggestion(
        publisher=parser.publisher.strip() or domain,
        published_at=_valid_date(parser.published_at.strip()),
        url=url,
        excerpt=_article_text(parser, 1200),
    )
