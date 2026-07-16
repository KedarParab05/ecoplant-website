"""
routers/newsletter.py — Subscribe / unsubscribe — Security Hardened
"""

import os
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from db.database import is_connected, get_db, json_db
from middleware.validators import validate_email

router = APIRouter(prefix="/api/newsletter", tags=["newsletter"])
limiter = Limiter(key_func=get_remote_address)


class EmailBody(BaseModel):
    email: str


@router.post("/subscribe")
@limiter.limit("5/minute")
async def subscribe(request: Request, body: EmailBody):
    email = validate_email(body.email)

    if is_connected():
        await get_db().subscribers.update_one(
            {"email": email},
            {"$set": {"email": email, "createdAt": datetime.now(timezone.utc)}},
            upsert=True,
        )
    else:
        existing = json_db.find_one("subscribers", lambda s: s["email"] == email)
        if not existing:
            json_db.push("subscribers", {
                "email": email,
                "createdAt": datetime.now(timezone.utc).isoformat(),
            })

    # Always return same message — no email enumeration
    return {"message": "🌱 Subscribed! Welcome to the EcoPlant family. Expect weekly plant love in your inbox."}


@router.post("/unsubscribe")
@limiter.limit("5/minute")
async def unsubscribe(request: Request, body: EmailBody):
    email = validate_email(body.email)

    if is_connected():
        await get_db().subscribers.delete_one({"email": email})
    else:
        json_db.remove("subscribers", lambda s: s["email"] == email)

    return {"message": "Unsubscribed successfully."}


@router.get("/subscribers")
@limiter.limit("10/minute")
async def get_subscribers(request: Request):
    admin_secret = request.headers.get("x-admin-secret", "")
    expected = os.getenv("ADMIN_SECRET", "")

    # Constant-time comparison to prevent timing attacks
    import hmac as hmac_mod
    if not expected or not hmac_mod.compare_digest(admin_secret.encode(), expected.encode()):
        raise HTTPException(403, "Forbidden")

    if is_connected():
        cursor = get_db().subscribers.find({}, {"_id": 0, "email": 1, "createdAt": 1}).sort("createdAt", -1).limit(1000)
        subs = [doc async for doc in cursor]
    else:
        subs = [{"email": s["email"], "createdAt": s.get("createdAt")} for s in json_db.get("subscribers")]

    return {"subscribers": subs, "total": len(subs)}
