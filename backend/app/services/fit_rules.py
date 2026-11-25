# Starter values. They are approximate: tune them with your own clothes (Part 9).

# For garment charts: (min, ideal, max) extra room in cm between the garment and
# your body, for a regular fit. The keys also decide which measurements matter
# for each garment type.
EASE_CM = {
    "shirt": {"chest": (6, 10, 16), "waist": (6, 12, 20)},
    "tshirt": {"chest": (6, 10, 18)},
    "kurta": {"chest": (6, 12, 20), "waist": (8, 14, 24), "hip": (8, 14, 24)},
    "jacket": {"chest": (8, 14, 22)},
    "dress": {"chest": (2, 6, 12), "waist": (2, 8, 16), "hip": (2, 8, 16)},
    "jeans": {"waist": (0, 2, 5), "hip": (4, 8, 14)},
    "trousers": {"waist": (0, 3, 6), "hip": (4, 10, 16)},
    "other": {"chest": (4, 10, 18), "waist": (4, 10, 18), "hip": (4, 10, 18)},
}

# Added to the ease range when the chart states a fit type.
FIT_SHIFT_CM = {"slim": -4, "regular": 0, "relaxed": 4, "oversized": 10, "unknown": 0}

# For body charts: how far your body may be from the chart's number for a size.
BODY_TOLERANCE_CM = 3

# A garment value below this fraction of your body measurement is probably a
# flat (half) width, such as pit-to-pit for a chest.
FLAT_WIDTH_RATIO = 0.65

# Penalty (cm) when a size row lacks a measurement that the others have.
MISSING_PENALTY = 5.0

# Sizes whose penalties differ by less than this count as tied. The larger wins.
TIE_MARGIN = 0.25


def measurements_for(garment_type: str) -> list[str]:
    return list(EASE_CM[garment_type])


def target_range(basis: str, garment_type: str, name: str, fit_type: str):
    """Return (low, ideal, high) for: chart value minus your body value, in cm."""
    if basis == "body":
        return (-BODY_TOLERANCE_CM, 0.0, BODY_TOLERANCE_CM)
    low, ideal, high = EASE_CM[garment_type][name]
    shift = FIT_SHIFT_CM[fit_type]
    return (low + shift, ideal + shift, high + shift)
