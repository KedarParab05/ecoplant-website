"""
middleware/auth.py — JWT authentication FastAPI dependencies
"""

import os
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

JWT_SECRET = os.getenv("JWT_SECRET", "ecoplant_universal_dev_secret_2024")
ALGORITHM = "HS256"

_bearer = HTTPBearer(auto_error=False)


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="No token provided")
    return _decode(credentials.credentials)


async def optional_auth(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict | None:
    if not credentials:
        return None
    try:
        return _decode(credentials.credentials)
    except HTTPException:
        return None
