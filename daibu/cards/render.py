import html
from pathlib import Path

from daibu.cards import diagrams, logo, pages
from daibu.cards.schema import BrandAsset, CarouselPage, ContentSection

ASSETS = Path(__file__).resolve().parent.parent.parent / "assets"
TEMPLATES = Path(__file__).resolve().parent / "templates"

FONT_FILES = {
    "__FONT_RG__": "LINESeedTW_OTF_Rg.otf",
    "__FONT_BD__": "LINESeedTW_OTF_Bd.otf",
    "__FONT_EB__": "LINESeedTW_OTF_Eb.otf",
}

SERIES_NAME = "一布懂 AI 新創"


def _company_name_class(company: str) -> str:
    length = len("".join(company.split()))
    if length <= 10:
        return "short"
    if length <= 16:
        return "medium"
    return "long"


def _section_html(section: ContentSection) -> str:
    return (
        '<section class="content-block">'
        f'<div class="content-label">{html.escape(section.label)}</div>'
        f"<p>{html.escape(section.text)}</p>"
        "</section>"
    )


def _header(page: CarouselPage, company: str, logo_uri: str) -> str:
    return (
        '<header class="page-header">'
        f'<div class="page-tag">{page.page_no:02d}｜'
        f"{html.escape(pages.label(page.page_type))}</div>"
        f'<img class="company-logo company-logo--small" '
        f'src="{logo_uri}" alt="{html.escape(company)} Logo">'
        "</header>"
    )


def _cover(page: CarouselPage, company: str, logo_uri: str) -> str:
    by_label = {section.label: section for section in page.sections}
    company_class = _company_name_class(company)
    return (
        '<div class="cover-content">'
        f'<div class="series-lockup">{SERIES_NAME}</div>'
        f'<img class="company-logo company-logo--cover" '
        f'src="{logo_uri}" alt="{html.escape(company)} Logo">'
        f'<div class="company-name company-name--{company_class}">'
        f'{html.escape(company)}</div>'
        f'<h1 class="cover-hook">{html.escape(page.heading)}</h1>'
        '<p class="cover-positioning">'
        f'{html.escape(by_label["一句話定位"].text)}</p>'
        "</div>"
    )


def _inner(page: CarouselPage, company: str, logo_uri: str) -> str:
    sections = "".join(_section_html(section) for section in page.sections)
    diagram = diagrams.diagram_html(page.diagram) if page.diagram else ""
    return (
        f"{_header(page, company, logo_uri)}"
        '<main class="content-stack">'
        f"<h1>{html.escape(page.heading)}</h1>"
        f'<div class="section-list">{sections}</div>'
        f"{diagram}"
        f'<div class="source-label">{html.escape(page.source_label)}</div>'
        "</main>"
    )


def page_html(
    page: CarouselPage,
    company: str,
    brand_asset: BrandAsset | None,
) -> str:
    css = (TEMPLATES / "ai-startup.css").read_text(encoding="utf-8")
    for token, filename in FONT_FILES.items():
        css = css.replace(token, (ASSETS / "fonts" / filename).as_uri())
    logo_uri = logo.logo_data_uri(brand_asset, company)
    content = (
        _cover(page, company, logo_uri)
        if page.page_type == "cover"
        else _inner(page, company, logo_uri)
    )
    return (
        (TEMPLATES / "ai-startup.html")
        .read_text(encoding="utf-8")
        .replace("__CSS__", css)
        .replace("__PAGE_TYPE__", html.escape(page.page_type))
        .replace("__CONTENT__", content)
    )
