from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, Mapping


CollisionPolicy = Literal["avoid", "allow", "background"]


@dataclass(frozen=True)
class ElementRule:
    label: str
    text: bool = False
    collision: CollisionPolicy = "avoid"
    min_w: float = 24
    min_h: float = 24
    min_font_size: float = 22
    max_font_size: float = 132


def _rules(**rules: ElementRule) -> Mapping[str, ElementRule]:
    return MappingProxyType(rules)


LEGACY_ELEMENT_REGISTRY: Mapping[str, Mapping[str, ElementRule]] = MappingProxyType(
    {
        "cover": _rules(
            series=ElementRule("系列名稱", True),
            **{
                "company-logo": ElementRule("企業 Logo"),
                "company-name": ElementRule(
                    "企業名稱",
                    True,
                    "allow",
                    max_font_size=320,
                ),
                "heading": ElementRule("封面標題", True),
                "rule": ElementRule("標題分隔線", False, "background", 24, 2),
                "positioning": ElementRule("一句話定位", True),
                "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
            },
        ),
        "who": _rules(
            header=ElementRule("頁首"),
            heading=ElementRule("頁面標題", True),
            positioning=ElementRule("白話定位", True),
            facts=ElementRule("基本資料", True),
            mascot=ElementRule("呆一布機器人", False, "allow", 120, 120),
        ),
        "problem": _rules(
            header=ElementRule("頁首"),
            heading=ElementRule("頁面標題", True),
            spine=ElementRule("問題脈絡線", False, "background", 2, 24),
            **{
                "stage-1": ElementRule("問題階段一", True),
                "stage-2": ElementRule("問題階段二", True),
                "stage-3": ElementRule("問題階段三", True),
                "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
            },
        ),
        "how-ai": _rules(
            header=ElementRule("頁首"),
            heading=ElementRule("頁面標題", True),
            spine=ElementRule("AI 流程線", False, "background", 2, 24),
            **{
                "step-1": ElementRule("流程一", True),
                "step-2": ElementRule("流程二", True),
                "step-3": ElementRule("流程三", True),
                "caution": ElementRule("要注意的點", True),
                "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
            },
        ),
        "results": _rules(
            header=ElementRule("頁首"),
            **{
                "before-title": ElementRule("改變前標題", True),
                "before-copy": ElementRule("改變前內容", True),
                "axis": ElementRule("對比軸線", False, "background", 2, 24),
                "to": ElementRule("到", True, "allow"),
                "after-title": ElementRule("改變後標題", True),
                "after-copy": ElementRule("改變後內容", True),
                "summary": ElementRule("結果摘要", True),
                "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
            },
        ),
        "why-care": _rules(
            header=ElementRule("頁首"),
            heading=ElementRule("頁面標題", True),
            **{
                "signal-1": ElementRule("觀察訊號一", True),
                "signal-2": ElementRule("觀察訊號二", True),
                "signal-3": ElementRule("觀察訊號三", True),
                "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
            },
        ),
        "cta": _rules(
            header=ElementRule("頁首"),
            heading=ElementRule("頁面標題", True),
            thesis=ElementRule("收束結論", True),
            question=ElementRule("讀者問題", True),
            invitation=ElementRule("互動邀請", True, "allow"),
            mascot=ElementRule("呆一布機器人", False, "allow", 120, 120),
        ),
    }
)


_v2_pages = dict(LEGACY_ELEMENT_REGISTRY)
_v2_pages["who"] = _rules(
    header=ElementRule("頁首"),
    heading=ElementRule("頁面標題", True),
    **{
        "positioning-bg": ElementRule(
            "白話定位背景", False, "background"
        ),
        "positioning-label": ElementRule("白話定位標籤", True),
        "positioning-body": ElementRule("白話定位正文", True),
        "facts-bg": ElementRule("基本資料背景", False, "background"),
        "facts-label": ElementRule("基本資料標籤", True),
        "facts-body": ElementRule("基本資料正文", True),
        "mascot": ElementRule(
            "呆一布機器人", False, "allow", 120, 120
        ),
    },
)
for _page_type in ("who", "problem", "how-ai", "results", "why-care", "cta"):
    _page_rules = dict(_v2_pages[_page_type])
    _page_rules.pop("header")
    _page_rules["series"] = ElementRule("系列名稱", True)
    _page_rules["company-name"] = ElementRule(
        "企業名稱", True, "allow", max_font_size=320
    )
    _v2_pages[_page_type] = MappingProxyType(_page_rules)

_problem_rules = dict(_v2_pages["problem"])
for _index in range(1, 4):
    _problem_rules.pop(f"stage-{_index}")
    _problem_rules[f"stage-{_index}-bg"] = ElementRule(
        f"問題階段{_index}背景", False, "background"
    )
    _problem_rules[f"stage-{_index}-label"] = ElementRule(
        f"問題階段{_index}標籤", True
    )
    _problem_rules[f"stage-{_index}-body"] = ElementRule(
        f"問題階段{_index}主句", True
    )
for _index in (1, 3):
    _problem_rules[f"stage-{_index}-context"] = ElementRule(
        f"問題階段{_index}補充", True
    )
_v2_pages["problem"] = MappingProxyType(_problem_rules)

_how_rules = dict(_v2_pages["how-ai"])
for _index in range(1, 4):
    _how_rules.pop(f"step-{_index}")
    _how_rules[f"step-{_index}-bg"] = ElementRule(
        f"流程{_index}背景", False, "background"
    )
    _how_rules[f"step-{_index}-label"] = ElementRule(
        f"流程{_index}標籤", True
    )
    _how_rules[f"step-{_index}-body"] = ElementRule(
        f"流程{_index}主句", True
    )
_how_rules.pop("caution")
_how_rules["caution-bg"] = ElementRule(
    "注意區背景", False, "background"
)
_how_rules["caution-label"] = ElementRule("注意區標籤", True)
_how_rules["caution-body"] = ElementRule("注意事項正文", True)
_v2_pages["how-ai"] = MappingProxyType(_how_rules)

_results_rules = dict(_v2_pages["results"])
_results_rules.pop("before-copy")
_results_rules.pop("after-copy")
_results_rules.update(
    {
        "results-before-bg": ElementRule(
            "改變前背景", False, "background"
        ),
        "results-after-bg": ElementRule(
            "改變後背景", False, "background"
        ),
        "before-body": ElementRule("改變前主句", True),
        "before-context": ElementRule("改變前補充", True),
        "after-label": ElementRule("改變後標籤", True),
        "after-body": ElementRule("改變後主句", True),
        "after-context": ElementRule("改變後補充", True),
    }
)
_v2_pages["results"] = MappingProxyType(_results_rules)

_signals_rules = dict(_v2_pages["why-care"])
for _index in range(1, 4):
    _signals_rules.pop(f"signal-{_index}")
    _signals_rules[f"signal-{_index}-bg"] = ElementRule(
        f"觀察訊號{_index}背景", False, "background"
    )
    _signals_rules[f"signal-{_index}-label"] = ElementRule(
        f"觀察訊號{_index}標籤", True
    )
    _signals_rules[f"signal-{_index}-body"] = ElementRule(
        f"觀察訊號{_index}主句", True
    )
    _signals_rules[f"signal-{_index}-context"] = ElementRule(
        f"觀察訊號{_index}補充", True
    )
_v2_pages["why-care"] = MappingProxyType(_signals_rules)

_cta_rules = dict(_v2_pages["cta"])
for _name, _label in (("thesis", "收束結論"), ("question", "讀者問題")):
    _cta_rules.pop(_name)
    _cta_rules[f"{_name}-bg"] = ElementRule(
        f"{_label}背景", False, "background"
    )
    _cta_rules[f"{_name}-label"] = ElementRule(f"{_label}標籤", True)
    _cta_rules[f"{_name}-body"] = ElementRule(f"{_label}正文", True)
_v2_pages["cta"] = MappingProxyType(_cta_rules)
SCHEMA_V3_ELEMENT_REGISTRY: Mapping[
    str, Mapping[str, ElementRule]
] = MappingProxyType(
    {
        "cover": _rules(
            **{
                "company-logo": ElementRule("企業 Logo"),
                "company-name": ElementRule("企業名稱", True, "allow", max_font_size=180),
                "positioning": ElementRule("一句話定位", True),
                "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
            }
        ),
        "who": _rules(
            heading=ElementRule("頁面標題", True),
            logo=ElementRule("企業 Logo"),
            positioning=ElementRule("白話定位", True),
            facts=ElementRule("基本資料", True),
            reason=ElementRule("為什麼值得介紹", True),
            mascot=ElementRule("呆一布機器人", False, "allow", 120, 120),
        ),
        "problem": _rules(
            heading=ElementRule("頁面標題", True),
            current=ElementRule("現在怎麼做", True),
            opportunity=ElementRule("哪裡還能更好", True),
            spine=ElementRule("流程連接線", False, "background", 2, 24),
            **{
                "stage-1": ElementRule("現有流程", True),
                "stage-2": ElementRule("優化空間", True),
                "stage-3": ElementRule("釋放價值", True),
                "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
            },
        ),
        "how-ai": _rules(
            heading=ElementRule("頁面標題", True),
            **{
                "step-1": ElementRule("理解輸入", True),
                "step-2": ElementRule("分析處理", True),
                "step-3": ElementRule("交付結果", True),
                "traditional": ElementRule("傳統做法", True),
                "ai-role": ElementRule("AI 的角色", True),
                "human": ElementRule("人仍負責", True),
                "difference": ElementRule("關鍵差別", True),
                "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
            },
        ),
        "results": _rules(
            heading=ElementRule("頁面標題", True),
            audience=ElementRule("代表使用者", True),
            before=ElementRule("使用前", True),
            intervention=ElementRule("產品介入", True),
            after=ElementRule("使用後", True),
            **{
                "core-difference": ElementRule("核心差異", True),
                "value": ElementRule("帶來的價值", True),
                "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
            },
        ),
        "cta": _rules(
            invitation=ElementRule(
                "追蹤邀請", True, "allow", min_w=420, min_h=180, min_font_size=34
            ),
            mascot=ElementRule("呆一布機器人", False, "allow", 120, 120),
        ),
    }
)

ELEMENT_REGISTRY = SCHEMA_V3_ELEMENT_REGISTRY


def registry_for_schema(
    schema_version: int,
) -> Mapping[str, Mapping[str, ElementRule]]:
    if schema_version == 3:
        return SCHEMA_V3_ELEMENT_REGISTRY
    raise ValueError(f"不支援的 schema_version：{schema_version}")
