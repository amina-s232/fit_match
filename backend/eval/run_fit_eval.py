import csv
import json
from datetime import datetime
from pathlib import Path

from app.schemas.measurements import UserMeasurements
from app.schemas.size_chart import SizeChart
from app.services.matcher import recommend, size_order

CASES_FILE = Path("eval/fit_cases.json")
LOG_FILE = Path("eval/fit_score_log.csv")


def main() -> None:
    cases = json.loads(CASES_FILE.read_text())
    exact = within_one = high_total = high_exact = 0

    for case in cases:
        chart = SizeChart.model_validate_json(Path(case["chart_file"]).read_text())
        result = recommend(chart, UserMeasurements(**case["user"]))
        known = case["known_good_size"].strip().upper()
        order = [label.strip().upper() for label in size_order(chart)]
        got = result.size.strip().upper() if result.size else None

        if got == known:
            status = "EXACT"
            exact += 1
            within_one += 1
        elif got in order and known in order and abs(order.index(got) - order.index(known)) == 1:
            status = "OFF BY ONE"
            within_one += 1
        else:
            status = "MISS"

        if result.confidence == "high":
            high_total += 1
            high_exact += status == "EXACT"
        print(
            f"{status:10} {case['chart_file']}: recommended {result.size} "
            f"({result.confidence}), known good {known}"
        )

    total = len(cases)
    print(f"\nExact: {exact}/{total}   Within one size: {within_one}/{total}")
    if high_total:
        print(f"High-confidence answers that were exact: {high_exact}/{high_total}")

    new_file = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["time", "cases", "exact", "within_one", "high_total", "high_exact"])
        writer.writerow(
            [datetime.now().isoformat(timespec="seconds"), total, exact, within_one, high_total, high_exact]
        )


if __name__ == "__main__":
    main()
