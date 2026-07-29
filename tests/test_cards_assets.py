from pathlib import Path

from daibu.cards import pages


ASSETS = Path(__file__).resolve().parent.parent / "assets"


def test_every_mascot_pose_file_exists():
    """七種都要有——網站共用同一組素材。"""
    for pose in pages.POSES:
        path = ASSETS / "mascot" / f"{pose}.svg"
        assert path.exists(), f"缺少姿勢素材：{path}"


def test_mascot_svgs_do_not_use_css_variables():
    """貼文圖是匯出的成品，顏色不得跟著介面深淺變。"""
    for pose in pages.POSES:
        text = (ASSETS / "mascot" / f"{pose}.svg").read_text(encoding="utf-8")
        assert "var(--" not in text, f"{pose}.svg 不得使用 CSS 變數"


def test_mascot_svgs_use_the_prd_palette():
    """機身必須是品牌主色，不得自創顏色。"""
    for pose in pages.POSES:
        text = (ASSETS / "mascot" / f"{pose}.svg").read_text(encoding="utf-8")
        assert "#8ACDD6" in text, f"{pose}.svg 的機身色不是品牌主色"


def test_three_font_weights_are_bundled():
    """出圖不得依賴網路字型，否則匯出的圖會跟預覽不一樣。"""
    for name in (
        "LINESeedTW_OTF_Rg.otf",
        "LINESeedTW_OTF_Bd.otf",
        "LINESeedTW_OTF_Eb.otf",
    ):
        assert (ASSETS / "fonts" / name).exists(), f"缺少字重：{name}"


def test_font_license_is_bundled():
    assert (ASSETS / "fonts" / "OFL.txt").exists()
