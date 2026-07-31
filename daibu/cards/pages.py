PAGE_TYPES = (
    "cover",
    "who",
    "problem",
    "how-ai",
    "results",
    "why-care",
    "cta",
)

# 七種姿勢與網站 PRD 共用同一組素材；貼文只用到前五種，
# confused 與 lost 是網站的空狀態與 404 頁在用的。
POSES = ("wave", "think", "happy", "point", "note", "confused", "lost")

MASCOT_FOR = {
    "cover": "think",
    "who": "point",
    "problem": "think",
    "how-ai": "point",
    "results": "happy",
    "why-care": "note",
    "cta": "wave",
}

SECTION_LABELS = {
    "cover": ("一句話定位", "產業分類"),
    "who": ("白話定位", "基本資料"),
    "problem": ("誰受影響", "原本的代價"),
    "how-ai": ("傳統做法", "AI 的角色", "人仍負責", "本頁要記住"),
    "results": ("代表使用者", "使用前後", "購買關係"),
    "why-care": ("觀察訊號 1", "觀察訊號 2", "證據限制"),
    "cta": ("收束結論", "給讀者的問題", "互動邀請"),
}
REQUIRED_SECTIONS = {
    page_type: set(labels)
    for page_type, labels in SECTION_LABELS.items()
}
SECTION_LABEL_SEQUENCES = {
    page_type: (labels,)
    for page_type, labels in SECTION_LABELS.items()
}
SECTION_LABEL_SEQUENCES["cta"] = (
    SECTION_LABELS["cta"],
    ("公司定位", "AI 的角色", "觀察重點", "互動邀請"),
)
REQUIRED_SECTIONS["cta"] = {"互動邀請"}
SECTION_LABEL_SEQUENCES["why-care"] = (
    SECTION_LABELS["why-care"],
    (
        "觀察訊號 1",
        "觀察訊號 2",
        "觀察訊號 3",
        "證據限制",
    ),
)

AI_ROLE_KINDS = {
    "ai-analyze",
    "ai-generate",
    "ai-predict",
    "ai-automate",
    "ai-infrastructure",
}
DIAGRAM_FOR = {
    "problem": {"problem-chain"},
    "how-ai": AI_ROLE_KINDS,
    "results": {"before-after"},
    "why-care": {"signals"},
}

LIMITS = {
    "hook": 26,
    "company": 20,
    "heading": 24,
    "inner_min": 140,
    "inner_max": 220,
}

LABELS = {
    "cover": "封面",
    "who": "公司身分卡",
    "problem": "它解決什麼問題",
    "how-ai": "AI 在裡面扮演什麼角色",
    "results": "誰會用、怎麼用",
    "why-care": "接下來觀察什麼",
    "cta": "收束與互動",
}


def label(page_type: str) -> str:
    return LABELS[page_type]
