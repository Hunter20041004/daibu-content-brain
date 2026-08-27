from daibu.cards import pages


def test_six_page_types_in_order():
    assert pages.PAGE_TYPES == (
        "cover",
        "who",
        "problem",
        "how-ai",
        "results",
        "cta",
    )
    assert "why-care" not in pages.MASCOT_FOR
    assert "why-care" not in pages.SECTION_LABELS


def test_every_page_type_maps_to_a_known_mascot_pose():
    """七種姿勢與網站 PRD 共用；貼文只會用到其中五種。"""
    assert pages.POSES == (
        "wave",
        "think",
        "happy",
        "point",
        "note",
        "confused",
        "lost",
    )
    assert set(pages.MASCOT_FOR) == set(pages.PAGE_TYPES)
    assert set(pages.MASCOT_FOR.values()) <= set(pages.POSES)


def test_curiosity_cover_uses_the_thinking_pose():
    assert pages.MASCOT_FOR["cover"] == "think"


def test_inner_pages_have_a_narrative_density_target():
    assert pages.LIMITS["inner_min"] == 140
    assert pages.LIMITS["inner_max"] == 220
    assert pages.AI_ROLE_KINDS == {
        "ai-analyze",
        "ai-generate",
        "ai-predict",
        "ai-automate",
        "ai-infrastructure",
    }


def test_page_labels_match_the_approved_reader_tasks():
    assert pages.SECTION_LABELS == {
        "cover": ("一句話定位",),
        "who": ("白話定位", "基本資料", "為什麼值得介紹"),
        "problem": ("現在怎麼做", "哪裡還能更好"),
        "how-ai": ("傳統做法", "AI 的角色", "人仍負責", "關鍵差別"),
        "results": ("代表使用者", "核心差異", "帶來的價值"),
        "cta": ("互動邀請",),
    }
    assert pages.label("results") == "它怎麼實際改善現有流程"
    assert pages.label("cta") == "追蹤呆一布"
