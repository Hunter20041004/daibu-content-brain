"""Verify startup eligibility against exact web-search evidence."""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Callable
from datetime import datetime
from urllib.parse import urlparse

from daibu import clock, db
from daibu.models import (
    CompanyEligibility,
    CompanyLead,
    EligibilityEvidence,
    Material,
)


ALLOWED_CLAIMS = {
    "founded",
    "private_independent",
    "public",
    "acquired",
}


class EligibilityResponseError(ValueError):
    pass


def normalize_company(company: str) -> str:
    return company.strip().casefold()


def build_prompt(
    companies: list[str],
    materials_by_company: dict[str, list[Material]],
    *,
    current_year: int,
) -> str:
    source_payload = {
        company: [
            {
                "title": material.title,
                "url": material.url,
                "snippet": material.snippet,
            }
            for material in materials_by_company.get(normalize_company(company), [])
        ]
        for company in companies
    }
    return f"""你是新創公司資格查核員。現在是 {current_year} 年。
只根據下方搜尋資料，逐家公司判斷：
1. 成立年份；2. 是否仍為私人且獨立的公司；3. 是否已上市或被收購。
成立至今不得超過十年，且必須仍為私人獨立公司，才可能符合資格。

只回傳 JSON 陣列，不要 markdown。每家公司都必須有一筆：
{{"company":"原名","founded_year":2020 或 null,
"ownership_status":"private_independent|public|acquired|unknown",
"reason":"簡短繁體中文理由",
"evidence":[{{"claim":"founded|private_independent|public|acquired",
"source_url":"必須逐字取自搜尋資料的 URL",
"quote":"必須逐字取自該 URL snippet 的短引文"}}]}}
沒有足夠證據就用 unknown，不可臆測。募資輪次或投資人資料可作為仍為私人獨立公司的證據；
IPO、股票代號或公開交易是 public；完成收購或成為子公司是 acquired。

待查公司：{json.dumps(companies, ensure_ascii=False)}
搜尋資料：{json.dumps(source_payload, ensure_ascii=False)}
"""


def _company_name(company: str | CompanyLead) -> str:
    return company.company if isinstance(company, CompanyLead) else company


def _search_query(company: str | CompanyLead) -> str:
    name = _company_name(company).strip()
    identity = []
    if isinstance(company, CompanyLead):
        identity.extend(
            value
            for value in (
                company.official_url,
                company.profile_url,
                company.batch_or_cohort,
                str(company.founded_year) if company.founded_year else "",
            )
            if value
        )
    return " ".join(
        [
            f'"{name}"',
            *identity,
            "founded founding year funding private company IPO",
            "publicly traded acquired acquisition subsidiary official",
        ]
    )


def _identity_material(company: str | CompanyLead) -> Material | None:
    if not isinstance(company, CompanyLead):
        return None
    source_url = company.profile_url or company.discovery_url
    if not source_url:
        return None
    facts = [company.description.strip()]
    if company.founded_year is not None:
        facts.append(
            f"{company.company.strip()} was founded in {company.founded_year}."
        )
    if company.batch_or_cohort:
        facts.append(f"Cohort: {company.batch_or_cohort}.")
    if company.official_url:
        facts.append(f"Official website: {company.official_url}.")
    if company.ownership_status:
        facts.append(f"Directory status: {company.ownership_status}.")
    return Material(
        f"{company.company.strip()} directory profile",
        source_url,
        " ".join(fact for fact in facts if fact),
    )


def evaluate_companies(
    companies: list[str | CompanyLead],
    search_fn: Callable[..., list[Material]],
    generate_text: Callable[[str], str],
    *,
    current_year: int,
    checked_at: str | None = None,
) -> dict[str, CompanyEligibility]:
    unique = {
        normalize_company(_company_name(company)): company
        for company in companies
        if _company_name(company).strip()
    }
    if not unique:
        return {}
    materials_by_company: dict[str, list[Material]] = {}
    for company_key, company in unique.items():
        query = _search_query(company)
        identity_material = _identity_material(company)
        try:
            searched = search_fn(query, limit=5)
        except Exception:
            searched = []
        materials_by_company[company_key] = [
            *([identity_material] if identity_material else []),
            *searched,
        ]
    company_names = [_company_name(company).strip() for company in unique.values()]
    raw = generate_text(
        build_prompt(
            company_names,
            materials_by_company,
            current_year=current_year,
        )
    )
    return verify_response(
        raw,
        company_names,
        materials_by_company,
        current_year=current_year,
        checked_at=checked_at or clock.now(),
        identities={
            company_key: company
            for company_key, company in unique.items()
            if isinstance(company, CompanyLead)
        },
    )


def backfill_existing(
    conn: sqlite3.Connection,
    provider: object,
    search_fn: Callable[..., list[Material]],
    *,
    current_year: int | None = None,
) -> dict[str, CompanyEligibility]:
    cached = db.get_company_eligibilities(conn)
    rows = conn.execute(
        """
        SELECT ideas.company
        FROM ideas
        JOIN themes ON themes.id = ideas.theme_id
        WHERE themes.content_kind = 'company_profile'
          AND TRIM(ideas.company) <> ''
        ORDER BY ideas.id
        """
    ).fetchall()
    unchecked: dict[str, str] = {}
    for row in rows:
        company = str(row["company"]).strip()
        company_key = normalize_company(company)
        if company_key not in cached:
            unchecked.setdefault(company_key, company)
    if not unchecked:
        return {}
    generate_text = getattr(provider, "generate_text")
    records = evaluate_companies(
        list(unchecked.values()),
        search_fn,
        generate_text,
        current_year=current_year or datetime.now().year,
    )
    for record in records.values():
        db.save_company_eligibility(conn, record)
    return records


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="回填既有公司的新創資格")
    subparsers = parser.add_subparsers(dest="command", required=True)
    backfill_parser = subparsers.add_parser("backfill")
    backfill_parser.add_argument(
        "--db",
        default=os.getenv("DAIBU_DB_PATH", "daibu.db"),
        help="SQLite 資料庫路徑",
    )
    args = parser.parse_args()
    if args.command == "backfill":
        from daibu.fetch import search
        from daibu.llm import base

        conn = db.connect(args.db)
        try:
            db.init_schema(conn)
            records = backfill_existing(
                conn,
                base.get_provider_from_env(),
                search.search_web,
            )
        finally:
            conn.close()
        print(f"已查核 {len(records)} 家公司。")


def _decode_array(raw: str) -> list[object]:
    start = raw.find("[")
    if start < 0:
        raise EligibilityResponseError("公司資格判定找不到 JSON 陣列")
    try:
        decoded, _ = json.JSONDecoder().raw_decode(raw[start:])
    except ValueError as error:
        raise EligibilityResponseError("公司資格判定 JSON 無法解析") from error
    if not isinstance(decoded, list):
        raise EligibilityResponseError("公司資格判定必須是 JSON 陣列")
    return decoded


def _matching_evidence(
    items: object,
    materials: list[Material],
    identity: CompanyLead | None = None,
) -> tuple[EligibilityEvidence, ...]:
    if not isinstance(items, list):
        return ()
    matched: list[EligibilityEvidence] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim", ""))
        source_url = str(item.get("source_url", ""))
        quote = str(item.get("quote", ""))
        if claim not in ALLOWED_CLAIMS or not quote:
            continue
        material = next(
            (
                material
                for material in materials
                if material.url == source_url and quote in material.snippet
            ),
            None,
        )
        if material is None:
            continue
        if (
            claim in {"founded", "public", "acquired"}
            and identity is not None
            and not _material_matches_identity(material, identity)
        ):
            continue
        matched.append(EligibilityEvidence(claim, source_url, quote))
    return tuple(matched)


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").casefold().removeprefix("www.")


def _material_matches_identity(
    material: Material,
    identity: CompanyLead,
) -> bool:
    if material.url in {
        identity.discovery_url,
        identity.profile_url,
        identity.official_url,
    }:
        return True
    official_host = _host(identity.official_url)
    if not official_host:
        return True
    material_text = " ".join(
        (material.url, material.title, material.snippet)
    ).casefold()
    return _host(material.url) == official_host or official_host in material_text


def _unknown(
    company: str,
    checked_at: str,
    reason: str = "公開資料不足，無法確認新創資格",
) -> CompanyEligibility:
    return CompanyEligibility(
        company_key=normalize_company(company),
        company=company.strip(),
        verdict="unknown",
        founded_year=None,
        ownership_status="unknown",
        reason=reason,
        evidence=(),
        checked_at=checked_at,
    )


def verify_response(
    raw: str,
    companies: list[str],
    materials_by_company: dict[str, list[Material]],
    *,
    current_year: int,
    checked_at: str,
    identities: dict[str, CompanyLead] | None = None,
) -> dict[str, CompanyEligibility]:
    requested = {normalize_company(company): company for company in companies}
    records: dict[str, CompanyEligibility] = {}
    for item in _decode_array(raw):
        if not isinstance(item, dict):
            continue
        company = str(item.get("company", "")).strip()
        company_key = normalize_company(company)
        if company_key not in requested or company_key in records:
            continue
        raw_year = item.get("founded_year")
        founded_year = (
            raw_year
            if isinstance(raw_year, int) and not isinstance(raw_year, bool)
            else None
        )
        ownership_status = str(item.get("ownership_status", "unknown"))
        evidence = _matching_evidence(
            item.get("evidence"),
            materials_by_company.get(company_key, []),
            (identities or {}).get(company_key),
        )
        claims = {proof.claim for proof in evidence}
        ownership_claims = claims & {
            "private_independent",
            "public",
            "acquired",
        }
        has_conflicting_ownership = len(ownership_claims) > 1
        has_founded_proof = (
            founded_year is not None
            and any(
                proof.claim == "founded"
                and str(founded_year) in proof.quote
                for proof in evidence
            )
        )
        is_eligible = (
            has_founded_proof
            and 0 <= current_year - founded_year <= 10
            and ownership_status == "private_independent"
            and "private_independent" in claims
            and not has_conflicting_ownership
        )
        is_too_old = (
            has_founded_proof
            and current_year - founded_year > 10
        )
        is_public = ownership_status == "public" and "public" in claims
        is_acquired = ownership_status == "acquired" and "acquired" in claims
        if has_conflicting_ownership:
            records[company_key] = _unknown(
                requested[company_key],
                checked_at,
                "公開資料對公司所有權的描述互相矛盾",
            )
        elif is_public or is_acquired:
            records[company_key] = CompanyEligibility(
                company_key=company_key,
                company=requested[company_key].strip(),
                verdict="ineligible",
                founded_year=founded_year if has_founded_proof else None,
                ownership_status=ownership_status,
                reason=str(item.get("reason", "")).strip()
                or ("已公開上市" if is_public else "已被收購"),
                evidence=evidence,
                checked_at=checked_at,
            )
        elif is_too_old:
            records[company_key] = CompanyEligibility(
                company_key=company_key,
                company=requested[company_key].strip(),
                verdict="ineligible",
                founded_year=founded_year,
                ownership_status=ownership_status,
                reason=str(item.get("reason", "")).strip()
                or "成立已超過十年",
                evidence=evidence,
                checked_at=checked_at,
            )
        elif is_eligible:
            records[company_key] = CompanyEligibility(
                company_key=company_key,
                company=requested[company_key].strip(),
                verdict="eligible",
                founded_year=founded_year,
                ownership_status=ownership_status,
                reason=str(item.get("reason", "")).strip()
                or "成立不超過十年，且仍為私人獨立公司",
                evidence=evidence,
                checked_at=checked_at,
            )
        else:
            records[company_key] = _unknown(
                requested[company_key],
                checked_at,
            )
    for company_key, company in requested.items():
        records.setdefault(company_key, _unknown(company, checked_at))
    return records


if __name__ == "__main__":
    _main()
