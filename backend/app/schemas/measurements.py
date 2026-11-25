from typing import Literal

from pydantic import BaseModel


class UserMeasurements(BaseModel):
    """Body measurements in centimetres. Leave a field empty if you do not know it."""

    chest: float | None = None
    waist: float | None = None
    hip: float | None = None

    def get(self, name: str) -> float | None:
        if name not in type(self).model_fields:
            return None
        return getattr(self, name)


class Recommendation(BaseModel):
    size: str | None
    confidence: Literal["high", "medium", "low"]
    runner_up: str | None = None
    reasons: list[str]
    penalties: dict[str, float] = {}
