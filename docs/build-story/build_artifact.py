"""把建造故事轉成可發佈到 Artifact 的版本。

Artifact 的沙箱會擋掉所有外部連線，所以這一版跟本機版有三個差別：

1. 拿掉 Tailwind CDN 與 Google Fonts（模板實際上沒用到任何 Tailwind class）
2. 字型改成系統堆疊：Apple 用 Songti TC / PingFang TC，Windows 用細明體 / 微軟正黑體，
   襯線標題與黑體內文的區別在兩個平台上都成立
3. 補上深色主題，因為 Artifact 會跟著讀者的系統主題或手動切換顯示

輸出是「內容片段」，不含 doctype / html / head / body ── 那些由 Artifact 在發佈時包上。

用法：python3 docs/build-story/build_artifact.py <輸出路徑>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / "docs" / "2026-08-07-呆一布內容工作站是怎麼做出來的.html"

FONT_STACKS = {
    "--font-serif": '"Songti TC", "Songti SC", "PMingLiU", "MingLiU", Georgia, serif',
    "--font-sans": '"PingFang TC", "PingFang SC", "Microsoft JhengHei", "Helvetica Neue", system-ui, sans-serif',
    "--font-mono": 'ui-monospace, "SF Mono", Menlo, Consolas, monospace',
}

DARK_TOKENS = """
        --paper: #12171a;
        --surface: #192025;
        --wash: #1a2830;
        --ink: #e3ebee;
        --deep: #9ed8e0;
        --deep-2: #7cb8c6;
        --accent: #6fc1cc;
        --rule: #2b353b;
        --muted: #93a5ad;
        --fill-strong: #16323c;
        --on-fill-strong: #e6f2f5;
        --warn-bg: #3a241c;
        --warn-fg: #f0b49a;
        --ok-bg: #16323c;
        --ok-fg: #a7dde5;
        --shadow: 0 18px 40px rgba(0, 0, 0, 0.45);
"""

LIGHT_TOKENS = """
        --paper: #fbfaf7;
        --surface: #ffffff;
        --wash: #e9f6ff;
        --ink: #14202a;
        --deep: #244a5b;
        --deep-2: #315f73;
        --accent: #6fc1cc;
        --rule: #ded8ce;
        --muted: #5a6a74;
        --fill-strong: #244a5b;
        --on-fill-strong: #eaf3f6;
        --warn-bg: #fbe6da;
        --warn-fg: #9a4a2c;
        --ok-bg: #dcf0f2;
        --ok-fg: #244a5b;
        --shadow: 0 18px 40px rgba(36, 74, 91, 0.1);
"""

THEME_BLOCK = f"""
      /* ---------- 深色主題 ----------
         讀者的系統偏好由 prefers-color-scheme 帶進來，
         Artifact 的主題切換鈕會在根元素蓋上 data-theme，必須贏過媒體查詢。
         只重新定義 token，元件一律透過 token 取色。 */
      @media (prefers-color-scheme: dark) {{
        :root {{{DARK_TOKENS}        }}
      }}

      :root[data-theme="dark"] {{{DARK_TOKENS}      }}

      :root[data-theme="light"] {{{LIGHT_TOKENS}      }}
"""


def extract(source: str) -> tuple[str, str]:
    style = re.search(r"<style>(.*?)</style>", source, re.S)
    body = re.search(r"<body>(.*?)</body>", source, re.S)
    if not style or not body:
        raise ValueError("找不到 <style> 或 <body> 區塊")
    return style.group(1), body.group(1)


def build(out_path: Path) -> Path:
    source = SOURCE.read_text(encoding="utf-8")
    style, body = extract(source)

    for token, stack in FONT_STACKS.items():
        pattern = rf"({re.escape(token)}:\s*)[^;]+;"
        style, count = re.subn(pattern, lambda m: f"{m.group(1)}{stack};", style, count=1)
        if count != 1:
            raise ValueError(f"沒有換到字型 token：{token}")

    style = style.rstrip() + "\n" + THEME_BLOCK

    page = (
        "<title>我沒寫程式，怎麼做出呆一布內容工作站</title>\n"
        f"<style>{style}</style>\n"
        f"{body.strip()}\n"
    )

    for blocked in ("cdn.tailwindcss.com", "fonts.googleapis.com", "fonts.gstatic.com"):
        if blocked in page:
            raise ValueError(f"外部資源沒有清乾淨：{blocked}")
    if "<!doctype" in page.lower() or "<body" in page.lower():
        raise ValueError("內容片段不該包含 doctype 或 body 標籤")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build-story-artifact.html"
    result = build(target)
    print(f"已產生 {result}（{result.stat().st_size / 1024:.0f} KB）", file=sys.stderr)
