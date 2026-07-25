import json

from daibu.llm.base import Idea
from daibu.models import Material


def build(
    theme_name: str,
    materials: list[Material],
    n: int,
) -> str:
    material_payload = [
        {
            "title": material.title,
            "url": material.url,
            "snippet": material.snippet,
        }
        for material in materials
    ]
    return f"""
你是「呆一布 AI 共學實驗室」社群組的選題軍師。
請為主題「{theme_name}」產生 {n} 則具體貼文題目。

素材：
{json.dumps(material_payload, ensure_ascii=False)}

要求：
- 切入角度使用文組視角，拆解邏輯，避免紅海 hype 腔。
- 有素材時必須填 source_url。
- 只輸出 JSON 陣列，不要 Markdown 或額外說明。
- 每個物件只含 title、angle、source_url。
""".strip()


def parse_ideas(raw: str) -> list[Idea]:
    array_start = raw.find("[")
    if array_start < 0:
        raise ValueError("LLM 回覆中找不到 JSON 陣列")

    decoded, _ = json.JSONDecoder().raw_decode(raw[array_start:])
    if not isinstance(decoded, list):
        raise ValueError("LLM 回覆的 JSON 必須是陣列")

    return [
        Idea(
            title=str(item.get("title", "")),
            angle=str(item.get("angle", "")),
            source_url=str(item.get("source_url", "")),
        )
        for item in decoded
        if isinstance(item, dict)
    ]
