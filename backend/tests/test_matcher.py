from app.schemas.measurements import UserMeasurements
from app.schemas.size_chart import SizeChart
from app.services.matcher import recommend, size_order


def make_chart(rows, garment_type="shirt", unit="cm", basis="body", fit="unknown"):
    return SizeChart(
        garment_type=garment_type,
        unit=unit,
        measurement_basis=basis,
        fit_type=fit,
        sizes=[{"label": label, "measurements": values} for label, values in rows.items()],
    )


BODY_ROWS = {
    "S": {"chest": 92, "waist": 78},
    "M": {"chest": 98, "waist": 84},
    "L": {"chest": 104, "waist": 90},
}
GARMENT_ROWS = {
    "S": {"chest": 100, "waist": 96},
    "M": {"chest": 106, "waist": 102},
    "L": {"chest": 112, "waist": 108},
}


def test_body_chart_exact_match_is_high_confidence():
    result = recommend(make_chart(BODY_ROWS), UserMeasurements(chest=98, waist=84))
    assert result.size == "M"
    assert result.confidence == "high"


def test_between_sizes_picks_larger_with_medium_confidence():
    result = recommend(make_chart(BODY_ROWS), UserMeasurements(chest=101, waist=87))
    assert result.size == "L"
    assert result.confidence == "medium"
    assert any("between sizes" in line for line in result.reasons)


def test_garment_chart_uses_ease():
    chart = make_chart(GARMENT_ROWS, basis="garment")
    result = recommend(chart, UserMeasurements(chest=96, waist=84))
    assert result.size == "M"
    assert result.confidence == "high"


def test_flat_widths_are_doubled():
    rows = {"S": {"chest": 50}, "M": {"chest": 53}, "L": {"chest": 56}}
    chart = make_chart(rows, garment_type="tshirt", basis="garment")
    result = recommend(chart, UserMeasurements(chest=96))
    assert result.size == "M"
    assert any("flat" in line for line in result.reasons)


def test_inch_chart_is_converted():
    rows = {"S": {"chest": 36}, "M": {"chest": 38}, "L": {"chest": 40}}
    chart = make_chart(rows, unit="in", garment_type="tshirt")
    result = recommend(chart, UserMeasurements(chest=96))
    assert result.size == "M"


def test_guessed_unit_forces_low_confidence():
    rows = {"S": {"chest": 36}, "M": {"chest": 38}, "L": {"chest": 40}}
    chart = make_chart(rows, unit="unknown", garment_type="tshirt")
    result = recommend(chart, UserMeasurements(chest=96))
    assert result.size == "M"
    assert result.confidence == "low"


def test_no_shared_measurement_returns_no_size():
    rows = {"S": {"length": 68}, "M": {"length": 70}}
    result = recommend(make_chart(rows), UserMeasurements(chest=96))
    assert result.size is None
    assert result.confidence == "low"


def test_oversized_fit_shifts_toward_larger_size():
    rows = {"S": {"chest": 100}, "M": {"chest": 106}, "L": {"chest": 112}}
    regular = make_chart(rows, garment_type="tshirt", basis="garment", fit="regular")
    oversized = make_chart(rows, garment_type="tshirt", basis="garment", fit="oversized")
    user = UserMeasurements(chest=96)
    assert recommend(regular, user).size == "M"
    assert recommend(oversized, user).size == "L"


def test_user_larger_than_chart_is_low_confidence():
    result = recommend(make_chart(BODY_ROWS), UserMeasurements(chest=130, waist=115))
    assert result.size == "L"
    assert result.confidence == "low"
    assert "No size fits well" in result.reasons[0]


def test_unknown_basis_same_answer_is_capped_at_medium():
    chart = make_chart({"M": {"chest": 100, "waist": 86}}, basis="unknown")
    result = recommend(chart, UserMeasurements(chest=96, waist=84))
    assert result.size == "M"
    assert result.confidence in ("low", "medium")
    assert any("Both readings give the same size" in line for line in result.reasons)


def test_unknown_basis_disagreement_picks_larger_and_low_confidence():
    chart = make_chart(BODY_ROWS, basis="unknown")
    result = recommend(chart, UserMeasurements(chest=98, waist=84))
    # Read as body measurements the answer is M; read as garment measurements it is L.
    assert result.size == "L"
    assert result.confidence == "low"
    assert any("picked the larger" in line for line in result.reasons)


def test_size_order_runs_small_to_large():
    assert size_order(make_chart(BODY_ROWS)) == ["S", "M", "L"]
