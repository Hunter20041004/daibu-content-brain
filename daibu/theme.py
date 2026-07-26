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

    [data-testid="stIconMaterial"] {{
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
        background: transparent;
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

    .empty-state {{
        border-style: dashed;
        text-align: center;
    }}

    .status-chip,
    .attention-chip {{
        align-items: center;
        background: var(--border);
        border-radius: 999px;
        color: var(--ink);
        display: inline-flex;
        font-size: 0.75rem;
        font-weight: 700;
        line-height: 1;
        min-height: 1.75rem;
        padding: 0.35rem 0.65rem;
    }}

    .attention-chip {{
        background: var(--highlight);
        color: var(--primary-button-ink);
    }}

    .score-badge {{
        align-items: center;
        aspect-ratio: 1;
        background: var(--brand-primary);
        border-radius: 999px;
        color: var(--primary-button-ink);
        display: inline-flex;
        flex-direction: column;
        font-variant-numeric: tabular-nums;
        font-weight: 800;
        justify-content: center;
        min-width: 4.75rem;
    }}

    .score-badge--review {{
        background: var(--highlight);
    }}

    .score-badge small {{
        color: var(--primary-button-ink);
        font-size: 0.65rem;
        font-weight: 700;
    }}

    .pipeline-bar {{
        background: var(--border);
        border-radius: 999px;
        display: flex;
        height: 0.75rem;
        overflow: hidden;
        width: 100%;
    }}

    .pipeline-bar__segment {{
        background: var(--brand-primary);
        min-width: 0;
    }}

    .pipeline-bar__segment:nth-child(even) {{
        background: var(--brand-secondary);
    }}

    .pipeline-legend {{
        display: flex;
        flex-wrap: wrap;
        font-size: 0.8rem;
        gap: 0.5rem 1rem;
        margin-top: 0.75rem;
    }}

    .hero-lockup {{
        align-items: center;
        display: flex;
        gap: clamp(1.5rem, 4vw, 4rem);
        padding: 1.5rem 0 2.5rem;
    }}

    .hero-lockup__visual {{
        flex: 0 0 160px;
    }}

    .hero-lockup__content {{
        max-width: 48rem;
    }}

    .hero-lockup__content h1 {{
        margin-bottom: 0.75rem;
    }}

    .today-stat {{
        min-height: 8rem;
    }}

    .today-stat__label {{
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        opacity: 0.72;
    }}

    .today-stat__value {{
        color: var(--ink);
        font-size: 2rem;
        font-variant-numeric: tabular-nums;
        font-weight: 800;
        line-height: 1.2;
        margin-top: 0.5rem;
    }}

    .candidate-card__title {{
        font-size: {TYPE_SCALE[2]};
        font-weight: {TYPE_WEIGHTS[2]};
        line-height: 1.3;
        margin: 0 0 0.5rem;
    }}

    .kanban-card-title {{
        display: -webkit-box;
        font-size: 0.95rem;
        font-weight: 700;
        line-height: 1.35;
        overflow: hidden;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 2;
    }}

    @media (hover: hover) and (pointer: fine) {{
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

    @media (max-width: 700px) {{
        .hero-lockup {{
            align-items: flex-start;
            flex-direction: column;
            gap: 1rem;
            padding-top: 0.5rem;
        }}

        .hero-lockup__visual {{
            flex-basis: auto;
            width: 104px;
        }}

        .pipeline-legend {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }}

        [data-testid="stHorizontalBlock"] {{
            gap: 1rem;
        }}
    }}

    @media (prefers-reduced-motion: reduce) {{
        .stButton > button,
        [data-testid^="stBaseButton"] {{
            transform: none !important;
            transition:
                border-color 160ms ease,
                background-color 160ms ease;
        }}
    }}
    """
