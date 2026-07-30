"""Pure state decisions for the carousel workbench."""

from typing import Protocol

from daibu.cards.schema import BrandAsset, VerifiedSource


class _IdeaWithCompany(Protocol):
    company: str


def missing_requirements(
    idea: _IdeaWithCompany,
    pack: tuple[VerifiedSource, ...],
    asset: BrandAsset | None,
) -> tuple[str, ...]:
    del asset
    missing = []
    if not idea.company.strip():
        missing.append("這則題目還沒有公司名")
    if not pack:
        missing.append("還沒有任何已查證來源")
    return tuple(missing)


def can_render(
    idea: _IdeaWithCompany,
    pack: tuple[VerifiedSource, ...],
    asset: BrandAsset | None,
) -> bool:
    return not missing_requirements(idea, pack, asset) and asset is not None
