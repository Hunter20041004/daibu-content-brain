import json

import pytest

from daibu.company_diversity import (
    AI_INFRASTRUCTURE,
    CONSUMER_CREATOR,
    ENTERPRISE_INDUSTRY,
    ROBOTICS_PHYSICAL,
    SCIENCE_HEALTH_BIOTECH,
    ClassifiedCompany,
    CompanyClassificationResponseError,
    build_classification_prompt,
    describe_shortage,
    parse_classifications,
    select_diverse_companies,
)
from daibu.models import CompanyLead


def _lead(company: str) -> CompanyLead:
    return CompanyLead(
        company,
        f"{company} description",
        f"https://example.com/{company.casefold()}",
        source_name="Test Directory",
    )


def _classified(company: str, category: str) -> ClassifiedCompany:
    return ClassifiedCompany(_lead(company), category)


def test_parse_classifications_returns_every_company_in_input_order():
    leads = [_lead("Railway"), _lead("Feldy")]
    raw = json.dumps(
        [
            {"company": "Feldy", "category": ENTERPRISE_INDUSTRY},
            {"company": "Railway", "category": AI_INFRASTRUCTURE},
        ]
    )

    result = parse_classifications(raw, leads)

    assert [item.lead.company for item in result] == ["Railway", "Feldy"]
    assert [item.category for item in result] == [
        AI_INFRASTRUCTURE,
        ENTERPRISE_INDUSTRY,
    ]


def test_parse_classifications_rejects_missing_company():
    leads = [_lead("Railway"), _lead("Feldy")]
    raw = json.dumps(
        [{"company": "Railway", "category": AI_INFRASTRUCTURE}]
    )

    with pytest.raises(CompanyClassificationResponseError, match="缺少"):
        parse_classifications(raw, leads)


def test_parse_classifications_rejects_duplicate_company():
    leads = [_lead("Railway")]
    raw = json.dumps(
        [
            {"company": "Railway", "category": AI_INFRASTRUCTURE},
            {"company": "Railway", "category": AI_INFRASTRUCTURE},
        ]
    )

    with pytest.raises(CompanyClassificationResponseError, match="重複"):
        parse_classifications(raw, leads)


def test_parse_classifications_rejects_unknown_company():
    leads = [_lead("Railway")]
    raw = json.dumps(
        [{"company": "Impostor", "category": AI_INFRASTRUCTURE}]
    )

    with pytest.raises(CompanyClassificationResponseError, match="未知"):
        parse_classifications(raw, leads)


def test_parse_classifications_rejects_invalid_category():
    raw = json.dumps(
        [{"company": "Railway", "category": "everything_ai"}]
    )

    with pytest.raises(CompanyClassificationResponseError, match="類別"):
        parse_classifications(raw, [_lead("Railway")])


def test_parse_classifications_rejects_non_object_rows():
    raw = json.dumps(
        [
            {"company": "Railway", "category": AI_INFRASTRUCTURE},
            "extra",
        ]
    )

    with pytest.raises(CompanyClassificationResponseError, match="物件"):
        parse_classifications(raw, [_lead("Railway")])


def test_classification_prompt_uses_core_product_and_approved_examples():
    prompt = build_classification_prompt([_lead("Acme")])

    assert "核心產品" in prompt
    assert "主要客戶" in prompt
    assert "Railway" in prompt and AI_INFRASTRUCTURE in prompt
    assert "Feldy" in prompt and ENTERPRISE_INDUSTRY in prompt
    assert "Risklytics" in prompt
    assert "Acme description" in prompt


def test_selector_caps_infrastructure_at_one():
    items = [
        _classified("Infra1", AI_INFRASTRUCTURE),
        _classified("Infra2", AI_INFRASTRUCTURE),
        _classified("Infra3", AI_INFRASTRUCTURE),
        _classified("Work1", ENTERPRISE_INDUSTRY),
        _classified("Work2", ENTERPRISE_INDUSTRY),
        _classified("Person1", CONSUMER_CREATOR),
        _classified("Person2", CONSUMER_CREATOR),
    ]

    selected = select_diverse_companies(items)

    assert selected is not None
    assert sum(
        item.category == AI_INFRASTRUCTURE for item in selected
    ) == 1


def test_selector_caps_every_other_category_at_two():
    items = [
        _classified("Work1", ENTERPRISE_INDUSTRY),
        _classified("Work2", ENTERPRISE_INDUSTRY),
        _classified("Work3", ENTERPRISE_INDUSTRY),
        _classified("Infra", AI_INFRASTRUCTURE),
        _classified("Person", CONSUMER_CREATOR),
        _classified("Robot", ROBOTICS_PHYSICAL),
    ]

    selected = select_diverse_companies(items)

    assert selected is not None
    assert sum(
        item.category == ENTERPRISE_INDUSTRY for item in selected
    ) <= 2


def test_selector_requires_three_categories():
    items = [
        _classified("Infra", AI_INFRASTRUCTURE),
        _classified("Work1", ENTERPRISE_INDUSTRY),
        _classified("Work2", ENTERPRISE_INDUSTRY),
        _classified("Person1", CONSUMER_CREATOR),
        _classified("Person2", CONSUMER_CREATOR),
    ]

    selected = select_diverse_companies(items)

    assert selected is not None
    assert len({item.category for item in selected}) >= 3


def test_selector_returns_exactly_five_and_prefers_more_categories():
    items = [
        _classified("Work1", ENTERPRISE_INDUSTRY),
        _classified("Work2", ENTERPRISE_INDUSTRY),
        _classified("Person1", CONSUMER_CREATOR),
        _classified("Person2", CONSUMER_CREATOR),
        _classified("Infra", AI_INFRASTRUCTURE),
        _classified("Robot", ROBOTICS_PHYSICAL),
        _classified("Health", SCIENCE_HEALTH_BIOTECH),
    ]

    selected = select_diverse_companies(items)

    assert selected is not None
    assert len(selected) == 5
    assert len({item.category for item in selected}) == 5


def test_selector_returns_none_when_no_combination_exists():
    items = [
        _classified(f"Infra{index}", AI_INFRASTRUCTURE)
        for index in range(6)
    ]

    assert select_diverse_companies(items) is None


def test_shortage_message_reports_inspected_count_and_category_counts():
    items = [
        _classified("Infra1", AI_INFRASTRUCTURE),
        _classified("Infra2", AI_INFRASTRUCTURE),
        _classified("Work", ENTERPRISE_INDUSTRY),
    ]

    message = describe_shortage(items, inspected_count=40)

    assert "已檢查 40 家" in message
    assert "AI 基礎建設 2 家" in message
    assert "企業／產業應用 1 家" in message
    assert "無法湊出 5 家且至少 3 類" in message
