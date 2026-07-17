"""
Vercel serverless entrypoint.

Vercel's Python runtime auto-detects any ASGI/WSGI-compatible `app` object
in files under /api. This file just re-exports the real FastAPI app from
app.main so the whole existing backend runs unchanged inside one
serverless function.
"""
import os
import sys

# Make sure `backend/` (the parent of this api/ folder) is importable as the
# project root, so `from app.main import app` resolves the same way it does
# when running `uvicorn app.main:app` locally.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402

# Vercel looks for a module-level `app` (or `handler`) callable.
