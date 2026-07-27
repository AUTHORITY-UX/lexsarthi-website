# app.py - Unknown Verdict v40.0 Main Application
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ⚖️ THE ADVOCACY – Global Law Firm

import os
import sys
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s  | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
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
    """Serve index.html with Third Eye theme"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
            # Replace version placeholders
            html = html.replace("{{VERSION}}", "40.0")
            html = html.replace("{{YEAR}}", str(datetime.now().year))
            return HTMLResponse(html)
    else:
        # Fallback if index.html missing
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Unknown Verdict v40.0</title>
            <style>
                body {{
                    background: #0a0a1a;
                    color: #e0e0e0;
                    font-family: 'Segoe UI', sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    text-align: center;
                }}
                .container {{
                    max-width: 600px;
                    padding: 40px;
                }}
                .logo {{ font-size: 4em; }}
                h1 {{
                    background: linear-gradient(135deg, #6C3CE1, #4ECDC4);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }}
                .trident {{ color: #FFD700; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">⚖️</div>
                <h1>THE ADVOCACY</h1>
                <p>Global Law Firm</p>
                <p style="color: #4ECDC4;">v40.0 • Unknown Verdict</p>
                <p>✅ {len(_core.agents)} Agents • {len(_core.verifiers)} Verifiers • AI Judge Online</p>
                <p><a href="/docs" style="color: #6C3CE1;">📚 API Documentation</a></p>
                <div class="trident">🔱 TRIDENT – PERMANENT ASSET – NEVER REMOVE</div>
            </div>
        </body>
        </html>
        """)

# ─── STARTUP EVENT ──────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("🚀 Unknown Verdict v40.0 - Application Startup")
    logger.info("=" * 60)
    logger.info("📊 System Statistics:")
    logger.info(f"   ├─ Python Version: {sys.version.split()[0]}")
    logger.info(f"   ├─ FastAPI Version: 40.0")
    logger.info(f"   ├─ API Docs: /docs")
    logger.info(f"   ├─ Agents: {len(_core.agents)}")
    logger.info(f"   ├─ Verifiers: {len(_core.verifiers)}")
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
        "agents": len(_core.agents),
        "verifiers": len(_core.verifiers),
        "timestamp": datetime.now().isoformat()
    })

# ─── MAIN ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    # Hugging Face uses PORT 7860 by default
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)