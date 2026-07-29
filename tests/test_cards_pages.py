from daibu.cards import pages


def test_seven_page_types_in_order():
    assert pages.PAGE_TYPES == (
        "cover",
        "who",
        "problem",
        "how-ai",
        "results",
        "why-care",
        "cta",
    )


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


def test_character_limits_match_spec():
    assert pages.LIMITS == {
        "hook": 20,
        "company": 16,
        "heading": 14,
        "body": 60,
    }


def test_label_returns_chinese_name():
    assert pages.label("how-ai") == "他們怎麼運用 AI"


def test_why_care_page_uses_the_brand_voice_name():
    """沿用網站 PRD 週報的「呆一布這週怎麼看」，讓兩邊是同一個聲音。"""
    assert pages.label("why-care") == "呆一布怎麼看"
