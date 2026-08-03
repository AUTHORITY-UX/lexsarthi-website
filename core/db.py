"""
core/db.py
==========
Neon PostgreSQL (with pgvector) + Redis connection layer.

Fixes the original bug where db.init() only ran SELECT 1 and never
created tables. Now _migrate() runs all CREATE TABLE IF NOT EXISTS
on startup — all 12 moat_* tables + core tables created automatically.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from core.config import settings

logger = logging.getLogger(__name__)

MIGRATION_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
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

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500),
    messages JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS legal_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(1000),
    doc_type VARCHAR(100),
    jurisdiction VARCHAR(100),
    content TEXT,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS verdicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INT REFERENCES users(id),
    query TEXT NOT NULL,
    verdict TEXT,
    confidence FLOAT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(255) UNIQUE,
    user_id INT REFERENCES users(id),
    name VARCHAR(255),
    rate_limit INT DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS moat_intelligence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module VARCHAR(100) NOT NULL,
    metric VARCHAR(100) NOT NULL,
    value JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS moat_evolution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(20),
    changes JSONB DEFAULT '[]'::jsonb,
    parent_id UUID REFERENCES moat_evolution(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS moat_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain VARCHAR(100),
    content TEXT,
    embedding vector(1536),
    confidence FLOAT DEFAULT 0.5,
    source VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS moat_verifiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    version VARCHAR(20),
    accuracy FLOAT DEFAULT 0.0,
    config JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS moat_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    specialty VARCHAR(255),
    model VARCHAR(100),
    config JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS moat_judge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT,
    analysis TEXT,
    verdict TEXT,
    confidence FLOAT,
    dissenting JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS moat_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INT REFERENCES users(id),
    query TEXT,
    rating INT,
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS moat_ip_vault (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_type VARCHAR(100),
    title VARCHAR(500),
    content TEXT,
    hash VARCHAR(255) UNIQUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS moat_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_type VARCHAR(100),
    name VARCHAR(255),
    count INT DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS moat_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type VARCHAR(100),
    pattern JSONB,
    frequency INT DEFAULT 1,
    last_seen TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS moat_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action VARCHAR(255),
    actor VARCHAR(255),
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS moat_cache_meta (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key VARCHAR(255) UNIQUE,
    provider VARCHAR(100),
    model VARCHAR(100),
    hit_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_legal_docs_juris ON legal_documents(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_legal_docs_type ON legal_documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_verdicts_user ON verdicts(user_id);
CREATE INDEX IF NOT EXISTS idx_moat_agents_active ON moat_agents(is_active);
CREATE INDEX IF NOT EXISTS idx_moat_verifiers_active ON moat_verifiers(is_active);
"""


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
            from psycopg2 import pool as pgpool
            dsn = settings.DATABASE_URL
            if "sslmode" not in dsn:
                dsn += "?sslmode=require" if "?" not in dsn else "&sslmode=require"
            self._pool = pgpool.ThreadedConnectionPool(minconn=2, maxconn=10, dsn=dsn)
            conn = self._pool.getconn()
            try:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.fetchone()
                self._connected = True
                logger.info("✅ Neon PostgreSQL connected")
            finally:
                self._pool.putconn(conn)
            await self._migrate()
        except Exception as exc:
            logger.error("❌ PostgreSQL connection failed: %s", exc)
            self._connected = False

    async def _init_redis(self):
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                settings.REDIS_URL, encoding="utf-8", decode_responses=True,
                socket_timeout=5, socket_connect_timeout=5, retry_on_timeout=True,
            )
            await self._redis.ping()
            self._redis_connected = True
            logger.info("✅ Redis connected")
        except Exception as exc:
            logger.warning("⚠️ Redis unavailable: %s — cache/rate-limit degraded", exc)
            self._redis_connected = False
            self._redis = None

    async def _migrate(self):
        if not self._pool:
            return
        loop = asyncio.get_event_loop()
        def _run():
            conn = self._pool.getconn()
            try:
                cur = conn.cursor()
                cur.execute(MIGRATION_SQL)
                conn.commit()
                cur.close()
            finally:
                self._pool.putconn(conn)
        try:
            await loop.run_in_executor(None, _run)
            logger.info("✅ Database migrations complete (all tables ensured)")
        except Exception as exc:
            logger.error("❌ Migration failed: %s", exc)

    async def execute(self, query, params=()):
        if not self._connected or not self._pool:
            return None
        loop = asyncio.get_event_loop()
        def _exec():
            conn = self._pool.getconn()
            try:
                cur = conn.cursor()
                cur.execute(query, params)
                conn.commit()
                result = cur.rowcount
                cur.close()
                return result
            except Exception:
                conn.rollback()
                raise
            finally:
                self._pool.putconn(conn)
        return await loop.run_in_executor(None, _exec)

    async def fetchone(self, query, params=()):
        if not self._connected or not self._pool:
            return None
        loop = asyncio.get_event_loop()
        def _fetch():
            conn = self._pool.getconn()
            try:
                cur = conn.cursor()
                cur.execute(query, params)
                row = cur.fetchone()
                if row:
                    cols = [desc[0] for desc in cur.description]
                    return dict(zip(cols, row))
                cur.close()
                return None
            finally:
                self._pool.putconn(conn)
        return await loop.run_in_executor(None, _fetch)

    async def fetchall(self, query, params=()):
        if not self._connected or not self._pool:
            return []
        loop = asyncio.get_event_loop()
        def _fetch():
            conn = self._pool.getconn()
            try:
                cur = conn.cursor()
                cur.execute(query, params)
                rows = cur.fetchall()
                if rows:
                    cols = [desc[0] for desc in cur.description]
                    return [dict(zip(cols, row)) for row in rows]
                cur.close()
                return []
            finally:
                self._pool.putconn(conn)
        return await loop.run_in_executor(None, _fetch)

    @property
    def redis(self):
        return self._redis if self._redis_connected else None

    @property
    def is_db_connected(self):
        return self._connected

    @property
    def is_redis_connected(self):
        return self._redis_connected

    async def close(self):
        if self._redis:
            await self._redis.aclose()
        if self._pool:
            self._pool.closeall()


_db: Optional[Database] = None

def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db
