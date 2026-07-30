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
