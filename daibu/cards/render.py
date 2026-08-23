import html
from pathlib import Path

from daibu.cards import diagrams, logo, pages
from daibu.cards.layout_schema import (
    LayoutDocument,
    LayoutElement,
    load_builtin_layout,
)
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
            aria_hidden=True,
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
    aria_hidden: bool = False,
) -> str:
    class_attribute = f' class="{classes}"' if classes else ""
    aria_attribute = ' aria-hidden="true"' if aria_hidden else ""
    return (
        f'<{tag}{class_attribute} data-layout-id="{element_id}"'
        f"{aria_attribute}>"
        f"{content}</{tag}>"
    )


def _element_css(element_id: str, element: LayoutElement) -> str:
    rect = element.rect
    text_style = element.text_style
    declarations = [
        "position:absolute!important",
        f"left:{rect.x:g}px",
        f"top:{rect.y:g}px",
        f"width:{rect.w:g}px",
        f"height:{rect.h:g}px",
    ]
    if text_style is not None:
        declarations.extend(
            (
                f"font-size:{text_style.font_size:g}px",
                f"text-align:{text_style.text_align}",
            )
        )
    return (
        f'.carousel-canvas [data-layout-id="{element_id}"]'
        f'{{{";".join(declarations)}}}'
    )


def layout_css(document: LayoutDocument, page_type: str) -> str:
    try:
        page_layout = document.pages[page_type]
    except KeyError as error:
        raise ValueError(f"版面缺少頁型：{page_type}") from error
    return "\n".join(
        _element_css(element_id, element)
        for element_id, element in page_layout.elements.items()
    )


def _editorial_document(
    page: CarouselPage,
    content: str,
    layout: LayoutDocument,
) -> str:
    css = (TEMPLATES / "editorial-v15-1.css").read_text(encoding="utf-8")
    for token, filename in FONT_FILES.items():
        css = css.replace(token, (ASSETS / "fonts" / filename).as_uri())
    return (
        (TEMPLATES / "editorial-v15-1.html")
        .read_text(encoding="utf-8")
        .replace("__CSS__", css)
        .replace("__LAYOUT_CSS__", layout_css(layout, page.page_type))
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


def _problem(page: CarouselPage, company: str) -> str:
    if page.diagram is None:
        raise ValueError("第 3 頁缺少問題流程圖解")
    nodes = page.diagram.nodes
    affected = _section_by_label(page, "誰受影響")
    cost = _section_by_label(page, "原本的代價")
    supplements: tuple[ContentSection | None, ...] = (affected, None, cost)
    stages = []
    for index, (node, supplement) in enumerate(
        zip(nodes, supplements, strict=True),
        start=1,
    ):
        supplement_html = (
            f'<p class="stage-context">{html.escape(supplement.text)}</p>'
            if supplement is not None
            else ""
        )
        stages.append(
            _layout_box(
                f"stage-{index}",
                f'<small>{html.escape(node.title)}</small>'
                f'<strong>{html.escape(node.text)}</strong>'
                f"{supplement_html}",
                tag="section",
                classes=(
                    "problem-stage problem-stage--anchor"
                    if index == 3
                    else "problem-stage"
                ),
            )
        )
    return (
        '<article class="card problem-v151" data-page-type="problem">'
        + _editorial_header(company)
        + _layout_box(
            "heading",
            html.escape(page.heading),
            tag="h1",
            classes="editorial-heading",
        )
        + _layout_box("spine", "", classes="story-spine")
        + "".join(stages)
        + _layout_box(
            "mascot",
            _mascot_html(page.page_type),
            classes="mascot-box",
        )
        + "</article>"
    )


def _how_ai(page: CarouselPage, company: str) -> str:
    if page.diagram is None:
        raise ValueError("第 4 頁缺少 AI 流程圖解")
    caution = _section_by_label(page, "人仍負責")
    steps = []
    for index, node in enumerate(page.diagram.nodes, start=1):
        modifiers = {
            2: " how-step--ai",
            3: " how-step--output",
        }.get(index, "")
        steps.append(
            _layout_box(
                f"step-{index}",
                f'<small>{html.escape(node.title)}</small>'
                f'<strong>{html.escape(node.text)}</strong>',
                tag="section",
                classes=f"how-step{modifiers}",
            )
        )
    return (
        '<article class="card how-v151" data-page-type="how-ai">'
        + _editorial_header(company)
        + _layout_box(
            "heading",
            html.escape(page.heading),
            tag="h1",
            classes="editorial-heading",
        )
        + _layout_box("spine", "", classes="story-spine")
        + "".join(steps)
        + _layout_box(
            "caution",
            '<span>要注意的點</span>'
            f'<strong>{html.escape(caution.text)}</strong>',
            tag="section",
            classes="how-caution",
        )
        + _layout_box(
            "mascot",
            _mascot_html(page.page_type),
            classes="mascot-box",
        )
        + "</article>"
    )


def _results(page: CarouselPage, company: str) -> str:
    if page.diagram is None or len(page.diagram.nodes) != 3:
        raise ValueError("第 5 頁需要三段前後對照圖解")
    before, transition, after = page.diagram.nodes
    audience = _section_by_label(page, "代表使用者")
    change = _section_by_label(page, "使用前後")
    purchase = _section_by_label(page, "購買關係")
    return (
        '<article class="card results-v151" data-page-type="results">'
        '<div class="results-before" aria-hidden="true"></div>'
        '<div class="results-after" aria-hidden="true"></div>'
        + _editorial_header(company)
        + _layout_box(
            "before-title",
            html.escape(before.title),
            tag="h1",
            classes="result-title result-title--before",
        )
        + _layout_box(
            "before-copy",
            f'<strong>{html.escape(before.text)}</strong>'
            f'<p>{html.escape(audience.text)}</p>',
            tag="section",
            classes="result-copy result-copy--before",
        )
        + _layout_box("axis", "", classes="result-axis")
        + _layout_box(
            "to",
            "到",
            tag="span",
            classes="result-to",
        )
        + _layout_box(
            "after-title",
            html.escape(after.title),
            tag="h1",
            classes="result-title result-title--after",
        )
        + _layout_box(
            "after-copy",
            f'<small>改變之後｜{html.escape(transition.title)}</small>'
            f'<strong>{html.escape(after.text)}</strong>'
            f'<p>{html.escape(change.text)}</p>',
            tag="section",
            classes="result-copy result-copy--after",
        )
        + _layout_box(
            "summary",
            html.escape(purchase.text),
            tag="p",
            classes="result-summary",
        )
        + _layout_box(
            "mascot",
            _mascot_html(page.page_type),
            classes="mascot-box",
        )
        + "</article>"
    )


def _why_care(page: CarouselPage, company: str) -> str:
    if page.diagram is None or len(page.diagram.nodes) != 3:
        raise ValueError("第 6 頁需要三個觀察訊號")
    signal_sections = tuple(
        _section_by_label(page, f"觀察訊號 {index}")
        for index in range(1, 4)
    )
    signals = []
    for index, (node, section) in enumerate(
        zip(page.diagram.nodes, signal_sections, strict=True),
        start=1,
    ):
        signals.append(
            _layout_box(
                f"signal-{index}",
                f'<small>{html.escape(node.title)}</small>'
                f'<strong>{html.escape(node.text)}</strong>'
                f'<p>{html.escape(section.text)}</p>',
                tag="section",
                classes=(
                    "signal signal--primary"
                    if index == 1
                    else "signal signal--secondary"
                ),
            )
        )
    return (
        '<article class="card signals-v151" data-page-type="why-care">'
        + _editorial_header(company)
        + _layout_box(
            "heading",
            html.escape(page.heading),
            tag="h1",
            classes="editorial-heading",
        )
        + "".join(signals)
        + _layout_box(
            "mascot",
            _mascot_html(page.page_type),
            classes="mascot-box",
        )
        + "</article>"
    )


def _cta(page: CarouselPage, company: str) -> str:
    thesis = _section_by_label(page, "收束結論")
    question = _section_by_label(page, "給讀者的問題")
    invitation = _section_by_label(page, "互動邀請")
    return (
        '<article class="card closing-v151" data-page-type="cta">'
        + _editorial_header(company)
        + _layout_box(
            "heading",
            html.escape(page.heading),
            tag="h1",
            classes="editorial-heading",
        )
        + _layout_box(
            "thesis",
            f'<small>{html.escape(thesis.label)}</small>'
            f'<strong>{html.escape(thesis.text)}</strong>',
            tag="section",
            classes="closing-thesis",
        )
        + _layout_box(
            "question",
            '<small>留給你的問題</small>'
            f'<strong>{html.escape(question.text)}</strong>',
            tag="section",
            classes="closing-question",
        )
        + _layout_box(
            "invitation",
            html.escape(invitation.text),
            classes="closing-invitation",
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
    document = layout or load_builtin_layout()
    logo_uri = logo.logo_data_uri(brand_asset, company)
    if page.page_type == "cover":
        return _editorial_document(
            page,
            _cover(page, company, logo_uri),
            document,
        )
    if page.page_type == "who":
        return _editorial_document(page, _who(page, company), document)
    if page.page_type == "problem":
        return _editorial_document(page, _problem(page, company), document)
    if page.page_type == "how-ai":
        return _editorial_document(page, _how_ai(page, company), document)
    if page.page_type == "results":
        return _editorial_document(page, _results(page, company), document)
    if page.page_type == "why-care":
        return _editorial_document(page, _why_care(page, company), document)
    if page.page_type == "cta":
        return _editorial_document(page, _cta(page, company), document)

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
