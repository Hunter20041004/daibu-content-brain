import html
from pathlib import Path

from daibu.cards import diagrams, logo, pages
from daibu.cards.layout_schema import LayoutDocument
from daibu.cards.schema import BrandAsset, CarouselPage, ContentSection

ASSETS = Path(__file__).resolve().parent.parent.parent / "assets"
TEMPLATES = Path(__file__).resolve().parent / "templates"

FONT_FILES = {
    "__FONT_RG__": "LINESeedTW_OTF_Rg.otf",
    "__FONT_BD__": "LINESeedTW_OTF_Bd.otf",
    "__FONT_EB__": "LINESeedTW_OTF_Eb.otf",
}

SERIES_NAME = "一布懂 AI 新創"
SHOT_FOR = {
    "cover": "hero",
    "who": "editorial",
    "problem": "editorial",
    "how-ai": "evidence",
    "results": "evidence",
    "why-care": "evidence",
    "cta": "hero",
}


def _company_name_class(company: str) -> str:
    length = len("".join(company.split()))
    if length <= 10:
        return "short"
    if length <= 16:
        return "medium"
    return "long"


def _mascot_uri(page_type: str) -> str:
    pose = pages.MASCOT_FOR[page_type]
    path = ASSETS / "mascot" / f"{pose}.svg"
    if not path.is_file():
        raise RuntimeError(f"找不到呆一布角色素材：{pose}")
    return path.as_uri()


def _mascot_html(page_type: str) -> str:
    pose = pages.MASCOT_FOR[page_type]
    return (
        f'<img class="story-mascot mascot--{pose}" '
        f'src="{_mascot_uri(page_type)}" alt="呆一布角色插圖">'
    )


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
        '<div class="page-identity">'
        f'<div class="series-mini">{SERIES_NAME}</div>'
        f'<div class="page-tag">{page.page_no:02d}｜'
        f"{html.escape(pages.label(page.page_type))}</div></div>"
        f'<img class="company-logo company-logo--small" '
        f'src="{logo_uri}" alt="{html.escape(company)} Logo">'
        "</header>"
    )


def _cover(page: CarouselPage, company: str, logo_uri: str) -> str:
    by_label = {section.label: section for section in page.sections}
    return (
        '<article class="card cover-v151" data-page-type="cover">'
        + _layout_box("series", html.escape(SERIES_NAME), classes="series")
        + _layout_box(
            "company-logo",
            f'<img src="{logo_uri}" alt="{html.escape(company)} Logo">',
        )
        + _layout_box(
            "company-name",
            html.escape(company),
            classes="company-name",
        )
        + _layout_box(
            "heading",
            html.escape(page.heading),
            tag="h1",
            classes="cover-heading",
        )
        + _layout_box("rule", "", classes="cover-rule")
        + _layout_box(
            "positioning",
            html.escape(by_label["一句話定位"].text),
            tag="p",
            classes="cover-copy",
        )
        + _layout_box(
            "mascot",
            _mascot_html(page.page_type),
            classes="mascot-box",
        )
        + "</article>"
    )


def _layout_box(
    element_id: str,
    content: str,
    *,
    tag: str = "div",
    classes: str = "",
) -> str:
    class_attribute = f' class="{classes}"' if classes else ""
    return (
        f'<{tag}{class_attribute} data-layout-id="{element_id}">'
        f"{content}</{tag}>"
    )


def _editorial_document(page: CarouselPage, content: str) -> str:
    css = (TEMPLATES / "editorial-v15-1.css").read_text(encoding="utf-8")
    for token, filename in FONT_FILES.items():
        css = css.replace(token, (ASSETS / "fonts" / filename).as_uri())
    return (
        (TEMPLATES / "editorial-v15-1.html")
        .read_text(encoding="utf-8")
        .replace("__CSS__", css)
        .replace("__PAGE_TYPE__", html.escape(page.page_type))
        .replace("__CONTENT__", content)
    )


def _section_by_label(page: CarouselPage, label: str) -> ContentSection:
    try:
        return next(section for section in page.sections if section.label == label)
    except StopIteration as error:
        raise ValueError(f"第 {page.page_no} 頁缺少「{label}」內容") from error


def _editorial_header(company: str) -> str:
    return (
        '<div class="editorial-header" data-layout-id="header">'
        f'<span class="series">{html.escape(SERIES_NAME)}</span>'
        f'<span class="company">{html.escape(company)}</span>'
        "</div>"
    )


def _who(page: CarouselPage, company: str) -> str:
    positioning = _section_by_label(page, "白話定位")
    facts = _section_by_label(page, "基本資料")
    return (
        '<article class="card profile-v151" data-page-type="who">'
        + _editorial_header(company)
        + _layout_box(
            "heading",
            html.escape(page.heading),
            tag="h1",
            classes="editorial-heading",
        )
        + _layout_box(
            "positioning",
            f'<small>{html.escape(positioning.label)}</small>'
            f'<p>{html.escape(positioning.text)}</p>',
            tag="section",
            classes="profile-positioning",
        )
        + _layout_box(
            "facts",
            f'<small>{html.escape(facts.label)}</small>'
            f'<p>{html.escape(facts.text)}</p>',
            tag="section",
            classes="profile-facts",
        )
        + _layout_box(
            "mascot",
            _mascot_html(page.page_type),
            classes="mascot-box",
        )
        + "</article>"
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
        "</main>"
        f'{_mascot_html(page.page_type)}'
        '<footer class="page-source source-label">'
        f'{html.escape(page.source_label)}</footer>'
    )


def page_html(
    page: CarouselPage,
    company: str,
    brand_asset: BrandAsset | None,
    layout: LayoutDocument | None = None,
) -> str:
    del layout
    logo_uri = logo.logo_data_uri(brand_asset, company)
    if page.page_type == "cover":
        return _editorial_document(page, _cover(page, company, logo_uri))
    if page.page_type == "who":
        return _editorial_document(page, _who(page, company))

    css = (TEMPLATES / "ai-startup.css").read_text(encoding="utf-8")
    for token, filename in FONT_FILES.items():
        css = css.replace(token, (ASSETS / "fonts" / filename).as_uri())
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
        .replace("__SHOT__", SHOT_FOR[page.page_type])
        .replace("__PAGE_NO__", f"{page.page_no:02d}")
        .replace("__CONTENT__", content)
    )
