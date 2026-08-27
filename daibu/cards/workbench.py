"""Pure state decisions for the carousel workbench."""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict
from typing import Protocol

from daibu.cards import pages as carousel_pages
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
    return render_fingerprint(draft, 0, 0)


def render_fingerprint(
    draft: CarouselDraft,
    template_version_id: int,
    content_revision: int,
) -> str:
    serialized = json.dumps(
        {
            "content": asdict(draft),
            "template_version_id": template_version_id,
            "content_revision": content_revision,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def cached_pngs(
    state: Mapping[str, object],
    idea_id: int,
    draft: CarouselDraft,
    template_version_id: int,
    content_revision: int,
) -> list[bytes] | None:
    try:
        cached = state[f"carousel-png-{idea_id}"]
    except KeyError:
        return None
    if not isinstance(cached, tuple) or len(cached) != 2:
        return None
    fingerprint, pngs = cached
    if (
        fingerprint
        != render_fingerprint(
            draft,
            template_version_id,
            content_revision,
        )
        or not isinstance(pngs, list)
        or len(pngs) != len(carousel_pages.PAGE_TYPES)
    ):
        return None
    return pngs
