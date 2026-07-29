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
    "cover": "wave",
    "who": "point",
    "problem": "think",
    "how-ai": "point",
    "results": "happy",
    "why-care": "note",
    "cta": "wave",
}

LIMITS = {"hook": 20, "company": 16, "heading": 14, "body": 60}

_LABELS = {
    "cover": "封面",
    "who": "他們是誰",
    "problem": "他們盯上什麼問題",
    "how-ai": "他們怎麼運用 AI",
    "results": "做出了什麼",
    "why-care": "呆一布怎麼看",
    "cta": "結尾",
}


def label(page_type: str) -> str:
    return _LABELS[page_type]
