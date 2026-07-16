"""
main.py — EcoPlant Pro · Python/FastAPI Backend (Security Hardened)
────────────────────────────────────────────────────────────────────
Security layers:
  1. SecurityMiddleware   — XSS/NoSQL injection, security headers, CSP, HSTS
  2. CORSMiddleware       — strict origin allowlist
  3. SlowAPI              — tiered rate limiting (general + per-endpoint)
  4. JWT auth middleware  — Bearer token verification
  5. Input validators     — email/password/name/ID validators
  6. Brute-force lockout  — per-IP failed-auth tracking
  7. Request size limits  — 15 MB max body
  8. Hidden error details — no stack traces in production
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

load_dotenv()

from db.database import connect
from middleware.security import SecurityMiddleware
from routers import auth, chat, doctor, orders, newsletter, reviews, plants, plant_diagnose

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ecoplant")

IS_PROD = os.getenv("VERCEL") == "1" or os.getenv("ENV", "").lower() == "production"

# ── Rate limiter ───────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/15minutes"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect()
    yield


# Hide docs in production
app = FastAPI(
    title="EcoPlant API",
    version="1.0.0",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Security middleware (runs first — innermost layer) ────────────────────────
app.add_middleware(SecurityMiddleware)

# ── CORS — strict origin allowlist ────────────────────────────────────────────
ALLOWED_ORIGINS = list(filter(None, [
    "https://ecoplant-pro.vercel.app",
    os.getenv("FRONTEND_URL", ""),
    # Local dev origins
    "http://localhost:5000",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5500",
    "http://localhost:8080",
    "http://127.0.0.1:5000",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:3000",
]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Secret"],
    max_age=600,
)

# ── Global validation error handler ──────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [{"field": ".".join(str(l) for l in e["loc"]), "msg": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"error": "Validation failed", "details": errors})


# ── Global 500 handler (hide internals in production) ─────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"[unhandled] {request.method} {request.url.path}: {exc}", exc_info=True)
    detail = str(exc) if not IS_PROD else "Internal server error"
    return JSONResponse(status_code=500, content={"error": detail})


# ── Request logger (dev only) ─────────────────────────────────────────────────
if not IS_PROD:
    @app.middleware("http")
    async def request_logger(request: Request, call_next):
        from datetime import datetime
        response = await call_next(request)
        logger.info(f"{request.method} {request.url.path} → {response.status_code}")
        return response

# ── API routers with per-router rate limits ───────────────────────────────────
app.include_router(auth.router)            # auth: brute-force handled in route
app.include_router(chat.router)            # AI: 10/min via slowapi in router
app.include_router(doctor.router)          # AI: 10/min
app.include_router(orders.router)
app.include_router(newsletter.router)
app.include_router(reviews.router)
app.include_router(plants.router)
app.include_router(plant_diagnose.router)  # AI: 10/min

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    from db.database import is_connected
    from datetime import datetime, timezone
    return {
        "status": "ok",
        "service": "EcoPlant API (Python/FastAPI)",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db": "mongodb" if is_connected() else "json-file",
        "security": "hardened",
        "ai": {"gemini": bool(os.getenv("GEMINI_API_KEY"))},
        "payments": bool(os.getenv("RAZORPAY_KEY_ID")),
    }


# ── Static files + SPA fallback ───────────────────────────────────────────────
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")
if os.path.isdir(PUBLIC_DIR):
    plants_img_dir = os.path.join(PUBLIC_DIR, "plants-imgs")
    if os.path.isdir(plants_img_dir):
        app.mount("/plants-imgs", StaticFiles(directory=plants_img_dir), name="plant-images")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str, request: Request):
        if full_path.startswith("api/"):
            return JSONResponse({"error": "Not found"}, status_code=404)
        # Block path traversal
        if ".." in full_path or full_path.startswith("/"):
            return JSONResponse({"error": "Bad request"}, status_code=400)
        file_path = os.path.normpath(os.path.join(PUBLIC_DIR, full_path))
        # Ensure the resolved path is still within PUBLIC_DIR
        if not file_path.startswith(os.path.normpath(PUBLIC_DIR)):
            return JSONResponse({"error": "Forbidden"}, status_code=403)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        index = os.path.join(PUBLIC_DIR, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return JSONResponse({"error": "Not found"}, status_code=404)
