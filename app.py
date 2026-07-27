# app.py - Main FastAPI Application for Hugging Face
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE

import logging
import sys
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s  | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("unknown_verdict")

# Import routes
from routes import router

# Import core
from core import get_core, UnknownVerdictCore

# Create FastAPI app
app = FastAPI(
    title="Unknown Verdict v40.0",
    description="Complete AGI Legal Platform - THE ADVOCACY",
    version="40.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router
app.include_router(router)

# Mount static files
static_dir = "static"
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"✅ Static files mounted from /{static_dir}")
else:
    os.makedirs(static_dir, exist_ok=True)
    logger.warning(f"⚠️ Static directory created: {static_dir}")

# Initialize core
_core = get_core()
logger.info("🚀 Unknown Verdict v40.0 - Initializing...")
logger.info(f"   ├─ Agents: {len(_core.agents)}")
logger.info(f"   ├─ Verifiers: {len(_core.verifiers)}")
logger.info(f"   └─ Judge: AI Judge v40.0")

# ─── ROOT ENDPOINT ──────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve index.html"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
            # Add version info
            html = html.replace("{{VERSION}}", "40.0")
            html = html.replace("{{YEAR}}", str(datetime.now().year))
            return HTMLResponse(html)
    else:
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head><title>Unknown Verdict v40.0</title></head>
        <body>
            <h1>⚖️ Unknown Verdict v40.0</h1>
            <h2>THE ADVOCACY – Global Law Firm</h2>
            <p>Status: ✅ Online</p>
            <p>Agents: {len(_core.agents)}</p>
            <p>Verifiers: {len(_core.verifiers)}</p>
            <p>Judge: AI Judge v40.0</p>
            <p><a href="/docs">📚 API Documentation</a></p>
            <p><a href="/static/index.html">📄 Static Index</a></p>
        </body>
        </html>
        """)

# ─── STARTUP EVENT ──────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("🚀 Unknown Verdict v40.0 - Application Startup")
    logger.info("=" * 60)
    logger.info(f"📊 System Statistics:")
    logger.info(f"   ├─ Python Version: {sys.version.split()[0]}")
    logger.info(f"   ├─ FastAPI Version: 40.0")
    logger.info(f"   ├─ API Docs: /docs")
    logger.info(f"   └─ Status: 🟢 ONLINE")
    logger.info("=" * 60)
    logger.info("🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE")
    logger.info("⚖️ THE ADVOCACY – Global Law Firm")
    logger.info("=" * 60)

# ─── HEALTH CHECK ──────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return JSONResponse({
        "status": "healthy",
        "version": "40.0",
        "timestamp": datetime.now().isoformat(),
        "agents": len(_core.agents),
        "verifiers": len(_core.verifiers)
    })

# ─── MAIN ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)