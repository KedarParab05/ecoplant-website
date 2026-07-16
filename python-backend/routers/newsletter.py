"""
routers/newsletter.py — Subscribe / unsubscribe
"""

import os
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from db.database import is_connected, get_db, json_db

router = APIRouter(prefix="/api/newsletter", tags=["newsletter"])


class EmailBody(BaseModel):
    email: str


@router.post("/subscribe")
async def subscribe(body: EmailBody):
    if "@" not in body.email:
        raise HTTPException(400, "Valid email is required")
    email = body.email.lower().strip()

    if is_connected():
        await get_db().subscribers.update_one(
            {"email": email}, {"$set": {"email": email, "createdAt": datetime.now(timezone.utc)}},
            upsert=True,
        )
    else:
        existing = json_db.find_one("subscribers", lambda s: s["email"] == email)
        if not existing:
            json_db.push("subscribers", {"email": email, "createdAt": datetime.now(timezone.utc).isoformat()})

    return {"message": "🌱 Subscribed! Welcome to the EcoPlant family. Expect weekly plant love in your inbox."}


@router.post("/unsubscribe")
async def unsubscribe(body: EmailBody):
    if not body.email:
        raise HTTPException(400, "Email is required")
    email = body.email.lower().strip()

    if is_connected():
        await get_db().subscribers.delete_one({"email": email})
    else:
        json_db.remove("subscribers", lambda s: s["email"] == email)

    return {"message": "Unsubscribed successfully."}


@router.get("/subscribers")
async def get_subscribers(request: Request):
    admin_secret = request.headers.get("x-admin-secret", "")
    if admin_secret != os.getenv("ADMIN_SECRET", ""):
        raise HTTPException(403, "Forbidden")

    if is_connected():
        cursor = get_db().subscribers.find().sort("createdAt", -1)
        subs = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            subs.append(doc)
    else:
        subs = json_db.get("subscribers")

    return {"subscribers": subs, "total": len(subs)}
