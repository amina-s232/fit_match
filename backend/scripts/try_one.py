import sys

from app.services.extractor import extract_size_chart

chart = extract_size_chart(sys.argv[1])
print(chart.model_dump_json(indent=2))
