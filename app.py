# =============================================================================
# app.py - Main Entry Point
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# =============================================================================

import os
import sys
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from databases import Database
import asyncpg
import redis.asyncio as redis

# ─── CREATE REQUIRED DIRECTORIES ──────────────────────────────────
REQUIRED_DIRS = ['static', 'uploads', 'temp', 'blog', 'data', 'logs', 'training_data']

for directory in REQUIRED_DIRS:
    os.makedirs(directory, exist_ok=True)
    try:
        os.chmod(directory, 0o755)
    except:
        pass

print(f"📁 Created {len(REQUIRED_DIRS)} directories: {', '.join(REQUIRED_DIRS)}")

# ─── FORCE FRESH ENVIRONMENT READ ──────────────────────────────────
def get_database_url():
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    try:
        with open("/etc/secrets/DATABASE_URL", "r") as f:
            return f.read().strip()
    except:
        pass
    try:
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("DATABASE_URL="):
                    return line.split("=", 1)[1].strip()
    except:
        pass
    return None

DATABASE_URL = get_database_url()
REDIS_URL = os.environ.get("REDIS_URL")

print(f"🔍 DATABASE_URL: {'✅ FOUND' if DATABASE_URL else '❌ NOT FOUND'}")
if DATABASE_URL:
    print(f"🔍 DATABASE_URL starts with: {DATABASE_URL[:30]}...")

# ─── IMPORT ROUTES ──────────────────────────────────────────────────
import routes
from config import REDIS_URL as CONFIG_REDIS_URL
from models import metadata
from core import (
    DIVINE_AGENTS, VERIFIERS, embedding_model, 
    set_database, set_pg_pool, set_redis_pool, set_logger,
    EDGE_AI_AVAILABLE
)

# ─── LOGGING ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/app.log", mode='a') if os.path.exists("logs") else logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("unknown_verdict")

# ─── GLOBALS ──────────────────────────────────────────────────────────
pg_pool = None
redis_pool = None
database = None

# ─── SET CORE GLOBALS ───────────────────────────────────────────────
set_logger(logger)

# ─── LIFESPAN ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pg_pool, redis_pool, database
    
    logger.info("🚀 Unknown Verdict v12.1 - Initializing...")
    logger.info(f"📁 Directories: {', '.join(REQUIRED_DIRS)}")
    
    db_url = os.environ.get("DATABASE_URL") or get_database_url()
    logger.info(f"📡 DATABASE_URL: {'✅ SET' if db_url else '❌ NOT SET'}")
    
    # ─── CONNECT TO NEON DATABASE ──────────────────────────────────
    if db_url:
        try:
            database = Database(db_url, min_size=2, max_size=20)
            await database.connect()
            logger.info("✅ Database connected successfully (Neon PostgreSQL)")
            
            pg_pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10, command_timeout=30)
            logger.info("✅ PostgreSQL pool created (Neon)")
            
            set_database(database)
            set_pg_pool(pg_pool)
            routes.pg_pool = pg_pool
            routes.database = database
            
            await routes._create_tables()
            await routes._ensure_test_user()
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            database = None
            pg_pool = None
    else:
        logger.error("❌ No DATABASE_URL available!")
        database = None
        pg_pool = None
    
    # ─── CONNECT TO REDIS ──────────────────────────────────────────
    # ✅ MOVED INSIDE LIFESPAN - NOW CORRECT
    redis_url = REDIS_URL or CONFIG_REDIS_URL or os.environ.get("REDIS_URL")
    
    if redis_url:
        try:
            clean_url = redis_url.strip()
            
            # Handle Upstash / TLS Redis
            if "upstash" in clean_url or "render" in clean_url or "rediss" in clean_url:
                if clean_url.startswith("redis://") and not clean_url.startswith("rediss://"):
                    clean_url = clean_url.replace("redis://", "rediss://", 1)
            
            redis_pool = redis.from_url(
                clean_url,
                decode_responses=True,
                max_connections=10,
                socket_keepalive=True,
                socket_timeout=10,
                retry_on_timeout=True,
                retry_on_error=[ConnectionError, TimeoutError, OSError],
                health_check_interval=30
            )
            # ✅ Now inside async function - this works!
            await redis_pool.ping()
            logger.info("✅ Redis connected successfully")
            set_redis_pool(redis_pool)
            routes.redis_pool = redis_pool
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e} - Using in-memory fallback")
            redis_pool = None
    else:
        logger.warning("⚠️ REDIS_URL not set – using in-memory fallback")
        redis_pool = None
    
    routes.pg_pool = pg_pool
    routes.redis_pool = redis_pool
    routes.database = database
    
    logger.info(f"✅ Loaded {len(DIVINE_AGENTS)} specialist personas")
    logger.info(f"✅ Loaded {len(VERIFIERS)} verifiers including judge Shakti")
    logger.info(f"📡 Edge AI: {'✅ AVAILABLE' if EDGE_AI_AVAILABLE else '⚠️ SIMULATION'}")
    logger.info(f"🗄️  Database: {'✅ Neon PostgreSQL' if database else '❌ NOT CONNECTED'}")
    logger.info("👁️ Unknown Verdict Engine v12.1 – Complete Enterprise Edition Ready.")
    
    yield
    
    # ─── SHUTDOWN ──────────────────────────────────────────────────
    logger.info("🛑 Shutting down Unknown Verdict...")
    if database:
        await database.disconnect()
    if pg_pool:
        await pg_pool.close()
    if redis_pool:
        await redis_pool.close()
    logger.info("✅ Shutdown complete")

# ─── APP ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Unknown Verdict v12.1 - Enterprise Legal AI",
    description="⚖️ AI-Powered Legal Advisory with 250 Specialist Personas, 10 Verifiers, and Judge Shakti",
    version="12.1.0",
    lifespan=lifespan
)

# ─── MIDDLEWARE ──────────────────────────────────────────────────────
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─── REGISTER ROUTES ──────────────────────────────────────────────────
routes.register_routes(app)

# ─── STATIC FILES ─────────────────────────────────────────────────────
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
    logger.info("✅ Static files mounted from /static")

# ─── STARTUP BANNER ──────────────────────────────────────────────────
@app.on_event("startup")
async def startup_banner():
    edge_status = "✅ AVAILABLE" if EDGE_AI_AVAILABLE else "⚠️ SIMULATION"
    db_status = "✅ Neon PostgreSQL" if DATABASE_URL else "❌ Not Configured"
    redis_status = "✅ Connected" if redis_pool else "⚠️ Disabled (in-memory)"
    
    banner = f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║    🏛️  UNKNOWN VERDICT v12.1 - Enterprise Legal AI                     ║
║    ⚖️  {len(DIVINE_AGENTS)} Specialist Personas | {len(VERIFIERS)} Verifiers + Judge Shakti      ║
║    🗄️  Database: {db_status}                                             ║
║    📡  Redis: {redis_status}                                             ║
║    📡  Edge AI: {edge_status}                                            ║
║    📁  static, uploads, temp, blog, data, logs, training_data           ║
║    🚀  Server: http://0.0.0.0:7860                                      ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """
    print("\033[96m" + banner + "\033[0m")

# ─── MAIN ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, workers=1, log_level="info", access_log=True, timeout_keep_alive=30)