import pytest

from daibu.fetch import page

HTML = """
<html><head>
<meta property="og:site_name" content="Example News">
<meta property="article:published_time" content="2026-07-20T08:30:00Z">
</head><body><article>
<h1>公司發表新的語音模型</h1>
<p>官方說明這個模型能保留語氣與節奏，並提供內容製作工具。</p>
<script>console.log("不該出現在引文裡")</script>
</article></body></html>
"""

PR_NEWSWIRE_HTML = """
<html><head>
<meta property="og:site_name" content="PR Newswire">
<meta property="article:published_time" content="2026-07-30T08:30:00Z">
</head><body>
<div>Accessibility Statement Skip to main content Products News Share this</div>
<main><article>
<h1>Railway announces a new platform update</h1>
<p>舊金山，2026 年 7 月 30 日。Railway 今日宣布推出新的雲端部署功能。</p>
<p>這項更新讓開發團隊能在同一個工作區管理服務與部署記錄，並檢視官方公開的運作資料。</p>
<p>公司表示後續還會公布更多可驗證細節。</p>
</article></main>
<div>Share on Facebook Share on X Contact us</div>
</body></html>
"""

DATA_PAGE_HTML = """
<html><body>
<div data-page="{&quot;props&quot;:{&quot;post&quot;:{
  &quot;published_at&quot;:&quot;2026-01-23T07:59:00.000-08:00&quot;
}}}">
<article><p>EquipmentShare built an operating system for construction.</p></article>
</div>
</body></html>
"""


def test_suggestion_prefills_publisher_date_and_excerpt():
    result = page.fetch_suggestion(
        "https://news.example/story",
        download=lambda _url: HTML,
    )

    assert result.publisher == "Example News"
    assert result.published_at == "2026-07-20"
    assert result.url == "https://news.example/story"
    assert "保留語氣與節奏" in result.excerpt
    assert "console.log" not in result.excerpt


def test_suggestion_rejects_non_https_and_reports_download_failure():
    with pytest.raises(ValueError, match="https"):
        page.fetch_suggestion("http://news.example/story")

    def explode(_url):
        raise OSError("boom")

    with pytest.raises(ValueError, match="抓不到這個網址"):
        page.fetch_suggestion(
            "https://news.example/story",
            download=explode,
        )


def test_article_body_beats_accessibility_and_share_chrome():
    result = page.fetch_suggestion(
        "https://www.prnewswire.com/news/example",
        download=lambda _url: PR_NEWSWIRE_HTML,
    )

    assert result.excerpt.startswith("舊金山，2026 年 7 月 30 日。")
    assert "Accessibility" not in result.excerpt
    assert "Share on" not in result.excerpt
    assert result.excerpt.endswith(("。", "！", "？", ".", "!", "?"))


def test_article_excerpt_stops_at_the_last_complete_sentence():
    extracted = page.extract_article(
        "<article><p>第一句有完整證據。"
        "第二句會超過限制並且不該留下半句。</p></article>",
        limit=14,
    )

    assert extracted == "第一句有完整證據。"


def test_suggestion_reads_date_from_embedded_page_data():
    result = page.fetch_suggestion(
        "https://www.ycombinator.com/blog/company",
        download=lambda _url: DATA_PAGE_HTML,
    )

    assert result.published_at == "2026-01-23"


@pytest.mark.contract
def test_real_page_returns_readable_text():
    result = page.fetch_suggestion("https://techcrunch.com/")

    assert result.publisher
    assert len(result.excerpt) > 80
