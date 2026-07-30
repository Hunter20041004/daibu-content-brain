"""Store verified company logos for reuse."""

import hashlib
import os
import re
import sqlite3
from pathlib import Path

from daibu import db
from daibu.cards import logo
from daibu.cards.schema import BrandAsset

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def logo_dir() -> Path:
    return Path(os.environ.get("DAIBU_LOGO_DIR", "assets/logos"))


def _company_slug(company: str) -> str:
    return _NON_SLUG.sub("-", company.strip().casefold()).strip("-") or "logo"


def store_logo(
    conn: sqlite3.Connection,
    company: str,
    filename: str,
    data: bytes,
    official_source_url: str,
    verified_at: str,
) -> BrandAsset:
    logo.validate_upload(data, filename)
    logo.validate_source_metadata(official_source_url, verified_at)
    directory = logo_dir()
    directory.mkdir(parents=True, exist_ok=True)
    suffix = Path(filename).suffix.lower()
    digest = hashlib.sha256(data).hexdigest()[:12]
    path = directory / f"{_company_slug(company)}-{digest}{suffix}"
    path.write_bytes(data)
    asset = BrandAsset(
        company.strip(),
        path,
        official_source_url.strip(),
        verified_at.strip(),
    )
    db.save_brand_asset(conn, asset)
    logo.logo_data_uri(asset, company)
    return asset
