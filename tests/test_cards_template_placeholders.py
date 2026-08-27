import base64
import re

from daibu.cards import pages
from daibu.cards import render
from daibu.cards.layout_schema import load_builtin_layout
from daibu.cards.template_placeholders import (
    COMPANY_PLACEHOLDER,
    SERIES_PLACEHOLDER,
    build_template_placeholder_draft,
)


def test_template_placeholder_draft_covers_all_six_semantic_pages():
    draft = build_template_placeholder_draft()
    assert tuple(page.page_type for page in draft.pages) == pages.PAGE_TYPES
    assert draft.pages[0].heading == "封面標題"
    assert all(
        page.heading == "頁面標題"
        for page in draft.pages[1:]
    )
    assert COMPANY_PLACEHOLDER == "公司名稱"
    assert SERIES_PLACEHOLDER == "系列名稱"


def test_template_editor_html_uses_semantic_company_and_logo():
    draft = build_template_placeholder_draft()
    cover = render.template_editor_page_html(
        draft.pages[0],
        COMPANY_PLACEHOLDER,
        None,
        load_builtin_layout(),
        series_name=SERIES_PLACEHOLDER,
        logo_placeholder_text="企業 Logo",
    )
    assert "公司名稱" in cover
    assert "系列名稱" not in cover
    assert "一布懂 AI 新創" not in cover
    match = re.search(
        r'<img src="data:image/svg\+xml;base64,([^"]+)" '
        r'alt="公司名稱 Logo">',
        cover,
    )
    assert match is not None
    assert "企業 Logo" in base64.b64decode(match.group(1)).decode("utf-8")
