"""Verify startup eligibility against exact web-search evidence."""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Callable
from datetime import datetime

from daibu import clock, db
from daibu.models import (
    CompanyEligibility,
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


def evaluate_companies(
    companies: list[str],
    search_fn: Callable[..., list[Material]],
    generate_text: Callable[[str], str],
    *,
    current_year: int,
    checked_at: str | None = None,
) -> dict[str, CompanyEligibility]:
    unique = {
        normalize_company(company): company.strip()
        for company in companies
        if company.strip()
    }
    if not unique:
        return {}
    materials_by_company: dict[str, list[Material]] = {}
    for company_key, company in unique.items():
        query = (
            f"{company} founded founding year funding private company IPO "
            "publicly traded acquired acquisition subsidiary official"
        )
        try:
            materials_by_company[company_key] = search_fn(query, limit=5)
        except Exception:
            materials_by_company[company_key] = []
    company_names = list(unique.values())
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
        if not any(
            material.url == source_url and quote in material.snippet
            for material in materials
        ):
            continue
        matched.append(EligibilityEvidence(claim, source_url, quote))
    return tuple(matched)


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
