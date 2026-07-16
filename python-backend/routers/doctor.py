"""
routers/doctor.py — AI Plant Doctor via Google Gemini Vision
POST /api/doctor  { image: base64string, mimeType: "image/jpeg" }
"""

import os
import json
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/doctor", tags=["doctor"])

DOCTOR_PROMPT = """You are an expert botanist and plant health specialist with 20+ years of experience identifying plant diseases and providing treatment advice.

Analyse the provided plant image and return ONLY valid JSON (no markdown, no code blocks, no extra text) in this EXACT format:

{
  "plantName": "Common plant name",
  "scientificName": "Genus species",
  "confidence": 87,
  "healthStatus": "Healthy",
  "healthScore": 87,
  "healthDotClass": "ok",
  "diagnosis": "Brief 1-2 sentence diagnosis of the plant's current condition.",
  "issues": ["Issue 1 if any", "Issue 2 if any"],
  "treatments": [
    "Specific actionable treatment step 1",
    "Specific actionable treatment step 2",
    "Specific actionable treatment step 3"
  ]
}

Rules:
- healthDotClass MUST be exactly "ok" (healthy), "warn" (minor issues), or "bad" (serious problems)
- healthScore: integer 0-100
- confidence: integer 0-100
- If the plant is healthy, issues array should be empty []
- treatments should always have 2-4 practical, actionable steps
- If the image doesn't show a plant, set plantName to "No plant detected" and healthStatus to "Unknown" """

_gen_ai = None


def get_client():
    global _gen_ai
    if _gen_ai is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            _gen_ai = genai
    return _gen_ai


def parse_json(raw: str) -> dict:
    cleaned = re.sub(r'^```(?:json)?\n?', '', raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r'\n?```$', '', cleaned).strip()
    return json.loads(cleaned)


class DoctorBody(BaseModel):
    image: str
    mimeType: Optional[str] = "image/jpeg"


@router.post("/")
async def doctor(body: DoctorBody):
    if not body.image:
        raise HTTPException(400, "image (base64) is required")

    allowed_mimes = ["image/jpeg", "image/png", "image/webp"]
    mime = body.mimeType if body.mimeType in allowed_mimes else "image/jpeg"

    if len(body.image) > 14_000_000:
        raise HTTPException(413, "Image too large. Maximum size is 10 MB.")

    client = get_client()
    if not client:
        raise HTTPException(503, "AI service not configured — add GEMINI_API_KEY to .env")

    try:
        import google.generativeai as genai
        import base64
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        # Decode base64 to bytes for inline image
        image_bytes = base64.b64decode(body.image)
        result_gen = model.generate_content([
            {"mime_type": mime, "data": image_bytes},
            DOCTOR_PROMPT,
        ])
        raw = result_gen.text

        try:
            result = parse_json(raw)
        except Exception:
            raise HTTPException(500, f"Failed to parse AI response: {raw}")

        return {"result": result}

    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "429" in msg or "quota" in msg.lower():
            raise HTTPException(429, "Gemini quota reached. Please try again shortly.")
        raise HTTPException(500, msg)
