import json

from daibu.llm.base import Idea
from daibu.models import Material


def build(
    theme_name: str,
    materials: list[Material],
    n: int,
    avoid_titles: list[str] | None = None,
) -> str:
    material_payload = [
        {
            "title": material.title,
            "url": material.url,
            "snippet": material.snippet,
        }
        for material in materials
    ]
    avoid_section = (
        ""
        if not avoid_titles
        else (
            "\n請避開以下已淘汰題目：\n"
            f"{json.dumps(avoid_titles, ensure_ascii=False)}"
        )
    )
    return f"""
你是「呆一布 AI 共學實驗室」社群組的選題軍師。
請為主題「{theme_name}」產生 {n} 則具體貼文題目。

素材：
{json.dumps(material_payload, ensure_ascii=False)}
{avoid_section}

要求：
- 每一則候選必須是**一家具體的公司**，而且公司名要出現在素材裡，不可憑印象編造。
- 嚴禁產出沒有公司名的通用觀點文（例如「文組生在 AI 新創的價值」這類）。
- 若素材裡找得到的公司不足 {n} 家，寧可少產幾則，也不要湊數。
- 切入角度使用文組視角，拆解邏輯，避免紅海 hype 腔。
- title 是「一句話說明這家公司在做什麼」。
- angle 是「為什麼現在值得講」。
- source_url 必須是該公司所依據的那一則素材的網址。
- source_excerpt 是該素材中支持這則候選的原文片段，原樣抄錄，不要改寫。
- 只輸出 JSON 陣列，不要 Markdown 或額外說明。
- 每個物件只含 company、title、angle、source_url、source_excerpt。
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
            company=str(item.get("company", "")),
            source_excerpt=str(item.get("source_excerpt", "")),
        )
        for item in decoded
        if isinstance(item, dict)
    ]
