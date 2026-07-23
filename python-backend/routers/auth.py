"""
routers/auth.py — Signup, Signin, Google OAuth, Forgot, Reset, Me (GET/PUT)
Security hardened:
  • Brute-force lockout per IP (via security middleware)
  • Strong password policy (8+ chars, letter + digit required)
  • Email format validation with regex
  • Input length limits on all fields
  • MongoDB query sanitization ($where/$regex etc. blocked)
  • Account enumeration prevention (forgot endpoint)
  • JWT: 7-day expiry (down from 30-day)
"""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from db.database import is_connected, get_db, json_db
from middleware.auth import require_auth
from middleware.security import record_failed_auth, clear_failed_auth, is_ip_locked
from middleware.validators import validate_email, validate_password, validate_name

import sys

JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-insecure-jwt-secret-set-JWT_SECRET-env")
if os.getenv("JWT_SECRET", "") == "":
    print("[WARNING] JWT_SECRET not set — using insecure dev default", file=sys.stderr)
ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = 7 * 24 * 3600   # 7 days

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
if not GOOGLE_CLIENT_ID:
    print("[WARNING] GOOGLE_CLIENT_ID not set — Google OAuth will be disabled", file=sys.stderr)

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

import uuid as uuid_lib

router = APIRouter(prefix="/api/auth", tags=["auth"])



# ── Helpers ─────────────────────────────────────────────────────────────────────
def sign_token(user: dict) -> str:
    from datetime import timedelta
    uid = str(user.get("_id", user.get("id", "")))
    exp = datetime.now(timezone.utc) + timedelta(seconds=JWT_EXPIRY_SECONDS)
    return jwt.encode(
        {"id": uid, "email": user["email"], "name": user["name"], "exp": exp},
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


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


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
async def signup(body: SignupBody, request: Request):
    ip = get_client_ip(request)
    if is_ip_locked(ip):
        raise HTTPException(429, "Too many attempts. Please try again later.")

    name = validate_name(body.name)
    email = validate_email(body.email)
    password = validate_password(body.password)

    password_hash = pwd_ctx.hash(password)

    if is_connected():
        db = get_db()
        existing = await db.users.find_one({"email": email})
        if existing:
            raise HTTPException(409, "Email already registered. Please sign in.")
        result = await db.users.insert_one(
            {"name": name, "email": email, "passwordHash": password_hash,
             "createdAt": datetime.now(timezone.utc), "loginAttempts": 0}
        )
        user = await db.users.find_one({"_id": result.inserted_id})
    else:
        existing = json_db.find_one("users", lambda u: u["email"] == email)
        if existing:
            raise HTTPException(409, "Email already registered. Please sign in.")
        user = json_db.push("users", {
            "id": str(uuid_lib.uuid4()), "name": name, "email": email,
            "passwordHash": password_hash,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })

    return {"message": "Account created!", "token": sign_token(user), "user": user_payload(user)}


# ── POST /api/auth/signin ────────────────────────────────────────────────────────
@router.post("/signin")
async def signin(body: SigninBody, request: Request):
    ip = get_client_ip(request)

    # Block locked IPs immediately
    if is_ip_locked(ip):
        raise HTTPException(429, "Too many failed attempts. Try again in 30 minutes.")

    # Basic input validation (don't reveal which field is wrong)
    if not body.email or not body.password:
        record_failed_auth(ip)
        raise HTTPException(401, "Invalid email or password")

    try:
        email = validate_email(body.email)
    except HTTPException:
        record_failed_auth(ip)
        raise HTTPException(401, "Invalid email or password")

    # Limit password length to prevent bcrypt DoS
    if len(body.password) > 128:
        record_failed_auth(ip)
        raise HTTPException(401, "Invalid email or password")

    if is_connected():
        user = await get_db().users.find_one({"email": email})
    else:
        user = json_db.find_one("users", lambda u: u["email"] == email)

    if not user or not pwd_ctx.verify(body.password, user.get("passwordHash", "")):
        record_failed_auth(ip)
        raise HTTPException(401, "Invalid email or password")

    # Successful login — clear failed counter
    clear_failed_auth(ip)
    return {"message": "Signed in!", "token": sign_token(user), "user": user_payload(user)}


# ── POST /api/auth/forgot ────────────────────────────────────────────────────────
@router.post("/forgot")
async def forgot(body: ForgotBody, request: Request):
    # Always return the same response — prevents email enumeration
    generic_response = {"message": "If that email is registered, a reset link has been sent."}

    if not body.email:
        return generic_response

    try:
        email = validate_email(body.email)
    except HTTPException:
        return generic_response

    if is_connected():
        user = await get_db().users.find_one({"email": email})
    else:
        user = json_db.find_one("users", lambda u: u["email"] == email)

    if not user:
        return generic_response

    uid = str(user.get("_id", user.get("id", "")))
    from datetime import timedelta
    exp = datetime.now(timezone.utc) + timedelta(hours=1)
    reset_token = jwt.encode(
        {"id": uid, "type": "reset", "exp": exp}, JWT_SECRET, algorithm=ALGORITHM
    )
    # In production: send via email. For now log (never expose to client).
    print(f"[auth/forgot] Reset token for {email}: {reset_token}")
    return generic_response


# ── POST /api/auth/reset ────────────────────────────────────────────────────────
@router.post("/reset")
async def reset(body: ResetBody):
    if not body.token or not body.password:
        raise HTTPException(400, "token and password are required")

    password = validate_password(body.password, "New password")

    try:
        payload = jwt.decode(body.token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(400, "Reset link is invalid or has expired")

    if payload.get("type") != "reset":
        raise HTTPException(400, "Invalid reset token")

    password_hash = pwd_ctx.hash(password)
    uid = payload["id"]

    if is_connected():
        from bson import ObjectId
        await get_db().users.update_one(
            {"_id": ObjectId(uid)}, {"$set": {"passwordHash": password_hash}}
        )
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
    name = validate_name(body.name)
    email = validate_email(body.email)

    uid = current_user["id"]
    if is_connected():
        from bson import ObjectId
        user = await get_db().users.find_one({"_id": ObjectId(uid)})
    else:
        user = json_db.find_one("users", lambda u: u["id"] == uid)

    if not user:
        raise HTTPException(404, "User not found")

    updates: dict = {"name": name, "email": email}

    if body.newPassword:
        if not body.currentPassword:
            raise HTTPException(400, "Current password is required")
        if len(body.currentPassword) > 128:
            raise HTTPException(401, "Current password is incorrect")
        if not pwd_ctx.verify(body.currentPassword, user.get("passwordHash", "")):
            raise HTTPException(401, "Current password is incorrect")
        new_pw = validate_password(body.newPassword, "New password")
        updates["passwordHash"] = pwd_ctx.hash(new_pw)

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
async def google_signin(body: GoogleBody, request: Request):
    ip = get_client_ip(request)
    if is_ip_locked(ip):
        raise HTTPException(429, "Too many attempts. Please try again later.")

    if not body.credential:
        raise HTTPException(400, "Google credential is required")
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(500, "Google Sign-In is not configured on the server")

    # Validate credential length to prevent DoS
    if len(body.credential) > 4096:
        raise HTTPException(400, "Invalid Google credential")

    try:
        info = google_id_token.verify_oauth2_token(
            body.credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except Exception:
        record_failed_auth(ip)
        raise HTTPException(401, "Invalid Google credential. Please try again.")

    email = info.get("email", "").lower().strip()
    name = info.get("name") or email.split("@")[0] or "EcoPlant User"
    google_id = info.get("sub", "")

    if not email:
        raise HTTPException(400, "Could not retrieve email from Google account")

    # Validate the email & name coming from Google
    try:
        email = validate_email(email)
    except HTTPException:
        raise HTTPException(400, "Google account email is not valid")

    # Sanitize name
    import re
    name = re.sub(r"[<>\"'`]", "", name)[:100].strip() or "EcoPlant User"

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

    clear_failed_auth(ip)

    status = 201 if is_new else 200
    msg = "Account created with Google!" if is_new else "Signed in with Google!"
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status,
        content={"message": msg, "token": sign_token(user), "user": user_payload(user), "isNew": is_new},
    )
