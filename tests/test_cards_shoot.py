import io
import struct
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from daibu import db
from daibu.cards import bundle, logo, render, shoot
from daibu.llm.base import Idea
from tests.card_fixtures import brand_asset, carousel_draft


def _png_size(data: bytes) -> tuple[int, int]:
    return struct.unpack(">II", data[16:24])


def _test_logo(tmp_path: Path) -> Path:
    path = tmp_path / "logo.png"
    Image.new("RGBA", (120, 60), (201, 50, 120, 255)).save(path)
    return path


def _html(tmp_path: Path) -> str:
    return render.page_html(
        carousel_draft().pages[0],
        "ElevenLabs",
        brand_asset(_test_logo(tmp_path)),
    )


def test_seven_pngs_have_logo_content_in_lower_third_and_no_overflow(tmp_path):
    asset = brand_asset(_test_logo(tmp_path))

    outputs = shoot.carousel_pngs(carousel_draft(), "ElevenLabs", asset)

    assert len(outputs) == 7
    assert all(_png_size(data) == (1080, 1350) for data in outputs)
    for data in outputs:
        image = Image.open(io.BytesIO(data)).convert("RGB")
        magenta = sum(
            1
            for pixel in image.get_flattened_data()
            if pixel[0] > 180 and pixel[1] < 90 and pixel[2] > 90
        )
        lower_ink = sum(
            1
            for y in range(900, 1200, 4)
            for x in range(120, 960, 4)
            if image.getpixel((x, y)) not in {
                (251, 252, 254),
                (213, 230, 244),
            }
        )
        assert magenta > 100
        assert lower_ink > 120

    reports = [
        shoot.inspect_html(render.page_html(page, "ElevenLabs", asset))
        for page in carousel_draft().pages
    ]
    assert all(report.logo_visible for report in reports)
    assert all(not report.canvas_overflow for report in reports)
    assert all(not report.content_overflow for report in reports)
    assert all(report.source_bottom <= 1260 for report in reports[1:])


def test_missing_logo_blocks_pngs_without_deleting_saved_draft(tmp_path):
    conn = db.connect(str(tmp_path / "t.db"))
    db.init_schema(conn)
    idea_id = db.add_idea(
        conn,
        None,
        Idea("t", "a", "", company="ElevenLabs"),
    )
    expected = carousel_draft()
    db.save_carousel_draft(conn, idea_id, expected)

    with pytest.raises(logo.BrandAssetRequired, match="官方 Logo"):
        shoot.carousel_pngs(expected, "ElevenLabs", None)

    assert db.get_carousel_draft(conn, idea_id) == expected


def test_who_page_uses_the_lower_part_of_the_canvas(tmp_path):
    asset = brand_asset(_test_logo(tmp_path))
    page = carousel_draft().pages[1]

    report = shoot.inspect_html(render.page_html(page, "ElevenLabs", asset))

    assert 1000 <= report.source_bottom <= 1260


def test_png_bytes_has_exact_canvas_size(tmp_path):
    data = shoot.png_bytes(_html(tmp_path))

    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert _png_size(data) == (1080, 1350)


def test_png_bytes_has_brand_pixels(tmp_path):
    data = shoot.png_bytes(_html(tmp_path))
    image = Image.open(io.BytesIO(data)).convert("RGB")

    assert image.getpixel((20, 20)) == (0xD5, 0xE6, 0xF4)
    assert image.getpixel((540, 300)) == (0xFB, 0xFC, 0xFE)


def test_text_actually_rendered_with_the_bundled_font(tmp_path):
    data = shoot.png_bytes(_html(tmp_path))
    image = Image.open(io.BytesIO(data)).convert("RGB")

    band = [image.getpixel((x, 715)) for x in range(140, 940, 4)]
    inked = [pixel for pixel in band if sum(pixel) < 650]

    assert len(inked) > 20, "白卡中央沒有足夠文字像素，代表字型可能未載入"


def test_missing_bundled_font_does_not_silently_use_fallback(tmp_path):
    html_text = _html(tmp_path).replace(".otf", "-missing.otf")

    with pytest.raises(RuntimeError, match="LINE Seed TW"):
        shoot.png_bytes(html_text)


def test_real_rendered_pngs_can_be_unpacked_from_the_bundle(tmp_path):
    asset = brand_asset(_test_logo(tmp_path))
    pngs = shoot.carousel_pngs(carousel_draft(), "ElevenLabs", asset)

    archive = bundle.carousel_zip(pngs)

    with zipfile.ZipFile(io.BytesIO(archive)) as packaged:
        assert packaged.namelist() == list(bundle.PAGE_FILENAMES)
        assert all(
            packaged.read(filename).startswith(b"\x89PNG")
            for filename in bundle.PAGE_FILENAMES
        )
