import html

from daibu.cards.mascot import q_head_svg
from daibu.cards.schema import DiagramNode, DiagramSpec


def _node(node: DiagramNode, class_name: str) -> str:
    return (
        f'<div class="{class_name}">'
        f"{q_head_svg(node.expression)}"
        '<div class="diagram-copy">'
        f"<strong>{html.escape(node.title)}</strong>"
        f"<span>{html.escape(node.text)}</span>"
        "</div></div>"
    )


def _step(node: DiagramNode) -> str:
    return (
        '<div class="step-row">'
        f"{q_head_svg(node.expression)}"
        '<div class="step-card"><div class="diagram-copy">'
        f"<strong>{html.escape(node.title)}</strong>"
        f"<span>{html.escape(node.text)}</span>"
        "</div></div></div>"
    )


def _arrow_svg() -> str:
    return (
        '<svg class="diagram-arrow" viewBox="0 0 48 24" aria-hidden="true">'
        '<path d="M4 12h34m-8-8 8 8-8 8" fill="none" '
        'stroke="#F8C5A9" stroke-width="5" stroke-linecap="round" '
        'stroke-linejoin="round"/></svg>'
    )


def diagram_html(spec: DiagramSpec) -> str:
    kind = html.escape(spec.kind)
    if spec.kind.startswith("ai-"):
        items = "".join(_step(node) for node in spec.nodes)
        return (
            f'<div class="diagram diagram--steps" data-diagram-kind="{kind}">'
            f"{items}</div>"
        )
    if spec.kind == "before-after":
        items = _arrow_svg().join(
            _node(node, "state-card") for node in spec.nodes
        )
        return (
            f'<div class="diagram diagram--before-after" '
            f'data-diagram-kind="{kind}">{items}</div>'
        )
    class_name = (
        "diagram--signals" if spec.kind == "signals" else "diagram--chain"
    )
    items = "".join(_node(node, "metric-card") for node in spec.nodes)
    return (
        f'<div class="diagram {class_name}" data-diagram-kind="{kind}">'
        f"{items}</div>"
    )
