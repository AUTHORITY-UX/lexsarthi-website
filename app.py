# ============================================
# APP.PY - UNKNOWN VERDICT v20.0
# ============================================

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-16s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("unknown_verdict")

app = FastAPI(
    title="Unknown Verdict v20.0",
    description="Complete Autonomous AGI Legal Platform",
    version="20.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
for d in ["static", "uploads", "temp", "blog", "data", "logs", "training_data", "contracts", "slp_drafts", "due_diligence", "legal_docs", "cache"]:
    os.makedirs(d, exist_ok=True)

# Check environment
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    logger.info(f"🔍 DATABASE_URL: ✅ FOUND")
else:
    logger.warning("🔍 DATABASE_URL: ❌ NOT FOUND")

# Import routes
try:
    import routes
    app.include_router(routes.router)
    logger.info("✅ Routes imported and mounted successfully")
except Exception as e:
    logger.error(f"❌ Error mounting routes: {e}")
    sys.exit(1)

# Static files
STATIC_DIR = Path("static")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    logger.info("✅ Static files mounted from /static")
    if (STATIC_DIR / "index.html").exists():
        logger.info("✅ index.html found in static directory")
else:
    logger.warning("⚠️ Static directory not found")

# ============================================
# STARTUP EVENT
# ============================================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Unknown Verdict v20.0 - Initializing...")
    
    try:
        if hasattr(routes, 'init_database'):
            logger.info("📡 Initializing database...")
            await routes.init_database()
        
        try:
            from core import get_engine
            engine = get_engine()
            if hasattr(engine, 'get_status'):
                status = engine.get_status()
                logger.info("✅ AGI Engine initialized successfully")
                logger.info(f"   ├─ Version: {status.get('version', '20.0')}")
                logger.info(f"   ├─ Agents: {status.get('agents', 0)}")
                logger.info(f"   ├─ Verifiers: {status.get('verifiers', 0)}")
                logger.info(f"   ├─ Knowledge Base: {status.get('knowledge_base', 0)} topics")
                logger.info(f"   └─ Judge: {status.get('judge', 'AI Judge v20.0')}")
        except Exception as e:
            logger.warning(f"⚠️ Engine initialization: {e}")
        
        logger.info("=" * 60)
        logger.info("🚀 Unknown Verdict v20.0 - Complete AGI System Ready")
        logger.info("=" * 60)
        logger.info(f"📊 System Statistics:")
        logger.info(f"   ├─ Python Version: {sys.version.split()[0]}")
        logger.info(f"   ├─ FastAPI Version: {app.version}")
        logger.info(f"   ├─ API Docs: /api/docs")
        logger.info(f"   └─ Status: 🟢 ONLINE")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Unknown Verdict v20.0 - Shutting down...")
    logger.info("✅ Shutdown complete")

# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
async def root():
    try:
        if (Path("static/index.html")).exists():
            return FileResponse("static/index.html")
        return {"message": "🚀 Unknown Verdict v20.0", "version": "20.0", "status": "running"}
    except:
        return {"message": "🚀 Unknown Verdict v20.0"}

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "20.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/status")
async def system_status():
    try:
        from core import get_engine
        engine = get_engine()
        return engine.get_status()
    except Exception as e:
        return {"status": "online", "version": "20.0", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)