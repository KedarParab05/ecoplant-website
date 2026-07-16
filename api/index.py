"""
api/index.py — Vercel serverless entry point for Python/FastAPI
Vercel routes all requests to this file via @vercel/python
"""

import sys
import os

# Add python-backend to path so imports resolve correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python-backend'))

from main import app
