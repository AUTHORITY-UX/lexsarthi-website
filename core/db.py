"""
core/db.py - Fixed with asyncpg and proper connection pooling
"""
from __future__ import annotations

import logging
from typing import Optional
import asyncpg
from core.config import settings

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self._pool = None
        self._redis = None
        self._connected = False
        self._redis_connected = False

    async def init(self):
        await self._init_postgres()
        await self._init_redis()

    async def _init_postgres(self):
        try:
            # Use asyncpg with proper connection pooling
            self._pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=2,
                max_size=10,
                timeout=30,
                command_timeout=30,
                ssl=True
            )
            # Test connection
            async with self._pool.acquire() as conn:
                await conn.execute("SELECT 1")
            self._connected = True
            logger.info("✅ Neon PostgreSQL connected")
            await self._migrate()
        except Exception as exc:
            logger.error(f"❌ PostgreSQL connection failed: {exc}")
            self._connected = False
            self._pool = None

    async def _init_redis(self):
        try:
            import redis.asyncio as aioredis
            if settings.REDIS_URL and settings.REDIS_URL != "redis://localhost:6379/0":
                self._redis = aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                )
                await self._redis.ping()
                self._redis_connected = True
                logger.info("✅ Redis connected")
            else:
                logger.warning("⚠️ REDIS_URL not configured - using in-memory fallback")
                self._redis_connected = False
                self._redis = None
        except Exception as exc:
            logger.warning(f"⚠️ Redis unavailable: {exc} — cache/rate-limit degraded")
            self._redis_connected = False
            self._redis = None

    async def _migrate(self):
        if not self._pool:
            return
        try:
            async with self._pool.acquire() as conn:
                # Create extension
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                
                # Drop and recreate tables
                tables = [
                    "moat_cache_meta", "moat_audit_log", "moat_patterns",
                    "moat_inventory", "moat_ip_vault", "moat_feedback",
                    "moat_judge", "moat_agents", "moat_verifiers",
                    "moat_knowledge", "moat_evolution", "moat_intelligence",
                    "verdicts", "legal_documents", "api_keys",
                    "conversations", "users"
                ]
                
                for table in tables:
                    await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                
                # Create all tables
                await conn.execute("""
                    CREATE TABLE users (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) UNIQUE,
                        phone VARCHAR(20) UNIQUE,
                        name VARCHAR(255),
                        password_hash VARCHAR(255),
                        plan VARCHAR(20) DEFAULT 'free',
                        queries_today INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE conversations (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id INT REFERENCES users(id) ON DELETE CASCADE,
                        title VARCHAR(500),
                        messages JSONB DEFAULT '[]'::jsonb,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE legal_documents (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        title VARCHAR(1000),
                        doc_type VARCHAR(100),
                        jurisdiction VARCHAR(100),
                        content TEXT,
                        metadata JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE verdicts (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id INT REFERENCES users(id),
                        query TEXT NOT NULL,
                        verdict TEXT,
                        confidence FLOAT,
                        metadata JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE api_keys (
                        id SERIAL PRIMARY KEY,
                        key_hash VARCHAR(255) UNIQUE,
                        user_id INT REFERENCES users(id),
                        name VARCHAR(255),
                        rate_limit INT DEFAULT 100,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    -- Moat tables
                    CREATE TABLE moat_intelligence (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        module VARCHAR(100) NOT NULL,
                        metric VARCHAR(100) NOT NULL,
                        value JSONB,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE moat_evolution (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        version VARCHAR(20),
                        changes JSONB DEFAULT '[]'::jsonb,
                        parent_id UUID REFERENCES moat_evolution(id),
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE moat_knowledge (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        domain VARCHAR(100),
                        content TEXT,
                        confidence FLOAT DEFAULT 0.5,
                        source VARCHAR(255),
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE moat_verifiers (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR(100) NOT NULL,
                        version VARCHAR(20),
                        accuracy FLOAT DEFAULT 0.0,
                        config JSONB DEFAULT '{}'::jsonb,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE moat_agents (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR(100) NOT NULL,
                        specialty VARCHAR(255),
                        model VARCHAR(100),
                        config JSONB DEFAULT '{}'::jsonb,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE moat_judge (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        query TEXT,
                        analysis TEXT,
                        verdict TEXT,
                        confidence FLOAT,
                        dissenting JSONB DEFAULT '[]'::jsonb,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE moat_feedback (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id INT REFERENCES users(id),
                        query TEXT,
                        rating INT,
                        comment TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE moat_ip_vault (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        asset_type VARCHAR(100),
                        title VARCHAR(500),
                        content TEXT,
                        hash VARCHAR(255) UNIQUE,
                        metadata JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE moat_inventory (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        item_type VARCHAR(100),
                        name VARCHAR(255),
                        count INT DEFAULT 1,
                        metadata JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE moat_patterns (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        pattern_type VARCHAR(100),
                        pattern JSONB,
                        frequency INT DEFAULT 1,
                        last_seen TIMESTAMP DEFAULT NOW(),
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE moat_audit_log (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        action VARCHAR(255),
                        actor VARCHAR(255),
                        details JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE TABLE moat_cache_meta (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        cache_key VARCHAR(255) UNIQUE,
                        provider VARCHAR(100),
                        model VARCHAR(100),
                        hit_count INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)
                
                # Create indexes
                await conn.execute("""
                    CREATE INDEX idx_legal_docs_juris ON legal_documents(jurisdiction);
                    CREATE INDEX idx_legal_docs_type ON legal_documents(doc_type);
                    CREATE INDEX idx_conversations_user ON conversations(user_id);
                    CREATE INDEX idx_verdicts_user ON verdicts(user_id);
                    CREATE INDEX idx_moat_agents_active ON moat_agents(is_active);
                    CREATE INDEX idx_moat_verifiers_active ON moat_verifiers(is_active);
                """)
                
            logger.info("✅ Database migrations complete (all 17 tables created)")
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")

    async def execute(self, query, params=()):
        if not self._pool:
            return None
        try:
            async with self._pool.acquire() as conn:
                return await conn.execute(query, *params)
        except Exception as e:
            logger.error(f"Execute error: {e}")
            return None

    async def fetchone(self, query, params=()):
        if not self._pool:
            return None
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(query, *params)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Fetchone error: {e}")
            return None

    async def fetchall(self, query, params=()):
        if not self._pool:
            return []
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"Fetchall error: {e}")
            return []

    @property
    def redis(self):
        return self._redis if self._redis_connected else None

    @property
    def is_db_connected(self):
        return self._connected and self._pool is not None

    @property
    def is_redis_connected(self):
        return self._redis_connected

    async def close(self):
        if self._redis:
            await self._redis.aclose()
        if self._pool:
            await self._pool.close()


_db: Optional[Database] = None

def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db