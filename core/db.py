# core/db.py

import asyncpg
from typing import Optional
import logging
from core.config import settings

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            # Enable pgvector extension
            async with self.pool.acquire() as conn:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            logger.info("✅ PostgreSQL pool created with pgvector")
        except Exception as e:
            logger.warning(f"⚠️ Database connection failed: {e}")
            self.pool = None
    
    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("✅ Database pool closed")
    
    async def execute(self, query: str, *args):
        if not self.pool:
            return None
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        if not self.pool:
            return []
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetch_one(self, query: str, *args):
        if not self.pool:
            return None
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

db = Database()