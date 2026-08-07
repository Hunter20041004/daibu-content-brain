"""一次性工具：在 template.html 的每一段可編輯文字上加編號（data-c）。

編號之後，copy.py 就能靠編號把文字倒出來、改完再倒回去，
而且編號不會因為你改了文字內容而跑掉。

已經有編號的元素不會被重編，所以之後新增段落時可以再跑一次。

用法：python3 docs/build-story/mark_copy.py
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template.html"

BLOCK_TAGS = {"h1", "h3", "p", "blockquote", "summary", "figcaption", "td", "th", "b"}
SPAN_CLASSES = {"ref", "compare__tag"}


class Marker(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=False)
        self.source = source
        self.line_starts = self._line_starts(source)
        self.hits: list[int] = []
        self.in_nav = 0
        self.in_paragraph = False

    @staticmethod
    def _line_starts(text: str) -> list[int]:
        starts, total = [0], 0
        for line in text.split("\n"):
            total += len(line) + 1
            starts.append(total)
        return starts

    def _offset(self) -> int:
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)

        if tag == "nav":
            self.in_nav += 1
            return
        if self.in_nav:
            return

        if tag == "p":
            self.in_paragraph = True
        # <b> 只在不屬於某個段落時才單獨標記，否則會跟外層的 <p> 重複
        if tag == "b" and self.in_paragraph:
            return

        if "data-c" in attributes:
            return

        classes = set(attributes.get("class", "").split())
        wanted = tag in BLOCK_TAGS
        if tag == "span":
            wanted = bool(classes & SPAN_CLASSES)
        if wanted:
            self.hits.append(self._offset())

    def handle_endtag(self, tag):
        if tag == "nav":
            self.in_nav = max(0, self.in_nav - 1)
        if tag == "p":
            self.in_paragraph = False


def main() -> None:
    source = TEMPLATE.read_text(encoding="utf-8")
    split_at = source.index("<body>")
    head, body = source[:split_at], source[split_at:]

    marker = Marker(body)
    marker.feed(body)
    hits = sorted(marker.hits)

    start_id = max((int(n) for n in re.findall(r'data-c="(\d+)"', body)), default=0) + 1
    numbering = {offset: start_id + index for index, offset in enumerate(hits)}

    for offset in reversed(hits):
        close = body.index(">", offset)
        body = f'{body[:close]} data-c="{numbering[offset]}"{body[close:]}'

    TEMPLATE.write_text(head + body, encoding="utf-8")
    if hits:
        print(f"已標記 {len(hits)} 段，編號 {start_id}–{start_id + len(hits) - 1}")
    else:
        print("沒有需要新標記的段落")


if __name__ == "__main__":
    main()
