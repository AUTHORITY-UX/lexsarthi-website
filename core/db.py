"""
core/db.py — Unknown Verdict v41.0
===================================
FIX: asyncpg placeholder mismatch (v41.0-stable)

ROOT CAUSE (from startup logs):
  2026-08-04 12:07:15,803 [ERROR] core.db: Execute error: syntax error at or near "%"

  asyncpg uses $1, $2, $3 ... placeholders.
  psycopg2 / SQLAlchemy-text uses %s, %s, %s ... placeholders.
  If you pass %s-style SQL to asyncpg, Postgres sees a literal "%" character
  and throws "syntax error at or near %".

THIS FILE:
  1. Provides a safe wrapper that auto-converts %s → $1,$2... so existing
     code that uses %s keeps working.
  2. Uses native $N placeholders for all NEW queries (chat insert, etc.).
  3. All methods are async (asyncpg is async-only).

DEPLOY: Replace core/db.py with this file.
"""

from __future__ import annotations

import os
import re
import json
import logging
import time
from typing import Any, Optional
from datetime import datetime

import asyncpg

logger = logging.getLogger("core.db")

# ──────────────────────────────────────────────────────────────────────────
# Placeholder conversion: %s → $1, $2, ...
# ──────────────────────────────────────────────────────────────────────────
_PERCENT_S_RE = re.compile(r"%s")


def _convert_placeholders(sql: str) -> str:
    """
    Convert psycopg2-style %s placeholders to asyncpg-style $N placeholders.

    Examples:
      "INSERT INTO foo (a,b) VALUES (%s, %s)"  →  "...VALUES ($1, $2)"
      "SELECT * FROM foo WHERE id = %s"        →  "...WHERE id = $1"

    Also handles %% (literal percent) → %.
    """
    # First, protect literal %% → temporary token
    sql = sql.replace("%%", "\x00PCT\x00")

    # Replace each %s with $1, $2, ... in order
    counter = [0]

    def _repl(_m):
        counter[0] += 1
        return f"${counter[0]}"

    sql = _PERCENT_S_RE.sub(_repl, sql)

    # Restore literal %
    sql = sql.replace("\x00PCT\x00", "%")
    return sql


# ──────────────────────────────────────────────────────────────────────────
# Database singleton
# ──────────────────────────────────────────────────────────────────────────
class Database:
    """Async PostgreSQL (Neon) connection pool wrapper."""

    _instance: Optional["Database"] = None
    _pool: Optional[asyncpg.Pool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database not initialised. Call db.connect() first.")
        return self._pool

    # ── Lifecycle ─────────────────────────────────────────────────────────
    async def connect(self) -> bool:
        """Create the connection pool and run migrations."""
        dsn = os.environ.get("DATABASE_URL") or os.environ.get(
            "NEON_DATABASE_URL", ""
        )
        if not dsn:
            logger.error("❌ DATABASE_URL / NEON_DATABASE_URL not set")
            return False

        # Neon requires SSL
        ssl_mode = "require" if "neon" in dsn.lower() else None

        try:
            self._pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=2,
                max_size=10,
                ssl=ssl_mode,
                command_timeout=30,
            )
            # Quick test
            async with self._pool.acquire() as conn:
                val = await conn.fetchval("SELECT 1")
                assert val == 1
            logger.info("✅ Neon PostgreSQL connected")
            await self._migrate()
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False

    async def disconnect(self):
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database pool closed")

    # ── Migration ─────────────────────────────────────────────────────────
    async def _migrate(self):
        """Run CREATE TABLE IF NOT EXISTS for all 17 tables."""
        statements = [
            # ── Core tables ────────────────────────────────────────────────
            """CREATE TABLE IF NOT EXISTS conversations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id TEXT,
                title TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS chat_messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                thinking TEXT,
                model TEXT,
                latency_ms INTEGER,
                tokens_used INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS legal_research (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                query TEXT NOT NULL,
                analysis TEXT,
                citations JSONB,
                model TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS documents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title TEXT,
                content TEXT,
                embedding VECTOR(1536),
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT UNIQUE,
                api_key TEXT UNIQUE,
                plan TEXT DEFAULT 'free',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            # ── Moat tables (12) ────────────────────────────────────────────
            """CREATE TABLE IF NOT EXISTS moat_intelligence (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                module TEXT NOT NULL,
                insight TEXT,
                confidence FLOAT DEFAULT 0.5,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS moat_evolution_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                module TEXT NOT NULL,
                change TEXT,
                version TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS moat_ip_vault (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                asset_name TEXT NOT NULL,
                asset_type TEXT,
                hash TEXT,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS moat_verifications (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                claim TEXT,
                result JSONB,
                verifier TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS moat_agents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                agent_name TEXT NOT NULL,
                specialty TEXT,
                performance FLOAT DEFAULT 0.5,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS moat_judgments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                case_summary TEXT,
                verdict TEXT,
                reasoning TEXT,
                confidence FLOAT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS moat_feedback (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                endpoint TEXT,
                rating INTEGER,
                comment TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS moat_knowledge (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                topic TEXT,
                content TEXT,
                embedding VECTOR(1536),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS moat_patterns (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                pattern_name TEXT,
                pattern_data JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS moat_metrics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                metric_name TEXT,
                metric_value FLOAT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS moat_cache (
                key TEXT PRIMARY KEY,
                value JSONB,
                expires_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS moat_audit_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                action TEXT,
                actor TEXT,
                details JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )""",
            # ── pgvector extension ──────────────────────────────────────────
            "CREATE EXTENSION IF NOT EXISTS vector",
        ]

        async with self._pool.acquire() as conn:
            for stmt in statements:
                try:
                    await conn.execute(stmt)
                except Exception as e:
                    # vector extension may not be available on all Neon tiers
                    logger.warning(f"Migration stmt skipped: {e}")

        logger.info(f"✅ Database migrations complete ({len(statements)} statements)")

    # ── Execute helpers ───────────────────────────────────────────────────
    async def execute(self, sql: str, *args) -> str:
        """
        Execute a SQL statement (INSERT/UPDATE/DELETE/CREATE).

        AUTO-CONVERTS %s → $1,$2,... so existing psycopg2-style code works.
        """
        sql = _convert_placeholders(sql)
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(sql, *args)
                return result
        except Exception as e:
            logger.error(f"Execute error: {e} | SQL: {sql[:200]}")
            raise

    async def fetch(self, sql: str, *args) -> list[asyncpg.Record]:
        """Fetch multiple rows. Auto-converts %s → $N."""
        sql = _convert_placeholders(sql)
        try:
            async with self._pool.acquire() as conn:
                return await conn.fetch(sql, *args)
        except Exception as e:
            logger.error(f"Fetch error: {e} | SQL: {sql[:200]}")
            raise

    async def fetchrow(self, sql: str, *args) -> Optional[asyncpg.Record]:
        """Fetch one row. Auto-converts %s → $N."""
        sql = _convert_placeholders(sql)
        try:
            async with self._pool.acquire() as conn:
                return await conn.fetchrow(sql, *args)
        except Exception as e:
            logger.error(f"Fetchrow error: {e} | SQL: {sql[:200]}")
            raise

    async def fetchval(self, sql: str, *args) -> Any:
        """Fetch a single value. Auto-converts %s → $N."""
        sql = _convert_placeholders(sql)
        try:
            async with self._pool.acquire() as conn:
                return await conn.fetchval(sql, *args)
        except Exception as e:
            logger.error(f"Fetchval error: ${e} | SQL: {sql[:200]}")
            raise

    # ── Chat-specific helpers (use native $N placeholders) ───────────────
    async def save_chat_message(
        self,
        conversation_id: str | None,
        role: str,
        content: str,
        thinking: str | None = None,
        model: str | None = None,
        latency_ms: int | None = None,
        tokens_used: int = 0,
    ) -> str | None:
        """
        Save a chat message to the chat_messages table.

        Uses NATIVE asyncpg $N placeholders — this is the specific fix for:
          "Execute error: syntax error at or near %"

        Returns the inserted row id, or None on failure.
        """
        sql = """
            INSERT INTO chat_messages
                (conversation_id, role, content, thinking, model, latency_ms, tokens_used)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """
        try:
            row = await self.fetchrow(sql, conversation_id, role, content, thinking, model, latency_ms, tokens_used)
            return str(row["id"]) if row else None
        except Exception as e:
            logger.error(f"save_chat_message failed: {e}")
            return None

    async def create_conversation(self, user_id: str | None = None, title: str = "New Conversation") -> str | None:
        """Create a new conversation and return its id."""
        sql = """
            INSERT INTO conversations (user_id, title)
            VALUES ($1, $2)
            RETURNING id
        """
        try:
            row = await self.fetchrow(sql, user_id, title)
            return str(row["id"]) if row else None
        except Exception as e:
            logger.error(f"create_conversation failed: {e}")
            return None

    async def get_conversation_history(self, conversation_id: str, limit: int = 50) -> list[dict]:
        """Fetch conversation history."""
        sql = """
            SELECT role, content, thinking, model, latency_ms, created_at
            FROM chat_messages
            WHERE conversation_id = $1
            ORDER BY created_at ASC
            LIMIT $2
        """
        rows = await self.fetch(sql, conversation_id, limit)
        return [dict(r) for r in rows]

    async def get_or_create_conversation(self, conversation_id: str | None) -> str | None:
        """Get existing conversation or create a new one."""
        if conversation_id:
            row = await self.fetchrow(
                "SELECT id FROM conversations WHERE id = $1", conversation_id
            )
            if row:
                return str(row["id"])
        return await self.create_conversation()

    # ── Health check ──────────────────────────────────────────────────────
    async def health(self) -> dict:
        """Return DB health status."""
        try:
            async with self._pool.acquire() as conn:
                tables = await conn.fetchval(
                    "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
                )
                return {
                    "connected": True,
                    "tables": tables,
                    "pool_size": self._pool.get_size() if self._pool else 0,
                    "idle_connections": self._pool.get_idle_size() if self._pool else 0,
                }
        except Exception as e:
            return {"connected": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────────────────
# Singleton accessor
# ──────────────────────────────────────────────────────────────────────────
db = Database()


# ──────────────────────────────────────────────────────────────────────────
# Backwards-compatible execute function (for code that calls db.execute_db)
# ──────────────────────────────────────────────────────────────────────────
async def execute_db(sql: str, *args) -> str:
    """Backwards-compatible execute wrapper."""
    return await db.execute(sql, *args)


async def fetch_db(sql: str, *args) -> list[dict]:
    """Backwards-compatible fetch wrapper."""
    rows = await db.fetch(sql, *args)
    return [dict(r) for r in rows]
