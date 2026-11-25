from statistics import median

from app.schemas.measurements import Recommendation, UserMeasurements
from app.schemas.size_chart import SizeChart
from app.services.fit_rules import (
    BODY_TOLERANCE_CM,
    FLAT_WIDTH_RATIO,
    MISSING_PENALTY,
    TIE_MARGIN,
    measurements_for,
    target_range,
)
from app.services.units import guess_unit, to_cm

LEVELS = ["low", "medium", "high"]


def _cap(level: str, cap: str) -> str:
    """Return the lower of two confidence levels."""
    return LEVELS[min(LEVELS.index(level), LEVELS.index(cap))]


def _normalize(chart: SizeChart):
    """Return ({label: {measurement: cm}}, notes, unit_was_guessed)."""
    notes: list[str] = []
    unit = chart.unit
    guessed = False
    if unit == "unknown":
        sample = [
            value
            for row in chart.sizes
            for name, value in row.measurements.items()
            if name in ("chest", "waist", "hip")
        ]
        unit = guess_unit(sample)
        guessed = True
        notes.append(f"The chart did not state a unit, so I guessed {unit}.")
    rows = {
        row.label: {name: to_cm(value, unit) for name, value in row.measurements.items()}
        for row in chart.sizes
    }
    return rows, notes, guessed


def size_order(chart: SizeChart) -> list[str]:
    """Size labels from smallest to largest, judged by their measurements."""
    rows, _, _ = _normalize(chart)
    return sorted(rows, key=lambda label: sum(rows[label].values()))


def _recommend(chart: SizeChart, user: UserMeasurements, basis: str) -> Recommendation:
    rows, notes, unit_guessed = _normalize(chart)
    order = sorted(rows, key=lambda label: sum(rows[label].values()))

    penalty = {label: 0.0 for label in rows}
    outside = {label: 0.0 for label in rows}
    detail: dict[str, dict[str, tuple[float, float]]] = {label: {} for label in rows}
    compared: list[str] = []

    for name in measurements_for(chart.garment_type):
        body_value = user.get(name)
        column = [row[name] for row in rows.values() if name in row]
        if body_value is None or not column:
            continue
        compared.append(name)
        low, ideal, high = target_range(basis, chart.garment_type, name, chart.fit_type)
        doubled = basis == "garment" and median(column) < FLAT_WIDTH_RATIO * body_value
        if doubled:
            notes.append(f"{name.title()} values look like flat (half) widths, so I doubled them.")
        for label, row in rows.items():
            if name not in row:
                penalty[label] += MISSING_PENALTY
                outside[label] += MISSING_PENALTY
                continue
            value = row[name] * 2 if doubled else row[name]
            diff = value - body_value
            miss = max(low - diff, 0.0, diff - high)
            penalty[label] += miss + 0.1 * abs(diff - ideal)
            outside[label] += miss
            detail[label][name] = (value, diff)

    if not compared:
        return Recommendation(
            size=None,
            confidence="low",
            reasons=notes
            + ["The chart and your saved measurements share no measurement I can compare."],
        )

    lowest = min(penalty.values())
    near_best = [label for label in order if penalty[label] <= lowest + TIE_MARGIN]
    best = near_best[-1]  # on a tie, the larger size wins
    others = sorted((label for label in rows if label != best), key=lambda label: penalty[label])
    runner = others[0] if others else None
    runner_fits = runner is not None and outside[runner] == 0

    if outside[best] > 2:
        level = "low"
    elif outside[best] == 0 and not runner_fits and len(compared) >= 2:
        level = "high"
    else:
        level = "medium"
    if unit_guessed:
        level = _cap(level, "low")

    reasons = list(notes)
    if outside[best] > 2:
        reasons.insert(0, f"No size fits well. {best} is the closest.")
    for name in compared:
        if name not in detail[best]:
            continue
        value, diff = detail[best][name]
        low, _, high = target_range(basis, chart.garment_type, name, chart.fit_type)
        mine = user.get(name)
        if basis == "body":
            text = (
                f"{name.title()}: the chart lists {value:.0f} cm for {best} and you measure "
                f"{mine:.0f} cm ({diff:+.0f} cm; within ±{BODY_TOLERANCE_CM} cm counts as a match)."
            )
        else:
            text = (
                f"{name.title()}: the garment is {value:.0f} cm and you measure {mine:.0f} cm, "
                f"so {diff:.0f} cm of room (usual for this fit: {low:.0f} to {high:.0f} cm)."
            )
        if diff < low:
            text += " Tighter than usual."
        elif diff > high:
            text += " Looser than usual."
        reasons.append(text)
    if runner_fits and outside[best] == 0:
        reasons.append(f"{runner} also fits, so you are between sizes.")

    return Recommendation(
        size=best,
        confidence=level,
        runner_up=runner,
        reasons=reasons,
        penalties={label: round(value, 2) for label, value in penalty.items()},
    )


def recommend(chart: SizeChart, user: UserMeasurements) -> Recommendation:
    if chart.measurement_basis != "unknown":
        return _recommend(chart, user, chart.measurement_basis)

    # The chart does not say what it lists, so try both readings.
    as_body = _recommend(chart, user, "body")
    as_garment = _recommend(chart, user, "garment")
    note = "The chart does not say whether it lists body or garment measurements."
    if as_body.size is not None and as_body.size == as_garment.size:
        return as_body.model_copy(
            update={
                "confidence": _cap(as_body.confidence, "medium"),
                "reasons": [note, "Both readings give the same size."] + as_body.reasons,
            }
        )
    candidates = [r for r in (as_body, as_garment) if r.size is not None]
    if not candidates:
        return as_body
    order = size_order(chart)
    picked = max(candidates, key=lambda r: order.index(r.size))
    return picked.model_copy(
        update={
            "confidence": "low",
            "reasons": [
                note,
                f"Read as body measurements the answer is {as_body.size}; read as garment "
                f"measurements it is {as_garment.size}. I picked the larger one.",
            ]
            + picked.reasons,
        }
    )
