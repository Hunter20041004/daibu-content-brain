import html as html_lib

from daibu.cards import pages, render


def _row(page_type="cover", heading="讓文字開口說話", body="ElevenLabs"):
    return {
        "page_no": pages.PAGE_TYPES.index(page_type) + 1,
        "page_type": page_type,
        "heading": heading,
        "body": body,
        "grounding": "model",
        "source_quote": "",
    }


def test_html_contains_the_text():
    out = render.page_html(_row(), company="ElevenLabs")

    assert "讓文字開口說話" in out
    assert "ElevenLabs" in out


def test_html_escapes_user_text():
    out = render.page_html(_row(heading="<script>x</script>"), company="A")

    assert "<script>x</script>" not in out
    assert html_lib.escape("<script>x</script>") in out


def test_html_escapes_company_and_body_text():
    company = 'A<script>company</script>"'
    body = 'B<script>body</script>"'

    cover = render.page_html(_row(), company=company)
    inside = render.page_html(_row("problem", body=body), company="A")

    assert company not in cover
    assert html_lib.escape(company) in cover
    assert body not in inside
    assert html_lib.escape(body) in inside


def test_html_declares_the_exact_canvas_size():
    out = render.page_html(_row(), company="ElevenLabs")

    assert ".canvas {" in out
    assert "width: 1080px" in out
    assert "height: 1350px" in out


def test_html_embeds_the_matching_mascot_pose():
    out = render.page_html(_row("problem"), company="ElevenLabs")
    think_svg = (render.ASSETS / "mascot" / "think.svg").read_text(
        encoding="utf-8"
    )

    assert think_svg.split(">", 1)[1][:60] in out


def test_non_cover_page_contains_its_body():
    out = render.page_html(
        _row("problem", body="聲音模型訓練成本很高"),
        company="ElevenLabs",
    )

    assert "聲音模型訓練成本很高" in out


def test_html_contains_the_page_type_label():
    out = render.page_html(_row("how-ai"), company="ElevenLabs")

    assert "他們怎麼運用 AI" in out


def test_font_is_loaded_from_local_files():
    out = render.page_html(_row(), company="ElevenLabs")
    style = out.split("</style>", 1)[0]

    assert "LINESeedTW_OTF_Rg.otf" in style
    assert "LINESeedTW_OTF_Bd.otf" in style
    assert "LINESeedTW_OTF_Eb.otf" in style
    assert "http" not in style.replace("file://", "")


def test_colors_match_the_brand_palette():
    out = render.page_html(_row(), company="ElevenLabs")

    assert "#D5E6F4" in out
    assert "#FBFCFE" in out
    assert "#47819A" in out
    for retired in ("#2E5C9E", "#F6BCC8", "#E8912D", "#5B8FC9"):
        assert retired not in out, f"{retired} 是改版前的舊色，不該出現"


def test_card_uses_the_approved_geometry():
    out = render.page_html(_row(), company="ElevenLabs")

    assert "inset: 70px" in out
    assert "border-radius: 40px" in out
    assert "0 6px 36px rgba(38,38,65,.06)" in out


def test_type_hierarchy_uses_approved_sizes_and_weights():
    out = render.page_html(_row(), company="ElevenLabs")

    for declaration in (
        "font-size: 32px",
        "font-size: 44px",
        "font-size: 72px",
        "font-size: 104px",
        "font-weight: 400",
        "font-weight: 700",
        "font-weight: 800",
    ):
        assert declaration in out


def test_html_includes_the_approved_frame_decorations():
    out = render.page_html(_row(), company="ElevenLabs")

    assert 'class="stripes"' in out
    assert 'class="dots"' in out
    assert 'class="handle"' in out
    assert "@呆一布" in out


def test_handle_sits_in_the_frame_below_the_card():
    out = render.page_html(_row(), company="ElevenLabs")

    assert "bottom: 16px" in out


def test_html_has_no_theme_dependent_colors():
    """貼文圖的顏色必須寫死。"""
    out = render.page_html(_row(), company="ElevenLabs")

    assert "var(--" not in out
    assert "light-dark(" not in out
    assert "prefers-color-scheme" not in out


def test_only_permitted_font_weights_are_used():
    """網站 PRD 明文禁止 500 / 600 與斜體。"""
    out = render.page_html(_row(), company="ElevenLabs")

    assert "font-weight: 500" not in out
    assert "font-weight: 600" not in out
    assert "font-style: italic" not in out


def test_embedded_mascot_scales_to_the_approved_container():
    out = render.page_html(_row(), company="ElevenLabs")

    assert ".mascot svg" in out
    assert "width: 100%" in out
