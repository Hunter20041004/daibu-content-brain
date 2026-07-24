import pytest

from daibu import theme


def test_contrast_ratio_black_on_white_is_21():
    assert round(theme.contrast_ratio("#000000", "#FFFFFF"), 1) == 21.0


def test_light_palette_matches_brand_tokens():
    assert theme.LIGHT["BRAND_PRIMARY"] == "#6FC1CC"
    assert theme.LIGHT["INK"] == "#0E0E2C"
    assert theme.LIGHT["CANVAS"] == "#E9F6FF"
    assert theme.LIGHT["SURFACE"] == "#FAFCFE"


def test_dark_palette_matches_brand_tokens():
    assert theme.DARK["INK"] == "#FAFCFE"
    assert theme.DARK["CANVAS"] == "#0E0E2C"
    assert theme.DARK["SURFACE"] == "#171733"


def test_primary_button_must_use_ink_not_white():
    primary = theme.LIGHT["BRAND_PRIMARY"]

    assert theme.contrast_ratio(theme.LIGHT["INK"], primary) >= 4.5
    assert theme.contrast_ratio("#FFFFFF", primary) < 4.5


@pytest.mark.parametrize("palette", [theme.LIGHT, theme.DARK])
def test_body_text_passes_aa(palette):
    assert theme.contrast_ratio(palette["INK"], palette["CANVAS"]) >= 4.5
    assert theme.contrast_ratio(palette["INK"], palette["SURFACE"]) >= 4.5


def test_dark_secondary_is_readable():
    secondary = theme.DARK["BRAND_SECONDARY"]

    assert secondary != "#32738F"
    assert theme.contrast_ratio(secondary, theme.DARK["CANVAS"]) >= 4.5


def test_light_and_dark_palettes_share_token_names():
    assert set(theme.LIGHT) == set(theme.DARK) == set(theme.PALETTE_KEYS)


def test_font_stack_covers_latin_and_chinese():
    assert "Figtree" in theme.FONT_STACK
    assert "Noto Sans TC" in theme.FONT_STACK


def test_type_scale_covers_h1_to_h6():
    assert len(theme.TYPE_SCALE) == 6
    assert len(theme.TYPE_WEIGHTS) == 6
    assert theme.TYPE_SCALE[0] == "2.5rem"
    assert theme.TYPE_WEIGHTS[0] == 800
