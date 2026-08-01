"""
Unknown Verdict v40.0 (Phase 2 - Production)
Main FastAPI Application with all middleware, auth, monitoring, and 36+ endpoints.

Production features:
  - JWT authentication & RBAC (admin, user, guest)
  - API key management
  - Rate limiting (per-endpoint)
  - Prometheus metrics (/metrics)
  - Redis caching with in-memory fallback
  - Gzip compression
  - Structured JSON logging
  - Request audit trail
  - Health checks for all services
  - Background monitoring
  - PostgreSQL + pgvector (with fallbacks)
"""
from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger as log

from .config import settings
from .core import core as uv_core
from .routes import router as api_router
from .auth_routes import router as auth_router
from .middleware import (
    RateLimitMiddleware, MetricsMiddleware, AuditMiddleware,
    setup_logging, cache, error_handler, get_cors_config,
)
from .monitoring import health_checker, background_monitor
from .db import init_db, close_db, pgvector_store
from .sarvam.client import sarvam_client

_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Setup logging
    setup_logging()

    log.info("=" * 60)
    log.info("🚀 Unknown Verdict v40.0 (Phase 2) - Initializing...")
    log.info("=" * 60)

    # Initialize core (agents, verifiers, judge, RAG, engines)
    uv_core.initialize()

    # Initialize database (optional - falls back gracefully)
    await init_db()

    # Initialize pgvector store
    await pgvector_store.init()

    # Connect to Redis cache
    await cache.connect()

    # Start background health monitor
    await background_monitor.start()

    log.info("=" * 60)
    log.info("🚀 Unknown Verdict v40.0 - Application Startup")
    log.info("=" * 60)
    log.info("📊 System Statistics:")
    log.info(f"   ├─ Python Version: 3.{os.sys.version_info.minor}.{os.sys.version_info.micro}")
    log.info(f"   ├─ FastAPI Version: {__import__('fastapi').__version__}")
    log.info(f"   ├─ API Docs: /docs")
    log.info(f"   ├─ ReDoc: /redoc")
    log.info(f"   ├─ Metrics: /metrics")
    log.info(f"   ├─ Health: /health")
    log.info(f"   ├─ Agents: {uv_core.agents.stats()['total_agents']}")
    log.info(f"   ├─ Verifiers: {uv_core.verifiers.stats()['total_verifiers']}")
    log.info(f"   ├─ Endpoints: 36")
    log.info(f"   ├─ Auth: JWT + API Keys")
    log.info(f"   ├─ Database: {'connected' if settings.is_database_configured else 'fallback (in-memory)'}")
    log.info(f"   ├─ Cache: {'Redis' if cache.is_connected else 'in-memory'}")
    log.info(f"   ├─ Sarvam: {'configured' if settings.is_sarvam_configured else 'not configured (fallback)'}")
    log.info(f"   └─ Status: 🟢 ONLINE")
    log.info("=" * 60)
    log.info("🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE")
    log.info("⚖️ THE ADVOCACY – Global Law Firm")
    log.info("=" * 60)

    yield

    # Shutdown
    log.info("Unknown Verdict v40.0 - Shutting down...")
    await background_monitor.stop()
    await cache.close()
    await sarvam_client.close()
    await close_db()
    log.info("Unknown Verdict v40.0 - Shutdown complete.")


# Create FastAPI app
app = FastAPI(
    title="Unknown Verdict",
    description=(
        "Production Legal AI Platform powered by Sarvam AI.\n\n"
        "**Phase 2 Production Features:**\n"
        "- JWT Authentication & RBAC (admin, user, guest)\n"
        "- API Key Management\n"
        "- Rate Limiting (per-endpoint)\n"
        "- Prometheus Metrics (/metrics)\n"
        "- Redis Caching (in-memory fallback)\n"
        "- Gzip Compression\n"
        "- Structured JSON Logging\n"
        "- Health Checks & Background Monitoring\n"
        "- PostgreSQL + pgvector (with fallbacks)\n\n"
        "**36 API Endpoints** across 8 application groups.\n"
        "250 Legal Agents · 15 Verifiers · AI Judge · RAG"
    ),
    version="40.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ===== Middleware (order matters: outermost first) =====

# Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=settings.GZIP_MIN_SIZE)

# CORS
app.add_middleware(
    CORSMiddleware,
    **get_cors_config(),
)

# Request audit logging
app.add_middleware(AuditMiddleware)

# Prometheus metrics collection
app.add_middleware(MetricsMiddleware)

# Rate limiting
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware, enabled=True)


# ===== Include Routers =====
app.include_router(auth_router, prefix="/api")     # /api/auth/*
app.include_router(api_router, prefix="/api")       # /api/* (36 endpoints)


# ===== Root and System Endpoints =====

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - serve dashboard."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {
        "name": "Unknown Verdict", "version": "40.0",
        "status": "🟢 ONLINE", "endpoints": 36,
        "docs": "/docs", "redoc": "/redoc", "metrics": "/metrics",
    }


@app.get("/health", tags=["System"])
async def health():
    """Comprehensive health check for all services."""
    report = await health_checker.check_all()
    return report


@app.get("/metrics", tags=["System"])
async def metrics():
    """Prometheus metrics endpoint."""
    if not settings.METRICS_ENABLED:
        return JSONResponse(content={"error": "Metrics disabled"})
    metrics_text = health_checker.get_metrics()
    return PlainTextResponse(content=metrics_text, media_type="text/plain")


@app.get("/metrics/json", tags=["System"])
async def metrics_json():
    """Metrics in JSON format for dashboards."""
    return health_checker.get_metrics_snapshot()


@app.get("/api/info", tags=["System"])
async def api_info():
    """API information endpoint."""
    return {
        "name": "Unknown Verdict",
        "version": "40.0",
        "phase": "2 - Production",
        "environment": settings.ENVIRONMENT,
        "sarvam_configured": settings.is_sarvam_configured,
        "database_configured": settings.is_database_configured,
        "redis_connected": cache.is_connected,
        "agents": uv_core.agents.stats(),
        "verifiers": uv_core.verifiers.stats(),
        "rag": uv_core.rag.stats(),
        "endpoints_total": 36,
        "features": {
            "jwt_auth": True,
            "api_keys": True,
            "rate_limiting": settings.RATE_LIMIT_ENABLED,
            "prometheus_metrics": settings.METRICS_ENABLED,
            "redis_cache": cache.is_connected,
            "gzip": True,
            "structured_logging": True,
            "health_checks": True,
            "background_monitor": True,
            "pgvector": pgvector_store.is_available,
        },
    }


# ===== Static files =====
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


# ===== Error handler =====
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return await error_handler.handle(request, exc)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "unknown_verdict.app:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
