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


@pytest.mark.contract
def test_real_page_returns_readable_text():
    result = page.fetch_suggestion("https://techcrunch.com/")

    assert result.publisher
    assert len(result.excerpt) > 80
