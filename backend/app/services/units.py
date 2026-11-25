from statistics import median

INCH_TO_CM = 2.54


def to_cm(value: float, unit: str) -> float:
    """Convert a chart value to centimetres. Only "in" needs converting."""
    return value * INCH_TO_CM if unit == "in" else value


def guess_unit(values: list[float]) -> str:
    """Guess the unit when a chart does not state one.

    Adult chest, waist and hip values are roughly 60-150 in cm and 24-60 in
    inches, so a median of 60 or less is treated as inches. Flat garment widths
    in cm (about 45-65) overlap that range, which is why a guessed unit always
    lowers the confidence.
    """
    if not values:
        return "cm"
    return "in" if median(values) <= 60 else "cm"
