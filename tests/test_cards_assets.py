from pathlib import Path

import pytest

from daibu import db
from daibu.cards import assets, logo, pages
from tests.card_fixtures import solid_png


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


def test_uploaded_logo_is_stored_once_and_reused_by_company(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("DAIBU_LOGO_DIR", str(tmp_path / "logos"))
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    data = solid_png(240, 80)

    stored = assets.store_logo(
        conn,
        "ElevenLabs",
        "official.png",
        data,
        "https://elevenlabs.io/about",
        "2026-07-30",
    )

    assert stored.local_path.is_file()
    assert stored.local_path.read_bytes() == data
    assert db.get_brand_asset(conn, "elevenlabs") == stored

    again = assets.store_logo(
        conn,
        "ElevenLabs",
        "official.png",
        data,
        "https://elevenlabs.io/about",
        "2026-07-30",
    )

    assert again.local_path == stored.local_path
    assert len(list(assets.logo_dir().iterdir())) == 1


def test_rejected_logo_leaves_no_file_or_database_record(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("DAIBU_LOGO_DIR", str(tmp_path / "logos"))
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    with pytest.raises(logo.InvalidBrandAsset, match="超過 4096 px"):
        assets.store_logo(
            conn,
            "ElevenLabs",
            "oversized.png",
            solid_png(4200, 120),
            "https://elevenlabs.io/about",
            "2026-07-30",
        )

    assert not assets.logo_dir().exists()
    assert db.get_brand_asset(conn, "ElevenLabs") is None


def test_invalid_logo_metadata_leaves_no_file_or_database_record(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("DAIBU_LOGO_DIR", str(tmp_path / "logos"))
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)

    with pytest.raises(logo.InvalidBrandAsset, match="官方 https"):
        assets.store_logo(
            conn,
            "ElevenLabs",
            "official.png",
            solid_png(240, 80),
            "http://unverified.example/logo",
            "2026-07-30",
        )

    assert not assets.logo_dir().exists()
    assert db.get_brand_asset(conn, "ElevenLabs") is None
