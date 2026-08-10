"""Verify startup eligibility against exact web-search evidence."""

from __future__ import annotations

import json

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
