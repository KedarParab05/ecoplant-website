"""
routers/auth.py — Signup, Signin, Google OAuth, Forgot, Reset, Me (GET/PUT)
"""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from db.database import is_connected, get_db, json_db
from middleware.auth import require_auth

import uuid as uuid_lib

router = APIRouter(prefix="/api/auth", tags=["auth"])

JWT_SECRET = os.getenv("JWT_SECRET", "ecoplant_universal_dev_secret_2024")
ALGORITHM = "HS256"
GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID",
    "676042745482-s2k2bpfcqktf62qm5bjtf27hnpap7hge.apps.googleusercontent.com",
)

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Helpers ─────────────────────────────────────────────────────────────────────
def sign_token(user: dict) -> str:
    uid = str(user.get("_id", user.get("id", "")))
    return jwt.encode(
        {"id": uid, "email": user["email"], "name": user["name"]},
        JWT_SECRET,
        algorithm=ALGORITHM,
    )


def user_payload(user: dict) -> dict:
    return {
        "id": str(user.get("_id", user.get("id", ""))),
        "name": user["name"],
        "email": user["email"],
        "createdAt": str(user.get("createdAt", "")),
    }


# ── Request schemas ─────────────────────────────────────────────────────────────
class SignupBody(BaseModel):
    name: str
    email: str
    password: str


class SigninBody(BaseModel):
    email: str
    password: str


class ForgotBody(BaseModel):
    email: str


class ResetBody(BaseModel):
    token: str
    password: str


class MeUpdateBody(BaseModel):
    name: str
    email: str
    currentPassword: Optional[str] = None
    newPassword: Optional[str] = None


class GoogleBody(BaseModel):
    credential: str


# ── POST /api/auth/signup ────────────────────────────────────────────────────────
@router.post("/signup", status_code=201)
async def signup(body: SignupBody):
    if not body.name.strip():
        raise HTTPException(400, "Name is required")
    if "@" not in body.email:
        raise HTTPException(400, "Valid email is required")
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    password_hash = pwd_ctx.hash(body.password)
    email = body.email.lower().strip()
    name = body.name.strip()

    if is_connected():
        db = get_db()
        existing = await db.users.find_one({"email": email})
        if existing:
            raise HTTPException(409, "Email already registered. Please sign in.")
        result = await db.users.insert_one(
            {"name": name, "email": email, "passwordHash": password_hash, "createdAt": datetime.now(timezone.utc)}
        )
        user = await db.users.find_one({"_id": result.inserted_id})
    else:
        existing = json_db.find_one("users", lambda u: u["email"] == email)
        if existing:
            raise HTTPException(409, "Email already registered. Please sign in.")
        user = json_db.push("users", {
            "id": str(uuid_lib.uuid4()), "name": name, "email": email,
            "passwordHash": password_hash, "createdAt": datetime.now(timezone.utc).isoformat(),
        })

    return {"message": "Account created!", "token": sign_token(user), "user": user_payload(user)}


# ── POST /api/auth/signin ────────────────────────────────────────────────────────
@router.post("/signin")
async def signin(body: SigninBody):
    if not body.email or not body.password:
        raise HTTPException(400, "Email and password are required")
    email = body.email.lower().strip()

    if is_connected():
        user = await get_db().users.find_one({"email": email})
    else:
        user = json_db.find_one("users", lambda u: u["email"] == email)

    if not user:
        raise HTTPException(401, "Invalid email or password")
    if not pwd_ctx.verify(body.password, user.get("passwordHash", "")):
        raise HTTPException(401, "Invalid email or password")

    return {"message": "Signed in!", "token": sign_token(user), "user": user_payload(user)}


# ── POST /api/auth/forgot ────────────────────────────────────────────────────────
@router.post("/forgot")
async def forgot(body: ForgotBody):
    if not body.email:
        raise HTTPException(400, "Email is required")
    email = body.email.lower().strip()

    if is_connected():
        user = await get_db().users.find_one({"email": email})
    else:
        user = json_db.find_one("users", lambda u: u["email"] == email)

    if not user:
        return {"message": "If that email is registered, a reset link has been sent."}

    uid = str(user.get("_id", user.get("id", "")))
    reset_token = jwt.encode({"id": uid, "type": "reset"}, JWT_SECRET, algorithm=ALGORITHM)
    print(f"[auth/forgot] Reset token for {email}: {reset_token}")
    return {"message": "If that email is registered, a reset link has been sent."}


# ── POST /api/auth/reset ────────────────────────────────────────────────────────
@router.post("/reset")
async def reset(body: ResetBody):
    if not body.token or not body.password:
        raise HTTPException(400, "token and password are required")
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    try:
        payload = jwt.decode(body.token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(400, "Reset link is invalid or has expired")
    if payload.get("type") != "reset":
        raise HTTPException(400, "Invalid reset token")

    password_hash = pwd_ctx.hash(body.password)
    uid = payload["id"]

    if is_connected():
        from bson import ObjectId
        await get_db().users.update_one({"_id": ObjectId(uid)}, {"$set": {"passwordHash": password_hash}})
    else:
        json_db.update("users", lambda u: u["id"] == uid, lambda _: {"passwordHash": password_hash})

    return {"message": "Password reset! Please sign in with your new password."}


# ── GET /api/auth/me ─────────────────────────────────────────────────────────────
@router.get("/me")
async def get_me(current_user: dict = Depends(require_auth)):
    uid = current_user["id"]
    if is_connected():
        from bson import ObjectId
        user = await get_db().users.find_one({"_id": ObjectId(uid)}, {"passwordHash": 0})
    else:
        user = json_db.find_one("users", lambda u: u["id"] == uid)

    if not user:
        raise HTTPException(404, "User not found")
    return {"user": user_payload(user)}


# ── PUT /api/auth/me ─────────────────────────────────────────────────────────────
@router.put("/me")
async def update_me(body: MeUpdateBody, current_user: dict = Depends(require_auth)):
    if not body.name.strip() or "@" not in body.email:
        raise HTTPException(400, "Valid name and email are required")

    uid = current_user["id"]
    if is_connected():
        from bson import ObjectId
        user = await get_db().users.find_one({"_id": ObjectId(uid)})
    else:
        user = json_db.find_one("users", lambda u: u["id"] == uid)

    if not user:
        raise HTTPException(404, "User not found")

    updates: dict = {"name": body.name.strip(), "email": body.email.lower().strip()}
    if body.newPassword:
        if not body.currentPassword:
            raise HTTPException(400, "Current password is required")
        if not pwd_ctx.verify(body.currentPassword, user.get("passwordHash", "")):
            raise HTTPException(401, "Current password is incorrect")
        if len(body.newPassword) < 6:
            raise HTTPException(400, "New password must be at least 6 characters")
        updates["passwordHash"] = pwd_ctx.hash(body.newPassword)

    if is_connected():
        from bson import ObjectId
        await get_db().users.update_one({"_id": ObjectId(uid)}, {"$set": updates})
        updated = await get_db().users.find_one({"_id": ObjectId(uid)})
    else:
        json_db.update("users", lambda u: u["id"] == uid, lambda _: updates)
        updated = json_db.find_one("users", lambda u: u["id"] == uid)

    return {"message": "Profile updated!", "user": user_payload(updated)}


# ── POST /api/auth/google ────────────────────────────────────────────────────────
@router.post("/google")
async def google_signin(body: GoogleBody):
    if not body.credential:
        raise HTTPException(400, "Google credential is required")
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(500, "Google Sign-In is not configured on the server")

    try:
        info = google_id_token.verify_oauth2_token(
            body.credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except Exception:
        raise HTTPException(401, "Invalid Google credential. Please try again.")

    email = info.get("email", "").lower().strip()
    name = info.get("name") or email.split("@")[0] or "EcoPlant User"
    google_id = info.get("sub", "")

    if not email:
        raise HTTPException(400, "Could not retrieve email from Google account")

    is_new = False
    if is_connected():
        db = get_db()
        user = await db.users.find_one({"email": email})
        if not user:
            result = await db.users.insert_one({
                "name": name, "email": email,
                "passwordHash": pwd_ctx.hash(google_id + JWT_SECRET),
                "createdAt": datetime.now(timezone.utc),
            })
            user = await db.users.find_one({"_id": result.inserted_id})
            is_new = True
    else:
        user = json_db.find_one("users", lambda u: u["email"] == email)
        if not user:
            user = json_db.push("users", {
                "id": str(uuid_lib.uuid4()), "name": name, "email": email,
                "passwordHash": "", "createdAt": datetime.now(timezone.utc).isoformat(),
            })
            is_new = True

    status = 201 if is_new else 200
    msg = "Account created with Google!" if is_new else "Signed in with Google!"
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status,
        content={"message": msg, "token": sign_token(user), "user": user_payload(user), "isNew": is_new},
    )
