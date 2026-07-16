"""
routers/doctor.py — AI Plant Doctor via Google Gemini Vision — Security Hardened
POST /api/doctor  { image: base64string, mimeType: "image/jpeg" }
"""

import os
import re
import json
import base64
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/api/doctor", tags=["doctor"])
limiter = Limiter(key_func=get_remote_address)

ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024   # 10 MB decoded

DOCTOR_PROMPT = """You are an expert botanist and plant health specialist with 20+ years of experience.

Analyse the provided plant image and return ONLY valid JSON (no markdown, no code blocks, no extra text) in this EXACT format:

{
  "plantName": "Common plant name",
  "scientificName": "Genus species",
  "confidence": 87,
  "healthStatus": "Healthy",
  "healthScore": 87,
  "healthDotClass": "ok",
  "diagnosis": "Brief 1-2 sentence diagnosis.",
  "issues": ["Issue 1 if any"],
  "treatments": [
    "Actionable step 1",
    "Actionable step 2"
  ]
}

Rules:
- healthDotClass MUST be "ok" (healthy), "warn" (minor issues), or "bad" (serious problems)
- healthScore and confidence: integers 0-100
- If healthy, issues = []
- treatments: 2-4 steps
- If not a plant image, plantName = "No plant detected", healthStatus = "Unknown"
- Never include personal data, URLs, or code in your response"""

_gen_ai = None


def get_client():
    global _gen_ai
    if _gen_ai is None:
        key = os.getenv("GEMINI_API_KEY", "")
        if key:
            import google.generativeai as genai
            genai.configure(api_key=key)
            _gen_ai = genai
    return _gen_ai


def parse_json(raw: str) -> dict:
    cleaned = re.sub(r'^```(?:json)?\n?', '', raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r'\n?```$', '', cleaned).strip()
    data = json.loads(cleaned)
    # Whitelist allowed keys only — strip anything unexpected
    allowed = {"plantName", "scientificName", "confidence", "healthStatus",
               "healthScore", "healthDotClass", "diagnosis", "issues", "treatments"}
    return {k: v for k, v in data.items() if k in allowed}


class DoctorBody(BaseModel):
    image: str
    mimeType: Optional[str] = "image/jpeg"

    @field_validator("image")
    @classmethod
    def validate_image(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("image (base64) is required")
        # Must be valid base64
        if len(v) > 14_000_000:
            raise ValueError("Image too large (max 10 MB)")
        # Strip data URI prefix if present
        if v.startswith("data:"):
            try:
                v = v.split(",", 1)[1]
            except IndexError:
                raise ValueError("Invalid data URI format")
        return v

    @field_validator("mimeType")
    @classmethod
    def validate_mime(cls, v):
        if v not in ALLOWED_MIMES:
            return "image/jpeg"
        return v


@router.post("/")
@limiter.limit("10/minute")
async def doctor(request: Request, body: DoctorBody):
    client = get_client()
    if not client:
        raise HTTPException(503, "AI service not configured — add GEMINI_API_KEY to .env")

    # Decode and validate actual image bytes
    try:
        image_bytes = base64.b64decode(body.image, validate=True)
    except Exception:
        raise HTTPException(400, "Invalid base64 image data")

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image too large. Maximum size is 10 MB.")

    # Validate MIME magic bytes
    magic_map = {
        b'\xff\xd8\xff': 'image/jpeg',
        b'\x89PNG': 'image/png',
        b'RIFF': 'image/webp',
    }
    detected = None
    for magic, mime in magic_map.items():
        if image_bytes[:len(magic)] == magic:
            detected = mime
            break
    if detected is None:
        raise HTTPException(400, "Invalid image format. Upload a JPG, PNG, or WEBP file.")

    try:
        import google.generativeai as genai
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        result_gen = model.generate_content([
            {"mime_type": detected, "data": image_bytes},
            DOCTOR_PROMPT,
        ])
        raw = result_gen.text

        try:
            result = parse_json(raw)
        except Exception:
            raise HTTPException(500, "Failed to parse AI response. Please try again.")

        # Sanitize string fields
        for key in ("plantName", "scientificName", "healthStatus", "healthDotClass", "diagnosis"):
            if key in result and isinstance(result[key], str):
                result[key] = result[key][:500]

        # Clamp numeric fields
        for key in ("confidence", "healthScore"):
            if key in result:
                result[key] = max(0, min(100, int(result[key])))

        # Clamp healthDotClass
        if result.get("healthDotClass") not in ("ok", "warn", "bad"):
            result["healthDotClass"] = "warn"

        return {"result": result}

    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "429" in msg or "quota" in msg.lower():
            raise HTTPException(429, "AI quota reached. Please try again shortly.")
        raise HTTPException(500, "Analysis failed. Please try again.")
