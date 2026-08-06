from pathlib import Path


HTML_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "2026-08-05-我怎麼用-vibe-coding-搭出呆一布內容工作站.html"
)


def test_story_opens_with_problem_and_product_outcome():
    source = HTML_PATH.read_text(encoding="utf-8")

    assert '<html lang="zh-TW">' in source
    assert "我怎麼用 Vibe Coding 搭出呆一布內容工作站" in source
    assert 'id="problem"' in source
    assert "找題材" in source
    assert "七張輪播圖" in source
    assert "<svg" in source
