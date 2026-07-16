"""
api/index.py — Vercel serverless entry point for Python/FastAPI
All requests are routed here by vercel.json via @vercel/python
"""

import sys
import os

# Resolve python-backend relative to this file (works both locally and on Vercel)
_here = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.join(_here, '..', 'python-backend')
sys.path.insert(0, os.path.normpath(_backend))

# Load env vars from the python-backend/.env if present (local dev only)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_backend, '.env'))
except Exception:
    pass

from main import app  # noqa: F401 — Vercel picks up `app` automatically
