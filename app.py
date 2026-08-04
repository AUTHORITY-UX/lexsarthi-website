"""
app.py
======
FastAPI application — entry point for Hugging Face Spaces.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from core.db import get_db
from core.llm.router import get_router
from core.auth import check_rate_limit
from routes import router, moat_router

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply rate limiting to API endpoints (not static files or docs)."""
    EXEMPT_PATHS = {"/", "/health", "/version", "/docs", "/openapi.json",
                    "/redoc", "/favicon.ico", "/static", "/app"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.EXEMPT_PATHS):
            return await call_next(request)
        try:
            await check_rate_limit(request)
        except Exception:
            pass  # Don't block requests if rate limiter fails
        response = await call_next(request)
        if hasattr(request.state, "rate_limit"):
            info = request.state.rate_limit
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Engine"] = info["engine"]
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("   Environment: %s", settings.ENVIRONMENT)
    logger.info("   LLM providers: %s", settings.available_llm_providers)

    db = get_db()
    await db.init()
    logger.info("   DB: %s | Redis: %s", db.is_db_connected, db.is_redis_connected)

    router_llm = get_router()
    await router_llm.init(redis_client=db.redis)
    logger.info("   LLM router initialized")

    logger.info("✅ %s v%s ready — 68 endpoints active", settings.APP_NAME, settings.APP_VERSION)
    
    yield  # This is where the app runs
    
    # Shutdown cleanup
    logger.info("🛑 Shutting down %s", settings.APP_NAME)
    await router_llm.close()
    await db.close()
    logger.info("✅ Shutdown complete")


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

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.add_middleware(RateLimitMiddleware)

app.include_router(router)
app.include_router(moat_router)

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/app", response_class=HTMLResponse)
async def frontend():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Unknown Verdict v41.0</h1><p>See <a href='/docs'>/docs</a></p>")


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404,
                        content={"error": "Not Found", "path": request.url.path,
                                 "available_endpoints": "/docs"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=7860, workers=1,
                log_level=settings.LOG_LEVEL.lower())