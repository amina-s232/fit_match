from typing import Literal

from pydantic import BaseModel

GarmentType = Literal[
    "shirt", "tshirt", "kurta", "jeans", "trousers", "dress", "jacket", "other"
]


class SizeRow(BaseModel):
    label: str
    measurements: dict[str, float]


class SizeChart(BaseModel):
    garment_type: GarmentType
    unit: Literal["cm", "in", "unknown"]
    measurement_basis: Literal["body", "garment", "unknown"]
    fit_type: Literal["slim", "regular", "relaxed", "oversized", "unknown"] = "unknown"
    sizes: list[SizeRow]
