import pathlib
import re
import tomllib

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


def test_carousel_preview_is_two_columns_on_desktop_and_one_on_mobile():
    styles = theme.css()
    selector = '[class*="st-key-carousel-preview-grid-"]'

    assert selector in styles
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in styles
    mobile = styles.split("@media (max-width: 700px)", maxsplit=1)[1]
    assert "grid-template-columns: minmax(0, 1fr)" in mobile
    assert "overflow-x: hidden" in mobile


def test_calendar_cards_have_fixed_height():
    styles = theme.css()
    calendar_rule = styles.split(
        ".calendar-card {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]

    assert "height:" in calendar_rule
    assert "overflow: hidden" in calendar_rule


def test_suggestion_card_label_is_smaller_than_its_message():
    styles = theme.css()
    label_rule = styles.split(
        ".suggestion-card__label {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    message_rule = styles.split(
        ".suggestion-card__message {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]

    assert "font-size: 0.75rem" in label_rule
    assert f"font-size: {theme.TYPE_SCALE[2]}" in message_rule


def test_suggestion_card_type_overrides_streamlit_paragraph_styles():
    styles = theme.css()
    message_rule = styles.split(
        ".stApp .suggestion-card__message {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]

    assert f"font-size: {theme.TYPE_SCALE[2]}" in message_rule


def test_header_is_not_transparent():
    styles = theme.css()
    header_rule = styles.split(
        '[data-testid="stHeader"] {',
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]

    assert "background: var(--canvas)" in header_rule
    assert "background: transparent" not in header_rule


def test_settings_form_has_a_readable_max_width():
    styles = theme.css()
    settings_rule = styles.split(
        '[class*="st-key-settings-form"] {',
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]

    assert "max-width: 35rem" in settings_rule
    assert "width: 100%" in settings_rule


def test_candidate_title_is_one_level_below_section_heading():
    styles = theme.css()
    candidate_rule = styles.split(
        ".candidate-card__title {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]

    assert f"font-size: {theme.TYPE_SCALE[3]}" in candidate_rule


def test_candidate_title_overrides_streamlit_heading_styles():
    styles = theme.css()
    candidate_rule = styles.split(
        ".stApp .candidate-card__title {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]

    assert f"font-size: {theme.TYPE_SCALE[3]}" in candidate_rule


def test_metrics_stay_in_one_row_on_mobile():
    styles = theme.css()
    mobile_styles = styles.split(
        "@media (max-width: 700px)",
        maxsplit=1,
    )[1]
    selector = (
        '[data-testid="stHorizontalBlock"]:has('
        '[data-testid="stMetric"]) {'
    )
    assert selector in mobile_styles
    metrics_rule = mobile_styles.split(
        selector,
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]

    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in metrics_rule


def test_mobile_overview_focuses_on_the_primary_action():
    styles = theme.css()
    mobile_styles = styles.split(
        "@media (max-width: 700px)",
        maxsplit=1,
    )[1]

    assert (
        '[class*="st-key-next-action-card"] .stButton > button {'
        in mobile_styles
    )
    assert "width: 100%" in mobile_styles.split(
        '[class*="st-key-next-action-card"] .stButton > button {',
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "display: none" in mobile_styles.split(
        ".page-deck {",
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]


def test_mobile_primary_action_expands_streamlit_wrapper():
    styles = theme.css()
    mobile_styles = styles.split(
        "@media (max-width: 700px)",
        maxsplit=1,
    )[1]
    wrapper_selector = (
        '[class*="st-key-next-action-card"] '
        '[data-testid="stElementContainer"]:has(.stButton) {'
    )

    assert wrapper_selector in mobile_styles
    wrapper_rule = mobile_styles.split(
        wrapper_selector,
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "width: 100%" in wrapper_rule


def test_workspace_scroll_iframe_does_not_take_layout_space():
    styles = theme.css()
    selector = (
        '[class*="st-key-workspace-scroll-bridge"] '
        '[data-testid="stElementContainer"]:has('
        '[data-testid="stIFrame"]) {'
    )

    assert selector in styles
    bridge_rule = styles.split(
        selector,
        maxsplit=1,
    )[1].split("}", maxsplit=1)[0]
    assert "position: absolute" in bridge_rule
    assert "height: 1px" in bridge_rule
    assert "overflow: hidden" in bridge_rule


def test_css_has_no_unused_classes():
    source_paths = [
        *pathlib.Path("pages").glob("*.py"),
        pathlib.Path("daibu/overview.py"),
        pathlib.Path("daibu/ui.py"),
    ]
    product_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in source_paths
    )
    css_classes = set(
        re.findall(
            r"\.([A-Za-z][A-Za-z0-9_-]*)",
            theme.css(),
        )
    )
    product_classes = {
        class_name
        for class_name in css_classes
        if (
            class_name not in {"stApp", "stButton"}
            and not class_name.startswith("st-emotion-cache-")
        )
    }

    assert {
        class_name
        for class_name in product_classes
        if class_name not in product_source
    } == set()
