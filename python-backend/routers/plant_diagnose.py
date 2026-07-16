"""
routers/plant_diagnose.py — Roboflow plant disease detection + mock fallback
POST /api/plant-diagnose  { image: base64string }
"""

import os
import random
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/plant-diagnose", tags=["plant-diagnose"])

MOCKS = [
    {
        "plantName": "Monstera Deliciosa",
        "scientificName": "Monstera deliciosa",
        "healthStatus": "Needs Attention",
        "healthScore": 68,
        "healthDotClass": "warn",
        "diagnosis": "The specimen shows classic signs of 'Leaf Tip Burn' and slight chlorosis on lower foliage. This is often indicative of inconsistent humidity levels or tap water mineral buildup.",
        "issues": ["Browning Leaf Tips", "Slight Overwatering", "Low Humidity"],
        "treatments": [
            "Trim the brown edges with sterilized shears.",
            "Switch to filtered or distilled water to avoid fluoride buildup.",
            "Increase local humidity using a pebble tray or humidifier.",
            "Ensure the top 2 inches of soil are dry before watering again.",
        ],
    },
    {
        "plantName": "Snake Plant",
        "scientificName": "Dracaena trifasciata",
        "healthStatus": "Healthy",
        "healthScore": 92,
        "healthDotClass": "ok",
        "diagnosis": "Overall health is excellent. Strong turgor pressure in leaves and good coloration. Minor mechanical damage on one leaf edge, likely due to physical contact.",
        "issues": ["Minor Mechanical Damage"],
        "treatments": [
            "No immediate action required.",
            "Wipe leaves with a damp cloth to remove dust and improve photosynthesis.",
            "Rotate 90 degrees every month for even growth.",
        ],
    },
    {
        "plantName": "Fiddle Leaf Fig",
        "scientificName": "Ficus lyrata",
        "healthStatus": "Critical",
        "healthScore": 35,
        "healthDotClass": "bad",
        "diagnosis": "Significant 'Edema' detected alongside early-stage root stress. The dark red/brown spots on new growth suggest a serious moisture imbalance in the root zone.",
        "issues": ["Root Rot Warning", "Severe Edema", "Light Deprivation"],
        "treatments": [
            "Immediately stop watering for at least 14 days.",
            "Move to a location with 6+ hours of bright, indirect light.",
            "Check roots for mushiness; repot in well-draining soil if necessary.",
            "Prune severely damaged leaves to conserve energy.",
        ],
    },
    {
        "plantName": "Peace Lily",
        "scientificName": "Spathiphyllum",
        "healthStatus": "Dehydrated",
        "healthScore": 45,
        "healthDotClass": "warn",
        "diagnosis": "Severe drooping (epinasty) detected. The plant is likely in a state of 'Temporary Wilting Point' due to underwatering or excessive heat exposure.",
        "issues": ["Severe Dehydration", "Heat Stress"],
        "treatments": [
            "Give the plant a thorough bottom-watering soak for 20 minutes.",
            "Move away from direct heat sources or drafty windows.",
            "Mist leaves to provide temporary relief while roots recover.",
        ],
    },
]


async def detect_plant_disease(image_base64: str) -> dict:
    api_key = os.getenv("ROBOFLOW_API_KEY", "")
    model_endpoint = os.getenv("ROBOFLOW_PLANT_MODEL", "plant-disease-lktfd/3")

    if not api_key or api_key == "your_roboflow_key":
        raise Exception("Roboflow API key is not configured.")

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


@router.post("/")
async def plant_diagnose(body: DiagnoseBody):
    if not body.image:
        raise HTTPException(400, "Image base64 is required.")

    try:
        roboflow_result = await detect_plant_disease(body.image)
        predictions = roboflow_result.get("predictions", [])
    except Exception:
        predictions = []

    if not predictions:
        return {"result": random.choice(MOCKS)}

    # Map Roboflow predictions to frontend format
    plant_name = "Unknown Plant"
    issues = []
    health_score = 95
    max_confidence = 0.0

    for p in predictions:
        if p["confidence"] > max_confidence:
            max_confidence = p["confidence"]
            cls = p.get("class", "")
            if "healthy" not in cls.lower():
                issues.append(cls)
            else:
                plant_name = cls

    issues = list(set(issues))
    if issues:
        health_score = max(10, 100 - len(issues) * 20)

    display_name = plant_name if plant_name != "Unknown Plant" else (predictions[0].get("class", "Houseplant") if predictions else "Houseplant")

    final_report = {
        "plantName": display_name,
        "healthStatus": "Needs Attention" if issues else "Healthy",
        "healthScore": health_score,
        "healthDotClass": "warn" if issues else "ok",
        "diagnosis": (
            f"Detected signs of {', '.join(issues)} with {round(max_confidence * 100)}% confidence."
            if issues else
            f"No major diseases detected. Confidence: {round((max_confidence or 0.8) * 100)}%"
        ),
        "issues": issues,
        "treatments": (
            ["Isolate the plant immediately.", "Adjust watering schedule.", "Apply appropriate fungicide/pesticide if symptoms worsen."]
            if issues else
            ["Continue current care routine.", "Ensure adequate sunlight."]
        ),
        "roboflowPredictions": predictions,
    }

    return {"result": final_report}
