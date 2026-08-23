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
    diagram_kinds = {"problem":"problem-chain","how-ai":"ai-generate","results":"before-after","why-care":"signals"}
    built = []
    for number, page_type in enumerate(pages.PAGE_TYPES, start=1):
        labels = pages.SECTION_LABEL_SEQUENCES[page_type][
            1 if page_type == "why-care" else 0
        ]
        sections = tuple(ContentSection(label, f"{label}的安全文字。", ("S1",), ()) for label in labels)
        diagram = None
        if page_type in diagram_kinds:
            diagram = DiagramSpec(diagram_kinds[page_type], tuple(DiagramNode(f"步驟 {i}", "安全驗證文字", "think") for i in range(1,4)))
        heading = "模板版面驗證"
        built.append(CarouselPage(number,page_type,heading,sections,diagram,f"來源：{company} · 2026-08-23"))
    return CarouselDraft((source,),tuple(built))


def build_template_stress_cases(
    actual_case: TemplateStressCase | None = None,
) -> tuple[TemplateStressCase, ...]:
    assets = Path(__file__).with_name("stress_assets")
    companies = (("SUN","logo-wide.svg"),("Billow AI Labs","logo-tall.svg"),("Shiraz AI","logo-wide.svg"))
    fixed = tuple(TemplateStressCase(_fixed_draft(company),company,BrandAsset(company,assets/filename,"https://example.com/logo","2026-08-23"),company) for company,filename in companies)
    return ((actual_case,) if actual_case else ()) + fixed
