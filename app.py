# =============================================================================
# app.py - Main Entry Point
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# =============================================================================

import os
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_VAR")
if not DATABASE_URL:
    print("❌ DATABASE_URL is NOT set! Please check Hugging Face secrets.")
else:
    print("✅ DATABASE_URL found!")
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from databases import Database
import asyncpg
import redis.asyncio as redis

from config import DATABASE_URL, REDIS_URL
from models import metadata
from core import DIVINE_AGENTS, VERIFIERS, embedding_model, set_database, set_pg_pool, set_redis_pool, set_logger

# ─── IMPORT ROUTES ──────────────────────────────────────────────────
import routes

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
database = None

# ─── SET CORE GLOBALS ───────────────────────────────────────────────
set_logger(logger)

# ─── DEBUG: CHECK DATABASE URL ──────────────────────────────────────
logger.info("🚀 Unknown Verdict v12.1 - Initializing...")
logger.info(f"📡 DATABASE_URL: {'✅ Set' if DATABASE_URL else '❌ NOT SET'}")

if DATABASE_URL:
    logger.info(f"📡 DATABASE_URL length: {len(DATABASE_URL)} characters")
    logger.info(f"📡 DATABASE_URL starts with: {DATABASE_URL[:20]}...")
else:
    logger.error("❌ DATABASE_URL is NOT set! Please check Hugging Face secrets.")

# ─── LIFESPAN ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pg_pool, redis_pool, database
    
    # ─── CHECK DATABASE URL ──────────────────────────────────────────
    logger.info(f"📡 DATABASE_URL: {'✅ Set' if DATABASE_URL else '❌ NOT SET'}")
    
    if DATABASE_URL:
        logger.info("🔗 Attempting to connect to Neon PostgreSQL...")
        try:
            database = Database(DATABASE_URL, min_size=2, max_size=20)
            await database.connect()
            logger.info("✅ Database connected successfully (Neon PostgreSQL)")
            
            # Create tables and seed test user
            await routes.create_tables(database)
            await routes.ensure_test_user(database)
            
            # Set database in core
            set_database(database)
            logger.info("✅ Database set in core")
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            database = None
    else:
        logger.error("❌ DATABASE_URL not found in environment variables")
        database = None
    
    # ─── POSTGRESQL POOL ────────────────────────────────────────────
    if DATABASE_URL:
        try:
            pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
            logger.info(f"✅ PostgreSQL pool created with {pg_pool._maxsize} connections")
            set_pg_pool(pg_pool)
            logger.info("✅ PostgreSQL pool set in core")
        except Exception as e:
            logger.error(f"❌ PostgreSQL pool creation failed: {e}")
            pg_pool = None
    
    # ─── REDIS ──────────────────────────────────────────────────────
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
    
    # ─── SET ROUTE GLOBALS ──────────────────────────────────────────
    routes.pg_pool = pg_pool
    routes.redis_pool = redis_pool
    routes.database = database
    
    logger.info(f"✅ Loaded {len(DIVINE_AGENTS)} specialist personas")
    logger.info(f"✅ Loaded {len(VERIFIERS)} verifiers including judge Shakti")
    
    # ─── FINAL STATUS ──────────────────────────────────────────────
    if database:
        logger.info("🗄️  Database: ✅ Neon PostgreSQL (Connected)")
    else:
        logger.error("🗄️  Database: ❌ NOT CONNECTED")
    
    logger.info("👁️ Unknown Verdict Engine v12.1 – Complete Enterprise Edition Ready.")
    
    yield
    
    # ─── SHUTDOWN ──────────────────────────────────────────────────
    if database:
        await database.disconnect()
        logger.info("🗄️  Database disconnected")
    if pg_pool:
        await pg_pool.close()
        logger.info("🗄️  PostgreSQL pool closed")
    if redis_pool:
        await redis_pool.close()
        logger.info("🗄️  Redis disconnected")

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