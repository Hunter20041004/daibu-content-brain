"""把建造故事的文字倒出成純文字檔，改完再倒回模板。

    python3 docs/build-story/copy.py 匯出    # 產生 docs/build-story/文案.txt
    python3 docs/build-story/copy.py 匯入    # 把改好的文字寫回 template.html

文字檔裡看不到任何 HTML 標籤。少數格式用符號表示：

    **粗體**      畫面上會是粗體字
    `程式碼`      畫面上會是等寬字（例如 app）
    （角色說明）  技術名詞後面那行灰色小字

編號 [N] 是給程式認的，不要改也不要刪。段落順序也不要調動。
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template.html"
COPY_FILE = HERE / "文案.txt"

# 標題含有不換行標記與斜體，結構特殊，不開放在這裡改
LOCKED = {2}

SECTION_NAMES = {
    "hero": "首屏",
    "build": "第一章 做出來",
    "system": "第二章 系統",
    "verify": "第三章 不寫歪",
    "recipe": "第四章 照著做",
}

TAG_NAMES = {
    "h1": "大標",
    "h3": "小標",
    "p": "段落",
    "blockquote": "大字引句",
    "summary": "名詞",
    "b": "項目標題",
    "td": "表格",
    "th": "表格欄名",
    "figcaption": "圖說",
    "span": "註記",
}

SLOT = re.compile(r'<(\w+)((?:[^>]*?)data-c="(\d+)"(?:[^>]*?))>(.*?)</\1>', re.S)


def to_text(inner: str) -> str:
    """HTML 內文 -> 純文字。"""
    text = re.sub(r'<span class="step">.*?</span>', "", inner, flags=re.S)
    text = re.sub(r'<span class="role">(.*?)</span>', r"（\1）", text, flags=re.S)
    text = re.sub(r"</?(?:strong|b)>", "**", text)
    text = re.sub(r'<code class="mono">(.*?)</code>', r"`\1`", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return " ".join(text.split())


def to_html(text: str, original: str) -> str:
    """純文字 -> HTML。步驟編號與粗體用的標籤都沿用原本那一個。"""
    step = re.search(r'<span class="step">.*?</span>', original, re.S)
    # <b> 與 <strong> 的樣式規則不同（.note-body b 只認得 <b>），不能互換
    bold = "b" if "<b>" in original else "strong"
    body = html.escape(text, quote=False)
    body = re.sub(r"`(.+?)`", r'<code class="mono">\1</code>', body)
    body = re.sub(r"\*\*(.+?)\*\*", rf"<{bold}>\1</{bold}>", body)
    body = re.sub(r"（([^（）]{2,12})）\s*$", r'<span class="role">\1</span>', body)
    return (step.group(0) if step else "") + body


def current_sections(body: str) -> dict[int, str]:
    """每個編號屬於哪一節。"""
    marks = [(m.start(), m.group(1)) for m in re.finditer(r'id="(hero|build|system|verify|recipe)"', body)]
    result = {}
    for m in SLOT.finditer(body):
        name = "首屏"
        for pos, section in marks:
            if pos < m.start():
                name = SECTION_NAMES[section]
        result[int(m.group(3))] = name
    return result


def export() -> None:
    body = TEMPLATE.read_text(encoding="utf-8").split("<body>", 1)[1]
    sections = current_sections(body)

    lines = [
        "# 建造故事 · 全部文字",
        "#",
        "# 直接改下面的中文就好。編號 [N] 不要改、不要刪，段落順序也不要調。",
        "# **粗體**、`等寬字`、（角色說明）這幾個符號會變成畫面上的格式，留著。",
        "#",
        "# 改完存檔，然後執行：",
        "#   python3 docs/build-story/copy.py 匯入 && python3 docs/build-story/build.py",
        "",
    ]
    last_section = None
    for match in SLOT.finditer(body):
        cid = int(match.group(3))
        if cid in LOCKED:
            continue
        section = sections.get(cid, "")
        if section != last_section:
            lines += ["", f"# ═══════════════  {section}  ═══════════════", ""]
            last_section = section
        kind = TAG_NAMES.get(match.group(1), match.group(1))
        lines.append(f"[{cid}] {kind}")
        lines.append(to_text(match.group(4)))
        lines.append("")

    COPY_FILE.write_text("\n".join(lines), encoding="utf-8")
    count = sum(1 for m in SLOT.finditer(body) if int(m.group(3)) not in LOCKED)
    print(f"已匯出 {count} 段到 {COPY_FILE.relative_to(HERE.parents[1])}")


def load_edits() -> dict[int, str]:
    edits: dict[int, str] = {}
    cid = None
    for raw in COPY_FILE.read_text(encoding="utf-8").split("\n"):
        line = raw.rstrip()
        if line.startswith("#") or line.startswith("=") or not line.strip():
            continue
        header = re.fullmatch(r"\[(\d+)\] .*", line)
        if header:
            cid = int(header.group(1))
            continue
        if cid is not None:
            edits[cid] = (edits.get(cid, "") + " " + line).strip()
    return edits


def import_() -> None:
    if not COPY_FILE.exists():
        raise SystemExit(f"找不到 {COPY_FILE}，請先執行：python3 {Path(__file__).name} 匯出")

    source = TEMPLATE.read_text(encoding="utf-8")
    split_at = source.index("<body>")
    head, body = source[:split_at], source[split_at:]
    edits = load_edits()
    changed = 0

    def replace(match: re.Match) -> str:
        nonlocal changed
        cid = int(match.group(3))
        if cid in LOCKED or cid not in edits:
            return match.group(0)
        rebuilt = to_html(edits[cid], match.group(4))
        if " ".join(match.group(4).split()) == rebuilt:
            return match.group(0)
        changed += 1
        return f"<{match.group(1)}{match.group(2)}>{rebuilt}</{match.group(1)}>"

    body = SLOT.sub(replace, body)
    TEMPLATE.write_text(head + body, encoding="utf-8")
    print(f"已更新 {changed} 段。接著執行：python3 docs/build-story/build.py")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "匯出"
    if action in ("匯出", "out", "export"):
        export()
    elif action in ("匯入", "in", "import"):
        import_()
    else:
        raise SystemExit("用法：copy.py 匯出　或　copy.py 匯入")
