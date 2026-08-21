import io
import struct
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image
from playwright.sync_api import Locator

from daibu import db
from daibu.cards import bundle, logo, render, shoot
from daibu.cards.layout_schema import load_builtin_layout, replace_element
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


def _renderable_draft():
    draft = carousel_draft()
    compact_text = {
        "who": {
            "基本資料": "服務有聲書、遊戲、影音與多語在地化等內容團隊。",
        },
        "problem": {
            "誰受影響": "內容改字時，團隊可能要重排配音、錄音與後製。",
            "原本的代價": "等待檔期、反覆重錄與版本管理會持續累積。",
        },
        "how-ai": {
            "人仍負責": "人要確認內容、聲音授權與最後品質。",
        },
        "results": {
            "代表使用者": "有聲書、遊戲與影音團隊會先做可調整版本。",
            "使用前後": "改字後先生成，人再確認品質。",
            "購買關係": "購買的是可整合的語音能力。",
        },
        "cta": {
            "收束結論": "語氣與節奏可以反覆調整，但內容、授權與品質仍由人負責。",
        },
    }
    pages = []
    for page in draft.pages:
        replacements = compact_text.get(page.page_type, {})
        sections = tuple(
            replace(section, text=replacements.get(section.label, section.text))
            for section in page.sections
        )
        pages.append(replace(page, sections=sections))
    return replace(draft, pages=tuple(pages))


def test_seven_pngs_have_logo_content_in_lower_third_and_no_overflow(tmp_path):
    asset = brand_asset(_test_logo(tmp_path))

    draft = _renderable_draft()
    outputs = shoot.carousel_pngs(draft, "ElevenLabs", asset)

    assert len(outputs) == 7
    assert all(_png_size(data) == (1080, 1350) for data in outputs)
    for index, data in enumerate(outputs):
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
        if index == 0:
            assert magenta > 100
        assert lower_ink > 120

    reports = [
        shoot.inspect_html(render.page_html(page, "ElevenLabs", asset))
        for page in draft.pages
    ]
    assert reports[0].logo_visible
    assert all(not report.logo_visible for report in reports[1:])
    assert all(not report.canvas_overflow for report in reports)
    assert all(not report.content_overflow for report in reports)


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


def test_invalid_layout_blocks_every_screenshot(tmp_path, monkeypatch):
    asset = brand_asset(_test_logo(tmp_path))
    layout = replace_element(
        load_builtin_layout(),
        "cover",
        "heading",
        h=24,
    )
    screenshots = []
    original_screenshot = Locator.screenshot

    def recording_screenshot(locator, *args, **kwargs):
        screenshots.append(locator)
        return original_screenshot(locator, *args, **kwargs)

    monkeypatch.setattr(Locator, "screenshot", recording_screenshot)

    with pytest.raises(RuntimeError, match="第 1 頁.*封面標題"):
        shoot.carousel_pngs(
            carousel_draft(),
            "ElevenLabs",
            asset,
            layout,
        )

    assert screenshots == []


def test_who_page_keeps_mascot_visible_without_source_footer(tmp_path):
    asset = brand_asset(_test_logo(tmp_path))
    page = _renderable_draft().pages[1]

    report = shoot.inspect_html(render.page_html(page, "ElevenLabs", asset))

    assert report.mascot_visible
    assert report.source_bottom == 0


def test_story_layout_keeps_mascot_and_bottom_source_visible_without_overlap(
    tmp_path,
):
    asset = brand_asset(_test_logo(tmp_path))
    draft = _renderable_draft()
    reports = [
        shoot.inspect_html(render.page_html(page, "ElevenLabs", asset))
        for page in draft.pages
    ]

    assert all(report.mascot_visible for report in reports)
    assert all(not report.source_overlap for report in reports)
    assert all(report.source_bottom == 0 for report in reports)


def test_png_bytes_has_exact_canvas_size(tmp_path):
    data = shoot.png_bytes(_html(tmp_path))

    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert _png_size(data) == (1080, 1350)


def test_png_bytes_has_brand_pixels(tmp_path):
    data = shoot.png_bytes(_html(tmp_path))
    image = Image.open(io.BytesIO(data)).convert("RGB")

    assert image.getpixel((20, 20)) == (0x10, 0x2F, 0x3D)
    assert image.getpixel((20, 1340)) == (0xEC, 0x98, 0x70)


def test_text_actually_rendered_with_the_bundled_font(tmp_path):
    data = shoot.png_bytes(_html(tmp_path))
    image = Image.open(io.BytesIO(data)).convert("RGB")

    band = [image.getpixel((x, 430)) for x in range(140, 760, 4)]
    inked = [pixel for pixel in band if sum(pixel) < 650]

    assert len(inked) > 20, "封面公司名沒有足夠文字像素，代表字型可能未載入"


def test_missing_bundled_font_does_not_silently_use_fallback(tmp_path):
    html_text = _html(tmp_path).replace(".otf", "-missing.otf")

    with pytest.raises(RuntimeError, match="LINE Seed TW"):
        shoot.png_bytes(html_text)


def test_real_rendered_pngs_can_be_unpacked_from_the_bundle(tmp_path):
    asset = brand_asset(_test_logo(tmp_path))
    pngs = shoot.carousel_pngs(_renderable_draft(), "ElevenLabs", asset)

    archive = bundle.carousel_zip(pngs)

    with zipfile.ZipFile(io.BytesIO(archive)) as packaged:
        assert packaged.namelist() == list(bundle.PAGE_FILENAMES)
        assert all(
            packaged.read(filename).startswith(b"\x89PNG")
            for filename in bundle.PAGE_FILENAMES
        )
