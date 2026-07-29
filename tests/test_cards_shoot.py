import io
import struct

import pytest
from PIL import Image

from daibu.cards import render, shoot


def _png_size(data: bytes) -> tuple[int, int]:
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def _row():
    return {
        "page_no": 1,
        "page_type": "cover",
        "heading": "讓文字開口說話",
        "body": "ElevenLabs",
        "grounding": "model",
        "source_quote": "",
    }


def test_png_has_the_exact_canvas_size():
    data = shoot.png_bytes(render.page_html(_row(), company="ElevenLabs"))

    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert _png_size(data) == (1080, 1350)


def test_frame_and_card_pixels_are_the_specified_colors():
    """真的看畫出來的像素，不是看函式回傳值。"""
    data = shoot.png_bytes(render.page_html(_row(), company="ElevenLabs"))
    image = Image.open(io.BytesIO(data)).convert("RGB")

    assert image.getpixel((20, 20)) == (0xD5, 0xE6, 0xF4)
    assert image.getpixel((540, 300)) == (0xFB, 0xFC, 0xFE)


def test_text_actually_rendered_with_the_bundled_font():
    """字型沒載到的話，文字區域會是空白的一片白。"""
    data = shoot.png_bytes(render.page_html(_row(), company="ElevenLabs"))
    image = Image.open(io.BytesIO(data)).convert("RGB")

    band = [image.getpixel((x, 500)) for x in range(140, 940, 4)]
    inked = [pixel for pixel in band if sum(pixel) < 600]

    assert len(inked) > 20, "白卡中央那一橫排完全沒有深色像素，代表字沒有畫出來"


def test_missing_bundled_font_does_not_silently_use_a_fallback():
    html_text = render.page_html(_row(), company="ElevenLabs").replace(
        ".otf", "-missing.otf"
    )

    with pytest.raises(RuntimeError, match="LINE Seed TW"):
        shoot.png_bytes(html_text)
