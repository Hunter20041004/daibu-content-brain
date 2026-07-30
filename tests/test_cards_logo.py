from pathlib import Path

import pytest
from PIL import Image

from daibu.cards import logo
from tests.card_fixtures import brand_asset


def test_logo_is_required_and_verified_png_becomes_data_uri(tmp_path):
    with pytest.raises(logo.BrandAssetRequired, match="官方 Logo"):
        logo.logo_data_uri(None, "ElevenLabs")

    path = Path(tmp_path) / "logo.png"
    Image.new("RGBA", (80, 40), (201, 50, 120, 255)).save(path)

    result = logo.logo_data_uri(brand_asset(path), "ElevenLabs")

    assert result.startswith("data:image/png;base64,")


def test_logo_rejects_svg_with_script(tmp_path):
    path = Path(tmp_path) / "logo.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg">'
        "<script>alert(1)</script></svg>",
        encoding="utf-8",
    )

    with pytest.raises(logo.InvalidBrandAsset, match="不安全"):
        logo.logo_data_uri(brand_asset(path), "ElevenLabs")


def test_logo_rejects_corrupt_png_with_valid_signature(tmp_path):
    path = Path(tmp_path) / "logo.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\nnot-a-real-image")

    with pytest.raises(logo.InvalidBrandAsset, match="格式不正確"):
        logo.logo_data_uri(brand_asset(path), "ElevenLabs")


def test_logo_rejects_png_without_transparency_channel(tmp_path):
    path = Path(tmp_path) / "logo.png"
    Image.new("RGB", (80, 40), (201, 50, 120)).save(path)

    with pytest.raises(logo.InvalidBrandAsset, match="透明"):
        logo.logo_data_uri(brand_asset(path), "ElevenLabs")


@pytest.mark.parametrize(
    "svg",
    (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<image href="//evil.example/logo.png"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<image href="data:image/png;base64,AAAA"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg">'
        "<style>@import url(https://evil.example/style.css);</style></svg>",
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<path style="fill:url(https://evil.example/image.svg)"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<path fill="url(https://evil.example/image.svg)"/></svg>',
        '<?xml-stylesheet type="text/css" href="https://evil.example/x.css"?>'
        '<svg xmlns="http://www.w3.org/2000/svg"/>',
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<animate attributeName="href" values="#safe;https://evil.example/x"/>'
        "</svg>",
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<set attributeName="href" to="https://evil.example/x"/></svg>',
    ),
)
def test_logo_rejects_svg_external_resource_bypasses(tmp_path, svg):
    path = Path(tmp_path) / "logo.svg"
    path.write_text(svg, encoding="utf-8")

    with pytest.raises(logo.InvalidBrandAsset, match="不安全|外部資源"):
        logo.logo_data_uri(brand_asset(path), "ElevenLabs")


def test_logo_accepts_svg_with_local_gradient_and_symbol(tmp_path):
    path = Path(tmp_path) / "logo.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<defs><linearGradient id="paint"><stop offset="0"/></linearGradient>'
        '<symbol id="mark"><path fill="url(#paint)" d="M0 0h10v10z"/></symbol>'
        '</defs><use href="#mark"/></svg>',
        encoding="utf-8",
    )

    result = logo.logo_data_uri(brand_asset(path), "ElevenLabs")

    assert result.startswith("data:image/svg+xml;base64,")
