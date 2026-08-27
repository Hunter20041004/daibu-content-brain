from daibu.cards.template_stress import build_template_stress_cases


def test_fixed_template_stress_cases_cover_three_company_shapes():
    cases=build_template_stress_cases()
    assert [case.company for case in cases]==["SUN","Billow AI Labs","Shiraz AI"]
    assert all(len(case.draft.pages)==6 for case in cases)
    assert cases[0].asset.local_path.name=="logo-wide.svg"
    assert cases[1].asset.local_path.name=="logo-tall.svg"
