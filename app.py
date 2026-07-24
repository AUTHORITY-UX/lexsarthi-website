# =============================================================================
# app.py - Main Entry Point
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# =============================================================================

import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from databases import Database
import asyncpg
import redis.asyncio as redis

# ─── FORCE ENVIRONMENT VARIABLE ──────────────────────────────────────
# This ensures DATABASE_URL is available everywhere
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # Try to read from a file if secrets aren't working
    try:
        with open("/etc/secrets/DATABASE_URL", "r") as f:
            DATABASE_URL = f.read().strip()
            os.environ["DATABASE_URL"] = DATABASE_URL
    except:
        pass

# ─── DEBUG ─────────────────────────────────────────────────────────────
print(f"🔍 DATABASE_URL: {'✅ FOUND' if DATABASE_URL else '❌ NOT FOUND'}")
print(f"🔍 DATABASE_URL value: {DATABASE_URL[:30]}...") if DATABASE_URL else None

# ─── IMPORT ROUTES ──────────────────────────────────────────────────
import routes
from config import REDIS_URL
from models import metadata
from core import DIVINE_AGENTS, VERIFIERS, embedding_model, set_database, set_pg_pool, set_redis_pool, set_logger

# ─── LOGGING ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("unknown_verdict")

# ─── GLOBALS ──────────────────────────────────────────────────────────
pg_pool = None
redis_pool = None
database = Database(DATABASE_URL) if DATABASE_URL else None

# ─── SET CORE GLOBALS ───────────────────────────────────────────────
set_logger(logger)

# ─── LIFESPAN ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pg_pool, redis_pool, database
    
    logger.info("🚀 Unknown Verdict v12.1 - Initializing...")
    logger.info(f"📡 DATABASE_URL: {'✅ SET' if DATABASE_URL else '❌ NOT SET'}")
    
    if database:
        try:
            await database.connect()
            logger.info("✅ Database connected successfully (Neon PostgreSQL)")
            await routes._create_tables()
            await routes._ensure_test_user()
            set_database(database)
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
    
    if DATABASE_URL:
        try:
            pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
            logger.info("✅ PostgreSQL pool created (Neon)")
            set_pg_pool(pg_pool)
        except Exception as e:
            logger.error(f"❌ PostgreSQL pool creation failed: {e}")
    
    if REDIS_URL:
        try:
            redis_pool = redis.from_url(REDIS_URL, decode_responses=True, max_connections=10)
            await redis_pool.ping()
            logger.info("✅ Redis connected successfully")
            set_redis_pool(redis_pool)
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            redis_pool = None
    else:
        logger.warning("⚠️ REDIS_URL not set – caching disabled")
    
    # Set globals for routes
    routes.pg_pool = pg_pool
    routes.redis_pool = redis_pool
    routes.database = database
    
    logger.info(f"✅ Loaded {len(DIVINE_AGENTS)} specialist personas")
    logger.info(f"✅ Loaded {len(VERIFIERS)} verifiers including judge Shakti")
    
    db_status = "✅ Neon PostgreSQL" if DATABASE_URL else "❌ NOT CONNECTED"
    logger.info(f"🗄️  Database: {db_status}")
    logger.info("👁️ Unknown Verdict Engine v12.1 – Complete Enterprise Edition Ready.")
    
    yield
    
    if database:
        await database.disconnect()
    if pg_pool:
        await pg_pool.close()
    if redis_pool:
        await redis_pool.close()

# ─── APP ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Unknown Verdict v12.1 - Enterprise Legal AI",
    description="⚖️ AI-Powered Legal Advisory with 250 Specialist Personas, 10 Verifiers, and Judge Shakti",
    version="12.1.0",
    lifespan=lifespan
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─── REGISTER ROUTES ──────────────────────────────────────────────────
routes.register_routes(app)

# ─── STATIC FILES ─────────────────────────────────────────────────────
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

# ─── STARTUP BANNER ──────────────────────────────────────────────────
@app.on_event("startup")
async def startup_banner():
    banner = f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║    🏛️  UNKNOWN VERDICT v12.1 - Enterprise Legal AI                     ║
║    ⚖️  {len(DIVINE_AGENTS)} Specialist Personas | {len(VERIFIERS)} Verifiers + Judge Shakti      ║
║    🗄️  Database: {'✅ Neon PostgreSQL' if DATABASE_URL else '❌ Not Configured'}                   ║
║    🚀  Server: http://0.0.0.0:7860                                      ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """
    print("\033[96m" + banner + "\033[0m")

# ─── MAIN ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, workers=1, log_level="info") 
# ─── CONNECT TO REDIS ──────────────────────────────────────────
redis_url = os.environ.get("REDIS_URL")

if redis_url:
    try:
        # Clean the URL
        clean_url = redis_url.strip()
        
        # If using Upstash or any TLS Redis
        if "upstash" in clean_url or "render" in clean_url:
            if clean_url.startswith("redis://"):
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
        await redis_pool.ping()
        logger.info("✅ Redis connected successfully")
        set_redis_pool(redis_pool)
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed: {e} - Using in-memory fallback")
        redis_pool = None
else:
    logger.warning("⚠️ REDIS_URL not set – using in-memory fallback")
    redis_pool = None