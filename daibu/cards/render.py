import base64
import html
from pathlib import Path

from daibu.cards import logo, pages
from daibu.cards.layout_schema import LayoutDocument, LayoutElement, load_builtin_layout
from daibu.cards.schema import BrandAsset, CarouselDraft, CarouselPage, ContentSection

ASSETS = Path(__file__).resolve().parent.parent.parent / "assets"
TEMPLATES = Path(__file__).resolve().parent / "templates"
FONT_FILES = {
    "__FONT_RG__": "LINESeedTW_OTF_Rg.otf",
    "__FONT_BD__": "LINESeedTW_OTF_Bd.otf",
    "__FONT_EB__": "LINESeedTW_OTF_Eb.otf",
}
SERIES_NAME = "一布懂 AI 新創"


def _mascot_uri(page_type: str) -> str:
    pose = pages.MASCOT_FOR[page_type]
    path = ASSETS / "mascot" / f"{pose}.svg"
    if not path.is_file():
        raise RuntimeError(f"找不到呆一布角色素材：{pose}")
    return "data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _mascot_html(page_type: str) -> str:
    pose = pages.MASCOT_FOR[page_type]
    return (
        f'<img class="story-mascot mascot--{pose}" '
        f'src="{_mascot_uri(page_type)}" alt="呆一布角色插圖">'
    )


def _layout_box(
    element_id: str,
    content: str,
    *,
    tag: str = "div",
    classes: str = "",
    edit_key: str | None = None,
    attributes: str = "",
) -> str:
    class_attribute = f' class="{classes}"' if classes else ""
    edit_attribute = f' data-edit-key="{html.escape(edit_key)}"' if edit_key else ""
    return (
        f'<{tag}{class_attribute} data-layout-id="{element_id}"{edit_attribute}'
        f"{(' ' + attributes) if attributes else ''}>"
        f"{content}</{tag}>"
    )


def _editable(key: str, value: str, *, tag: str = "span") -> str:
    return (
        f'<{tag} data-edit-key="{html.escape(key)}">'
        f"{html.escape(value)}</{tag}>"
    )


def _hidden_edit_hook(key: str) -> str:
    return f'<span class="editor-metadata-hook" data-edit-key="{html.escape(key)}"></span>'


def _section_by_label(page: CarouselPage, label: str) -> ContentSection:
    try:
        return next(section for section in page.sections if section.label == label)
    except StopIteration as error:
        raise ValueError(f"第 {page.page_no} 頁缺少「{label}」內容") from error


def _problem_icon(index: int) -> str:
    drawings = (
        '<path d="M22 52a30 30 0 1 1 9 21"/><path d="M19 70l12 3-2-13"/>',
        '<circle cx="48" cy="48" r="29"/><circle cx="48" cy="48" r="16"/>'
        '<path d="M48 8v15M48 73v15M8 48h15M73 48h15"/>',
        '<path d="M13 76l22-22 15 13 32-37"/><path d="M64 30h18v18"/>'
        '<path d="M14 87h70"/>',
    )
    visual = ("cycle-icon", "target-icon", "growth-icon")[index]
    return (
        f'<svg class="card-icon" data-card-icon="problem-{index + 1}" '
        f'data-visual="{visual}" viewBox="0 0 96 96" aria-hidden="true" '
        'fill="none" stroke="currentColor" stroke-width="7" '
        f'stroke-linecap="round" stroke-linejoin="round">{drawings[index]}</svg>'
    )


def _node_card(page: CarouselPage, index: int, element_id: str, classes: str) -> str:
    assert page.diagram is not None
    node = page.diagram.nodes[index]
    prefix = f"page.{page.page_type}.diagram.{index}"
    if page.page_type == "problem":
        expression = (
            _problem_icon(index)
            + f'<i class="node-index" aria-hidden="true">{index + 1:02d}</i>'
            + _hidden_edit_hook(f"{prefix}.expression")
        )
    elif page.page_type == "how-ai":
        expression = (
            f'<i>{("IN", "AI", "OUT")[index]}</i>'
            + _hidden_edit_hook(f"{prefix}.expression")
        )
    elif page.page_type == "results":
        expression = (
            f'<i>{("BEFORE", "→", "AFTER")[index]}</i>'
            + _hidden_edit_hook(f"{prefix}.expression")
        )
    else:
        expression = (
            f'<i data-edit-key="{prefix}.expression">'
            f"{html.escape(node.expression)}</i>"
        )
    return _layout_box(
        element_id,
        expression + _editable(f"{prefix}.title", node.title, tag="b")
        + _editable(f"{prefix}.text", node.text),
        tag="section",
        classes=classes,
    )


def _heading(page: CarouselPage) -> str:
    return _layout_box(
        "heading",
        _editable(f"page.{page.page_type}.heading", page.heading),
        tag="h1",
        classes="page-title",
    )


def _cover(page: CarouselPage, company: str, logo_uri: str) -> str:
    positioning = _section_by_label(page, "一句話定位")
    return (
        '<article class="card page-cover" data-page-type="cover">'
        '<span class="tape tape-left"></span><span class="tape tape-right"></span>'
        + _layout_box(
            "company-logo",
            f'<img src="{logo_uri}" alt="{html.escape(company)} Logo">',
            classes="company-logo",
        )
        + _layout_box(
            "company-name", html.escape(company), tag="h1", classes="company-name"
        )
        + _layout_box(
            "heading",
            _editable("page.cover.heading", page.heading),
            tag="h2",
            classes="cover-heading",
        )
        + _layout_box(
            "positioning",
            _editable("page.cover.section.0.text", positioning.text),
            tag="p",
            classes="sticky-note cover-positioning",
        )
        + _layout_box("mascot", _mascot_html("cover"), classes="mascot-box")
        + "</article>"
    )


def _who(page: CarouselPage, logo_uri: str, company: str) -> str:
    positioning = _section_by_label(page, "白話定位")
    facts = _section_by_label(page, "基本資料")
    reason = _section_by_label(page, "為什麼值得介紹")
    return (
        '<article class="card page-who" data-page-type="who">'
        '<span class="tape tape-left"></span><span class="tape tape-right"></span>'
        '<div class="sheet folder"></div>'
        '<div class="sheet profile-sheet">'
        '<div class="page-label">COMPANY FILE</div>'
        + _heading(page)
        + '<div class="identity-map" aria-hidden="true">'
        '<span data-visual="identity-node">AI 產品</span><i>→</i>'
        '<span data-visual="identity-node">目標使用者</span><i>→</i>'
        '<span data-visual="identity-node">核心價值</span>'
        '</div>'
        '<div class="profile-grid schema-profile">'
        + _layout_box(
            "logo",
            f'<img src="{logo_uri}" alt="{html.escape(company)} Logo">',
            classes="logo-slot",
        )
        + '<div class="profile-copy">'
        + _layout_box(
            "positioning",
            f"<b>{html.escape(positioning.label)}</b>"
            + _editable("page.who.section.0.text", positioning.text),
            tag="section",
            classes="profile-section",
        )
        + _layout_box(
            "facts",
            f"<b>{html.escape(facts.label)}</b>"
            + _editable("page.who.section.1.text", facts.text),
            tag="section",
            classes="profile-section",
        )
        + "</div></div>"
        + _layout_box(
            "reason",
            f"<b>{html.escape(reason.label)}</b>"
            + _editable("page.who.section.2.text", reason.text),
            tag="div",
            classes="thesis",
        )
        + '</div>'
        + _layout_box("mascot", _mascot_html("who"), classes="mascot-box")
        + "</article>"
    )


def _problem(page: CarouselPage) -> str:
    if page.diagram is None or len(page.diagram.nodes) != 3:
        raise ValueError("第 3 頁缺少問題流程圖解")
    current = _section_by_label(page, "現在怎麼做")
    opportunity = _section_by_label(page, "哪裡還能更好")
    return (
        '<article class="card page-problem" data-page-type="problem">'
        '<span class="tape tape-left"></span><span class="tape tape-right"></span>'
        '<div class="sheet shared-back"></div>'
        '<div class="sheet shared-sheet">'
        '<div class="question-bg" aria-hidden="true">?</div>'
        '<div class="page-label">THE OPPORTUNITY</div>'
        + _heading(page)
        + '<div class="problem-context">'
        + _layout_box(
            "current",
            f"<b>{html.escape(current.label)}</b>"
            + _editable("page.problem.section.0.text", current.text),
            classes="sticky-note mint",
        )
        + _layout_box(
            "opportunity",
            f"<b>{html.escape(opportunity.label)}</b>"
            + _editable("page.problem.section.1.text", opportunity.text),
            classes="sticky-note yellow",
        )
        + '</div><div class="notes schema-notes">'
        + _layout_box(
            "spine",
            "",
            classes="causal-spine",
            attributes='data-visual="causal-spine"',
        )
        + _node_card(page, 0, "stage-1", "problem-note n1")
        + _node_card(page, 1, "stage-2", "problem-note n2")
        + _node_card(page, 2, "stage-3", "problem-note n3")
        + '</div></div>'
        + _layout_box("mascot", _mascot_html("problem"), classes="mascot-box")
        + "</article>"
    )


def _how_ai(page: CarouselPage) -> str:
    if page.diagram is None or len(page.diagram.nodes) != 3:
        raise ValueError("第 4 頁缺少 AI 流程圖解")
    labels = ("傳統做法", "AI 的角色", "人仍負責", "關鍵差別")
    ids = ("traditional", "ai-role", "human", "difference")
    context = []
    for element_id, label in zip(ids, labels, strict=True):
        section = _section_by_label(page, label)
        index = page.sections.index(section)
        context.append(
            _layout_box(
                element_id,
                f"<b>{html.escape(label)}</b>"
                + _editable(f"page.how-ai.section.{index}.text", section.text),
                classes="sticky-note context-note",
            )
        )
    return (
        '<article class="card page-how" data-page-type="how-ai">'
        '<span class="tape tape-left"></span><span class="tape tape-right"></span>'
        '<div class="sheet shared-back"></div>'
        '<div class="sheet shared-sheet solution-sheet">'
        '<div class="page-label">HOW AI WORKS</div>'
        + _heading(page)
        + '<div class="flow-arrows" aria-hidden="true"></div>'
        + '<div class="route schema-route">'
        '<span class="flow-arrow a1" data-visual="flow-arrow" aria-hidden="true">→</span>'
        '<span class="flow-arrow a2" data-visual="flow-arrow" aria-hidden="true">→</span>'
        + _node_card(page, 0, "step-1", "step s1")
        + _node_card(page, 1, "step-2", "step s2")
        + _node_card(page, 2, "step-3", "step s3")
        + '</div><div class="how-context">'
        + "".join(context)
        + "</div></div>"
        + _layout_box("mascot", _mascot_html("how-ai"), classes="mascot-box")
        + "</article>"
    )


def _results(page: CarouselPage) -> str:
    if page.diagram is None or len(page.diagram.nodes) != 3:
        raise ValueError("第 5 頁需要三段前後對照圖解")
    audience = _section_by_label(page, "代表使用者")
    difference = _section_by_label(page, "核心差異")
    value = _section_by_label(page, "帶來的價值")
    return (
        '<article class="card page-results" data-page-type="results">'
        '<span class="tape tape-left"></span><span class="tape tape-right"></span>'
        '<div class="sheet shared-back"></div>'
        '<div class="sheet shared-sheet model-sheet results-sheet">'
        '<div class="page-label">BEFORE &amp; AFTER</div>'
        + _heading(page)
        + _layout_box(
            "audience",
            f"<b>{html.escape(audience.label)}</b>"
            + _editable("page.results.section.0.text", audience.text),
            classes="sticky-note audience",
        )
        + '<div class="result-flow">'
        + _node_card(page, 0, "before", "result-card mint")
        + _node_card(page, 1, "intervention", "result-card yellow")
        + _node_card(page, 2, "after", "result-card mint")
        + "</div>"
        + _layout_box(
            "core-difference",
            f"<b>{html.escape(difference.label)}</b>"
            + _editable("page.results.section.1.text", difference.text),
            classes="sticky-note white",
        )
        + _layout_box(
            "value",
            f"<b>{html.escape(value.label)}</b>"
            + _editable("page.results.section.2.text", value.text),
            classes="sticky-note yellow",
        )
        + "</div>"
        + _layout_box("mascot", _mascot_html("results"), classes="mascot-box")
        + "</article>"
    )


def _cta(page: CarouselPage) -> str:
    invitation = _section_by_label(page, "互動邀請")
    first, second = pages.CTA_TEXT.splitlines()
    return (
        '<article class="card page-cta" data-page-type="cta">'
        '<span class="tape tape-left"></span><span class="tape tape-right"></span>'
        '<div class="sheet shared-back"></div>'
        '<div class="sheet shared-sheet close-sheet">'
        + _layout_box(
            "invitation",
            f'<p class="cta-line follow">{html.escape(first)}</p>'
            f'<p class="cta-line prompt">{html.escape(second)}</p>'
            f'<span class="legacy-generated" hidden>{html.escape(invitation.text)}</span>',
            classes="cta-copy cta-center",
        )
        + "</div>"
        + _layout_box("mascot", _mascot_html("cta"), classes="mascot-box")
        + _hidden_edit_hook("page.cta.heading")
        + "</article>"
    )


def _element_css(element_id: str, element: LayoutElement) -> str:
    rect = element.rect
    declarations = [
        "position:absolute!important",
        f"left:{rect.x:g}px",
        f"top:{rect.y:g}px",
        f"width:{rect.w:g}px",
        f"height:{rect.h:g}px",
    ]
    if element.text_style is not None:
        declarations.extend(
            (f"font-size:{element.text_style.font_size:g}px", f"text-align:{element.text_style.text_align}")
        )
    return f'.carousel-canvas [data-layout-id="{element_id}"]' + "{" + ";".join(declarations) + "}"


def layout_css(document: LayoutDocument, page_type: str) -> str:
    try:
        page_layout = document.pages[page_type]
    except KeyError as error:
        raise ValueError(f"版面缺少頁型：{page_type}") from error
    return "\n".join(
        _element_css(element_id, element)
        for element_id, element in page_layout.elements.items()
    )


def _sticky_document(
    page: CarouselPage,
    content: str,
    layout: LayoutDocument,
    *,
    browser_preview: bool = False,
) -> str:
    css = (TEMPLATES / "sticky-notebook-v1.css").read_text(encoding="utf-8")
    for token, filename in FONT_FILES.items():
        font_uri = f"/app/static/fonts/{filename}" if browser_preview else (ASSETS / "fonts" / filename).as_uri()
        css = css.replace(token, font_uri)
    return (
        (TEMPLATES / "sticky-notebook-v1.html")
        .read_text(encoding="utf-8")
        .replace("__CSS__", css)
        .replace("__LAYOUT_CSS__", layout_css(layout, page.page_type))
        .replace("__PAGE_TYPE__", html.escape(page.page_type))
        .replace("__PAGE_NO__", f"{page.page_no:02d}")
        .replace("__CONTENT__", content)
    )


def page_html(
    page: CarouselPage,
    company: str,
    brand_asset: BrandAsset | None,
    layout: LayoutDocument | None = None,
    *,
    allow_logo_placeholder: bool = False,
    browser_preview: bool = False,
    logo_placeholder_text: str = "LOGO 待確認",
) -> str:
    document = layout or load_builtin_layout()
    if brand_asset is None and allow_logo_placeholder:
        placeholder = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="160" viewBox="0 0 320 160">'
            '<text x="160" y="92" text-anchor="middle" fill="#405a82" font-size="24">'
            f"{html.escape(logo_placeholder_text)}</text></svg>"
        )
        logo_uri = "data:image/svg+xml;base64," + base64.b64encode(placeholder.encode()).decode()
    else:
        logo_uri = logo.logo_data_uri(brand_asset, company)
    renderers = {
        "cover": lambda: _cover(page, company, logo_uri),
        "who": lambda: _who(page, logo_uri, company),
        "problem": lambda: _problem(page),
        "how-ai": lambda: _how_ai(page),
        "results": lambda: _results(page),
        "cta": lambda: _cta(page),
    }
    try:
        content = renderers[page.page_type]()
    except KeyError as error:
        raise ValueError(f"不支援的頁型：{page.page_type}") from error
    return _sticky_document(page, content, document, browser_preview=browser_preview)


def draft_html_pages(
    draft: CarouselDraft,
    company: str,
    brand_asset: BrandAsset | None,
    layout: LayoutDocument | None = None,
    *,
    allow_logo_placeholder: bool = False,
    browser_preview: bool = False,
) -> dict[str, str]:
    return {
        page.page_type: page_html(
            page,
            company,
            brand_asset,
            layout,
            allow_logo_placeholder=allow_logo_placeholder,
            browser_preview=browser_preview,
        )
        for page in draft.pages
    }


def template_editor_page_html(
    page: CarouselPage,
    company: str,
    brand_asset: BrandAsset | None,
    layout: LayoutDocument,
    *,
    series_name: str = SERIES_NAME,
    logo_placeholder_text: str = "LOGO 待確認",
) -> str:
    output = page_html(
        page,
        company,
        brand_asset,
        layout,
        allow_logo_placeholder=True,
        browser_preview=True,
        logo_placeholder_text=logo_placeholder_text,
    ).replace(html.escape(SERIES_NAME), html.escape(series_name))
    return output.replace(
        'data-template="sticky-notebook-v1"',
        'data-template="sticky-notebook-v1" data-template-editor="true"',
        1,
    )
