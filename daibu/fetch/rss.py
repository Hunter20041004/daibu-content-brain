import ssl
from html.parser import HTMLParser
from urllib.request import Request, urlopen

import certifi
import feedparser

from daibu.models import Material


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _download(url: str) -> str:
    request = Request(url, headers={"User-Agent": "daibu-content-brain/1.0"})
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(request, timeout=15, context=ssl_context) as response:
        return response.read().decode("utf-8", errors="replace")


def _plain_text(value: str, limit: int = 500) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    return " ".join("".join(parser.parts).split())[:limit]


def fetch(url: str, limit: int = 10) -> list[Material]:
    parsed = feedparser.parse(_download(url))
    return [
        Material(
            title=str(entry.get("title", "")),
            url=str(entry.get("link", "")),
            snippet=_plain_text(str(entry.get("summary", ""))),
        )
        for entry in parsed.entries[:limit]
    ]
