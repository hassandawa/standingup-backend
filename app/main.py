import logging
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# --- Bulletproof logging setup -------------------------------------------
# Writes every log line to backend/logs/app.log AND the console when running
# on a normal filesystem (local dev, Render, etc). On Vercel the filesystem
# is read-only outside /tmp, so file logging is skipped there (Vercel sets
# the VERCEL env var automatically) and we just log to stdout, which Vercel
# captures anyway.
# `force=True` overrides any handlers already configured (e.g. by uvicorn),
# so this is guaranteed to take effect.
_handlers = [logging.StreamHandler(sys.stdout)]
if not os.environ.get("VERCEL"):
    try:
        _LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
        _LOG_DIR.mkdir(exist_ok=True)
        _LOG_FILE = _LOG_DIR / "app.log"
        _handlers.append(logging.FileHandler(_LOG_FILE, encoding="utf-8"))
    except OSError:
        pass  # read-only filesystem (e.g. serverless) - stdout logging still works

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [pid:%(process)d] %(levelname)s %(name)s: %(message)s",
    handlers=_handlers,
    force=True,
)
# ---------------------------------------------------------------------------

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio

from app.database import client, db, ensure_indexes
from app.routes import auth, profile, startups, enhanced, saved_ideas, billing

logger = logging.getLogger(__name__)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Abort requests that take too long (e.g. hanging Gemini calls)."""

    def __init__(self, app, timeout: float = 60.0):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            logger.error("Request timed out: %s %s", request.method, request.url.path)
            return JSONResponse(
                status_code=504,
                content={"detail": "Request timed out. Please try again.", "status_code": 504},
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== startingUP backend starting up (pid %s) ===", os.getpid())
    # Startup: verify MongoDB connection and create indexes when available.
    # Do not fail the whole web process here; Render must see the app bind to $PORT.
    try:
        client.admin.command("ping")
        ensure_indexes()
        logger.info("MongoDB connection established successfully.")
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error("MongoDB connection failed on startup: %s", e)
    except Exception as e:
        logger.error("MongoDB startup check failed: %s", e, exc_info=True)
    yield
    # Shutdown: close MongoDB connection
    client.close()
    logger.info("MongoDB connection closed.")


app = FastAPI(title="startingUP", version="1.0.0", lifespan=lifespan)

# CORS: environment-based origins instead of wildcard
_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if _origins_env:
    _allowed_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]
else:
    _allowed_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(TimeoutMiddleware, timeout=60.0)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(startups.router)
app.include_router(enhanced.router)
app.include_router(saved_ideas.router)
app.include_router(billing.router)


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "startingUP",
        "health": "/health",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred. Please try again later.",
            "status_code": 500,
        },
    )


@app.get("/health")
async def health_check():
    try:
        client.admin.command("ping")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return {
        "status": "healthy",
        "service": "startingUP",
        "database": db_status,
    }
