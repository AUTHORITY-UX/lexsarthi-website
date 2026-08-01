"""
Unknown Verdict v40.0 - Main FastAPI Application
Production Legal AI Platform powered by Sarvam AI.

36 API Endpoints · 250 Agents · 15 Verifiers · AI Judge · RAG
"""
from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger as log

from .config import settings
from .core import core as uv_core
from .routes import router

_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    log.info("=" * 60)
    log.info("🚀 Unknown Verdict v40.0 - Initializing...")
    log.info("=" * 60)

    uv_core.initialize()

    log.info("=" * 60)
    log.info("🚀 Unknown Verdict v40.0 - Application Startup")
    log.info("=" * 60)
    log.info("📊 System Statistics:")
    log.info(f"   ├─ Python Version: 3.{os.sys.version_info.minor}.{os.sys.version_info.micro}")
    log.info(f"   ├─ FastAPI Version: {__import__('fastapi').__version__}")
    log.info(f"   ├─ API Docs: /docs")
    log.info(f"   ├─ ReDoc: /redoc")
    log.info(f"   ├─ Agents: {uv_core.agents.stats()['total_agents']}")
    log.info(f"   ├─ Verifiers: {uv_core.verifiers.stats()['total_verifiers']}")
    log.info(f"   ├─ Endpoints: 36")
    log.info(f"   └─ Status: 🟢 ONLINE")
    log.info("=" * 60)
    log.info("🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE")
    log.info("⚖️ THE ADVOCACY – Global Law Firm")
    log.info("=" * 60)

    yield

    log.info("Unknown Verdict v40.0 - Shutting down...")
    from .sarvam.client import sarvam_client
    await sarvam_client.close()
    log.info("Unknown Verdict v40.0 - Shutdown complete.")


app = FastAPI(
    title="Unknown Verdict",
    description=(
        "Production Legal AI Platform powered by Sarvam AI.\n\n"
        "**36 API Endpoints** across 8 application groups:\n"
        "1. Core Legal (8) - chat, research, draft, cases, manage, compliance\n"
        "2. Markets & Trading (4) - indices, crypto, stocks, global\n"
        "3. Reports & News (4) - generate, pdf, news, personalized\n"
        "4. Sports & Governance (4) - cricket, player, framework, policy\n"
        "5. Predictive AI (4) - case, market, risk, training\n"
        "6. Privacy & Security (4) - dsar, drop, alerts, scan\n"
        "7. Finance/HR/RE/Intl (4) - stocks, hr, properties, treaties\n"
        "8. Additional Core (4) - health, docs, lens, infinity\n\n"
        "250 Legal Agents · 15 Verifiers · AI Judge · RAG"
    ),
    version="40.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all 36 endpoints under /api prefix
app.include_router(router, prefix="/api")


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
        "docs": "/docs", "redoc": "/redoc",
    }


@app.get("/health", tags=["System"])
async def health():
    """Health check."""
    uptime = time.time() - _start_time
    return {
        "status": "healthy", "version": "40.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(uptime, 2),
        "components": {
            "agents": "operational", "verifiers": "operational",
            "judge": "operational", "rag": "operational",
            "sarvam": "operational" if settings.is_sarvam_configured else "not_configured",
            "infinity": "ENABLED",
        },
    }


# ===== Static files =====
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")
    log.info("✅ Static files mounted from /static")


# ===== Error handler =====
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc), "code": "INTERNAL_ERROR"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "unknown_verdict.app:app",
        host=settings.HOST, port=settings.PORT,
        reload=settings.DEBUG, log_level=settings.LOG_LEVEL.lower(),
    )
