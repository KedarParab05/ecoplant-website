"""
routers/reviews.py — Product reviews (MongoDB + JSON fallback)
"""

import uuid as uuid_lib
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db.database import is_connected, get_db, json_db
from middleware.auth import require_auth, optional_auth

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


class ReviewBody(BaseModel):
    rating: int
    text: str


# ── GET /api/reviews/{plant_id} ──────────────────────────────────────────────────
@router.get("/{plant_id}")
async def get_reviews(plant_id: int, current_user: Optional[dict] = Depends(optional_auth)):
    if is_connected():
        cursor = get_db().reviews.find({"plantId": plant_id}).sort("createdAt", -1)
        reviews = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            reviews.append(doc)
    else:
        all_reviews = json_db.get("reviews")
        reviews = sorted(
            [r for r in all_reviews if r.get("plantId") == plant_id],
            key=lambda r: r.get("createdAt", ""), reverse=True,
        )

    total = len(reviews)
    avg = round(sum(r["rating"] for r in reviews) / total, 1) if total else 0.0
    distribution = {s: sum(1 for r in reviews if r["rating"] == s) for s in [5, 4, 3, 2, 1]}

    return {"reviews": reviews, "total": total, "average": avg, "distribution": distribution}


# ── POST /api/reviews/{plant_id} ─────────────────────────────────────────────────
@router.post("/{plant_id}", status_code=201)
async def post_review(plant_id: int, body: ReviewBody, current_user: dict = Depends(require_auth)):
    if not 1 <= body.rating <= 5:
        raise HTTPException(400, "Rating must be between 1 and 5")
    if not body.text.strip() or len(body.text.strip()) < 5:
        raise HTTPException(400, "Review text must be at least 5 characters")

    uid = current_user["id"]
    name = current_user.get("name", "Anonymous")

    if is_connected():
        from bson import ObjectId
        review = await get_db().reviews.find_one_and_update(
            {"plantId": plant_id, "userId": uid},
            {"$set": {"rating": body.rating, "text": body.text.strip(), "userName": name}},
            upsert=True, return_document=True,
        )
        review["id"] = str(review.pop("_id"))
    else:
        existing = [r for r in json_db.get("reviews") if r.get("plantId") == plant_id and r.get("userId") == uid]
        filtered = [r for r in json_db.get("reviews") if not (r.get("plantId") == plant_id and r.get("userId") == uid)]
        json_db.set("reviews", filtered)
        review = json_db.push("reviews", {
            "id": str(uuid_lib.uuid4()), "plantId": plant_id, "userId": uid,
            "userName": name, "rating": body.rating, "text": body.text.strip(),
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })

    return {"message": "Review submitted!", "review": review}


# ── DELETE /api/reviews/{review_id} ─────────────────────────────────────────────
@router.delete("/{review_id}")
async def delete_review(review_id: str, current_user: dict = Depends(require_auth)):
    uid = current_user["id"]
    if is_connected():
        from bson import ObjectId
        deleted = await get_db().reviews.find_one_and_delete({"_id": ObjectId(review_id), "userId": uid})
        if not deleted:
            raise HTTPException(404, "Review not found")
    else:
        json_db.remove("reviews", lambda r: r["id"] == review_id and r.get("userId") == uid)

    return {"message": "Review deleted"}
