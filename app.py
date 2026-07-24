# app.py - Main Entry Point
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
from models import metadata, users
from core import DIVINE_AGENTS, VERIFIERS, embedding_model

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
database = Database(DATABASE_URL) if DATABASE_URL else None

# ─── LIFESPAN ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pg_pool, redis_pool, database
    
    logger.info("🚀 Unknown Verdict v12.1 - Initializing...")
    
    if database:
        await database.connect()
        await routes._create_tables()
        await routes._ensure_test_user()
    
    if DATABASE_URL:
        pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    
    if REDIS_URL:
        try:
            redis_pool = redis.from_url(REDIS_URL, decode_responses=True, max_connections=10)
            await redis_pool.ping()
            logger.info("✅ Redis connected successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            redis_pool = None
    else:
        logger.warning("⚠️ REDIS_URL not set – caching disabled")
    
    # Set globals for routes
    routes.pg_pool = pg_pool
    routes.redis_pool = redis_pool
    routes.database = database
    routes.embedding_model = embedding_model
    
    logger.info(f"✅ Loaded {len(DIVINE_AGENTS)} specialist personas")
    logger.info(f"✅ Loaded {len(VERIFIERS)} verifiers including judge Shakti")
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
# ✅ FIX: Pass app to routes.register_routes()
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