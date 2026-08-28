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


SCHEMA_V3_REGISTRY: Mapping[str, Mapping[str, ElementRule]] = MappingProxyType(
    {
        "cover": _rules(
            **{
                "company-logo": ElementRule("企業 Logo"),
                "company-name": ElementRule(
                    "企業名稱", True, "allow", max_font_size=180
                ),
                "heading": ElementRule("頁面標題", True),
                "positioning": ElementRule("一句話定位", True),
                "mascot": ElementRule(
                    "呆一布機器人", False, "allow", 120, 120
                ),
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
                "mascot": ElementRule(
                    "呆一布機器人", False, "allow", 120, 120
                ),
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
                "mascot": ElementRule(
                    "呆一布機器人", False, "allow", 120, 120
                ),
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
                "mascot": ElementRule(
                    "呆一布機器人", False, "allow", 120, 120
                ),
            },
        ),
        "cta": _rules(
            invitation=ElementRule(
                "追蹤邀請",
                True,
                "allow",
                min_w=420,
                min_h=180,
                min_font_size=34,
            ),
            mascot=ElementRule("呆一布機器人", False, "allow", 120, 120),
        ),
    }
)


def _text(label: str, *, collision: CollisionPolicy = "avoid", min_font_size: float = 12, max_font_size: float = 132) -> ElementRule:
    return ElementRule(
        label,
        True,
        collision,
        min_font_size=min_font_size,
        max_font_size=max_font_size,
    )


def _background(label: str) -> ElementRule:
    return ElementRule(label, collision="background")


ELEMENT_REGISTRY: Mapping[str, Mapping[str, ElementRule]] = MappingProxyType(
    {
        "cover": SCHEMA_V3_REGISTRY["cover"],
        "who": _rules(
            **{
                "page-label": _text("頁面｜英文眉標", collision="allow"),
                "heading": ElementRule("頁面標題", True),
                "logo": ElementRule("企業 Logo"),
                "identity-product": _text("身份流程｜AI 產品", collision="allow"),
                "identity-arrow-1": _text("身份流程｜箭頭一", collision="allow"),
                "identity-user": _text("身份流程｜目標使用者", collision="allow"),
                "identity-arrow-2": _text("身份流程｜箭頭二", collision="allow"),
                "identity-value": _text("身份流程｜核心價值", collision="allow"),
                "positioning-bg": _background("白話定位｜背景"),
                "positioning-label": _text("白話定位｜標籤"),
                "positioning-text": _text("白話定位｜說明"),
                "facts-bg": _background("基本資料｜背景"),
                "facts-label": _text("基本資料｜標籤"),
                "facts-text": _text("基本資料｜說明"),
                "reason-bg": _background("為什麼值得介紹｜背景"),
                "reason-label": _text("為什麼值得介紹｜標籤"),
                "reason-text": _text("為什麼值得介紹｜說明"),
                "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
            }
        ),
        "problem": _rules(
            **{
                "page-label": _text("頁面｜英文眉標", collision="allow"),
                "heading": ElementRule("頁面標題", True),
                "question-mark": ElementRule("頁面｜問號裝飾", False, "allow"),
                "current-bg": _background("現在怎麼做｜背景"),
                "current-label": _text("現在怎麼做｜標籤"),
                "current-text": _text("現在怎麼做｜說明"),
                "opportunity-bg": _background("哪裡還能更好｜背景"),
                "opportunity-label": _text("哪裡還能更好｜標籤"),
                "opportunity-text": _text("哪裡還能更好｜說明"),
                "spine": ElementRule("流程連接線", False, "background", 2, 24),
                **{
                    f"stage-{index}-{role}": (
                        _background(f"{label}｜背景")
                        if role == "bg"
                        else ElementRule(f"{label}｜圖示", False, "allow")
                        if role == "icon"
                        else _text(f"{label}｜{ {'index': '編號', 'title': '標題', 'text': '說明'}[role] }")
                    )
                    for index, label in enumerate(("現有流程", "優化空間", "釋放價值"), start=1)
                    for role in ("bg", "icon", "index", "title", "text")
                },
                "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
            }
        ),
        "how-ai": _rules(
            **{
                "page-label": _text("頁面｜英文眉標", collision="allow"),
                "heading": ElementRule("頁面標題", True),
                "flow-arrow-1": ElementRule("流程｜箭頭一", False, "allow"),
                "flow-arrow-2": ElementRule("流程｜箭頭二", False, "allow"),
                **{
                    f"step-{index}-{role}": (
                        _background(f"{label}｜背景")
                        if role == "bg"
                        else _text(f"{label}｜{ {'tag': '英文標籤', 'title': '標題', 'text': '說明'}[role] }")
                    )
                    for index, label in enumerate(("理解輸入", "分析處理", "交付結果"), start=1)
                    for role in ("bg", "tag", "title", "text")
                },
                **{
                    f"{element_id}-{role}": (
                        _background(f"{label}｜背景")
                        if role == "bg"
                        else _text(f"{label}｜{ '標籤' if role == 'label' else '說明' }")
                    )
                    for element_id, label in (
                        ("traditional", "傳統做法"),
                        ("ai-role", "AI 的角色"),
                        ("human", "人仍負責"),
                        ("difference", "關鍵差別"),
                    )
                    for role in ("bg", "label", "text")
                },
                "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
            }
        ),
        "results": _rules(
            **{
                "page-label": _text("頁面｜英文眉標", collision="allow"),
                "heading": ElementRule("頁面標題", True),
                "audience-bg": _background("代表使用者｜背景"),
                "audience-label": _text("代表使用者｜標籤"),
                "audience-text": _text("代表使用者｜說明"),
                **{
                    f"{element_id}-{role}": (
                        _background(f"{label}｜背景")
                        if role == "bg"
                        else ElementRule(f"{label}｜箭頭", False, "allow")
                        if role == "arrow"
                        else _text(f"{label}｜{ {'tag': '英文標籤', 'title': '標題', 'text': '說明'}[role] }")
                    )
                    for element_id, label, roles in (
                        ("before", "使用前", ("bg", "tag", "title", "text")),
                        ("intervention", "產品介入", ("bg", "arrow", "title", "text")),
                        ("after", "使用後", ("bg", "tag", "title", "text")),
                    )
                    for role in roles
                },
                "core-difference-bg": _background("核心差異｜背景"),
                "core-difference-label": _text("核心差異｜標籤"),
                "core-difference-text": _text("核心差異｜說明"),
                "value-bg": _background("帶來的價值｜背景"),
                "value-label": _text("帶來的價值｜標籤"),
                "value-text": _text("帶來的價值｜說明"),
                "mascot": ElementRule("呆一布機器人", False, "allow", 120, 120),
            }
        ),
        "cta": SCHEMA_V3_REGISTRY["cta"],
    }
)


def registry_for_schema(
    schema_version: int,
) -> Mapping[str, Mapping[str, ElementRule]]:
    if schema_version == 3:
        return SCHEMA_V3_REGISTRY
    if schema_version == 4:
        return ELEMENT_REGISTRY
    raise ValueError(f"不支援的 schema_version：{schema_version}")
