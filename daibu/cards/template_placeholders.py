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
    "why-care": "signals",
}
_DIAGRAM_ELEMENT_IDS = {
    "problem": ("stage-1-label", "stage-2-label", "stage-3-label"),
    "how-ai": ("step-1-label", "step-2-label", "step-3-label"),
    "results": ("before-title", "to", "after-title"),
    "why-care": ("signal-1-label", "signal-2-label", "signal-3-label"),
}


def build_template_placeholder_draft() -> CarouselDraft:
    built = []
    for page_no, page_type in enumerate(pages.PAGE_TYPES, start=1):
        sequence_index = 1 if page_type == "why-care" else 0
        labels = pages.SECTION_LABEL_SEQUENCES[page_type][sequence_index]
        sections = tuple(
            ContentSection(label, label, (), ())
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
