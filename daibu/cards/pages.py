PAGE_TYPES = (
    "cover",
    "who",
    "problem",
    "how-ai",
    "results",
    "cta",
)

CTA_TEXT = "追蹤呆一布 AI 共學實驗室\n帶你看更多最新 AI 資訊"

# 七種姿勢與網站 PRD 共用同一組素材；貼文只用到前五種，
# confused 與 lost 是網站的空狀態與 404 頁在用的。
POSES = ("wave", "think", "happy", "point", "note", "confused", "lost")

MASCOT_FOR = {
    "cover": "think",
    "who": "point",
    "problem": "think",
    "how-ai": "point",
    "results": "happy",
    "cta": "wave",
}

SECTION_LABELS = {
    "cover": ("一句話定位",),
    "who": ("白話定位", "基本資料", "為什麼值得介紹"),
    "problem": ("現在怎麼做", "哪裡還能更好"),
    "how-ai": ("傳統做法", "AI 的角色", "人仍負責", "關鍵差別"),
    "results": ("代表使用者", "核心差異", "帶來的價值"),
    "cta": ("互動邀請",),
}
REQUIRED_SECTIONS = {
    page_type: set(labels)
    for page_type, labels in SECTION_LABELS.items()
}
SECTION_LABEL_SEQUENCES = {
    page_type: (labels,)
    for page_type, labels in SECTION_LABELS.items()
}

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
}

LIMITS = {
    "hook": 26,
    "company": 20,
    "heading": 24,
    "inner_min": 140,
    "inner_max": 220,
}

# These are output-safe limits, calibrated against the actual v57 geometry
# with full-width Chinese glyphs in bundled LINE Seed TW.
SECTION_HARD_LIMITS = {
    "cover": (40,),
    "who": (95, 70, 55),
    "problem": (85, 85),
    "how-ai": (52, 56, 54, 38),
    "results": (56, 60, 58),
    "cta": (len(CTA_TEXT),),
}
HEADING_HARD_LIMITS = {
    "cover": 24,
    "who": 18,
    "problem": 18,
    "how-ai": 16,
    "results": 16,
    "cta": 24,
}
DIAGRAM_TITLE_HARD_LIMIT = 7
DIAGRAM_TEXT_HARD_LIMIT = 14

LABELS = {
    "cover": "封面",
    "who": "它在做什麼",
    "problem": "它想優化什麼",
    "how-ai": "AI 扮演什麼樣的角色",
    "results": "它怎麼實際改善現有流程",
    "cta": "追蹤呆一布",
}


def label(page_type: str) -> str:
    return LABELS[page_type]
