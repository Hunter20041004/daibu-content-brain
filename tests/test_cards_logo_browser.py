from daibu.cards import logo_browser


def test_render_site_returns_javascript_inserted_logo(tmp_path):
    page_path = tmp_path / "dynamic-logo.html"
    page_path.write_text(
        """
        <html><body><nav id="brand-home"></nav>
        <script>
          const image = document.createElement('img');
          image.alt = 'Acme logo';
          image.src = 'data:image/svg+xml,' + encodeURIComponent(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"></svg>'
          );
          document.querySelector('#brand-home').appendChild(image);
        </script></body></html>
        """,
        encoding="utf-8",
    )

    rendered = logo_browser.render_site(page_path.as_uri())

    assert 'alt="Acme logo"' in rendered.html
    assert "data:image/svg+xml" in rendered.html
