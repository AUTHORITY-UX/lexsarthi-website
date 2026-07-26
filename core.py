# ============================================
# APP.PY - Main FastAPI Application
# ============================================

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-16s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("unknown_verdict")

# Create app
app = FastAPI(title="Unknown Verdict v12.1", version="12.1")

# CORS middleware
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
logger.info(f"📁 Created {len(directories)} directories: {', '.join(directories)}")

# Check DATABASE_URL
if os.getenv("DATABASE_URL"):
    logger.info("🔍 DATABASE_URL: ✅ FOUND")
    db_url = os.getenv("DATABASE_URL")
    logger.info(f"🔍 DATABASE_URL starts with: {db_url[:30]}...")
else:
    logger.warning("🔍 DATABASE_URL: ❌ NOT FOUND")

# ============================================
# IMPORT ROUTES
# ============================================

try:
    import routes
    app.include_router(routes.router)
    logger.info("✅ Routes imported and mounted")
except Exception as e:
    logger.error(f"❌ Failed to import routes: {e}")

# ============================================
# MOUNT STATIC FILES
# ============================================

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("✅ Static files mounted from /static")
else:
    logger.warning("⚠️ Static directory not found")

# ============================================
# STARTUP EVENT
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize all systems on startup"""
    try:
        from core import init_unknown_verdict
        await init_unknown_verdict()
        
        # Initialize database (if routes has the function)
        if hasattr(routes, 'init_database'):
            logger.info("📡 Initializing database...")
            await routes.init_database()
            
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")

# ============================================
# ROOT ENDPOINT (Fallback)
# ============================================

@app.get("/")
async def root():
    """Root endpoint - serves index.html if available"""
    try:
        from fastapi.responses import FileResponse
        if os.path.exists("static/index.html"):
            return FileResponse("static/index.html")
        return {
            "message": "Unknown Verdict v12.1",
            "status": "running",
            "docs": "/docs"
        }
    except:
        return {"message": "Unknown Verdict v12.1", "status": "running"}

# ============================================
# RUN (if executed directly)
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)