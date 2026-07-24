from daibu import theme


def test_contrast_ratio_black_on_white_is_21():
    assert round(theme.contrast_ratio("#000000", "#FFFFFF"), 1) == 21.0
