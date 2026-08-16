"""Fetch unconfirmed Logo candidates from Brandfetch by official domain."""

import ssl
from collections.abc import Callable
from urllib.parse import quote
from urllib.request import Request, urlopen

import certifi

from daibu.cards import logo
from daibu.cards.logo_discovery import LogoCandidate
from daibu.cards.official_site import OfficialSite


class BrandfetchNotConfigured(ValueError):
    pass


def _asset_url(
    domain: str,
    kind: str,
    theme: str,
    client_id: str,
) -> str:
    path = (
        f"domain/{quote(domain, safe='.')}/theme/{theme}/"
        f"fallback/404/type/{kind}.svg"
    )
    return f"https://cdn.brandfetch.io/{path}?c={quote(client_id, safe='')}"


def _download(url: str) -> tuple[bytes, str, int]:
    context = ssl.create_default_context(cafile=certifi.where())
    request = Request(
        url,
        headers={"User-Agent": "daibu-content-brain/1.0"},
    )
    with urlopen(request, timeout=15, context=context) as response:
        return (
            response.read(logo.MAX_FILE_BYTES + 1),
            response.headers.get_content_type(),
            response.status,
        )


def fetch_candidates(
    site: OfficialSite,
    *,
    client_id: str | None = None,
    fetch_fn: Callable[[str], tuple[bytes, str, int]] | None = None,
) -> tuple[LogoCandidate, ...]:
    if not (client_id or "").strip():
        raise BrandfetchNotConfigured(
            "尚未設定 Brandfetch Client ID，仍可手動上傳 Logo。"
        )
    fetch = fetch_fn or _download
    candidates: list[LogoCandidate] = []
    seen_data: set[bytes] = set()
    for kind in ("logo", "symbol"):
        for theme in ("dark", "light"):
            asset_url = _asset_url(site.domain, kind, theme, client_id or "")
            try:
                data, content_type, status = fetch(asset_url)
                if status != 200 or not data or content_type != "image/svg+xml":
                    continue
                filename = f"{site.domain.replace('.', '-')}-{kind}-{theme}.svg"
                logo.validate_upload(data, filename)
            except (OSError, ValueError):
                continue
            if data in seen_data:
                continue
            seen_data.add(data)
            candidates.append(
                LogoCandidate(
                    site.company,
                    filename,
                    data,
                    site.website_url,
                    asset_url.split("?", maxsplit=1)[0],
                    site.website_url,
                    "brandfetch",
                    kind,
                    theme,
                    "needs_review",
                    (
                        "Brandfetch 網域與官網一致；官網無可交叉比對素材",
                    ),
                )
            )
    return tuple(candidates[:3])
