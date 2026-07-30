EXPRESSIONS = {"listen", "think", "happy", "concerned"}


def q_head_svg(expression: str) -> str:
    if expression not in EXPRESSIONS:
        expression = "think"
    eyes = {
        "listen": '<circle cx="39" cy="51" r="5"/><circle cx="65" cy="51" r="5"/>',
        "think": '<circle cx="39" cy="51" r="5"/><circle cx="65" cy="49" r="3"/>',
        "happy": (
            '<path d="M34 49q5 7 10 0" fill="none"/>'
            '<path d="M60 49q5 7 10 0" fill="none"/>'
        ),
        "concerned": '<circle cx="39" cy="51" r="5"/><circle cx="65" cy="51" r="5"/>',
    }[expression]
    mouth = {
        "listen": "M43 66q9 8 18 0",
        "think": "M44 68q8-3 16 0",
        "happy": "M40 64q12 14 24 0",
        "concerned": "M43 72q9-8 18 0",
    }[expression]
    return (
        '<svg class="q-head" viewBox="0 0 104 96" '
        'aria-hidden="true" focusable="false">'
        '<path d="M52 16V8" stroke="#47819A" stroke-width="4" '
        'stroke-linecap="round"/>'
        '<circle cx="52" cy="7" r="6" fill="#F8C5A9"/>'
        '<path d="M20 32Q20 20 34 20H70Q84 20 84 32V63'
        'Q84 80 68 80H36Q20 80 20 63Z" fill="#FBFCFE" '
        'stroke="#8ACDD6" stroke-width="6"/>'
        '<circle cx="17" cy="51" r="5" fill="#F8C5A9"/>'
        '<circle cx="87" cy="51" r="5" fill="#F8C5A9"/>'
        f'<g fill="#47819A" stroke="#47819A" stroke-width="3" '
        f'stroke-linecap="round">{eyes}'
        f'<path d="{mouth}" fill="none"/></g>'
        '<circle cx="32" cy="63" r="4" fill="#F8C5A9" opacity=".65"/>'
        '<circle cx="72" cy="63" r="4" fill="#F8C5A9" opacity=".65"/>'
        "</svg>"
    )
