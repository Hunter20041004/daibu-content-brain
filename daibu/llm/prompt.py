import json
from typing import TYPE_CHECKING

from daibu.llm.base import Idea
from daibu.models import Material

if TYPE_CHECKING:
    from daibu.cards.schema import CarouselDraft, VerifiedSource


def build(
    theme_name: str,
    materials: list[Material],
    n: int,
    avoid_titles: list[str] | None = None,
    content_kind: str = "general",
    avoid_companies: list[str] | None = None,
) -> str:
    material_payload = [
        {
            "title": material.title,
            "url": material.url,
            "snippet": material.snippet,
        }
        for material in materials
    ]
    avoid_title_label = (
        "已出現題目" if content_kind == "company_profile" else "已淘汰題目"
    )
    avoid_title_section = (
        ""
        if not avoid_titles
        else (
            f"\n請避開以下{avoid_title_label}：\n"
            f"{json.dumps(avoid_titles, ensure_ascii=False)}"
        )
    )
    avoid_company_section = (
        ""
        if not avoid_companies
        else (
            "\n已出現公司如下，不得再次使用：\n"
            f"{json.dumps(avoid_companies, ensure_ascii=False)}"
        )
    )
    if content_kind == "company_profile":
        candidate_rules = f"""
- 每一則候選必須是**一家具體的公司**，而且公司名要出現在素材裡，不可憑印象編造。
- 優先提出成立不超過十年、仍為私人且獨立的公司，排除已上市或已被收購的公司；後續系統會再查證。
- 嚴禁產出沒有公司名的通用觀點文（例如「文組生在 AI 新創的價值」這類）。
- 若素材裡找得到的公司不足 {n} 家，寧可少產幾則，也不要湊數。
- title 是「一句話說明這家公司在做什麼」。
- angle 是「為什麼現在值得講」。
- source_url 必須是該公司所依據的那一則素材的 HTTPS 網址。
- source_excerpt 是該素材中支持這則候選的原文片段，原樣抄錄，不要改寫。
- 每個物件只含 company、title、angle、source_url、source_excerpt。
""".strip()
    else:
        candidate_rules = """
- 每一則 title 都要是具體可理解的貼文題目。
- angle 是「為什麼現在值得講」。
- source_url 必須是候選所依據的素材網址。
- 每個物件只含 title、angle、source_url。
""".strip()
    return f"""
你是「呆一布 AI 共學實驗室」社群組的選題軍師。
請為主題「{theme_name}」產生 {n} 則具體貼文題目。

素材：
{json.dumps(material_payload, ensure_ascii=False)}
{avoid_title_section}
{avoid_company_section}

要求：
- 切入角度使用文組視角，拆解邏輯，避免紅海 hype 腔。
{candidate_rules}
- 只輸出 JSON 陣列，不要 Markdown 或額外說明。
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


def decode_carousel(
    raw: str,
    sources: tuple["VerifiedSource", ...],
) -> "CarouselDraft":
    from daibu.cards.schema import (
        CarouselDraft,
        page_from_mapping,
    )

    array_start = raw.find("[")
    if array_start < 0:
        raise ValueError("LLM 回覆中找不到 JSON 陣列")
    decoded, _ = json.JSONDecoder().raw_decode(raw[array_start:])
    if not isinstance(decoded, list):
        raise ValueError("輪播 JSON 必須是陣列")
    if any(not isinstance(item, dict) for item in decoded):
        raise ValueError("輪播 JSON 的每一頁必須是物件")
    pages = tuple(
        page_from_mapping(item, sources)
        for item in decoded
    )
    return CarouselDraft(sources, pages)


def parse_carousel(
    raw: str,
    sources: tuple["VerifiedSource", ...],
) -> "CarouselDraft":
    from daibu.cards.schema import validate_draft

    draft = decode_carousel(raw, sources)
    validate_draft(draft)
    return draft


def build_carousel(
    company: str,
    title: str,
    angle: str,
    sources: tuple["VerifiedSource", ...],
) -> str:
    from dataclasses import asdict

    source_payload = [asdict(source) for source in sources]
    return f"""
你是「呆一布 AI 共學實驗室」的公司介紹編輯。
請把下列已查證資料整理成剛好六頁 IG 輪播。

公司：{company}
既有定位：{title}
選題角度：{angle}
已查證資料：
{json.dumps(source_payload, ensure_ascii=False)}

六頁閱讀任務依序是：封面定位、公司輪廓、流程優化機會、AI 的角色、流程改善、社群 CTA。
第 1 頁 heading 必須是 12–24 個中文字的好奇鉤子：用問題、反差或
意外結果，讓人想知道公司如何做到；不得用來源沒有的事實製造懸念，
不得誇張或製造焦慮。
第 2–5 頁 heading 要簡潔有力、直接回答該頁閱讀任務；不必反覆寫公司名。

第 3 頁從「現在怎麼做」出發，說明 AI 公司如何優化既有流程，而不是預設原做法卡住。
圖解的三個節點依序表達「現有流程、優化空間、釋放價值」。
第 5 頁用三個等量節點表達「使用前、產品介入、使用後」。
第 4 頁只選最符合來源的 AI 角色：分析、生成、預測、自動執行或基礎設施；
對應 diagram.kind 只能是 ai-analyze、ai-generate、ai-predict、
ai-automate 或 ai-infrastructure。
第 1、2、6 頁的 diagram 必須是 null。第 3、4、5 頁的 diagram
必須各有剛好 3 個 nodes，每個 node 都要有 title、text、expression；
第 3、5 頁的 kind 依序只能是 problem-chain、before-after。

每個事實 section 都要附 evidence_quotes。每筆 evidence_quote 只含 source_id 與 quote；
source_id 必須來自上方來源，quote 必須從對應 excerpt 逐字抄錄，不可改寫。
不得加入來源中沒有的公司、人物、客戶、數字或能力。
第 2–5 頁 140–220 字是建議目標，證據不足時就少寫，不為湊字數補造。
資料不足時明寫「目前公開證據有限」，不可用模型常識補齊。

第 6 頁只放以下兩行固定 CTA，不做摘要、不提問、不加其他區塊：
追蹤呆一布 AI 共學實驗室
帶你看更多最新 AI 資訊
語氣要淺顯、講因果、降低焦慮，不寫「不學就被取代」或「不懂就落伍」。

輸出前檢查六頁都完成各自閱讀任務，事實都有逐字引句，然後只輸出 JSON，
頁序與區塊名稱必須照這份清單：
1 cover：一句話定位
2 who：白話定位、基本資料、為什麼值得介紹
3 problem：現在怎麼做、哪裡還能更好
4 how-ai：傳統做法、AI 的角色、人仍負責、關鍵差別
5 results：代表使用者、核心差異、帶來的價值
6 cta：互動邀請
不要 Markdown 或額外說明。API 的 JSON Schema 會約束欄位型別與六頁數量，
應用程式會再逐項驗證頁序、區塊與逐字證據。
""".strip()
