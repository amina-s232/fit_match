import argparse
from pathlib import Path

from app.schemas.measurements import UserMeasurements
from app.schemas.size_chart import SizeChart
from app.services.matcher import recommend

parser = argparse.ArgumentParser(description="Try the size matcher on a saved chart")
parser.add_argument("chart_json", help="path to a ground truth or extracted JSON file")
parser.add_argument("--chest", type=float, help="your chest in cm")
parser.add_argument("--waist", type=float, help="your waist in cm")
parser.add_argument("--hip", type=float, help="your hip in cm")
args = parser.parse_args()

chart = SizeChart.model_validate_json(Path(args.chart_json).read_text())
user = UserMeasurements(chest=args.chest, waist=args.waist, hip=args.hip)
result = recommend(chart, user)

print(f"Size: {result.size}   Confidence: {result.confidence}   Runner-up: {result.runner_up}")
for line in result.reasons:
    print(" -", line)
