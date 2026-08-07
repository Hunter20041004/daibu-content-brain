"""組裝建造故事 HTML。

把 template.html 裡的佔位符換成實際內容，輸出成一份可獨立分享的單檔 HTML：

    {{IMG:name}}      -> docs/build-story/assets/<name>.jpg 的 base64 data URI
    {{SVG:mascot}}    -> assets/mascot/wave.svg 的內容
    {{COMMENT_CSS}}   -> docs/build-story/partials/comment-tool.css
    {{COMMENT_HTML}}  -> docs/build-story/partials/comment-tool.html
    {{COMMENT_JS}}    -> docs/build-story/partials/comment-tool.js

圖片必須內嵌，否則檔案分享出去之後圖片路徑會失效。

用法：python3 docs/build-story/build.py
"""

from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TEMPLATE = HERE / "template.html"
ASSETS = HERE / "assets"
PARTIALS = HERE / "partials"
MASCOT = ROOT / "assets" / "mascot" / "wave.svg"
OUTPUT = ROOT / "docs" / "2026-08-07-呆一布內容工作站是怎麼做出來的.html"

BANNER = (
    "<!-- 這份檔案由 docs/build-story/build.py 產生，請改 docs/build-story/template.html "
    "後重跑，不要直接編輯這裡。 -->\n"
)


def image_data_uri(name: str) -> str:
    path = ASSETS / f"{name}.jpg"
    if not path.exists():
        raise FileNotFoundError(f"找不到圖片素材：{path}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def build() -> Path:
    html = TEMPLATE.read_text(encoding="utf-8")

    for key, partial in (
        ("COMMENT_CSS", "comment-tool.css"),
        ("COMMENT_HTML", "comment-tool.html"),
        ("COMMENT_JS", "comment-tool.js"),
    ):
        html = html.replace("{{" + key + "}}", (PARTIALS / partial).read_text(encoding="utf-8").rstrip())

    html = html.replace("{{SVG:mascot}}", MASCOT.read_text(encoding="utf-8").strip())

    html = re.sub(r"\{\{IMG:([a-z0-9\-]+)\}\}", lambda m: image_data_uri(m.group(1)), html)

    leftover = re.findall(r"\{\{[^}]+\}\}", html)
    if leftover:
        raise ValueError(f"還有沒替換掉的佔位符：{sorted(set(leftover))}")

    html = html.replace("<!doctype html>\n", "<!doctype html>\n" + BANNER, 1)
    OUTPUT.write_text(html, encoding="utf-8")
    return OUTPUT


if __name__ == "__main__":
    out = build()
    size = out.stat().st_size
    print(f"已產生 {out.relative_to(ROOT)}（{size / 1024:.0f} KB）", file=sys.stderr)
