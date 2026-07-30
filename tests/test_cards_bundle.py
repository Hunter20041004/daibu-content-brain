import zipfile
from datetime import date
from io import BytesIO

import pytest

from daibu.cards import bundle


def test_zip_contains_seven_numbered_pages_in_order():
    pngs = [f"png-{index}".encode() for index in range(7)]

    archive = bundle.carousel_zip(pngs)

    with zipfile.ZipFile(BytesIO(archive)) as bundled:
        assert bundled.namelist() == [
            "01-cover.png",
            "02-who.png",
            "03-problem.png",
            "04-how-ai.png",
            "05-results.png",
            "06-why-care.png",
            "07-cta.png",
        ]
        assert bundled.read("04-how-ai.png") == b"png-3"


def test_zip_rejects_a_wrong_number_of_pages():
    with pytest.raises(ValueError, match="七張"):
        bundle.carousel_zip([b"only-one"])


def test_zip_name_is_traceable():
    assert bundle.zip_name("ElevenLabs", date(2026, 7, 30)) == (
        "elevenlabs-carousel-20260730.zip"
    )
    assert bundle.zip_name("Hugging Face!", date(2026, 7, 30)) == (
        "hugging-face-carousel-20260730.zip"
    )
