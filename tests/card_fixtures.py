import json
from dataclasses import asdict, replace
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
                _section(
                    "為什麼值得介紹",
                    "它把生成式 AI 放進既有聲音製作流程，讓團隊能更快測試內容，"
                    "同時保留人工審核、授權與精細演出的空間。",
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
                    "現在怎麼做",
                    "有聲書、遊戲與影音團隊常要處理大量台詞；一段內容改字，就可能重新安排配音員、"
                    "錄音室與後製。小團隊尤其難同時負擔多語版本，同一作品版本越多，這些安排就越"
                    "容易互相牽動。",
                    "S2",
                    "S3",
                ),
                _section(
                    "哪裡還能更好",
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
                    "關鍵差別",
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
                    "核心差異",
                    "過去每次改字都可能重新錄音；現在可以先更新文字並產生新版本，快速確認節奏"
                    "與方向。需要精細演出的段落仍可回到真人錄製。",
                    "S1",
                    "S3",
                ),
                _section(
                    "帶來的價值",
                    "付費方買的是可整合進內容流程的語音能力與製作工具，不只是單一音檔。沒有公開"
                    "客戶案例時，只描述官方展示的代表情境。",
                    "S1",
                    "S2",
                ),
            ),
            DiagramSpec(
                "before-after",
                (
                    DiagramNode("使用前", "改字後重新排錄音與後製", "concerned"),
                    DiagramNode("產品介入", "先產生可聽、可修改版本", "think"),
                    DiagramNode("使用後", "人力集中在內容與品質", "happy"),
                ),
            ),
            "來源：ElevenLabs · 2026-07-12、2026-07-18；Verified News · 2026-07-20",
        ),
        CarouselPage(
            6,
            "cta",
            "追蹤呆一布 AI 共學實驗室",
            (
                _section(
                    "互動邀請",
                    "追蹤呆一布 AI 共學實驗室\n帶你看更多最新 AI 資訊",
                ),
            ),
            None,
            "",
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
        for page in draft.pages[1:5]
    )
    return draft


def company_stress_draft(company: str) -> CarouselDraft:
    """Return approved v15.1 stress content for three distinct company shapes."""
    content = {
        "SUN": {
            "headings": (
                "你的 Podcast\n可以只為你而生嗎？",
                "先認識 SUN",
                "音訊很多，\n選擇卻沒有更容易",
                "SUN 怎麼生成\n個人化音訊？",
                "從節目搜尋到直接生成",
                "你會怎麼用 SUN？",
            ),
            "sections": {
                "一句話定位": "按需生成能互動、能理解個人脈絡的音訊內容。",
                "產業分類": "個人化音訊",
                "白話定位": "不是推薦節目，而是依主題與個人脈絡直接生成當下想聽的音訊。",
                "基本資料": "常見場景包含 Podcast、有聲書、音訊課程與個人筆記延伸內容。",
                "為什麼值得介紹": "它把個人脈絡從推薦條件變成內容生成的一部分，改變聽眾取得知識的流程。",
                "現在怎麼做": "想學一個主題的聽眾，得先搜尋、比較，再決定從哪一集開始。",
                "哪裡還能更好": "時間花在挑選與略過段落，真正理解主題反而被延後。",
                "傳統做法": "先到目錄搜尋節目，再配合固定內容的節奏與解釋深度。",
                "AI 的角色": "依個人背景安排內容、語氣與順序，生成貼近需求的版本。",
                "人仍負責": "內容來源、個資界線與正確性，仍需要由人確認。",
                "關鍵差別": "內容可以一邊聽、一邊追問，再隨著問題繼續展開。",
                "代表使用者": "Podcast、有聲書、課程與個人筆記的使用者。",
                "核心差異": "從先找固定節目，變成依照當下問題直接生成音訊。",
                "帶來的價值": "價值不只在聲音，而在內容是否真的理解你。",
                "觀察訊號 1": "個人化不能建立在錯誤資訊上，引用來源也要能追查。",
                "觀察訊號 2": "筆記與個人資料如何取用、保存及刪除，必須說清楚。",
                "觀察訊號 3": "不只短段落好聽，也要支撐完整內容與持續追問。",
                "證據限制": "現有資料能說明方向，仍需更多真實使用證據。",
                "收束結論": "SUN 把個人脈絡變成可互動的音訊，真正考驗是正確性、隱私與長時間品質。",
                "給讀者的問題": "你最想讓 AI 為你生成什麼音訊？",
                "互動邀請": "追蹤呆一布 AI 共學實驗室\n帶你看更多最新 AI 資訊",
            },
            "diagrams": {
                "problem": (
                    ("內容平台", "海量節目與有聲內容"),
                    ("傳統限制", "同一內容給所有人"),
                    ("累積成本", "搜尋、挑選與跳著聽"),
                ),
                "how-ai": (
                    ("先給什麼", "讀取使用者脈絡"),
                    ("AI 做什麼", "按需求組織音訊"),
                    ("最後得到", "生成並持續互動"),
                ),
                "results": (
                    ("從節目搜尋", "在目錄裡挑選節目"),
                    ("按需生成", "AI 先理解問題"),
                    ("直接生成", "音訊依你的問題出現"),
                ),
            },
        },
        "Billow AI Labs": {
            "headings": (
                "會計服務可以\n從 AI 原生開始嗎？",
                "先認識 Billow AI Labs",
                "企業會計慢的，\n不只是輸入資料",
                "Billow AI Labs\n怎麼重做會計服務？",
                "從人工堆疊到 AI 原生服務",
                "你怎麼看 Billow AI Labs？",
            ),
            "sections": {
                "一句話定位": "以 AI 原生的會計服務，挑戰傳統專業諮詢結構。",
                "產業分類": "企業會計服務",
                "白話定位": "不只賣軟體，也把 AI 放進企業會計工作的核心交付流程。",
                "基本資料": "服務涵蓋每月結帳、報表整理、資料核對與持續追蹤。",
                "為什麼值得介紹": "它不只提供軟體，而是把 AI 放進會計服務的實際交付流程。",
                "現在怎麼做": "企業財務資料散落在發票、合約與交易系統，還要持續補齊缺漏。",
                "哪裡還能更好": "專業時間耗在分類與核對，真正需要判斷的異常更晚被看見。",
                "傳統做法": "人工先整理大量文件，再把剩餘時間留給審核與交付。",
                "AI 的角色": "整合文件、分類紀錄並標出需要專業人員追查的異常。",
                "人仍負責": "準確性、審核與責任歸屬，不能因自動化消失。",
                "關鍵差別": "AI 處理重複工作，會計人員負責審核、解釋與交付。",
                "代表使用者": "企業財務、營運團隊、會計人員與管理者。",
                "核心差異": "從人力先做重複整理，變成專業時間回到審核與解釋。",
                "帶來的價值": "企業得到的不是自動填表，而是可靠、可追溯的會計結果。",
                "觀察訊號 1": "會計流程不能只偶爾正確，例外情況也要及時攔下。",
                "觀察訊號 2": "企業需要知道數字來源、調整紀錄與誰曾經確認。",
                "觀察訊號 3": "AI 參與後，專業責任、審核權限與錯誤處理仍要清楚。",
                "證據限制": "正式貼文仍需補充產品與客戶成效證據。",
                "收束結論": "AI 可以重做會計流程，但不能取代信任與責任，差異在服務是否更透明可靠。",
                "給讀者的問題": "你會先把哪一段會計流程交給 AI？",
                "互動邀請": "追蹤呆一布 AI 共學實驗室\n帶你看更多最新 AI 資訊",
            },
            "diagrams": {
                "problem": (
                    ("資料入口", "文件散落在不同系統"),
                    ("傳統阻礙", "人工分類與反覆核對"),
                    ("信任成本", "審核、追溯與責任"),
                ),
                "how-ai": (
                    ("先給什麼", "整合企業文件與紀錄"),
                    ("AI 做什麼", "整理分類與異常線索"),
                    ("最後得到", "專業人員審核交付"),
                ),
                "results": (
                    ("從人工堆疊", "人力處理大量重複工作"),
                    ("AI 先整理", "標出異常線索"),
                    ("AI 原生服務", "專業時間回到審核解釋"),
                ),
            },
        },
        "Shiraz AI": {
            "headings": (
                "示範一次，\n機器人就能學會嗎？",
                "先認識 Shiraz AI",
                "自動化難的，\n是每次任務都不同",
                "Shiraz AI 怎麼從\n示範中學習？",
                "從工程師編程到現場示範",
                "你會怎麼用 Shiraz AI？",
            ),
            "sections": {
                "一句話定位": "讓工廠機器人從一次示範中，學會新的現場任務。",
                "產業分類": "工業機器人",
                "白話定位": "不是先寫程式，而是讓現場人員用示範教機器人執行任務。",
                "基本資料": "適合產品切換頻繁、任務常變動、難以每次重寫程式的工廠。",
                "為什麼值得介紹": "它讓最熟悉工序的人直接參與自動化，縮短現場知識轉成機器動作的距離。",
                "現在怎麼做": "產品尺寸、位置或步驟一變，原本的固定程式就可能無法使用。",
                "哪裡還能更好": "新任務越多，工程排程、測試與停線時間越容易拖慢導入。",
                "傳統做法": "每次變更都要等待工程師重新編程與測試。",
                "AI 的角色": "把人類示範拆成可重複執行、持續調整的機器人任務。",
                "人仍負責": "安全、例外處理與現場責任，仍由人員掌握。",
                "關鍵差別": "最懂工序的人，也能直接參與教機器人怎麼工作。",
                "代表使用者": "產線人員、工廠主管、自動化工程與設備團隊。",
                "核心差異": "從等待重新編程，變成懂工序的人直接示範任務。",
                "帶來的價值": "價值是縮短現場知識到自動化執行之間的距離。",
                "觀察訊號 1": "新任務是否真能快速學會，還是仍要大量工程調整。",
                "觀察訊號 2": "遇到物件移位或人員靠近時，能否可靠停止並回報。",
                "觀察訊號 3": "換工件與環境後，也要維持同樣穩定的表現。",
                "證據限制": "一次示範的實際成效仍需更多案例驗證。",
                "收束結論": "示範式學習讓自動化更靠近現場工作者，門檻仍是安全、穩定與跨任務表現。",
                "給讀者的問題": "你會先教機器人做哪一項工廠任務？",
                "互動邀請": "追蹤呆一布 AI 共學實驗室\n帶你看更多最新 AI 資訊",
            },
            "diagrams": {
                "problem": (
                    ("現場變化", "產品與工序持續調整"),
                    ("傳統阻礙", "工程師重新編程"),
                    ("部署成本", "等待、測試與停線風險"),
                ),
                "how-ai": (
                    ("先給什麼", "人類實際操作一次"),
                    ("AI 做什麼", "辨認可重複動作模式"),
                    ("最後得到", "部署、觀察與調整"),
                ),
                "results": (
                    ("工程師編程", "新任務等待重新編程"),
                    ("示範一次", "AI 辨認任務模式"),
                    ("現場示範", "懂工序的人直接教機器人"),
                ),
            },
        },
    }
    try:
        selected = content[company]
    except KeyError as error:
        raise ValueError(f"沒有 {company} 的版型壓力資料") from error

    pages = []
    for page, heading in zip(
        carousel_draft().pages,
        selected["headings"],
        strict=True,
    ):
        sections = tuple(
            replace(section, text=selected["sections"][section.label])
            for section in page.sections
        )
        diagram = page.diagram
        if diagram is not None:
            nodes = tuple(
                replace(node, title=title, text=text)
                for node, (title, text) in zip(
                    diagram.nodes,
                    selected["diagrams"][page.page_type],
                    strict=True,
                )
            )
            diagram = replace(diagram, nodes=nodes)
        pages.append(
            replace(
                page,
                heading=heading,
                sections=sections,
                diagram=diagram,
            )
        )
    return replace(carousel_draft(), pages=tuple(pages))


def renderable_carousel_draft() -> CarouselDraft:
    """Keep the standard ElevenLabs fixture within the approved visual boxes."""
    draft = carousel_draft()
    compact_text = {
        "who": {
            "基本資料": "服務有聲書、遊戲、影音與多語在地化等內容團隊。",
        },
        "problem": {
            "現在怎麼做": "內容改字時，團隊可能要重排配音、錄音與後製。",
            "哪裡還能更好": "等待檔期、反覆重錄與版本管理會持續累積。",
        },
        "how-ai": {
            "人仍負責": "人要確認內容、聲音授權與最後品質。",
        },
        "results": {
            "代表使用者": "有聲書、遊戲與影音團隊會先做可調整版本。",
            "核心差異": "改字後先生成，人再確認品質。",
            "帶來的價值": "團隊得到的是可整合的語音能力。",
        },
    }
    revised = []
    for page in draft.pages:
        replacements = compact_text.get(page.page_type, {})
        sections = tuple(
            replace(section, text=replacements.get(section.label, section.text))
            for section in page.sections
        )
        revised.append(replace(page, sections=sections))
    return replace(draft, pages=tuple(revised))


def brand_asset(path: Path, *, company: str = "ElevenLabs") -> BrandAsset:
    return BrandAsset(
        company,
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
