"""
routers/reviews.py — Product reviews — Security Hardened
"""

import re
import uuid as uuid_lib
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from db.database import is_connected, get_db, json_db
from middleware.auth import require_auth, optional_auth
from middleware.validators import validate_text

router = APIRouter(prefix="/api/reviews", tags=["reviews"])
limiter = Limiter(key_func=get_remote_address)


class ReviewBody(BaseModel):
    rating: int
    text: str

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if not isinstance(v, int) or not 1 <= v <= 5:
            raise ValueError("Rating must be an integer between 1 and 5")
        return v

    @field_validator("text")
    @classmethod
    def validate_text_field(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Review text is required")
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Review text must be at least 5 characters")
        if len(v) > 1000:
            raise ValueError("Review text must be at most 1000 characters")
        # Strip HTML tags
        v = re.sub(r"<[^>]+>", "", v)
        return v


def _safe_plant_id(plant_id: int) -> int:
    if not isinstance(plant_id, int) or plant_id < 1 or plant_id > 10_000:
        raise HTTPException(400, "Invalid plant ID")
    return plant_id


# ── GET /api/reviews/{plant_id} ──────────────────────────────────────────────────
@router.get("/{plant_id}")
@limiter.limit("60/minute")
async def get_reviews(
    request: Request,
    plant_id: int,
    current_user: Optional[dict] = Depends(optional_auth),
):
    plant_id = _safe_plant_id(plant_id)

    if is_connected():
        cursor = get_db().reviews.find(
            {"plantId": plant_id},
            {"_id": 1, "plantId": 1, "userName": 1, "rating": 1, "text": 1, "createdAt": 1}
        ).sort("createdAt", -1).limit(200)
        reviews = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            doc.pop("userId", None)   # Never expose userId
            reviews.append(doc)
    else:
        all_reviews = json_db.get("reviews")
        reviews = sorted(
            [
                {k: v for k, v in r.items() if k != "userId"}   # strip userId
                for r in all_reviews if r.get("plantId") == plant_id
            ],
            key=lambda r: r.get("createdAt", ""), reverse=True,
        )[:200]

    total = len(reviews)
    avg = round(sum(r["rating"] for r in reviews) / total, 1) if total else 0.0
    distribution = {s: sum(1 for r in reviews if r["rating"] == s) for s in [5, 4, 3, 2, 1]}

    return {"reviews": reviews, "total": total, "average": avg, "distribution": distribution}


# ── POST /api/reviews/{plant_id} ─────────────────────────────────────────────────
@router.post("/{plant_id}", status_code=201)
@limiter.limit("10/minute")
async def post_review(
    request: Request,
    plant_id: int,
    body: ReviewBody,
    current_user: dict = Depends(require_auth),
):
    plant_id = _safe_plant_id(plant_id)
    uid = current_user["id"]
    name = current_user.get("name", "Anonymous")[:100]
    # Sanitize name for display
    name = re.sub(r"[<>\"'`]", "", name).strip() or "Anonymous"

    if is_connected():
        review = await get_db().reviews.find_one_and_update(
            {"plantId": plant_id, "userId": uid},
            {"$set": {
                "rating": body.rating,
                "text": body.text,
                "userName": name,
                "updatedAt": datetime.now(timezone.utc),
            }},
            upsert=True,
            return_document=True,
        )
        safe_review = {
            "id": str(review["_id"]),
            "plantId": review["plantId"],
            "userName": review["userName"],
            "rating": review["rating"],
            "text": review["text"],
            "createdAt": str(review.get("createdAt", "")),
        }
    else:
        filtered = [r for r in json_db.get("reviews")
                    if not (r.get("plantId") == plant_id and r.get("userId") == uid)]
        json_db.set("reviews", filtered)
        review = json_db.push("reviews", {
            "id": str(uuid_lib.uuid4()), "plantId": plant_id, "userId": uid,
            "userName": name, "rating": body.rating, "text": body.text,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })
        safe_review = {k: v for k, v in review.items() if k != "userId"}

    return {"message": "Review submitted!", "review": safe_review}


# ── DELETE /api/reviews/{review_id} ─────────────────────────────────────────────
@router.delete("/{review_id}")
@limiter.limit("20/minute")
async def delete_review(
    request: Request,
    review_id: str,
    current_user: dict = Depends(require_auth),
):
    # Validate review_id format
    if not re.match(r"^[a-f0-9]{24}$|^[0-9a-f\-]{36}$", review_id, re.IGNORECASE):
        raise HTTPException(400, "Invalid review ID format")

    uid = current_user["id"]
    if is_connected():
        from bson import ObjectId
        try:
            deleted = await get_db().reviews.find_one_and_delete(
                {"_id": ObjectId(review_id), "userId": uid}
            )
        except Exception:
            raise HTTPException(400, "Invalid review ID")
        if not deleted:
            raise HTTPException(404, "Review not found")
    else:
        json_db.remove("reviews", lambda r: r["id"] == review_id and r.get("userId") == uid)

    return {"message": "Review deleted"}
