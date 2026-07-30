"""Package rendered carousel pages for download."""

import zipfile
from datetime import date
from io import BytesIO
import re

from daibu.cards import pages

PAGE_FILENAMES = tuple(
    f"{index:02d}-{page_type}.png"
    for index, page_type in enumerate(pages.PAGE_TYPES, start=1)
)
_NON_SLUG = re.compile(r"[^a-z0-9]+")


def company_slug(company: str) -> str:
    return _NON_SLUG.sub("-", company.strip().casefold()).strip("-") or (
        "carousel"
    )


def zip_name(company: str, today: date) -> str:
    return f"{company_slug(company)}-carousel-{today:%Y%m%d}.zip"


def carousel_zip(pngs: list[bytes]) -> bytes:
    if len(pngs) != len(PAGE_FILENAMES):
        raise ValueError("輪播圖必須剛好包含七張")
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename, data in zip(PAGE_FILENAMES, pngs):
            archive.writestr(filename, data)
    return buffer.getvalue()
