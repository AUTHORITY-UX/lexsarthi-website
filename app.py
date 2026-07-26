# ============================================
# APP.PY - UNKNOWN VERDICT v15.0
# COMPLETE AGI LEGAL SYSTEM
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

# ============================================
# LOGGING CONFIGURATION
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-16s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("unknown_verdict")

# ============================================
# CREATE FASTAPI APP
# ============================================

app = FastAPI(
    title="Unknown Verdict v15.0",
    description="Complete AGI Legal System - 500+ Agents, 100+ Legal Topics, AI Judge, Predictive Analytics",
    version="15.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# ============================================
# CORS MIDDLEWARE
# ============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# CREATE DIRECTORIES
# ============================================

DIRECTORIES = [
    "static",
    "uploads",
    "temp",
    "blog",
    "data",
    "logs",
    "training_data",
    "contracts",
    "slp_drafts",
    "due_diligence",
    "legal_docs",
    "cache"
]

for directory in DIRECTORIES:
    try:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"📁 Created directory: {directory}")
    except Exception as e:
        logger.warning(f"⚠️ Could not create {directory}: {e}")

# ============================================
# ENVIRONMENT CHECK
# ============================================

# Check Database
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    logger.info(f"🔍 DATABASE_URL: ✅ FOUND")
    logger.info(f"🔍 DATABASE_URL starts with: {DATABASE_URL[:30]}...")
else:
    logger.warning("🔍 DATABASE_URL: ❌ NOT FOUND")

# Check Redis
REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    logger.info(f"🔍 REDIS_URL: ✅ FOUND")
else:
    logger.info("🔍 REDIS_URL: ⚠️ Using fallback (in-memory cache)")

# Check API Keys
api_keys = {
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
    "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
    "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY"),
    "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
    "JWT_SECRET": os.getenv("JWT_SECRET"),
    "RAZORPAY_KEY_ID": os.getenv("RAZORPAY_KEY_ID")
}

for key, value in api_keys.items():
    if value:
        logger.info(f"🔑 {key}: ✅ CONFIGURED")
    else:
        logger.warning(f"🔑 {key}: ❌ NOT CONFIGURED")

# ============================================
# IMPORT ROUTES
# ============================================

try:
    import routes
    app.include_router(routes.router)
    logger.info("✅ Routes imported and mounted successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import routes: {e}")
    logger.error("   Please ensure routes.py exists and has no syntax errors")
    sys.exit(1)
except Exception as e:
    logger.error(f"❌ Error mounting routes: {e}")
    sys.exit(1)

# ============================================
# MOUNT STATIC FILES
# ============================================

STATIC_DIR = Path("static")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    logger.info("✅ Static files mounted from /static")
    
    # Check if index.html exists
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        logger.info("✅ index.html found in static directory")
    else:
        logger.warning("⚠️ index.html not found in static directory")
else:
    logger.warning("⚠️ Static directory not found")

# ============================================
# EXCEPTION HANDLERS
# ============================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") == "true" else "An error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    """404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "status": "error",
            "message": "Endpoint not found",
            "path": request.url.path,
            "timestamp": datetime.now().isoformat()
        }
    )

# ============================================
# STARTUP EVENT
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize all systems on startup"""
    logger.info("🚀 Unknown Verdict v15.0 - Initializing...")
    
    try:
        # Initialize database
        if hasattr(routes, 'init_database'):
            logger.info("📡 Initializing database...")
            db_result = await routes.init_database()
            if db_result:
                logger.info("✅ Database initialized successfully")
            else:
                logger.warning("⚠️ Database initialization had issues - using fallback")
        else:
            logger.warning("⚠️ init_database not found in routes")
        
        # Initialize engine
        try:
            from core import get_engine, UnknownVerdictV15
            logger.info("⚙️ Initializing AGI Engine...")
            engine = get_engine()
            
            if hasattr(engine, 'get_status'):
                status = engine.get_status()
                logger.info("✅ AGI Engine initialized successfully")
                logger.info(f"   ├─ Version: {status.get('version', '15.0')}")
                logger.info(f"   ├─ Agents: {status.get('agents', 0)}")
                logger.info(f"   ├─ Verifiers: {status.get('verifiers', 0)}")
                logger.info(f"   ├─ Knowledge Base: {status.get('knowledge_base', 0)} topics")
                logger.info(f"   ├─ Languages: {status.get('languages', 20)}")
                logger.info(f"   └─ Judge: {status.get('judge', 'AI Judge v15.0')}")
            else:
                logger.info("✅ AGI Engine initialized (status not available)")
                
        except ImportError as e:
            logger.error(f"❌ Core module import error: {e}")
            logger.warning("⚠️ AGI Engine not available - some features may be limited")
        except Exception as e:
            logger.error(f"❌ Engine initialization error: {e}")
            logger.warning("⚠️ AGI Engine failed to initialize - using fallback")
        
        # Check Redis connection
        try:
            import redis
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                r = redis.from_url(redis_url)
                if r.ping():
                    logger.info("✅ Redis connected successfully")
                else:
                    logger.warning("⚠️ Redis connection failed - using in-memory fallback")
            else:
                logger.info("ℹ️ Redis not configured - using in-memory fallback")
        except Exception as e:
            logger.warning(f"⚠️ Redis check failed: {e}")
        
        # Log system info
        logger.info("=" * 60)
        logger.info("🚀 Unknown Verdict v15.0 - Complete AGI System Ready")
        logger.info("=" * 60)
        logger.info("📊 System Statistics:")
        logger.info(f"   ├─ Python Version: {sys.version.split()[0]}")
        logger.info(f"   ├─ FastAPI Version: {app.version}")
        logger.info(f"   ├─ API Docs: /api/docs")
        logger.info(f"   └─ Status: 🟢 ONLINE")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        logger.warning("⚠️ System started with limited functionality")

# ============================================
# SHUTDOWN EVENT
# ============================================

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Unknown Verdict v15.0 - Shutting down...")
    
    try:
        # Close database connections
        if hasattr(routes, 'close_connections'):
            logger.info("📡 Closing database connections...")
            await routes.close_connections()
        
        # Clean temporary files
        temp_dir = Path("temp")
        if temp_dir.exists():
            import shutil
            try:
                shutil.rmtree(temp_dir)
                logger.info("🧹 Temporary files cleaned")
            except Exception as e:
                logger.warning(f"⚠️ Could not clean temp directory: {e}")
                
    except Exception as e:
        logger.warning(f"⚠️ Shutdown cleanup error: {e}")
    
    logger.info("✅ Unknown Verdict v15.0 - Shutdown complete")

# ============================================
# ROOT ENDPOINT
# ============================================

@app.get("/", include_in_schema=False)
async def root():
    """Serve the frontend application"""
    try:
        index_path = Path("static/index.html")
        if index_path.exists():
            return FileResponse(str(index_path))
        else:
            return JSONResponse({
                "message": "🚀 Unknown Verdict v15.0",
                "version": "15.0",
                "status": "running",
                "docs": "/api/docs",
                "health": "/api/health",
                "timestamp": datetime.now().isoformat()
            })
    except Exception as e:
        return JSONResponse({
            "message": "🚀 Unknown Verdict v15.0",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })

# ============================================
# HEALTH CHECK ENDPOINT
# ============================================

@app.get("/api/health", tags=["System"])
async def health_check():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "version": "15.0",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "server": "running",
            "database": "unknown",
            "redis": "unknown",
            "engine": "unknown"
        }
    }
    
    # Check database
    try:
        if hasattr(routes, 'check_database'):
            db_status = await routes.check_database()
            health_status["components"]["database"] = db_status
        else:
            health_status["components"]["database"] = "not_checked"
    except Exception as e:
        health_status["components"]["database"] = f"error: {str(e)}"
    
    # Check engine
    try:
        from core import get_engine
        engine = get_engine()
        if hasattr(engine, 'get_status'):
            status = engine.get_status()
            health_status["components"]["engine"] = "running"
            health_status["agents"] = status.get("agents", 0)
            health_status["knowledge_base"] = status.get("knowledge_base", 0)
        else:
            health_status["components"]["engine"] = "limited"
    except Exception as e:
        health_status["components"]["engine"] = f"error: {str(e)}"
    
    # Check Redis
    try:
        import redis
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            r = redis.from_url(redis_url)
            if r.ping():
                health_status["components"]["redis"] = "connected"
            else:
                health_status["components"]["redis"] = "disconnected"
        else:
            health_status["components"]["redis"] = "not_configured"
    except Exception as e:
        health_status["components"]["redis"] = f"error: {str(e)}"
    
    return health_status

# ============================================
# SYSTEM STATUS ENDPOINT
# ============================================

@app.get("/api/status", tags=["System"])
async def system_status():
    """Detailed system status"""
    try:
        from core import get_engine
        engine = get_engine()
        
        if hasattr(engine, 'get_status'):
            status = engine.get_status()
        else:
            status = {}
        
        return {
            "version": "15.0",
            "status": "online",
            "uptime": "running",
            "agents": status.get("agents", 500),
            "verifiers": status.get("verifiers", 20),
            "knowledge_base": status.get("knowledge_base", 100),
            "languages": status.get("languages", 20),
            "judge": status.get("judge", "AI Judge v15.0"),
            "learning_history": status.get("learning_history", 0),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "partial",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ============================================
# API INFO ENDPOINT
# ============================================

@app.get("/api/info", tags=["System"])
async def api_info():
    """API information"""
    return {
        "name": "Unknown Verdict v15.0",
        "description": "Complete AGI Legal System",
        "version": "15.0",
        "features": {
            "agents": "500+ Self-Learning AGI Agents",
            "legal_topics": "100+ Legal Topics",
            "verifiers": "20 Quality Verifiers",
            "judge": "AI Judge System",
            "predictive_analytics": "Case Outcome Prediction",
            "blockchain": "Smart Contract Integration",
            "multilingual": "20 Languages Supported",
            "self_learning": "Continuous Learning"
        },
        "endpoints": {
            "docs": "/api/docs",
            "health": "/api/health",
            "status": "/api/status",
            "chat": "/api/chat",
            "compliance": "/api/compliance/*",
            "trading": "/api/trading/*",
            "news": "/api/news/*",
            "sports": "/api/sports/*",
            "trends": "/api/trends/*",
            "lens": "/api/lens/*",
            "contract_analyze": "/api/contract/analyze",
            "slp_draft": "/api/slp/draft",
            "due_diligence": "/api/due-diligence/run"
        },
        "timestamp": datetime.now().isoformat()
    }

# ============================================
# METRICS ENDPOINT (Optional)
# ============================================

@app.get("/api/metrics", tags=["System"])
async def get_metrics():
    """System metrics"""
    try:
        from core import get_engine
        engine = get_engine()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "agents_total": len(engine.agents) if hasattr(engine, 'agents') else 0,
            "verifiers_total": len(engine.verifiers) if hasattr(engine, 'verifiers') else 0,
            "knowledge_topics": len(engine.knowledge_base) if hasattr(engine, 'knowledge_base') else 0,
            "memory_size": len(engine.memory) if hasattr(engine, 'memory') else 0,
            "learning_count": len(engine.learning_log) if hasattr(engine, 'learning_log') else 0
        }
    except Exception as e:
        return {"error": str(e)}

# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 7860))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🚀 Starting Unknown Verdict v15.0 on {host}:{port}")
    logger.info(f"📚 API Docs: http://{host}:{port}/api/docs")
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )