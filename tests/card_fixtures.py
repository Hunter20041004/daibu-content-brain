import json
from dataclasses import asdict
from pathlib import Path

from daibu.cards.schema import (
    BrandAsset,
    CarouselDraft,
    CarouselPage,
    ContentSection,
    DiagramNode,
    DiagramSpec,
    EvidenceQuote,
    VerifiedSource,
)


def verified_sources() -> tuple[VerifiedSource, ...]:
    return (
        VerifiedSource(
            "S1",
            "ElevenLabs",
            "2026-07-12",
            "https://elevenlabs.io/about",
            "公司開發能保留語氣、節奏與情緒的語音模型，並提供內容製作工具。",
            "official",
        ),
        VerifiedSource(
            "S2",
            "ElevenLabs",
            "2026-07-18",
            "https://elevenlabs.io/use-cases",
            "官方列出的使用情境包含有聲書、遊戲、影音內容與多語在地化。",
            "official",
        ),
        VerifiedSource(
            "S3",
            "Verified News",
            "2026-07-20",
            "https://news.example/elevenlabs-profile",
            "報導說明專業配音需要錄音、重錄與逐段調整，製作排程會受人力與錄音室限制。",
            "third_party",
        ),
    )


def solid_png(width: int, height: int) -> bytes:
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGBA", (width, height), (10, 20, 30, 255)).save(
        buffer,
        format="PNG",
    )
    return buffer.getvalue()


def _section(label: str, text: str, *source_ids: str) -> ContentSection:
    by_id = {source.source_id: source for source in verified_sources()}
    return ContentSection(
        label,
        text,
        tuple(source_ids),
        tuple(
            EvidenceQuote(source_id, by_id[source_id].excerpt)
            for source_id in source_ids
        ),
    )


def carousel_draft() -> CarouselDraft:
    pages = (
        CarouselPage(
            1,
            "cover",
            "讓每段文字保留說話方式",
            (
                _section(
                    "一句話定位",
                    "ElevenLabs 用 AI 生成與轉換保有語氣的聲音。",
                    "S1",
                ),
                _section("產業分類", "生成式語音", "S1"),
            ),
            None,
            "來源：ElevenLabs · 2026-07-12",
        ),
        CarouselPage(
            2,
            "who",
            "先認識 ElevenLabs",
            (
                _section(
                    "白話定位",
                    "它不是單純把文字念出來，而是把語氣、節奏和情緒一起當成聲音內容來處理。"
                    "這讓創作者能先做出可調整的版本，再決定哪些地方需要真人補錄。因此它比較像"
                    "聲音製作工具，而不是取代整段製作的朗讀按鈕。",
                    "S1",
                ),
                _section(
                    "基本資料",
                    "公司把產品放在內容製作流程裡，服務有聲書、遊戲、影音與多語在地化等情境。"
                    "公開資料若沒有完整創辦資訊，就只呈現已確認的市場與服務對象。",
                    "S1",
                    "S2",
                ),
            ),
            None,
            "來源：ElevenLabs · 2026-07-12、2026-07-18",
        ),
        CarouselPage(
            3,
            "problem",
            "配音慢的不是朗讀本身",
            (
                _section(
                    "誰受影響",
                    "有聲書、遊戲與影音團隊常要處理大量台詞；一段內容改字，就可能重新安排配音員、"
                    "錄音室與後製。小團隊尤其難同時負擔多語版本，同一作品版本越多，這些安排就越"
                    "容易互相牽動。",
                    "S2",
                    "S3",
                ),
                _section(
                    "原本的代價",
                    "真正的成本不只是一小時錄音費，還有等待檔期、反覆重錄、逐段校正與版本管理。"
                    "內容越常修改，前後協調時間越容易累積；如果最後才發現語氣不對，前面的流程還要"
                    "再走一次。",
                    "S3",
                ),
            ),
            DiagramSpec(
                "problem-chain",
                (
                    DiagramNode("內容團隊", "大量台詞與多語版本", "listen"),
                    DiagramNode("傳統阻礙", "排檔、重錄、逐段調整", "think"),
                    DiagramNode("累積成本", "時間、人力與版本管理", "concerned"),
                ),
            ),
            "來源：ElevenLabs · 2026-07-18；Verified News · 2026-07-20",
        ),
        CarouselPage(
            4,
            "how-ai",
            "ElevenLabs 用 AI 重建說話方式",
            (
                _section(
                    "傳統做法",
                    "傳統合成語音多半把每個字念對，卻不容易保留一個人的停頓、重音與情緒；"
                    "創作者仍要花時間重錄或逐句修正。",
                    "S1",
                    "S3",
                ),
                _section(
                    "AI 的角色",
                    "模型從聲音範例辨認說話特徵，再依新文字安排語氣。它處理的是可重複調整的"
                    "聲音版本，不是替內容團隊決定要說什麼。",
                    "S1",
                ),
                _section(
                    "人仍負責",
                    "人要決定內容、語氣是否合適，也要確認聲音授權與最後品質。AI 先產生版本，"
                    "並不等於可以不經審核直接發布。",
                    "S1",
                ),
                _section(
                    "本頁要記住",
                    "改變不是『有沒有聲音』，而是說話方式能被保存、調整，再放進新的內容。",
                    "S1",
                ),
            ),
            DiagramSpec(
                "ai-generate",
                (
                    DiagramNode("提供聲音範例", "讓模型辨認節奏與表達", "listen"),
                    DiagramNode("AI 理解特徵", "依新文字安排說話方式", "think"),
                    DiagramNode("產生可調版本", "交由人員審核與修正", "happy"),
                ),
            ),
            "來源：ElevenLabs · 2026-07-12；Verified News · 2026-07-20",
        ),
        CarouselPage(
            5,
            "results",
            "誰把 ElevenLabs 放進工作裡",
            (
                _section(
                    "代表使用者",
                    "需要大量聲音內容的有聲書、遊戲、影音與在地化團隊，會先用它製作可聽、"
                    "可修改的版本，再把人工時間留給內容判斷。",
                    "S2",
                ),
                _section(
                    "使用前後",
                    "過去每次改字都可能重新錄音；現在可以先更新文字並產生新版本，快速確認節奏"
                    "與方向。需要精細演出的段落仍可回到真人錄製。",
                    "S1",
                    "S3",
                ),
                _section(
                    "購買關係",
                    "付費方買的是可整合進內容流程的語音能力與製作工具，不只是單一音檔。沒有公開"
                    "客戶案例時，只描述官方展示的代表情境。",
                    "S1",
                    "S2",
                ),
            ),
            DiagramSpec(
                "before-after",
                (
                    DiagramNode("以前", "改字後重新排錄音與後製", "concerned"),
                    DiagramNode("AI 介入", "先產生可聽、可修改版本", "think"),
                    DiagramNode("現在", "人力集中在內容與品質", "happy"),
                ),
            ),
            "來源：ElevenLabs · 2026-07-12、2026-07-18；Verified News · 2026-07-20",
        ),
        CarouselPage(
            6,
            "why-care",
            "觀察 ElevenLabs 的三個訊號",
            (
                _section(
                    "觀察訊號 1",
                    "聲音是否能長時間維持一致，而不是只在短句示範裡自然。這會決定產品能不能"
                    "進入有聲書、遊戲等長內容。",
                    "S1",
                    "S2",
                ),
                _section(
                    "觀察訊號 2",
                    "內容團隊是否真的減少重錄與版本往返，而不只是多一個生成步驟。工作流程的"
                    "改變，比單次展示更能說明價值。",
                    "S2",
                    "S3",
                ),
                _section(
                    "觀察訊號 3",
                    "聲音授權、審核和追溯機制能否跟上使用規模。生成品質越高，能不能清楚管理"
                    "誰有權使用聲音就越重要。",
                    "S1",
                ),
                _section(
                    "證據限制",
                    "目前公開資料能看出產品方向與使用情境，但不足以證明所有團隊都能得到相同成果。",
                ),
            ),
            DiagramSpec(
                "signals",
                (
                    DiagramNode("長內容一致性", "不只短句自然", "listen"),
                    DiagramNode("流程是否縮短", "少重錄、少往返", "think"),
                    DiagramNode("授權可追溯", "能管理與審核", "happy"),
                ),
            ),
            "來源：ElevenLabs · 2026-07-12、2026-07-18；Verified News · 2026-07-20",
        ),
        CarouselPage(
            7,
            "cta",
            "你會怎麼看 ElevenLabs",
            (
                _section(
                    "收束結論",
                    "ElevenLabs 把語氣與節奏放進可反覆調整的生成式語音流程，但最後內容、"
                    "授權與品質仍由人負責。",
                    "S1",
                ),
                _section("給讀者的問題", "你會先用 AI 語音處理哪一種內容？"),
                _section("互動邀請", "按讚並追蹤呆一布，繼續看懂 AI 公司。"),
            ),
            None,
            "來源：ElevenLabs · 2026-07-12",
        ),
    )
    draft = CarouselDraft(verified_sources(), pages)
    assert all(
        140
        <= sum(
            len("".join(section.text.split()))
            for section in page.sections
        )
        <= 220
        for page in draft.pages[1:6]
    )
    return draft


def brand_asset(path: Path) -> BrandAsset:
    return BrandAsset(
        "ElevenLabs",
        path,
        "https://elevenlabs.io/about",
        "2026-07-29",
    )


def structured_llm_response(
    draft: CarouselDraft | None = None,
) -> str:
    payload = []
    for page in (draft or carousel_draft()).pages:
        payload.append(
            {
                "page_no": page.page_no,
                "page_type": page.page_type,
                "heading": page.heading,
                "sections": [asdict(section) for section in page.sections],
                "diagram": asdict(page.diagram) if page.diagram else None,
            }
        )
    return json.dumps(payload, ensure_ascii=False)
