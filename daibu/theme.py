PALETTE_KEYS = (
    "BRAND_PRIMARY",
    "BRAND_SECONDARY",
    "INK",
    "SURFACE",
    "CANVAS",
    "HIGHLIGHT",
    "BORDER",
)

FONT_STACK = '"Figtree", "Noto Sans TC", sans-serif'
TYPE_SCALE = ["2.5rem", "1.75rem", "1.375rem", "1.125rem", "1rem", "0.875rem"]
TYPE_WEIGHTS = [800, 800, 700, 700, 600, 600]

LIGHT = {
    "BRAND_PRIMARY": "#6FC1CC",
    "BRAND_SECONDARY": "#32738F",
    "INK": "#0E0E2C",
    "SURFACE": "#FAFCFE",
    "CANVAS": "#E9F6FF",
    "HIGHLIGHT": "#F8C0A0",
    "BORDER": "#C7E2EA",
}

DARK = {
    "BRAND_PRIMARY": "#6FC1CC",
    "BRAND_SECONDARY": "#6FC1CC",
    "INK": "#FAFCFE",
    "SURFACE": "#171733",
    "CANVAS": "#0E0E2C",
    "HIGHLIGHT": "#F8C0A0",
    "BORDER": "#2A2A4A",
}

# Streamlit 1.60.0 exposes no stable data-theme attribute. These verified
# Emotion classes let manual theme changes update both .stApp and #portal
# immediately; media queries and st.context remain fallback layers.
STREAMLIT_THEME_CLASSES = {
    "light": "st-emotion-cache-1ad78rz",
    "dark": "st-emotion-cache-13icvhg",
}


def relative_luminance(hex_color: str) -> float:
    normalized = hex_color.removeprefix("#")
    channels = [int(normalized[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted(
        (relative_luminance(first), relative_luminance(second)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def _css_variables(palette: dict[str, str]) -> str:
    return "\n".join(
        f"--{key.lower().replace('_', '-')}: {palette[key]};"
        for key in PALETTE_KEYS
    )


def _adaptive_css_variables() -> str:
    light_variables = _css_variables(LIGHT)
    dark_variables = _css_variables(DARK)
    return f"""
    :root {{
        {light_variables}
    }}

    @media (prefers-color-scheme: dark) {{
        :root {{
            {dark_variables}
        }}
    }}
    """


def _manual_theme_overrides() -> str:
    return "\n".join(
        (
            f"body:has(.stApp.{STREAMLIT_THEME_CLASSES[mode]}) {{\n"
            f"{_css_variables(palette)}\n"
            "}"
        )
        for mode, palette in (("light", LIGHT), ("dark", DARK))
    )


def css(mode: str | None = None) -> str:
    selected_palette_rules = ""
    if mode is not None:
        selected_variables = _css_variables(
            {"light": LIGHT, "dark": DARK}[mode],
        )
        selected_palette_rules = f"""
        :root {{
            {selected_variables}
        }}
        """
    adaptive_rules = _adaptive_css_variables()
    manual_theme_rules = _manual_theme_overrides()
    heading_rules = "\n".join(
        (
            f"h{level} {{ font-size: {size}; font-weight: {weight}; }}"
            for level, (size, weight) in enumerate(
                zip(TYPE_SCALE, TYPE_WEIGHTS, strict=True),
                start=1,
            )
        ),
    )
    return f"""
    {adaptive_rules}
    {manual_theme_rules}
    {selected_palette_rules}

    :root {{
        --primary-button-ink: {LIGHT["INK"]};
        --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
        font-family: {FONT_STACK};
    }}

    .stApp {{
        background: var(--canvas);
        color: var(--ink);
        font-family: {FONT_STACK};
    }}

    .stApp *,
    .stApp button,
    .stApp input,
    .stApp textarea,
    .stApp select {{
        font-family: {FONT_STACK};
    }}

    [data-testid="stTextArea"] [data-baseweb="textarea"] {{
        background: var(--surface) !important;
        border-color: var(--border) !important;
    }}

    [data-testid="stTextArea"] textarea {{
        caret-color: var(--brand-secondary);
        color: var(--ink) !important;
        -webkit-text-fill-color: var(--ink) !important;
    }}

    [data-testid="stIconMaterial"],
    [data-testid="stExpanderIconSpinner"],
    [data-testid="stExpanderIconCheck"],
    [data-testid="stExpanderIconError"] {{
        font-family: "Material Symbols Rounded" !important;
    }}

    {heading_rules}

    h1 {{
        letter-spacing: 0.04em;
        line-height: 1.12;
    }}

    .stApp h1, .stApp h2, .stApp h3,
    .stApp h4, .stApp h5, .stApp h6,
    .stApp p, .stApp label, .stApp span {{
        color: var(--ink);
    }}

    a {{
        color: var(--brand-secondary);
    }}

    [data-testid="stHeader"] {{
        background: var(--canvas);
        border-bottom: 1px solid var(--border);
    }}

    [data-testid="stSidebar"] {{
        background: var(--surface);
        border-right: 1px solid var(--border);
    }}

    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: var(--surface);
        border-color: var(--border);
        border-radius: 16px;
        box-shadow: none;
    }}

    [data-testid="stMetric"] {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1rem;
    }}

    [data-testid="stMetricLabel"],
    [data-testid="stMetricLabel"] *,
    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] * {{
        color: var(--ink);
    }}

    .stButton > button,
    [data-testid^="stBaseButton"] {{
        min-height: 44px;
        border-color: var(--border);
        border-radius: 12px;
        color: var(--ink);
        transition:
            transform 160ms var(--ease-out),
            border-color 160ms ease,
            background-color 160ms ease;
    }}

    .stButton > button:active,
    [data-testid^="stBaseButton"]:active {{
        transform: scale(0.97);
    }}

    .stButton > button[kind="primary"],
    [data-testid="stBaseButton-primary"] {{
        background: var(--brand-primary);
        border-color: var(--brand-primary);
        color: var(--primary-button-ink) !important;
        font-weight: 700;
    }}

    .stButton > button[kind="primary"] *,
    [data-testid="stBaseButton-primary"] * {{
        color: var(--primary-button-ink) !important;
    }}

    button:focus-visible,
    a:focus-visible,
    input:focus-visible,
    textarea:focus-visible,
    select:focus-visible,
    [tabindex]:focus-visible {{
        outline: 2px solid var(--brand-primary) !important;
        outline-offset: 2px;
    }}

    .page-kicker {{
        color: var(--brand-secondary) !important;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        margin-bottom: 0.35rem;
        text-transform: uppercase;
    }}

    .page-deck {{
        color: var(--ink);
        font-size: 1rem;
        line-height: 1.6;
        max-width: 68ch;
        opacity: 0.78;
    }}

    [data-testid="stVerticalBlock"][class*="st-key-theme-item-"] {{
        gap: 0 !important;
    }}

    .theme-item__meta {{
        color: var(--ink);
        font-size: 0.875rem;
        line-height: 1.5;
        margin-top: 0.25rem !important;
        margin-bottom: 0.9rem !important;
        opacity: 0.62;
    }}

    .theme-item__current {{
        background: color-mix(in srgb, var(--brand-primary) 24%, var(--surface));
        border-radius: 999px;
        display: block;
        font-size: 0.68rem;
        font-weight: 800;
        margin-bottom: 0.35rem;
        opacity: 1;
        padding: 0.25rem 0.5rem;
        width: fit-content;
    }}

    [data-testid="stVerticalBlock"][class*="st-key-source-row-"] {{
        gap: 0 !important;
        padding: 0.3rem 0;
    }}

    [data-testid="stVerticalBlock"][class*="st-key-source-row-"]
    [data-testid="stHorizontalBlock"] {{
        align-items: center;
        gap: 0.5rem;
    }}

    .source-row__summary {{
        align-items: center;
        display: grid;
        gap: 0.1rem 0.45rem;
        grid-template-areas:
            "name badge"
            "usage domain";
        grid-template-columns: minmax(0, 1fr) auto;
        min-height: 2.5rem;
        min-width: 0;
        overflow: hidden;
        white-space: nowrap;
    }}

    .source-row__name {{
        font-size: 0.875rem;
        font-weight: 700;
        grid-area: name;
        line-height: 1.2;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    .source-row__badge {{
        background: var(--border);
        border-radius: 999px;
        font-size: 0.65rem;
        font-weight: 800;
        grid-area: badge;
        line-height: 1;
        padding: 0.25rem 0.45rem;
    }}

    .source-row__usage,
    .source-row__domain {{
        font-size: 0.75rem;
        line-height: 1.2;
        opacity: 0.62;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    .source-row__usage {{
        grid-area: usage;
    }}

    .source-row__domain {{
        grid-area: domain;
    }}

    [data-testid="stVerticalBlock"][class*="st-key-source-row-"]
    [data-testid="stPopoverButton"] {{
        height: 2.25rem;
        min-height: 2.25rem;
        padding: 0 0.65rem;
    }}

    [data-testid="stVerticalBlock"][class*="st-key-source-row-"]
    [data-testid="stPopoverButton"] p {{
        font-size: 0.75rem;
        line-height: 1;
        white-space: nowrap;
    }}

    [data-testid="stVerticalBlock"][class*="st-key-source-row-"]
    [data-testid="stPopoverButton"] [data-testid="stIconMaterial"] {{
        display: none;
    }}

    .brand-lockup {{
        align-items: center;
        display: flex;
        gap: 0.75rem;
    }}

    .brand-lockup svg {{
        display: block;
        flex: 0 0 auto;
        height: auto;
    }}

    .brand-lockup__name {{
        color: var(--ink);
        font-size: 1rem;
        font-weight: 800;
        line-height: 1.25;
    }}

    .brand-lockup__meta {{
        color: var(--brand-secondary);
        display: block;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        margin-top: 0.15rem;
        text-transform: uppercase;
    }}

    .theme-switcher {{
        border-top: 1px dashed var(--border);
        margin-top: 0.75rem;
        padding-top: 0.75rem;
    }}

    .theme-switcher__eyebrow,
    .theme-switcher__status {{
        color: var(--brand-secondary) !important;
        font-size: 0.75rem;
        font-weight: 700;
        line-height: 1.35;
        margin: 0 0 0.4rem;
    }}

    .theme-switcher__button {{
        align-items: center;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.75rem;
        color: var(--ink);
        cursor: pointer;
        display: flex;
        font-size: 0.875rem;
        font-weight: 800;
        gap: 0.65rem;
        justify-content: flex-start;
        min-height: 44px;
        padding: 0.65rem 0.8rem;
        transition:
            background-color 160ms var(--ease-out),
            border-color 160ms var(--ease-out),
            color 160ms var(--ease-out),
            transform 140ms var(--ease-out);
        width: 100%;
    }}

    .theme-switcher__icon {{
        background: var(--brand-secondary);
        display: block;
        flex: 0 0 1.15rem;
        height: 1.15rem;
        -webkit-mask-position: center;
        -webkit-mask-repeat: no-repeat;
        -webkit-mask-size: contain;
        mask-position: center;
        mask-repeat: no-repeat;
        mask-size: contain;
        width: 1.15rem;
    }}

    .theme-switcher__icon--moon {{
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' xmlns='http://www%2Ew3%2Eorg/2000/svg'%3E%3Cpath d='M20.2 15.4A8.4 8.4 0 0 1 8.6 3.8 8.5 8.5 0 1 0 20.2 15.4Z'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' xmlns='http://www%2Ew3%2Eorg/2000/svg'%3E%3Cpath d='M20.2 15.4A8.4 8.4 0 0 1 8.6 3.8 8.5 8.5 0 1 0 20.2 15.4Z'/%3E%3C/svg%3E");
    }}

    .theme-switcher__icon--sun {{
        -webkit-mask-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' xmlns='http://www%2Ew3%2Eorg/2000/svg'%3E%3Ccircle cx='12' cy='12' r='4'/%3E%3Cpath d='M11 1h2v4h-2zM11 19h2v4h-2zM1 11h4v2H1zM19 11h4v2h-4zM3.5 4.9l1.4-1.4 2.8 2.8-1.4 1.4zM16.3 17.7l1.4-1.4 2.8 2.8-1.4 1.4zM3.5 19.1l2.8-2.8 1.4 1.4-2.8 2.8zM16.3 6.3l2.8-2.8 1.4 1.4-2.8 2.8z'/%3E%3C/svg%3E");
        mask-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 24 24' xmlns='http://www%2Ew3%2Eorg/2000/svg'%3E%3Ccircle cx='12' cy='12' r='4'/%3E%3Cpath d='M11 1h2v4h-2zM11 19h2v4h-2zM1 11h4v2H1zM19 11h4v2h-4zM3.5 4.9l1.4-1.4 2.8 2.8-1.4 1.4zM16.3 17.7l1.4-1.4 2.8 2.8-1.4 1.4zM3.5 19.1l2.8-2.8 1.4 1.4-2.8 2.8zM16.3 6.3l2.8-2.8 1.4 1.4-2.8 2.8z'/%3E%3C/svg%3E");
    }}

    .theme-switcher__button:focus-visible {{
        outline: 3px solid var(--brand-primary);
        outline-offset: 2px;
    }}

    .theme-switcher__button:disabled {{
        cursor: wait;
        opacity: 0.6;
    }}

    .theme-switcher__status {{
        margin: 0.4rem 0 0;
        min-height: 1rem;
    }}

    @media (hover: hover) and (pointer: fine) {{
        .theme-switcher__button:hover {{
            background: color-mix(in srgb, var(--brand-primary) 16%, var(--surface));
            border-color: var(--brand-primary);
        }}

        .theme-switcher__button:active {{
            transform: scale(0.98);
        }}
    }}

    .mascot-coach {{
        align-items: center;
        background:
            radial-gradient(circle at 92% 18%, var(--highlight) 0 4px, transparent 5px),
            var(--surface);
        border: 1px solid var(--border);
        border-radius: 22px;
        display: grid;
        gap: 1rem;
        grid-template-columns: 6.5rem minmax(0, 1fr);
        overflow: hidden;
        padding: 1.1rem 1.25rem;
        position: relative;
    }}

    .mascot-coach::after {{
        border: 1px dashed var(--brand-primary);
        border-radius: 999px;
        content: "";
        height: 5rem;
        opacity: 0.45;
        position: absolute;
        right: -2rem;
        top: -2rem;
        width: 5rem;
    }}

    .mascot-coach--success {{
        background: color-mix(in srgb, var(--brand-primary) 18%, var(--surface));
    }}

    .mascot-coach--warning {{
        background: color-mix(in srgb, var(--highlight) 35%, var(--surface));
    }}

    .mascot-coach__figure {{
        align-items: center;
        display: flex;
        justify-content: center;
        min-height: 5.5rem;
    }}

    .mascot-coach__figure svg {{
        height: auto;
        max-height: 6.25rem;
        width: 100% !important;
    }}

    .mascot-coach__copy strong {{
        display: block;
        font-size: {TYPE_SCALE[2]};
        font-weight: 800;
        letter-spacing: -0.02em;
        line-height: 1.25;
    }}

    .mascot-coach__copy p {{
        line-height: 1.55;
        margin: 0.45rem 0 0;
        opacity: 0.72;
    }}

    .series-row {{
        align-items: center;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 16px;
        display: grid;
        gap: 1.25rem;
        grid-template-columns: minmax(10rem, 0.75fr) minmax(22rem, 1.6fr);
        margin-bottom: 0.75rem;
        padding: 1rem 1.1rem;
        transition:
            border-color 160ms ease,
            transform 160ms var(--ease-out);
    }}

    .series-row__identity span {{
        display: block;
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        margin-bottom: 0.2rem;
        opacity: 0.58;
    }}

    .series-row__identity strong {{
        font-size: 1rem;
        line-height: 1.35;
    }}

    .workflow-stepper {{
        display: grid;
        gap: 0.45rem;
        grid-template-columns: repeat(4, minmax(0, 1fr));
    }}

    .workflow-step {{
        align-items: center;
        border-bottom: 2px solid var(--border);
        display: flex;
        font-size: 0.75rem;
        font-weight: 700;
        gap: 0.3rem;
        min-height: 2rem;
        opacity: 0.48;
        padding-bottom: 0.35rem;
    }}

    .workflow-step b {{
        font-size: 0.85rem;
    }}

    .workflow-step--complete {{
        border-color: var(--brand-primary);
        opacity: 0.78;
    }}

    .workflow-step--current {{
        border-color: var(--highlight);
        opacity: 1;
    }}

    .workflow-step--current b {{
        color: var(--brand-secondary) !important;
    }}

    .workflow-step--upcoming {{
        opacity: 0.42;
    }}

    .daibu-card,
    .empty-state,
    .suggestion-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 16px;
        color: var(--ink);
        padding: 1.25rem;
    }}

    .suggestion-card {{
        background: var(--highlight);
        color: var(--primary-button-ink);
    }}

    .suggestion-card * {{
        color: var(--primary-button-ink);
    }}

    .stApp .suggestion-card__label {{
        color: var(--primary-button-ink);
        display: block;
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        opacity: 0.65;
    }}

    .stApp .suggestion-card__message {{
        color: var(--primary-button-ink);
        font-size: {TYPE_SCALE[2]};
        font-weight: {TYPE_WEIGHTS[2]};
        line-height: 1.35;
        margin: 0.4rem 0 0;
    }}

    [data-testid="stVerticalBlock"][class*="st-key-next-action-card"] {{
        background: var(--highlight);
        border: 1px solid var(--border);
        border-radius: 16px;
        gap: 0.75rem;
        padding: 1.25rem;
    }}

    [data-testid="stVerticalBlock"][class*="st-key-next-action-card"]
    .suggestion-card {{
        background: transparent;
        border: 0;
        padding: 0;
    }}

    [data-testid="stVerticalBlock"][class*="st-key-settings-form"] {{
        max-width: 35rem;
        width: 100%;
    }}

    [class*="st-key-workspace-scroll-bridge"] [data-testid="stElementContainer"]:has([data-testid="stIFrame"]) {{
        height: 1px;
        opacity: 0;
        overflow: hidden;
        pointer-events: none;
        position: absolute;
        width: 1px;
    }}

    .calendar-card {{
        box-sizing: border-box;
        height: 7.5rem;
        overflow: hidden;
        position: relative;
    }}

    .calendar-card p {{
        display: -webkit-box;
        margin-bottom: 0;
        overflow: hidden;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 3;
    }}

    .calendar-card--empty p {{
        opacity: 0.45;
    }}

    .calendar-card--today {{
        border-top: 4px solid var(--brand-primary);
    }}

    .empty-state {{
        border-style: dashed;
        text-align: center;
    }}

    .stApp .idea-company {{
        color: var(--brand-secondary);
        font-size: {TYPE_SCALE[5]};
        font-weight: 700;
        letter-spacing: 0.02em;
        line-height: 1.3;
        margin-bottom: 0.25rem;
    }}

    .stApp .candidate-card__title {{
        font-size: {TYPE_SCALE[3]};
        font-weight: {TYPE_WEIGHTS[3]};
        line-height: 1.3;
        margin: 0 0 0.5rem;
    }}

    .candidate-card__new {{
        align-items: center;
        background: var(--brand-primary);
        border-radius: 999px;
        color: var(--primary-button-ink) !important;
        display: inline-flex;
        font-size: 0.65rem;
        font-weight: 800;
        line-height: 1;
        margin-right: 0.4rem;
        min-height: 1.25rem;
        padding: 0.2rem 0.4rem;
        vertical-align: 0.15em;
    }}

    .stApp .candidate-card__angle {{
        color: var(--ink);
        font-size: {TYPE_SCALE[5]};
        font-weight: 600;
        line-height: 1.45;
    }}

    .carousel-status {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        margin: 0.5rem 0 1rem;
        padding: 0.9rem 1rem;
    }}

    .carousel-checklist {{
        display: grid;
        gap: 0.5rem;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        list-style: none;
        margin: 0 0 1rem;
        padding: 0;
    }}

    .carousel-checklist__item {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        display: grid;
        gap: 0.2rem;
        min-width: 0;
        padding: 0.75rem;
    }}

    .carousel-checklist__item > span {{
        font-size: 0.68rem;
        font-variant-numeric: tabular-nums;
        font-weight: 800;
        opacity: 0.5;
    }}

    .carousel-checklist__item strong {{
        font-size: 0.78rem;
        line-height: 1.35;
    }}

    .carousel-checklist__item small {{
        font-size: 0.68rem;
        font-weight: 700;
        opacity: 0.55;
    }}

    .carousel-checklist__item--complete {{
        background: color-mix(in srgb, var(--brand-primary) 14%, var(--surface));
    }}

    .carousel-checklist__item--current {{
        background: color-mix(in srgb, var(--highlight) 42%, var(--surface));
        border-color: var(--highlight);
        transform: translateY(-2px);
    }}

    .carousel-checklist__item--current small {{
        opacity: 1;
    }}

    .carousel-checklist__item--blocked {{
        opacity: 0.48;
    }}

    .carousel-status strong {{
        display: block;
        font-size: 1rem;
        line-height: 1.35;
    }}

    .carousel-status p {{
        font-size: 0.875rem;
        line-height: 1.55;
        margin: 0.35rem 0 0;
        opacity: 0.72;
    }}

    .verified-source,
    .verified-logo {{
        align-items: baseline;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        display: flex;
        gap: 0.75rem;
        justify-content: space-between;
        margin-top: 0.65rem;
        padding: 0.75rem 0.9rem;
    }}

    .logo-candidate-card {{
        background: var(--surface);
        border: 1px solid var(--brand-primary);
        border-radius: 16px;
        box-shadow: 0 10px 24px color-mix(
            in srgb,
            var(--ink) 12%,
            transparent
        );
        margin: 0.75rem 0;
        padding: 1rem;
    }}

    .logo-candidate-card strong {{
        display: block;
        font-size: 1rem;
        line-height: 1.4;
        margin-top: 0.65rem;
    }}

    .logo-candidate-card p {{
        font-size: 0.875rem;
        line-height: 1.6;
        margin: 0.4rem 0 0;
        opacity: 0.72;
    }}

    .logo-candidate-card__status {{
        background: var(--canvas);
        border: 1px solid var(--brand-primary);
        border-radius: 999px;
        display: inline-flex;
        font-size: 0.75rem;
        font-weight: 800;
        line-height: 1;
        padding: 0.35rem 0.6rem;
    }}

    .logo-evidence-card {{
        background: color-mix(in srgb, var(--surface) 88%, var(--canvas));
        border: 1px solid var(--border);
        border-left: 3px solid var(--brand-primary);
        border-radius: 12px;
        margin: 1rem 0 0.65rem;
        padding: 0.85rem 0.95rem;
        transition: transform 180ms ease, border-color 180ms ease;
    }}

    .logo-evidence-card__heading {{
        align-items: baseline;
        display: flex;
        gap: 0.75rem;
        justify-content: space-between;
    }}

    .logo-evidence-card__heading span {{
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        opacity: 0.62;
        text-transform: uppercase;
    }}

    .logo-evidence-card__heading strong {{
        font-size: 0.9rem;
        overflow-wrap: anywhere;
    }}

    .logo-evidence-card__facts {{
        align-items: center;
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-top: 0.65rem;
    }}

    .logo-evidence-card__facts span {{
        background: var(--canvas);
        border: 1px solid var(--border);
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        line-height: 1.25;
        padding: 0.24rem 0.5rem;
    }}

    .logo-evidence-card p {{
        font-size: 0.8rem;
        line-height: 1.5;
        margin: 0.65rem 0 0;
        opacity: 0.7;
    }}

    [class*="st-key-logo-preview-"] {{
        background: linear-gradient(
            90deg,
            #f8fafc 0 50%,
            #171733 50% 100%
        );
        border: 1px solid var(--border);
        border-radius: 12px;
        min-height: 8.5rem;
        padding: 1.25rem;
    }}

    [class*="st-key-logo-preview-"] [data-testid="stImage"] {{
        margin-inline: auto;
    }}

    .verified-source strong,
    .verified-logo strong {{
        font-size: 0.875rem;
        line-height: 1.4;
    }}

    .verified-source time {{
        flex: 0 0 auto;
        font-size: 0.75rem;
        opacity: 0.62;
    }}

    .source-kind {{
        border: 1px solid var(--border);
        border-radius: 999px;
        display: inline-flex;
        font-size: 0.72rem;
        font-weight: 700;
        line-height: 1.25;
        margin-left: 0.55rem;
        padding: 0.18rem 0.5rem;
    }}

    .source-kind[data-kind="official"] {{
        border-color: var(--brand-primary);
        color: var(--brand-primary);
    }}

    .source-kind[data-kind="third_party"] {{
        border-color: var(--highlight);
        color: var(--ink);
    }}

    [data-testid="stVerticalBlock"][class*="st-key-carousel-preview-grid-"] {{
        display: grid;
        gap: 1rem;
        grid-template-columns: minmax(0, 1fr);
    }}

    @media (hover: hover) and (pointer: fine) {{
        .logo-evidence-card:hover {{
            border-color: var(--brand-primary);
            transform: translateY(-1px);
        }}

        .series-row:hover {{
            border-color: var(--brand-primary);
            transform: translateY(-1px);
        }}

        .stButton > button:hover,
        [data-testid^="stBaseButton"]:hover {{
            border-color: var(--brand-secondary);
        }}

        .stButton > button[kind="primary"]:hover,
        [data-testid="stBaseButton-primary"]:hover {{
            background: var(--brand-primary);
            border-color: var(--brand-primary);
            transform: translateY(-1px);
        }}
    }}

    @media (min-width: 701px) {{
        [data-testid="stLayoutWrapper"]:has(> [data-testid="stVerticalBlock"][class*="st-key-context-column"]) {{
            position: sticky;
            top: 4.5rem;
        }}

        .context-column,
        [data-testid="stVerticalBlock"][class*="st-key-context-column"] {{
            max-height: calc(100vh - 5.5rem);
            overflow-y: auto;
            scrollbar-gutter: stable;
        }}
    }}

    @media (max-width: 700px) {{
        .logo-evidence-card__facts {{
            align-items: flex-start;
        }}

        .mascot-coach {{
            gap: 0.75rem;
            grid-template-columns: 4.5rem minmax(0, 1fr);
            padding: 0.9rem;
        }}

        .mascot-coach__figure {{
            min-height: 4.5rem;
        }}

        .mascot-coach__copy strong {{
            font-size: 1.05rem;
        }}

        .mascot-coach__copy p {{
            font-size: 0.82rem;
        }}

        .series-row {{
            gap: 0.75rem;
            grid-template-columns: minmax(0, 1fr);
        }}

        .workflow-step {{
            font-size: 0.68rem;
        }}

        .carousel-checklist {{
            grid-template-columns: minmax(0, 1fr);
        }}

        .carousel-checklist__item {{
            align-items: center;
            gap: 0.65rem;
            grid-template-columns: 2rem minmax(0, 1fr) auto;
            padding: 0.65rem 0.75rem;
        }}

        .carousel-checklist__item--current {{
            transform: none;
        }}

        [data-testid="stVerticalBlock"][class*="st-key-carousel-preview-grid-"] {{
            grid-template-columns: minmax(0, 1fr);
            min-width: 0;
            overflow-x: hidden;
        }}

        [data-testid="stVerticalBlock"][class*="st-key-carousel-preview-grid-"]
        [data-testid="stImage"] {{
            max-width: 100%;
        }}

        .page-deck {{
            display: none;
        }}

        [class*="st-key-next-action-card"] .stButton,
        [class*="st-key-next-action-card"] .stButton > button {{
            width: 100%;
        }}

        [class*="st-key-next-action-card"] [data-testid="stElementContainer"]:has(.stButton) {{
            width: 100%;
        }}

        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {{
            display: grid;
            gap: 0.5rem;
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }}

        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"])
        > [data-testid="stColumn"] {{
            min-width: 0 !important;
            width: auto !important;
        }}

        [data-testid="stMetric"] {{
            padding: 0.75rem 0.5rem;
        }}

        [data-testid="stMetricLabel"] p {{
            font-size: 0.75rem;
        }}

        [data-testid="stMetricValue"] {{
            font-size: 1.75rem;
        }}

        [data-testid="stHorizontalBlock"] {{
            gap: 1rem;
        }}

        [data-testid="stVerticalBlock"][class*="st-key-source-row-"]
        [data-testid="stHorizontalBlock"] {{
            flex-wrap: nowrap;
        }}

        [data-testid="stVerticalBlock"][class*="st-key-source-row-"]
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
            min-width: 0 !important;
        }}

        [data-testid="stVerticalBlock"][class*="st-key-source-row-"]
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {{
            flex: 1 1 auto !important;
        }}

        [data-testid="stVerticalBlock"][class*="st-key-source-row-"]
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {{
            flex: 0 0 3.25rem !important;
        }}
    }}

    @media (prefers-reduced-motion: reduce) {{
        .stButton > button,
        [data-testid^="stBaseButton"],
        .theme-switcher__button {{
            transform: none !important;
            transition:
                border-color 160ms ease,
                background-color 160ms ease;
        }}
    }}
    """
