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


ELEMENT_REGISTRY: Mapping[str, Mapping[str, ElementRule]] = MappingProxyType(
    {
        "cover": _rules(
            series=ElementRule("系列名稱", True),
            **{
                "company-logo": ElementRule("企業 Logo"),
                "company-name": ElementRule("企業名稱", True, "allow"),
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
            invitation=ElementRule("互動邀請", True),
            mascot=ElementRule("呆一布機器人", False, "allow", 120, 120),
        ),
    }
)
