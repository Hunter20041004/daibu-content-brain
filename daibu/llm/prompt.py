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


def parse_carousel(raw: str) -> list[dict]:
    from daibu.cards import pages as card_pages

    array_start = raw.find("[")
    if array_start < 0:
        raise ValueError("LLM 回覆中找不到 JSON 陣列")
    decoded, _ = json.JSONDecoder().raw_decode(raw[array_start:])
    if not isinstance(decoded, list):
        raise ValueError("LLM 回覆的 JSON 必須是陣列")
    if len(decoded) != len(card_pages.PAGE_TYPES):
        raise ValueError(
            f"輪播必須剛好 {len(card_pages.PAGE_TYPES)} 頁，"
            f"收到 {len(decoded)} 頁"
        )

    rows = []
    for index, item in enumerate(decoded):
        grounding = str(item.get("grounding", "")).strip().lower()
        if grounding != "source":
            grounding = "model"
        rows.append(
            {
                "page_no": index + 1,
                "page_type": card_pages.PAGE_TYPES[index],
                "heading": str(item.get("heading", "")),
                "body": str(item.get("body", "")),
                "grounding": grounding,
                "source_quote": (
                    str(item.get("source_quote", ""))
                    if grounding == "source"
                    else ""
                ),
            }
        )
    return rows


def build_carousel(
    company: str,
    title: str,
    angle: str,
    source_excerpt: str,
) -> str:
    from daibu.cards import pages as card_pages

    limits = card_pages.LIMITS
    outline = "\n".join(
        f"{index + 1}. {page_type} — {card_pages.label(page_type)}"
        for index, page_type in enumerate(card_pages.PAGE_TYPES)
    )
    return f"""
你是「呆一布 AI 共學實驗室」社群組的貼文編輯。
請為以下這家公司寫一份 IG 輪播貼文，剛好 {len(card_pages.PAGE_TYPES)} 頁。

公司：{company}
它在做什麼：{title}
為什麼現在值得講：{angle}
原文片段：{source_excerpt}

頁序與每頁要寫的東西（順序不可更動）：
{outline}

這則貼文是在介紹「一家公司如何運用 AI」，不是在教讀者怎麼使用工具。
不要寫定價、不要寫操作步驟。第 4 頁 how-ai 是整份的核心，要寫得最具體。
第 6 頁 why-care 是「呆一布怎麼看」，要寫自己的觀點，不是複述新聞。

呆一布的三條語氣鐵律，每一頁都適用：
1. **講邏輯，不講工具**——寫「為什麼這樣做」，不是「又出了什麼新東西」。
2. **降低焦慮，不製造焦慮**——嚴禁「不懂就落伍」「不學就被取代」
   「再不跟上就來不及」這類寫法。第 6 頁最容易犯，因為「值得注意」
   很容易被寫成威脅。正確做法是講清楚它改變了什麼，讓讀者自己判斷。
3. **知道下一步**——第 7 頁 cta 要給具體去處與時間
   （例如這個系列每週幾更新），不可只寫「追蹤我們」「留言告訴我」這種空話。

字數上限（超過就自己縮短，不可截成半句）：
- 第 1 頁的 heading（鉤子）最多 {limits["hook"]} 字，
  body 放公司名，最多 {limits["company"]} 字元
- 第 2–7 頁的 heading 最多 {limits["heading"]} 字，
  body 最多 {limits["body"]} 字

每一頁都要標 grounding：
- 寫成 "source"：這頁的內容在上面的原文片段裡找得到，
  並在 source_quote 原樣抄錄支持它的那一句
- 寫成 "model"：原文片段裡沒有，是你從自己的知識補的，
  source_quote 留空字串

**不確定的時候一律標 "model"。** 標錯成 "source" 會讓編輯以為查證過了。
數字（融資金額、用戶數、成立年份）除非原文片段裡明確出現，
否則一律標 "model"。

只輸出 JSON 陣列，不要 Markdown 或額外說明。
每個物件只含 page_type、heading、body、grounding、source_quote。
""".strip()
