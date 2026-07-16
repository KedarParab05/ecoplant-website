"""
api/index.py — EcoPlant Pro · Vercel Python Function Entry Point
All source files (main.py, db/, middleware/, routers/) live in api/
so Vercel's python runtime picks them up with zero path manipulation.
"""
from main import app  # noqa: F401

__all__ = ["app"]
