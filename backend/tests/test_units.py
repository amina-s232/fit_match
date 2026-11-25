from app.services.units import guess_unit, to_cm


def test_inches_convert_to_cm():
    assert to_cm(10, "in") == 25.4


def test_cm_and_unknown_are_unchanged():
    assert to_cm(100, "cm") == 100
    assert to_cm(100, "unknown") == 100


def test_guess_unit_inches():
    assert guess_unit([36, 38, 40]) == "in"


def test_guess_unit_cm():
    assert guess_unit([92, 98, 104]) == "cm"


def test_guess_unit_empty_defaults_to_cm():
    assert guess_unit([]) == "cm"
