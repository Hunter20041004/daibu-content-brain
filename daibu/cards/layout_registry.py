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


def registry_for_schema(
    schema_version: int,
) -> Mapping[str, Mapping[str, ElementRule]]:
    if schema_version == 3:
        return ELEMENT_REGISTRY
    raise ValueError(f"不支援的 schema_version：{schema_version}")
