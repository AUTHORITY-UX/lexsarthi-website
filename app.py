# ============================================
# APP.PY - Full Production Version
# ============================================

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from pathlib import Path

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-16s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("unknown_verdict")

# Create app
app = FastAPI(
    title="Unknown Verdict v12.1",
    description="Complete Legal AGI Platform",
    version="12.1"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
directories = ["static", "uploads", "temp", "blog", "data", "logs", "training_data"]
for d in directories:
    os.makedirs(d, exist_ok=True)
logger.info(f"📁 Created {len(directories)} directories")

# Import routes
import routes
app.include_router(routes.router)
logger.info("✅ Routes mounted")

# Mount static
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("✅ Static files mounted")

# Startup
@app.on_event("startup")
async def startup_event():
    """Initialize full system"""
    try:
        # Initialize database
        await routes.init_database()
        
        # Initialize engine
        from core import get_engine
        engine = get_engine()
        status = engine.get_status()
        logger.info(f"🚀 Unknown Verdict v12.1 - Full Production Ready")
        logger.info(f"   ├─ Agents: {status['agents']}")
        logger.info(f"   ├─ Verifiers: {status['verifiers']}")
        logger.info(f"   ├─ Knowledge Base: {status['knowledge_base']}")
        logger.info(f"   ├─ Languages: {status['languages']}")
        logger.info(f"   └─ Judge: {status['judge']}")
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")

# Run
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)