"""
routers/room_design.py - AI Room Design via Google Gemini Vision
POST /api/room-design  { image: base64string, mimeType: "image/jpeg" }
"""

import os
import re
import json
import base64
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger("ecoplant.room_design")

router = APIRouter(prefix="/api/room-design", tags=["room-design"])
limiter = Limiter(key_func=get_remote_address)

ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024   # 10 MB decoded

ROOM_ANALYSIS_PROMPT = """You are an expert interior designer and botanist. Analyse this room photo carefully.

Return ONLY valid JSON (no markdown, no code blocks) in EXACTLY this format:

{
  "roomType": "Living Room",
  "lightLevel": "bright indirect",
  "style": "modern minimalist",
  "colorPalette": ["warm whites", "natural wood", "grey"],
  "placements": [
    {
      "plant_name": "Monstera Deliciosa",
      "scientific_name": "Monstera deliciosa",
      "location_description": "left corner near the window",
      "reason": "Thrives in bright indirect light, adds tropical drama to the neutral palette",
      "pot_style": "white ceramic pot",
      "care_level": "easy",
      "price_range": "Rs. 599 - Rs. 1,499",
      "bounding_box": { "x": 5, "y": 40, "width": 20, "height": 45 }
    },
    {
      "plant_name": "Snake Plant",
      "scientific_name": "Dracaena trifasciata",
      "location_description": "right side of the sofa",
      "reason": "Tolerates low light, architectural form complements modern furniture",
      "pot_style": "dark matte concrete pot",
      "care_level": "very easy",
      "price_range": "Rs. 349 - Rs. 899",
      "bounding_box": { "x": 70, "y": 45, "width": 15, "height": 40 }
    }
  ],
  "overall_tip": "This room would benefit most from plants with bold leaf shapes to contrast the clean lines."
}

Rules:
- Suggest 2-3 plants maximum
- bounding_box values are PERCENTAGES of the image (0-100) - place plants in empty floor/shelf spaces
- Choose plants that match the room light level and style
- Be specific about location_description (e.g. 'left corner beside the bookshelf')
- Match pot_style to room aesthetics
- care_level must be one of: very easy, easy, moderate, demanding"""

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
    return json.loads(cleaned)


class RoomDesignBody(BaseModel):
    image: str
    mimeType: Optional[str] = "image/jpeg"

    @field_validator("image")
    @classmethod
    def validate_image(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("image (base64) is required")
        if len(v) > 14_000_000:
            raise ValueError("Image too large (max 10 MB)")
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


@router.post("")
@router.post("/")
@limiter.limit("10/minute")
async def room_design(request: Request, body: RoomDesignBody):
    client = get_client()
    if not client:
        raise HTTPException(503, "AI service not configured - add GEMINI_API_KEY to .env")

    try:
        image_bytes = base64.b64decode(body.image, validate=True)
    except Exception:
        raise HTTPException(400, "Invalid base64 image data")

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image too large. Maximum size is 10 MB.")

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
        detected = body.mimeType or "image/jpeg"

    try:
        import google.generativeai as genai
        # Try gemini-2.0-flash, gemini-2.5-flash, or fallback
        model = None
        for m_name in ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"]:
            try:
                model = genai.GenerativeModel(model_name=m_name)
                break
            except Exception:
                continue

        if not model:
            model = genai.GenerativeModel(model_name="gemini-2.0-flash")

        result_gen = model.generate_content([
            {"mime_type": detected, "data": image_bytes},
            ROOM_ANALYSIS_PROMPT,
        ])
        raw = result_gen.text
        analysis = parse_json(raw)

        return {
            "success": True,
            "analysis": analysis,
            "renderedImage": None,
            "imagenAvailable": False
        }

    except Exception as exc:
        logger.error(f"[room-design] AI error: {exc}", exc_info=True)
        raise HTTPException(500, f"AI Room Design failed: {str(exc)}")
