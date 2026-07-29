import html
from pathlib import Path

from daibu.cards import pages

ASSETS = Path(__file__).resolve().parent.parent.parent / "assets"
TEMPLATES = Path(__file__).resolve().parent / "templates"

FONT_FILES = {
    "__FONT_RG__": "LINESeedTW_OTF_Rg.otf",
    "__FONT_BD__": "LINESeedTW_OTF_Bd.otf",
    "__FONT_EB__": "LINESeedTW_OTF_Eb.otf",
}


def _mascot_svg(page_type: str) -> str:
    pose = pages.MASCOT_FOR[page_type]
    return (ASSETS / "mascot" / f"{pose}.svg").read_text(encoding="utf-8")


def page_html(row: dict, company: str) -> str:
    css = (TEMPLATES / "ai-startup.css").read_text(encoding="utf-8")
    for token, filename in FONT_FILES.items():
        css = css.replace(token, (ASSETS / "fonts" / filename).as_uri())

    shell = (TEMPLATES / "ai-startup.html").read_text(encoding="utf-8")
    is_cover = row["page_type"] == "cover"
    main = (
        f'<div class="heading">{html.escape(row["heading"])}</div>'
        f'<div class="company">{html.escape(company)}</div>'
        if is_cover
        else f'<div class="heading">{html.escape(row["heading"])}</div>'
        f'<div class="body">{html.escape(row["body"])}</div>'
    )
    return (
        shell.replace("__CSS__", css)
        .replace("__TAG__", html.escape(pages.label(row["page_type"])))
        .replace("__MAIN__", main)
        .replace("__MASCOT__", _mascot_svg(row["page_type"]))
    )
