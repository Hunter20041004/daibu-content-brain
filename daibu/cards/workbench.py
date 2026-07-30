"""Pure state decisions for the carousel workbench."""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict
from typing import Protocol

from daibu.cards.schema import BrandAsset, CarouselDraft, VerifiedSource


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


def draft_fingerprint(draft: CarouselDraft) -> str:
    serialized = json.dumps(
        asdict(draft),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def cached_pngs(
    state: Mapping[str, object],
    idea_id: int,
    draft: CarouselDraft,
) -> list[bytes] | None:
    try:
        cached = state[f"carousel-png-{idea_id}"]
    except KeyError:
        return None
    if not isinstance(cached, tuple) or len(cached) != 2:
        return None
    fingerprint, pngs = cached
    if fingerprint != draft_fingerprint(draft) or not isinstance(pngs, list):
        return None
    return pngs
