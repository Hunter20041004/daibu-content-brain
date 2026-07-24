PALETTE_KEYS = (
    "BRAND_PRIMARY",
    "BRAND_SECONDARY",
    "INK",
    "SURFACE",
    "CANVAS",
    "HIGHLIGHT",
    "BORDER",
)

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
