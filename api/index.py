"""
api/index.py — EcoPlant Pro · Self-contained FastAPI for Vercel
───────────────────────────────────────────────────────────────
All Python code lives here so Vercel's @vercel/python builder
has zero path issues. python-backend/ is still used locally.
"""

import sys
import os

# ── Path setup: let python-backend modules be imported if present ─────────────
_api_dir = os.path.dirname(os.path.abspath(__file__))
_root    = os.path.dirname(_api_dir)
_backend = os.path.join(_root, "python-backend")

# Insert python-backend first so local dev uses the real modules
if os.path.isdir(_backend):
    sys.path.insert(0, _backend)

# ── Environment ───────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    # Try python-backend/.env first, then root .env
    _env = os.path.join(_backend, ".env")
    load_dotenv(_env if os.path.exists(_env) else os.path.join(_root, ".env"))
except ImportError:
    pass

# ── Import the FastAPI app ─────────────────────────────────────────────────────
try:
    from main import app                        # python-backend/main.py
except ModuleNotFoundError:
    # python-backend not on path (shouldn't happen with includeFiles) — build minimal fallback
    from fastapi import FastAPI
    app = FastAPI()

    @app.get("/api/health")
    def _health():
        return {"status": "error", "detail": "python-backend not bundled — check vercel.json includeFiles"}

__all__ = ["app"]
