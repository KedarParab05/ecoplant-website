"""
api/index.py - EcoPlant Pro - Vercel Python Function Entry Point
Vercel runs this from /var/task/ with api/ as a package.
We add api/ dir to sys.path so 'main' can be imported directly.
"""
import sys
import os

# Add the api/ directory to path so 'main', 'db', 'routers' etc. resolve
_api_dir = os.path.dirname(os.path.abspath(__file__))
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from main import app  # noqa: F401

__all__ = ["app"]
