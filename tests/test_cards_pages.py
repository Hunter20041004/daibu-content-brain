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
    assert pages.label("results") == "誰會用、怎麼用"
    assert pages.label("why-care") == "接下來觀察什麼"
    assert pages.label("cta") == "收束與互動"
