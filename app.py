"""
unknown_verdict.app
====================
FastAPI application — entry point for Hugging Face Spaces.

This replaces the old app.py that had broken relative imports.
All imports are now absolute (the fix that made '✅ Routes imported' appear).

Startup sequence:
  1. Load settings (all 25 secrets from HF Space)
  2. Connect to Neon PostgreSQL + run migrations
  3. Connect to Redis
  4. Initialize LLM router (loads all provider API keys)
  5. Mount all 68 endpoints (36 base + 32 moat)
  6. Serve the frontend
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from unknown_verdict.core.config import settings
from unknown_verdict.core.db import get_db
from unknown_verdict.core.llm import get_router
from unknown_verdict.core.routes import router, moat_router
from unknown_verdict.core.auth import check_rate_limit

# ─── Logging ──────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Rate limit middleware ─────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply rate limiting to API endpoints (not static files)."""

    EXEMPT_PATHS = {"/", "/health", "/version", "/docs", "/openapi.json",
                    "/redoc", "/favicon.ico", "/static"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Skip rate limiting for health checks and docs
        if any(path.startswith(p) for p in self.EXEMPT_PATHS):
            return await call_next(request)

        try:
            await check_rate_limit(request)
        except Exception:
            pass  # Don't block requests if rate limiter fails

        response = await call_next(request)

        # Add rate limit headers if available
        if hasattr(request.state, "rate_limit"):
            info = request.state.rate_limit
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Engine"] = info["engine"]

        return response


# ─── Lifespan (startup/shutdown) ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("🚀 Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("   Environment: %s", settings.ENVIRONMENT)
    logger.info("   LLM providers available: %s", settings.available_llm_providers)

    # 1. Initialize database (Neon + Redis)
    db = get_db()
    await db.init()
    logger.info("   DB connected: %s | Redis connected: %s",
                db.is_db_connected, db.is_redis_connected)

    # 2. Initialize LLM router with Redis cache
    router_llm = get_router()
    await router_llm.init(redis_client=db.redis)
    logger.info("   LLM router initialized")

    # 3. Log startup complete
    logger.info("✅ %s v%s is ready — 68 endpoints active",
                settings.APP_NAME, settings.APP_VERSION)

    yield

    # Shutdown
    logger.info("🛑 Shutting down %s", settings.APP_NAME)
    await router_llm.close()
    await db.close()
    logger.info("✅ Shutdown complete")


# ─── Create app ─────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI legal platform with 250+ agents, 15 verifiers, AI Judge, "
        "and a self-evolving intelligence layer (Moat). "
        "Powered by multi-LLM routing (Sarvam, OpenAI, Gemini, Groq, DeepSeek, OpenRouter)."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── Middleware ─────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)


# ─── Routes ─────────────────────────────────────────────────────────────────

app.include_router(router)
app.include_router(moat_router)


# ─── Static frontend ────────────────────────────────────────────────────────

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/app", response_class=HTMLResponse)
async def frontend():
    """Serve the chat frontend if it exists."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Unknown Verdict v41.0</h1><p>Frontend not found. See <a href='/docs'>/docs</a></p>")


# ─── Catch-all 404 handler ─────────────────────────────────────────────────

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "path": request.url.path,
            "available_endpoints": "/docs",
        },
    )


# ─── HF Spaces entry point ─────────────────────────────────────────────────
# HF Spaces runs: `python app.py` → uvicorn on port 7860

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "unknown_verdict.app:app",
        host="0.0.0.0",
        port=7860,
        workers=1,
        log_level=settings.LOG_LEVEL.lower(),
    )
