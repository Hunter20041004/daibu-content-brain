from collections import Counter
from dataclasses import dataclass
from itertools import combinations
import json

from daibu.models import CompanyLead


AI_INFRASTRUCTURE = "ai_infrastructure"
ENTERPRISE_INDUSTRY = "enterprise_industry"
CONSUMER_CREATOR = "consumer_creator"
ROBOTICS_PHYSICAL = "robotics_physical"
SCIENCE_HEALTH_BIOTECH = "science_health_biotech"
GOVERNANCE_SOCIAL_BUSINESS = "governance_social_business"

CATEGORIES = (
    AI_INFRASTRUCTURE,
    ENTERPRISE_INDUSTRY,
    CONSUMER_CREATOR,
    ROBOTICS_PHYSICAL,
    SCIENCE_HEALTH_BIOTECH,
    GOVERNANCE_SOCIAL_BUSINESS,
)
CATEGORY_LABELS = {
    AI_INFRASTRUCTURE: "AI 基礎建設",
    ENTERPRISE_INDUSTRY: "企業／產業應用",
    CONSUMER_CREATOR: "消費者／創作者工具",
    ROBOTICS_PHYSICAL: "機器人／實體世界",
    SCIENCE_HEALTH_BIOTECH: "科學／醫療／生技",
    GOVERNANCE_SOCIAL_BUSINESS: "治理／社會／新商業模式",
}


class CompanyClassificationResponseError(ValueError):
    pass


@dataclass(frozen=True)
class ClassifiedCompany:
    lead: CompanyLead
    category: str


def build_classification_prompt(leads: list[CompanyLead]) -> str:
    payload = [
        {
            "company": lead.company,
            "description": lead.description,
            "tags": list(lead.tags),
            "source": lead.source_name,
        }
        for lead in leads
    ]
    return f"""
請依公司的核心產品與主要客戶，替每家公司選一個且只有一個主類別。
不要依這次可能採用的貼文角度改分類。

允許類別：{json.dumps(CATEGORIES, ensure_ascii=False)}
校準例子：
- Railway、Dipole、Marengo：{AI_INFRASTRUCTURE}
- Feldy、Billow AI Labs、Almanac：{ENTERPRISE_INDUSTRY}
- Risklytics：{GOVERNANCE_SOCIAL_BUSINESS}

公司資料：{json.dumps(payload, ensure_ascii=False)}

只輸出 JSON 陣列。每家公司恰好一個物件，只含 company 與 category；
不得新增、刪除或重複公司。
""".strip()


def select_diverse_companies(
    items: list[ClassifiedCompany],
    count: int = 5,
) -> tuple[ClassifiedCompany, ...] | None:
    best: tuple[ClassifiedCompany, ...] | None = None
    best_category_count = -1
    for candidate in combinations(items, count):
        counts = Counter(item.category for item in candidate)
        if counts[AI_INFRASTRUCTURE] > 1:
            continue
        if any(
            amount > 2
            for category, amount in counts.items()
            if category != AI_INFRASTRUCTURE
        ):
            continue
        if len(counts) < 3:
            continue
        if len(counts) > best_category_count:
            best = candidate
            best_category_count = len(counts)
    return best


def describe_shortage(
    items: list[ClassifiedCompany],
    inspected_count: int,
) -> str:
    counts = Counter(item.category for item in items)
    detail = "、".join(
        f"{CATEGORY_LABELS[category]} {counts[category]} 家"
        for category in CATEGORIES
        if counts[category]
    )
    return (
        f"已檢查 {inspected_count} 家；目前可用分類：{detail}。"
        "無法湊出 5 家且至少 3 類，這次沒有新增候選。"
    )


def parse_classifications(
    raw: str,
    leads: list[CompanyLead],
) -> tuple[ClassifiedCompany, ...]:
    array_start = raw.find("[")
    if array_start < 0:
        raise CompanyClassificationResponseError("分類回覆缺少 JSON 陣列")
    try:
        decoded, _ = json.JSONDecoder().raw_decode(raw[array_start:])
    except (TypeError, ValueError) as error:
        raise CompanyClassificationResponseError("分類回覆不是有效 JSON") from error
    if not isinstance(decoded, list):
        raise CompanyClassificationResponseError("分類回覆必須是陣列")
    if any(not isinstance(item, dict) for item in decoded):
        raise CompanyClassificationResponseError("分類陣列每一項都必須是物件")
    valid_rows = list(decoded)
    keys = [
        str(item.get("company", "")).strip().casefold()
        for item in valid_rows
    ]
    if len(keys) != len(set(keys)):
        raise CompanyClassificationResponseError("分類回覆有重複公司")
    rows = dict(zip(keys, valid_rows))
    expected_keys = {lead.company.strip().casefold() for lead in leads}
    if set(rows) - expected_keys:
        raise CompanyClassificationResponseError("分類回覆包含未知公司")
    if any(
        str(item.get("category", "")) not in CATEGORIES
        for item in rows.values()
    ):
        raise CompanyClassificationResponseError("分類回覆包含不支援的類別")
    try:
        return tuple(
            ClassifiedCompany(
                lead,
                str(rows[lead.company.strip().casefold()]["category"]),
            )
            for lead in leads
        )
    except (KeyError, TypeError) as error:
        raise CompanyClassificationResponseError(
            "分類回覆缺少公司或類別"
        ) from error
