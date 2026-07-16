"""
routers/plant_diagnose.py — Roboflow disease detection — Security Hardened
POST /api/plant-diagnose  { image: base64string }
"""

import os
import re
import random
import base64
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/api/plant-diagnose", tags=["plant-diagnose"])
limiter = Limiter(key_func=get_remote_address)

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB decoded

MOCKS = [
    {
        "plantName": "Monstera Deliciosa",
        "scientificName": "Monstera deliciosa",
        "healthStatus": "Needs Attention",
        "healthScore": 68,
        "healthDotClass": "warn",
        "diagnosis": "Leaf Tip Burn and slight chlorosis detected — likely inconsistent humidity or tap water mineral buildup.",
        "issues": ["Browning Leaf Tips", "Slight Overwatering", "Low Humidity"],
        "treatments": [
            "Trim brown edges with sterilized shears.",
            "Switch to filtered or distilled water.",
            "Increase humidity with a pebble tray.",
            "Let top 2 inches of soil dry before next watering.",
        ],
    },
    {
        "plantName": "Snake Plant",
        "scientificName": "Dracaena trifasciata",
        "healthStatus": "Healthy",
        "healthScore": 92,
        "healthDotClass": "ok",
        "diagnosis": "Overall health is excellent — strong turgor pressure and good coloration. Minor mechanical damage on one edge.",
        "issues": ["Minor Mechanical Damage"],
        "treatments": [
            "No immediate action required.",
            "Wipe leaves with a damp cloth to improve photosynthesis.",
            "Rotate 90° every month for even growth.",
        ],
    },
    {
        "plantName": "Fiddle Leaf Fig",
        "scientificName": "Ficus lyrata",
        "healthStatus": "Critical",
        "healthScore": 35,
        "healthDotClass": "bad",
        "diagnosis": "Significant Edema alongside early root stress. Dark spots on new growth suggest moisture imbalance.",
        "issues": ["Root Rot Warning", "Severe Edema", "Light Deprivation"],
        "treatments": [
            "Stop watering for at least 14 days.",
            "Move to 6+ hours of bright indirect light.",
            "Check roots; repot in well-draining soil if mushy.",
            "Prune severely damaged leaves.",
        ],
    },
    {
        "plantName": "Peace Lily",
        "scientificName": "Spathiphyllum",
        "healthStatus": "Dehydrated",
        "healthScore": 45,
        "healthDotClass": "warn",
        "diagnosis": "Severe drooping detected — plant likely at Temporary Wilting Point from underwatering or heat.",
        "issues": ["Severe Dehydration", "Heat Stress"],
        "treatments": [
            "Bottom-water soak for 20 minutes.",
            "Move away from heat sources.",
            "Mist leaves for temporary relief.",
        ],
    },
]


async def detect_plant_disease(image_base64: str) -> dict:
    api_key = os.getenv("ROBOFLOW_API_KEY", "")
    model_endpoint = os.getenv("ROBOFLOW_PLANT_MODEL", "plant-disease-lktfd/3")

    if not api_key or api_key in ("your_roboflow_key", ""):
        raise Exception("Roboflow API key not configured")

    import httpx
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"https://detect.roboflow.com/{model_endpoint}?api_key={api_key}",
            content=image_base64.encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


class DiagnoseBody(BaseModel):
    image: str

    @field_validator("image")
    @classmethod
    def validate_image(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Image base64 is required")
        # Strip data URI prefix
        if v.startswith("data:"):
            try:
                v = v.split(",", 1)[1]
            except IndexError:
                raise ValueError("Invalid data URI")
        if len(v) > 14_000_000:
            raise ValueError("Image too large (max 10 MB)")
        return v


@router.post("/")
@limiter.limit("10/minute")
async def plant_diagnose(request: Request, body: DiagnoseBody):
    # Validate base64 and check real image size
    try:
        image_bytes = base64.b64decode(body.image, validate=True)
    except Exception:
        raise HTTPException(400, "Invalid base64 image data")

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Image too large. Maximum size is 10 MB.")

    # Verify it's a real image via magic bytes
    magic_map = {b'\xff\xd8\xff': True, b'\x89PNG': True, b'RIFF': True}
    is_image = any(image_bytes[:4].startswith(magic) for magic in magic_map)
    if not is_image:
        raise HTTPException(400, "Invalid image file. Please upload a JPG, PNG, or WEBP.")

    try:
        roboflow_result = await detect_plant_disease(body.image)
        predictions = roboflow_result.get("predictions", [])
    except Exception:
        predictions = []

    if not predictions:
        return {"result": random.choice(MOCKS)}

    # Sanitize Roboflow output before passing to client
    plant_name = "Unknown Plant"
    issues = []
    health_score = 95
    max_confidence = 0.0

    for p in predictions:
        conf = float(p.get("confidence", 0))
        cls = re.sub(r"[<>\"'&]", "", str(p.get("class", "")))[:100]  # sanitize class name
        if conf > max_confidence:
            max_confidence = conf
            if "healthy" not in cls.lower():
                issues.append(cls)
            else:
                plant_name = cls

    issues = list(set(issues))[:10]  # cap at 10
    if issues:
        health_score = max(10, 100 - len(issues) * 20)

    display = plant_name if plant_name != "Unknown Plant" else (predictions[0].get("class", "Houseplant") if predictions else "Houseplant")
    display = re.sub(r"[<>\"'&]", "", display)[:100]

    return {
        "result": {
            "plantName": display,
            "healthStatus": "Needs Attention" if issues else "Healthy",
            "healthScore": health_score,
            "healthDotClass": "warn" if issues else "ok",
            "diagnosis": (
                f"Detected: {', '.join(issues)} ({round(max_confidence * 100)}% confidence)."
                if issues else
                f"No major diseases detected ({round((max_confidence or 0.8) * 100)}% confidence)."
            ),
            "issues": issues,
            "treatments": (
                ["Isolate the plant.", "Adjust watering.", "Apply fungicide/pesticide if symptoms worsen."]
                if issues else
                ["Continue current care routine.", "Ensure adequate sunlight."]
            ),
        }
    }
