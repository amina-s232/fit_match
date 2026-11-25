import csv
from collections import Counter
from datetime import datetime
from pathlib import Path

from app.schemas.size_chart import GarmentType, SizeChart
from app.services.extractor import BACKEND, MODEL, PROMPT_VERSION, extract_size_chart

CHARTS_DIR = Path("eval/charts")
TRUTH_DIR = Path("eval/ground_truth")
LOG_FILE = Path("eval/score_log.csv")
TOLERANCE = 0.5
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
GARMENT_HINTS: dict[str, GarmentType] = {
    "dress": "dress",
    "jeans": "jeans",
    "kurti": "kurta",
    "shirt": "shirt",
    "tshirt": "tshirt",
}


def garment_hint_from_filename(image: Path) -> GarmentType | None:
    prefix = image.stem.split("_", maxsplit=1)[0].lower()
    return GARMENT_HINTS.get(prefix)


def compare(pred: SizeChart, truth: SizeChart) -> list[str]:
    """Return a list of problem codes. An empty list means a perfect match."""
    problems = []
    for field in ("garment_type", "unit", "measurement_basis"):
        if getattr(pred, field) != getattr(truth, field):
            problems.append(f"wrong_{field}")

    pred_rows = {r.label.strip().upper(): r.measurements for r in pred.sizes}
    truth_rows = {r.label.strip().upper(): r.measurements for r in truth.sizes}
    if set(pred_rows) != set(truth_rows):
        problems.append("size_labels")

    for label, truth_vals in truth_rows.items():
        pred_vals = pred_rows.get(label, {})
        for name, value in truth_vals.items():
            if name not in pred_vals:
                problems.append(f"missing_{name}")
            elif abs(pred_vals[name] - value) > TOLERANCE:
                problems.append(f"wrong_value_{name}")
        for name in pred_vals:
            if name not in truth_vals:
                problems.append(f"extra_{name}")
    return problems


def main() -> None:
    results = []
    for image in sorted(CHARTS_DIR.iterdir()):
        if image.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        truth_file = TRUTH_DIR / f"{image.stem}.json"
        if not truth_file.exists():
            print(f"SKIP  {image.name} (no ground truth)")
            continue
        truth = SizeChart.model_validate_json(truth_file.read_text())
        try:
            problems = compare(
                extract_size_chart(image, garment_hint_from_filename(image)), truth
            )
        except Exception as exc:
            problems = ["extraction_failed"]
            print(f"  error on {image.name}: {exc}")
        results.append((image.name, problems))
        status = "PASS" if not problems else "FAIL"
        print(f"{status}  {image.name}  {sorted(set(problems))}")

    total = len(results)
    if total == 0:
        print("No charts evaluated.")
        return

    passed = sum(1 for _, problems in results if not problems)
    print(f"\n{passed}/{total} charts fully correct ({passed / total:.0%})")
    counts = Counter(p for _, problems in results for p in set(problems))
    for problem, n in counts.most_common():
        print(f"  {problem}: {n} chart(s)")

    new_file = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["time", "backend", "model", "prompt_version", "passed", "total"])
        writer.writerow(
            [datetime.now().isoformat(timespec="seconds"), BACKEND, MODEL, PROMPT_VERSION, passed, total]
        )


if __name__ == "__main__":
    main()
