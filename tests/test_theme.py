import pathlib
import pytest
import tomllib

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


def test_config_toml_matches_tokens():
    config = tomllib.loads(
        pathlib.Path(".streamlit/config.toml").read_text(),
    )
    light = config["theme"]["light"]
    dark = config["theme"]["dark"]

    assert light["backgroundColor"].upper() == theme.LIGHT["CANVAS"]
    assert light["textColor"].upper() == theme.LIGHT["INK"]
    assert light["primaryColor"].upper() == theme.LIGHT["BRAND_PRIMARY"]
    assert dark["backgroundColor"].upper() == theme.DARK["CANVAS"]
    assert dark["textColor"].upper() == theme.DARK["INK"]


def test_css_declares_tokens_as_variables():
    styles = theme.css()

    assert "--brand-primary: #6FC1CC" in styles
    assert theme.FONT_STACK in styles


def test_css_protects_primary_action_and_motion_preferences():
    styles = theme.css()

    assert "--primary-button-ink: #0E0E2C" in styles
    assert "scale(0.97)" in styles
    assert "focus-visible" in styles
    assert "prefers-reduced-motion" in styles
    assert "transition: all" not in styles


def test_css_preserves_streamlit_material_icon_font():
    styles = theme.css()

    assert '[data-testid="stIconMaterial"]' in styles
    assert '"Material Symbols Rounded"' in styles


def test_css_does_not_depend_on_light_dark_function():
    styles = theme.css()

    assert "light-dark(" not in styles


def test_css_defines_dark_palette_in_media_query():
    styles = theme.css()

    dark_section = styles.split(
        "@media (prefers-color-scheme: dark)",
        maxsplit=1,
    )
    assert len(dark_section) == 2
    assert f"--ink: {theme.DARK['INK']}" in dark_section[1]


def test_palette_variables_are_defined_on_root_not_app():
    styles = theme.css()
    root_section = styles.split(":root {", maxsplit=1)[1].split("}", maxsplit=1)[0]

    assert f"--ink: {theme.LIGHT['INK']}" in root_section


def test_app_text_color_rule_does_not_override_portal_labels():
    styles = theme.css()

    assert "\n    p, label, span {" not in styles
    assert ".stApp p, .stApp label, .stApp span {" in styles


def test_css_explicit_mode_is_the_final_palette_override():
    styles = theme.css("light")

    assert styles.rfind(f"--ink: {theme.LIGHT['INK']}") > styles.rfind(
        "@media (prefers-color-scheme: dark)",
    )


def test_css_uses_verified_streamlit_classes_for_manual_theme_switch():
    styles = theme.css()

    assert (
        "body:has(.stApp.st-emotion-cache-1ad78rz)"
        in styles
    )
    dark_override = styles.split(
        "body:has(.stApp.st-emotion-cache-13icvhg)",
        maxsplit=1,
    )
    assert len(dark_override) == 2
    assert f"--ink: {theme.DARK['INK']}" in dark_override[1]


def test_theme_list_caption_hugs_its_button():
    styles = theme.css()
    meta_styles = styles.split(".theme-item__meta {", maxsplit=1)

    assert (
        '[data-testid="stVerticalBlock"][class*="st-key-theme-item-"]'
        in styles
    )
    assert "gap: 0 !important" in styles
    assert len(meta_styles) == 2
    rule = meta_styles[1].split("}", maxsplit=1)[0]
    assert "margin-top: 0.25rem" in rule
    assert "margin-bottom: 0.9rem" in rule


def test_context_column_sticks_on_desktop():
    styles = theme.css()
    desktop_styles = styles.split(
        "@media (min-width: 701px)",
        maxsplit=1,
    )

    assert len(desktop_styles) == 2
    wrapper_rule = desktop_styles[1].split(
        '[data-testid="stLayoutWrapper"]:has(',
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    context_rule = desktop_styles[1].split(
        ".context-column",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "position: sticky" in wrapper_rule
    assert "top:" in wrapper_rule
    assert "max-height:" in context_rule
    assert "overflow-y: auto" in context_rule


def test_context_column_sticky_applies_to_streamlit_layout_wrapper():
    styles = theme.css()

    assert (
        '[data-testid="stLayoutWrapper"]:has(> '
        '[data-testid="stVerticalBlock"][class*="st-key-context-column"])'
        in styles
    )
