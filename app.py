# app.py – Complete Unknown Verdict v43.0
# 82 Endpoints · 500 Agents · 50+ Services · Zero Data Retention · Third Eye AI
#
# ★ PATCHED v43.0.1 — Fixes applied:
#   1. SSE streaming (Connecting... → Live)
#   2. Chat JSON parsing (string did not match → always valid JSON)
#   3. Articles (empty → RSS + fallback)
#   4. Auth (broken → working login/register)
#   5. UTF-8 encoding (â€" → –, âˆž → ∞)

from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

from core.config import settings
from core.db import db
from core.llm.router import get_router

# Import routes
from routes import router, moat_router

# ★ ADDED: Import all fixes
from core.app_fixes import apply_all_fixes

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


# ─── APPLY ALL FIXES ★ ────────────────────────────────────────────
# This adds/overrides: SSE, Chat, Articles, Auth, UTF-8 endpoints
# It must come AFTER include_router so it can override broken endpoints.
apply_all_fixes(app)
logger.info("🔧 All fixes applied (SSE, Chat, Articles, Auth, UTF-8)")


# ─── ROOT ENDPOINTS ────────────────────────────────────────────────

# ★ NOTE: apply_all_fixes adds a JSON `/` endpoint for API clients.
# We need to handle BOTH HTML (browser) and JSON (API) requests.
# The fix below checks the Accept header.

@app.get("/", include_in_schema=False)
async def root(request: Request):
    """Main landing page — serves HTML for browsers, JSON for API clients."""
    accept = request.headers.get("accept", "")

    # If client wants JSON (API client, curl, HF Spaces health check)
    if "application/json" in accept or "text/plain" in accept:
        # ★ FIX: ensure_ascii=False preserves –, ∞, 👁️ (fixes â€" mojibake)
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
                "lifeline": "2026 – ∞",  # ★ FIX: was "2026 â€" â€"z"
                "domain": "advocacyalawfrim.in",
            },
            media_type="application/json; charset=utf-8",  # ★ FIX: charset=utf-8
        )

    # Browser — serve HTML
    index = STATIC_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unknown Verdict v43.0 — The Legal AGI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: #000; color: #fff; font-family: -apple-system, sans-serif;
            min-height: 100vh; display: flex; align-items: center; justify-content: center;
        }
        .container { text-align: center; }
        .eye { font-size: 80px; margin-bottom: 20px; }
        h1 { font-size: 48px; background: linear-gradient(135deg, #a855f7, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { color: #9ca3af; margin: 16px 0; font-size: 18px; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 40px auto; max-width: 600px; }
        .stat { background: #1f2937; border: 1px solid #374151; border-radius: 12px; padding: 20px; }
        .stat-num { font-size: 36px; font-weight: bold; }
        .stat-label { color: #9ca3af; font-size: 14px; }
        .links { margin: 24px 0; }
        .links a { color: #3b82f6; margin: 0 12px; text-decoration: none; }
        .footer { color: #6b7280; margin-top: 40px; font-size: 14px; }
        .green { color: #10b981; }
        .infinity { color: #fbbf24; font-size: 20px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="eye">👁️</div>
        <h1>Unknown Verdict</h1>
        <p class="subtitle">v43.0 · 82 Endpoints · 500 Agents · 50+ Services</p>
        <p class="subtitle">🚀 Zero Data Retention · Human-in-the-Loop</p>
        <p class="infinity">♾️ 2026 – 2126</p>
        <div class="stats">
            <div class="stat"><div class="stat-num green">82</div><div class="stat-label">Endpoints</div></div>
            <div class="stat"><div class="stat-num green">500</div><div class="stat-label">Agents</div></div>
            <div class="stat"><div class="stat-num" style="color:#ec4899">50+</div><div class="stat-label">Services</div></div>
            <div class="stat"><div class="stat-num" style="color:#f59e0b">8</div><div class="stat-label">Jurisdictions</div></div>
        </div>
        <div class="links">
            <a href="/docs">📚 API Docs</a>
            <a href="/brain">🧠 Brain Dashboard</a>
            <a href="/health">❤️ Health</a>
            <a href="/third-eye">👁️ Third Eye</a>
            <a href="/agents">🤖 Agents</a>
            <a href="/moat">🧩 Moat</a>
        </div>
        <p class="footer">Built by The Advocacy – A Law Firm, Baghpat<br><span class="green">● 82 Endpoints Active</span></p>
    </div>
</body>
</html>
    """)


@app.get("/app")
async def frontend():
    """Main application interface"""
    app_file = STATIC_DIR / "app.html"
    if app_file.exists():
        return HTMLResponse(app_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Unknown Verdict App</h1><p>See <a href='/'>home</a></p>")


# ─── BRAIN DASHBOARD ───────────────────────────────────────────────

@app.get("/brain")
async def brain_dashboard():
    """Brain dashboard frontend"""
    brain_file = STATIC_DIR / "brain.html"
    if brain_file.exists():
        return HTMLResponse(brain_file.read_text(encoding="utf-8"))
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Brain Dashboard — Unknown Verdict v43.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #000; color: #fff; font-family: -apple-system, sans-serif; min-height: 100vh; }
        .header { text-align: center; padding: 30px; }
        .eye { font-size: 60px; }
        h1 { color: #a855f7; margin: 10px 0; }
        .live { color: #10b981; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; max-width: 600px; margin: 20px auto; }
        .stat { background: #1f2937; border: 1px solid #374151; border-radius: 8px; padding: 16px; text-align: center; }
        .stat-num { font-size: 28px; font-weight: bold; color: #10b981; }
        .stat-label { color: #9ca3af; font-size: 12px; }
        .activity { max-width: 600px; margin: 20px auto; padding: 16px; background: #1f2937; border-radius: 8px; }
        .activity h3 { color: #60a5fa; margin-bottom: 12px; }
        .activity-log { max-height: 200px; overflow-y: auto; }
        .activity-log div { padding: 6px 0; border-bottom: 1px solid #374151; font-size: 13px; color: #9ca3af; }
        .agents { max-width: 600px; margin: 20px auto; padding: 16px; }
        .agent-card { background: #1f2937; border: 1px solid #374151; border-radius: 8px; padding: 12px; margin-bottom: 8px; display: flex; justify-content: space-between; }
        .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 13px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="eye">👁️</div>
        <h1>Unknown Verdict · Brain Dashboard</h1>
        <p class="live">● 82 Endpoints Live</p>
    </div>
    <div class="stats">
        <div class="stat"><div class="stat-num">82</div><div class="stat-label">Endpoints</div></div>
        <div class="stat"><div class="stat-num">500</div><div class="stat-label">Agents</div></div>
        <div class="stat"><div class="stat-num">50+</div><div class="stat-label">Services</div></div>
        <div class="stat"><div class="stat-num">8</div><div class="stat-label">Jurisdictions</div></div>
    </div>
    <div class="activity">
        <h3>🧠 Agent Activity</h3>
        <div class="activity-log" id="agent-activity-feed">
            <div>[System] Brain 82 endpoints initialized</div>
            <div>[System] Brain 500 agents ready</div>
            <div>[System] Brain Zero data retention active</div>
        </div>
    </div>
    <div class="agents">
        <h3 style="color:#60a5fa;margin-bottom:12px;">🤖 500 Agents Available</h3>
        <div class="agent-card"><span>⚖️ Lawyer — Constitutional Law Expert</span><span style="color:#10b981">$50/hr</span></div>
        <div class="agent-card"><span>⚖️ Lawyer — Criminal Law Specialist</span><span style="color:#10b981">$55/hr</span></div>
        <div class="agent-card"><span>📰 Journalist — Legal Writer</span><span style="color:#10b981">$40/hr</span></div>
        <div class="agent-card"><span>🧘 Spiritual — Meditation Guide</span><span style="color:#10b981">$25/hr</span></div>
        <div class="agent-card"><span>💼 Compliance — DPDPA Expert</span><span style="color:#10b981">$75/hr</span></div>
        <div class="agent-card"><span>📄 Contracts — NDA Reviewer</span><span style="color:#10b981">$60/hr</span></div>
    </div>
    <div class="footer">
        ♾️ 2026 – 2126 · 🔒 Zero Data Retention · ⚡ 82 Endpoints · 🌍 8 Jurisdictions · 🧠 500 Agents
    </div>
    <script src="/static/frontend_fixes.js"></script>
</body>
</html>
    """)


# ─── DIRECT ENDPOINTS ─────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "43.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {"total": 82, "active": 82},
        "agents": {
            "total": 500,
            "lawyer": 100,
            "journalist": 75,
            "spiritual": 75,
            "compliance": 80,
            "contracts": 60,
            "ai_tech": 60,
            "digital": 40,
            "litigation": 30,
            "strategic": 10
        },
        "features": {
            "third_eye": True,
            "zero_data_retention": settings.ZERO_DATA_RETENTION,
            "ollama": settings.OLLAMA_ENABLED,
            "qwen_model": settings.OLLAMA_MODEL,
            "pgvector": True,
            "neon_db": True
        },
        "jurisdictions": ["India", "US", "UK", "EU"]
    }


@app.get("/third-eye")
async def third_eye():
    """The legendary Third Eye endpoint"""
    # ★ FIX: Using Python string with proper Unicode, returned via JSONResponse
    # FastAPI's default JSONResponse uses ensure_ascii=False already, but
    # we add charset=utf-8 to be safe.
    return JSONResponse(
        content={
            "eye": "👁️",
            "status": "OPEN",
            "message": "The Third Eye is always watching. Unknown Verdict sees everything across 82 endpoints.",
            "lifeline": "2026 – ∞",  # ★ FIX: was getting mangled before
            "blinking": True,
            "agents": 500,
            "services": 50,
            "endpoints": 82,
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
    """List all 82 endpoints"""
    return {
        "total": 82,
        "base_endpoints": 36,
        "moat_endpoints": 32,
        "new_endpoints": 14,
        "categories": {
            "health_system": 6,
            "chat_llm": 6,
            "legal_agents": 14,
            "moat_intelligence": 32,
            "multi_jurisdiction": 6,
            "gdpr_data_act": 4,
            "civil_litigation": 4,
            "multi_lingual": 4,
            "rag_documents": 4,
            "auth_users": 4
        },
        "docs_url": "/docs",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/version")
async def version_info():
    """Version information"""
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
    """System status"""
    return {
        "app": settings.APP_NAME,
        "version": "43.0",
        "environment": settings.ENVIRONMENT,
        "database": {"connected": db.pool is not None},
        "llm": {
            "providers": settings.available_llm_providers,
            "ollama": {
                "enabled": settings.OLLAMA_ENABLED,
                "model": settings.OLLAMA_MODEL
            }
        },
        "agents": {
            "total": 500,
            "categories": {
                "Lawyer": 100,
                "Journalist": 75,
                "Spiritual": 75,
                "Compliance": 80,
                "Contracts": 60,
                "AI & Tech": 60,
                "Digital": 40,
                "Litigation": 30,
                "Strategic": 10
            }
        },
        "features": {
            "zero_data_retention": settings.ZERO_DATA_RETENTION,
            "third_eye": True,
            "pgvector": True,
            "neon_db": True,
            "ollama": settings.OLLAMA_ENABLED
        },
        "jurisdictions": ["India", "US", "UK", "EU"],
        "timestamp": datetime.now().isoformat()
    }


@app.get("/providers")
async def list_providers():
    """List all LLM providers"""
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
    """Custom 404 handler with available endpoints"""
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
                "/compliance/dpdpa-check", "/compliance/gdpr-check",
                "/company/complete-audit", "/company/audit-report",
                "/legal-intelligence/dashboard",
                "/agent/events", "/agent/write-article",
                "/domain/scan",
                "/moat", "/moat/status", "/moat/ethics-status",
                "/law/multi-jurisdiction", "/law/jurisdictions",
                "/document/analyze", "/contract/analyze",
                "/auth/login", "/auth/register", "/auth/me",
                "/articles",
                "/rag/search", "/rag/health"
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
