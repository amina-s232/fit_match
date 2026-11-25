import hashlib
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

from app.schemas.size_chart import GarmentType, SizeChart

load_dotenv()

BACKEND = os.getenv("BACKEND", "gemini").lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY_SECONDS", "5"))
MODEL = GEMINI_MODEL if BACKEND == "gemini" else OLLAMA_MODEL

PROMPT_VERSION = "v3"  # change this whenever you change PROMPT
CACHE_DIR = Path(".cache/extractions")
MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

PROMPT = """You are reading a clothing size chart from an online store.
Return ONLY a JSON object, with no explanation and no markdown fences, in exactly this format:
{
  "garment_type": "shirt",
  "unit": "cm",
  "measurement_basis": "body",
  "fit_type": "unknown",
  "sizes": [{"label": "M", "measurements": {"chest": 100, "waist": 86}}]
}
Rules:
- garment_type is one of: shirt, tshirt, kurta, jeans, trousers, dress, jacket, other.
- unit is "cm", "in" or "unknown". If the chart shows both inches and cm, use the cm values and unit "cm".
- measurement_basis is "body" if the chart lists body measurements, "garment" if it lists the garment's own measurements, "unknown" if it does not say.
- fit_type is slim, regular, relaxed, oversized or unknown. Use unknown unless the chart states it.
- label is the size name exactly as printed (S, M, 32, UK 8).
- Use lowercase English measurement names such as chest, waist, hip, shoulder, sleeve, length, inseam, thigh. For any other, use snake_case.
- Normalize "inseam length" to "inseam".
- Copy numbers exactly. If a value is a range like 96-101, return the midpoint (98.5).
- Include every complete size row and every measurement shown for that row.
- Never invent a value that is not in the chart. Leave a measurement out if the chart does not show it."""

MEASUREMENT_ALIASES = {"inseam_length": "inseam"}


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _call_gemini(image_bytes: bytes, media_type: str, prompt: str) -> str:
    from google import genai
    from google.genai import errors
    from google.genai import types

    if not GEMINI_MODEL:
        raise RuntimeError("Set GEMINI_MODEL in backend/.env")
    client = genai.Client()  # reads GEMINI_API_KEY from the environment
    for attempt in range(2):
        time.sleep(REQUEST_DELAY if attempt == 0 else 2)
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=media_type),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    temperature=0, response_mime_type="application/json"
                ),
            )
            return response.text or ""
        except errors.ServerError as exc:
            if exc.code != 503 or attempt == 1:
                raise
    raise RuntimeError("Gemini request retry loop exited unexpectedly")


def _call_ollama(image_bytes: bytes, media_type: str, prompt: str) -> str:
    import ollama

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt, "images": [image_bytes]}],
        format="json",
        options={"temperature": 0},
    )
    return response["message"]["content"]


def _call_model(
    image_bytes: bytes,
    media_type: str,
    previous_error: str | None = None,
    garment_hint: GarmentType | None = None,
) -> str:
    prompt = PROMPT
    if garment_hint:
        prompt += (
            f"\n\nProduct category metadata: {garment_hint}. "
            "Use this exact value for garment_type."
        )
    if previous_error:
        prompt += f"\n\nYour previous answer was invalid: {previous_error}\nReturn corrected JSON only."
    if BACKEND == "gemini":
        return _call_gemini(image_bytes, media_type, prompt)
    if BACKEND == "ollama":
        return _call_ollama(image_bytes, media_type, prompt)
    raise RuntimeError(f"Unknown BACKEND: {BACKEND}")


def ping() -> str:
    """Text-only connectivity check. No image is sent."""
    question = "Reply with the single word OK"
    if BACKEND == "gemini":
        from google import genai

        client = genai.Client()
        return client.models.generate_content(model=GEMINI_MODEL, contents=question).text or ""
    import ollama

    reply = ollama.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": question}])
    return reply["message"]["content"]


def extract_size_chart(
    image_path, garment_hint: GarmentType | None = None
) -> SizeChart:
    path = Path(image_path)
    media_type = MEDIA_TYPES.get(path.suffix.lower())
    if media_type is None:
        raise ValueError(f"Unsupported image type: {path.suffix}")
    image_bytes = path.read_bytes()

    key_material = image_bytes + (
        f"{BACKEND}|{MODEL}|{PROMPT_VERSION}|{garment_hint or ''}".encode()
    )
    cache_file = CACHE_DIR / f"{hashlib.sha256(key_material).hexdigest()}.json"
    if cache_file.exists():
        return SizeChart.model_validate_json(cache_file.read_text())

    error = None
    raw = ""
    for _ in range(2):  # one retry with the validation error fed back
        raw = _call_model(image_bytes, media_type, error, garment_hint)
        try:
            chart = SizeChart.model_validate_json(_strip_fences(raw))
        except ValidationError as exc:
            error = str(exc)[:500]
            continue
        sizes = []
        for row in chart.sizes:
            measurements = {}
            for name, value in row.measurements.items():
                canonical_name = MEASUREMENT_ALIASES.get(name, name)
                if canonical_name in measurements:
                    raise ValueError(
                        f"Duplicate measurement after normalization: {canonical_name}"
                    )
                measurements[canonical_name] = value
            sizes.append(row.model_copy(update={"measurements": measurements}))
        chart = chart.model_copy(
            update={
                "garment_type": garment_hint or chart.garment_type,
                "sizes": sizes,
            }
        )
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(chart.model_dump_json(indent=2))
        return chart
    raise ValueError(f"Extraction failed after retry.\nLast output:\n{raw[:500]}\nError: {error}")
