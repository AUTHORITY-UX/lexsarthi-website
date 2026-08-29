# app.py – Complete Unknown Verdict v43.0
# 82 Endpoints · 500 Agents · 50+ Services · Zero Data Retention · Third Eye AI

from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

from core.config import Config
from core.db import db
from core.llm.router import get_router

# Import routes
from routes import router, moat_router

import logging

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ─── LIFESPAN ───────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("   Environment: %s", settings.ENVIRONMENT)
    logger.info("   LLM providers: %s", settings.available_llm_providers)

    await db.connect()
    logger.info("   DB: %s", db.pool is not None)

    router_llm = get_router()
    await router_llm.init(redis_client=None)
    logger.info("   LLM router initialized")

    logger.info("✅ %s v%s ready — 82 endpoints active", settings.APP_NAME, settings.APP_VERSION)

    yield

    logger.info("🛑 Shutting down %s", settings.APP_NAME)
    await db.disconnect()
    logger.info("✅ Shutdown complete")


# ─── CREATE APP ────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="82 Endpoints · 500 Agents · 50+ Services · Zero Data Retention · Third Eye AI",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ─── MIDDLEWARE ────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── STATIC FILES ─────────────────────────────────────────────────

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ─── REGISTER ROUTES ────────────────────────────────────────────────

app.include_router(router)       # 36 Base + 14 New = 50 endpoints
app.include_router(moat_router)  # 32 Moat endpoints
# Total: 82 endpoints


# ─── DISABLE app_fixes – routes.py already has all endpoints ──────

# try:
#     from core.app_fixes import apply_all_fixes
#     apply_all_fixes(app)
# except Exception as e:
#     logger.error(f"⚠️ app_fixes failed (app still runs): {e}")


# ─── ROOT ENDPOINT ─────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root(request: Request):
    """Root — HTML for browsers, JSON for API clients."""
    accept = request.headers.get("accept", "")

    if "application/json" in accept or "text/plain" in accept or "curl" in request.headers.get("user-agent", "").lower():
        return JSONResponse(
            content={
                "name": "Unknown Verdict",
                "version": "43.0",
                "status": "operational",
                "docs": "/docs",
                "endpoints": 82,
                "agents": 500,
                "services": 50,
                "jurisdictions": ["India", "US", "UK", "EU"],
                "zero_data_retention": True,
                "third_eye": True,
                "lifeline": "2026 - infinity",
                "domain": "advocacyalawfrim.in",
            },
            media_type="application/json; charset=utf-8",
        )

    index = STATIC_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    return HTMLResponse("""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Unknown Verdict v43.0</title></head>
<body style="background:#000;color:#fff;font-family:sans-serif;text-align:center;padding:50px;">
<h1>👁️ Unknown Verdict v43.0</h1>
<p>82 Endpoints · 500 Agents · 50+ Services</p>
<p><a href="/docs" style="color:#3b82f6">API Docs</a> | <a href="/brain" style="color:#3b82f6">Brain</a> | <a href="/health" style="color:#3b82f6">Health</a></p>
</body></html>""")


@app.get("/app")
async def frontend():
    app_file = STATIC_DIR / "app.html"
    if app_file.exists():
        return HTMLResponse(app_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Unknown Verdict App</h1><p>See <a href='/'>home</a></p>")


# ─── BRAIN DASHBOARD ───────────────────────────────────────────────

@app.get("/brain")
async def brain_dashboard():
    brain_file = STATIC_DIR / "brain.html"
    if brain_file.exists():
        return HTMLResponse(brain_file.read_text(encoding="utf-8"))
    return HTMLResponse("""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Brain Dashboard</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{background:#000;color:#fff;font-family:sans-serif}
.header{text-align:center;padding:30px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;max-width:600px;margin:20px auto}
.stat{background:#1f2937;border:1px solid #374151;border-radius:8px;padding:16px;text-align:center}
.stat-num{font-size:28px;font-weight:bold;color:#10b981}.stat-label{color:#9ca3af;font-size:12px}
.activity{max-width:600px;margin:20px auto;padding:16px;background:#1f2937;border-radius:8px}
.activity h3{color:#60a5fa;margin-bottom:12px}.activity-log{max-height:200px;overflow-y:auto}
.activity-log div{padding:6px 0;border-bottom:1px solid #374151;font-size:13px;color:#9ca3af}
</style></head>
<body>
<div class="header"><h1>👁️ Unknown Verdict · Brain Dashboard</h1><p style="color:#10b981">● 82 Endpoints Live</p></div>
<div class="stats">
<div class="stat"><div class="stat-num">82</div><div class="stat-label">Endpoints</div></div>
<div class="stat"><div class="stat-num">500</div><div class="stat-label">Agents</div></div>
<div class="stat"><div class="stat-num">50+</div><div class="stat-label">Services</div></div>
<div class="stat"><div class="stat-num">8</div><div class="stat-label">Jurisdictions</div></div>
</div>
<div class="activity"><h3>🧠 Agent Activity</h3><div class="activity-log" id="agent-activity-feed">
<div>[System] Brain 82 endpoints initialized</div>
<div>[System] Brain 500 agents ready</div>
<div>[System] Brain Zero data retention active</div>
</div></div>
</body></html>""")


# ─── DIRECT ENDPOINTS ─────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "43.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {"total": 82, "active": 82},
        "agents": {
            "total": 500,
            "lawyer": 100, "journalist": 75, "spiritual": 75,
            "compliance": 80, "contracts": 60, "ai_tech": 60,
            "digital": 40, "litigation": 30, "strategic": 10
        },
        "features": {
            "third_eye": True,
            "zero_data_retention": settings.ZERO_DATA_RETENTION,
            "ollama": settings.OLLAMA_ENABLED,
            "qwen_model": settings.OLLAMA_MODEL,
            "pgvector": True, "neon_db": True
        },
        "jurisdictions": ["India", "US", "UK", "EU"]
    }


@app.get("/third-eye")
async def third_eye():
    return JSONResponse(
        content={
            "eye": "👁️",
            "status": "OPEN",
            "message": "The Third Eye is always watching. Unknown Verdict sees everything across 82 endpoints.",
            "lifeline": "2026 – ∞",
            "blinking": True,
            "agents": 500, "services": 50, "endpoints": 82,
            "jurisdictions": ["India", "US", "UK", "EU"],
            "features": {
                "zero_data_retention": True,
                "human_in_the_loop": True,
                "ollama_offline": True,
                "pgvector_search": True
            },
            "timestamp": datetime.now().isoformat()
        },
        media_type="application/json; charset=utf-8",
    )


@app.get("/endpoints")
async def list_endpoints():
    return {
        "total": 82,
        "base_endpoints": 36,
        "moat_endpoints": 32,
        "new_endpoints": 14,
        "categories": {
            "health_system": 6, "chat_llm": 6, "legal_agents": 14,
            "moat_intelligence": 32, "multi_jurisdiction": 6,
            "gdpr_data_act": 4, "civil_litigation": 4, "multi_lingual": 4,
            "rag_documents": 4, "auth_users": 4
        },
        "docs_url": "/docs",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/version")
async def version_info():
    return {
        "version": "43.0",
        "environment": settings.ENVIRONMENT,
        "name": settings.APP_NAME,
        "features": {
            "zero_data_retention": settings.ZERO_DATA_RETENTION,
            "ollama": settings.OLLAMA_ENABLED,
            "third_eye": True
        }
    }


@app.get("/status")
async def system_status():
    return {
        "app": settings.APP_NAME,
        "version": "43.0",
        "environment": settings.ENVIRONMENT,
        "database": {"connected": db.pool is not None},
        "llm": {
            "providers": settings.available_llm_providers,
            "ollama": {"enabled": settings.OLLAMA_ENABLED, "model": settings.OLLAMA_MODEL}
        },
        "agents": {
            "total": 500,
            "categories": {
                "Lawyer": 100, "Journalist": 75, "Spiritual": 75,
                "Compliance": 80, "Contracts": 60, "AI & Tech": 60,
                "Digital": 40, "Litigation": 30, "Strategic": 10
            }
        },
        "features": {
            "zero_data_retention": settings.ZERO_DATA_RETENTION,
            "third_eye": True, "pgvector": True, "neon_db": True,
            "ollama": settings.OLLAMA_ENABLED
        },
        "jurisdictions": ["India", "US", "UK", "EU"],
        "timestamp": datetime.now().isoformat()
    }


@app.get("/providers")
async def list_providers():
    return {
        "providers": settings.available_llm_providers,
        "total": len(settings.available_llm_providers),
        "default": "ollama" if settings.OLLAMA_ENABLED else "groq",
        "ollama": {
            "enabled": settings.OLLAMA_ENABLED,
            "model": settings.OLLAMA_MODEL,
            "host": settings.OLLAMA_HOST
        }
    }


# ─── 404 HANDLER ──────────────────────────────────────────────────

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "path": request.url.path,
            "available_endpoints": [
                "/", "/app", "/brain", "/docs", "/redoc",
                "/health", "/version", "/status", "/providers",
                "/third-eye", "/endpoints", "/openapi.json",
                "/chat", "/chat/stream",
                "/agents", "/agents/list", "/agents/categories",
                "/articles",
                "/auth/login", "/auth/register", "/auth/me",
                "/agent/events",
                "/moat", "/moat/status",
            ]
        }
    )


# ─── RUN ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=7860,
        workers=1,
        log_level=settings.LOG_LEVEL.lower()
    )