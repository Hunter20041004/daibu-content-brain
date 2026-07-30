import pytest

from daibu.cards import diagrams
from daibu.cards.schema import DiagramNode, DiagramSpec


@pytest.mark.parametrize(
    "kind",
    (
        "problem-chain",
        "ai-analyze",
        "ai-generate",
        "ai-predict",
        "ai-automate",
        "ai-infrastructure",
        "before-after",
        "signals",
    ),
)
def test_every_diagram_uses_the_fixed_brand_component_set(kind):
    spec = DiagramSpec(
        kind,
        (
            DiagramNode("第一步", "先理解情境", "listen"),
            DiagramNode("第二步", "整理關係", "think"),
            DiagramNode("第三步", "交給人判斷", "happy"),
        ),
    )

    result = diagrams.diagram_html(spec)

    assert f'data-diagram-kind="{kind}"' in result
    assert "<svg" in result
    assert "http://" not in result and "https://" not in result


def test_ai_role_diagram_is_a1_with_unframed_m1_heads_and_no_dotted_line():
    spec = DiagramSpec(
        "ai-generate",
        (
            DiagramNode("聲音範例", "辨認說話方式", "listen"),
            DiagramNode("AI 理解", "安排新文字語氣", "think"),
            DiagramNode("人員確認", "審核並微調", "happy"),
        ),
    )

    result = diagrams.diagram_html(spec)

    assert result.count('class="q-head"') == 3
    assert 'class="step-row"><svg class="q-head"' in result
    assert 'class="step-card"' in result
    assert "mascot-frame" not in result
    assert "stroke-dasharray" not in result
    assert "connector-line" not in result
