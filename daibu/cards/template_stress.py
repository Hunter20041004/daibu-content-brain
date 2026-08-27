from dataclasses import dataclass
from pathlib import Path

from daibu.cards import pages
from daibu.cards.schema import (
    BrandAsset,
    CarouselDraft,
    CarouselPage,
    ContentSection,
    DiagramNode,
    DiagramSpec,
    VerifiedSource,
)


@dataclass(frozen=True)
class TemplateStressCase:
    draft: CarouselDraft
    company: str
    asset: BrandAsset
    label: str


def _fixed_draft(company: str) -> CarouselDraft:
    source = VerifiedSource("S1", company, "2026-08-23", "https://example.com/source", "已核對的壓力測試內容。", "official")
    diagram_kinds = {
        "problem": "problem-chain",
        "how-ai": "ai-generate",
        "results": "before-after",
    }
    built = []
    for number, page_type in enumerate(pages.PAGE_TYPES, start=1):
        labels = pages.SECTION_LABEL_SEQUENCES[page_type][0]
        sections = tuple(
            ContentSection(
                label,
                (
                    pages.CTA_TEXT
                    if page_type == "cta"
                    else "字" * pages.SECTION_HARD_LIMITS[page_type][index]
                ),
                () if page_type == "cta" else ("S1",),
                (),
            )
            for index, label in enumerate(labels)
        )
        diagram = None
        if page_type in diagram_kinds:
            diagram = DiagramSpec(
                diagram_kinds[page_type],
                tuple(
                    DiagramNode(
                        "題" * pages.DIAGRAM_TITLE_HARD_LIMIT,
                        "字" * pages.DIAGRAM_TEXT_HARD_LIMIT,
                        "think",
                    )
                    for _index in range(3)
                ),
            )
        heading = "標" * pages.HEADING_HARD_LIMITS[page_type]
        source_label = "" if page_type == "cta" else f"來源：{company} · 2026-08-23"
        built.append(CarouselPage(number,page_type,heading,sections,diagram,source_label))
    return CarouselDraft((source,),tuple(built))


def build_template_stress_cases(
    actual_case: TemplateStressCase | None = None,
) -> tuple[TemplateStressCase, ...]:
    assets = Path(__file__).with_name("stress_assets")
    companies = (("SUN","logo-wide.svg"),("Billow AI Labs","logo-tall.svg"),("Shiraz AI","logo-wide.svg"))
    fixed = tuple(TemplateStressCase(_fixed_draft(company),company,BrandAsset(company,assets/filename,"https://example.com/logo","2026-08-23"),company) for company,filename in companies)
    return ((actual_case,) if actual_case else ()) + fixed
