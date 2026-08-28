from daibu.cards import pages
from daibu.cards.layout_registry import ELEMENT_REGISTRY
from daibu.cards.schema import (
    CarouselDraft,
    CarouselPage,
    ContentSection,
    DiagramNode,
    DiagramSpec,
)


COMPANY_PLACEHOLDER = "公司名稱"
SERIES_PLACEHOLDER = "系列名稱"

_DIAGRAM_KIND = {
    "problem": "problem-chain",
    "how-ai": "ai-generate",
    "results": "before-after",
}
_DIAGRAM_ELEMENT_IDS = {
    "problem": ("stage-1-title", "stage-2-title", "stage-3-title"),
    "how-ai": ("step-1-title", "step-2-title", "step-3-title"),
    "results": ("before-title", "intervention-title", "after-title"),
}


def build_template_placeholder_draft() -> CarouselDraft:
    built = []
    for page_no, page_type in enumerate(pages.PAGE_TYPES, start=1):
        labels = pages.SECTION_LABEL_SEQUENCES[page_type][0]
        sections = tuple(
            ContentSection(
                label,
                (
                    "追蹤呆一布 AI 共學實驗室\n帶你看更多最新 AI 資訊"
                    if page_type == "cta"
                    else label
                ),
                (),
                (),
            )
            for label in labels
        )
        diagram = None
        if page_type in _DIAGRAM_KIND:
            diagram = DiagramSpec(
                _DIAGRAM_KIND[page_type],
                tuple(
                    DiagramNode(
                        ELEMENT_REGISTRY[page_type][element_id].label,
                        "圖解說明",
                        "think",
                    )
                    for element_id in _DIAGRAM_ELEMENT_IDS[page_type]
                ),
            )
        built.append(
            CarouselPage(
                page_no,
                page_type,
                "封面標題" if page_type == "cover" else "頁面標題",
                sections,
                diagram,
                "",
            )
        )
    return CarouselDraft((), tuple(built))
