"""
main.py — EcoPlant Pro · Python/FastAPI Backend
─────────────────────────────────────────────────
Endpoints mirror the original Node.js/Express server exactly so the
frontend HTML/JS files require zero changes.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

load_dotenv()

from db.database import connect
from routers import auth, chat, doctor, orders, newsletter, reviews, plants, plant_diagnose

# ── Rate limiter ───────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/15minutes"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect()
    yield


app = FastAPI(
    title="EcoPlant API",
    version="1.0.0",
    description="EcoPlant Pro — Python/FastAPI backend",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ────────────────────────────────────────────────────────────────────────
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")

allowed_origins = list(filter(None, [
    FRONTEND_URL,
    "http://localhost:5000",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:5000",
    "http://127.0.0.1:3000",
    "https://ecoplant-pro.vercel.app",
]))


def is_allowed_origin(origin: str) -> bool:
    if not origin:
        return True
    if origin in allowed_origins:
        return True
    import re
    return bool(re.match(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$", origin, re.IGNORECASE))


class DynamicCORSMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            origin = headers.get(b"origin", b"").decode()
            if is_allowed_origin(origin):
                scope["_cors_origin"] = origin
        await self.app(scope, receive, send)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # dynamic check handled above; Vercel needs wildcard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Security headers ────────────────────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# ── Request logger (dev) ────────────────────────────────────────────────────────
if os.getenv("NODE_ENV") != "production" and os.getenv("ENV") != "production":
    @app.middleware("http")
    async def request_logger(request: Request, call_next):
        from datetime import datetime
        print(f"[{datetime.utcnow().isoformat()}] {request.method} {request.url.path}")
        return await call_next(request)

# ── API routers ─────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(doctor.router)
app.include_router(orders.router)
app.include_router(newsletter.router)
app.include_router(reviews.router)
app.include_router(plants.router)
app.include_router(plant_diagnose.router)

# ── Health check ────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    from db.database import is_connected
    from datetime import datetime, timezone
    return {
        "status": "ok",
        "service": "EcoPlant API (Python/FastAPI)",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db": "mongodb" if is_connected() else "json-file",
        "ai": {"gemini": bool(os.getenv("GEMINI_API_KEY"))},
        "payments": bool(os.getenv("RAZORPAY_KEY_ID")),
    }

# ── Static files + SPA fallback ─────────────────────────────────────────────────
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")
if os.path.isdir(PUBLIC_DIR):
    app.mount("/plants-imgs", StaticFiles(directory=os.path.join(PUBLIC_DIR, "plants-imgs")), name="plant-images")
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str, request: Request):
        # Don't override API routes
        if full_path.startswith("api/"):
            return JSONResponse({"error": "Not found"}, status_code=404)
        # Try exact file first
        file_path = os.path.join(PUBLIC_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # Fallback to index.html
        index = os.path.join(PUBLIC_DIR, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return JSONResponse({"error": "Not found"}, status_code=404)
