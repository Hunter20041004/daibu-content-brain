"""Create grounded, editable social copy for an adopted company idea."""

import json
from collections.abc import Callable
from dataclasses import asdict

from daibu.cards.schema import VerifiedSource, validate_sources
from daibu.models import StoredIdea

MIN_DRAFT_CHARS = 350
MAX_DRAFT_CHARS = 500


class CopyDraftError(ValueError):
    pass


def build_prompt(
    idea: StoredIdea,
    sources: tuple[VerifiedSource, ...],
) -> str:
    if not idea.company.strip():
        raise ValueError("這則題目沒有公司名，無法產生初稿。")
    if not sources:
        raise ValueError("至少需要一筆已驗證來源才能產生初稿。")
    validate_sources(sources)
    source_payload = [asdict(source) for source in sources]
    return f"""
你是「呆一布 AI 共學實驗室」的社群編輯。
請為下列已採用公司寫一份可繼續編輯的社群初稿。

公司：{idea.company}
這家公司在做什麼：{idea.title}
內部選題角度：{idea.angle}

你只能根據下列已驗證來源陳述公司事實：
{json.dumps(source_payload, ensure_ascii=False)}

要求：
- 使用繁體中文，全文 350–500 個字元。
- 開頭用一句清楚鉤子，但不誇張、不製造焦慮。
- 白話說明公司在做什麼、解決誰的什麼問題，以及 AI 扮演什麼角色。
- 證據不足的地方明說，不用模型常識補齊。
- 不加入投資建議、未查證數字、客戶或人物。
- 結尾提出一個讓讀者思考或留言的問題。
- 只輸出初稿純文字，不要 JSON、Markdown 標題或來源清單。
""".strip()


def generate_draft(
    idea: StoredIdea,
    sources: tuple[VerifiedSource, ...],
    generate_text: Callable[[str], str],
) -> str:
    prompt_text = build_prompt(idea, sources)
    last_length = 0
    for _attempt in range(2):
        result = generate_text(prompt_text).strip()
        last_length = len(result)
        if MIN_DRAFT_CHARS <= last_length <= MAX_DRAFT_CHARS:
            return result
    raise CopyDraftError(
        "AI 兩次都沒有產出 350–500 字的初稿"
        f"（最後一次為 {last_length} 字），原文沒有變更。"
    )
