"""
Database connection management with Redis support
"""

import os
import logging
from typing import Optional, Union
from contextlib import contextmanager

import asyncpg
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

class Database:
    """Database manager with PostgreSQL and Redis support"""
    
    def __init__(self):
        self._engine = None
        self._async_engine = None
        self._async_session_maker = None
        self._redis_client = None
        self._pool = None
        
    def get_engine(self):
        """Get sync SQLAlchemy engine"""
        if not self._engine:
            self._engine = create_engine(
                settings.DATABASE_URL.replace("postgresql://", "postgresql://"),
                echo=settings.DEBUG,
                pool_size=10,
                max_overflow=20
            )
        return self._engine
    
    def get_async_engine(self):
        """Get async SQLAlchemy engine"""
        if not self._async_engine:
            self._async_engine = create_async_engine(
                settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
                echo=settings.DEBUG,
                pool_size=10,
                max_overflow=20
            )
        return self._async_engine
    
    def get_session_maker(self):
        """Get sync session maker"""
        return sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.get_engine()
        )
    
    def get_async_session_maker(self):
        """Get async session maker"""
        if not self._async_session_maker:
            self._async_session_maker = async_sessionmaker(
                self.get_async_engine(),
                class_=AsyncSession,
                expire_on_commit=False
            )
        return self._async_session_maker
    
    async def get_redis(self) -> Optional[redis.Redis]:
        """Get Redis client"""
        if self._redis_client is None:
            if settings.REDIS_URL:
                try:
                    self._redis_client = redis.from_url(
                        settings.REDIS_URL,
                        decode_responses=True,
                        max_connections=10
                    )
                    # Test connection
                    await self._redis_client.ping()
                    logger.info("✅ Redis connected successfully")
                except Exception as e:
                    logger.warning(f"⚠️ Redis connection failed: {e}")
                    self._redis_client = None
            else:
                logger.info("ℹ️ Redis URL not configured, using in-memory fallback")
        
        return self._redis_client
    
    async def get_pool(self):
        """Get asyncpg connection pool"""
        if self._pool is None:
            try:
                self._pool = await asyncpg.create_pool(
                    settings.DATABASE_URL,
                    min_size=2,
                    max_size=10
                )
                logger.info("✅ Database pool created")
            except Exception as e:
                logger.error(f"❌ Database pool creation failed: {e}")
                raise
        return self._pool
    
    async def close(self):
        """Close all connections"""
        if self._pool:
            await self._pool.close()
            self._pool = None
        
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
        
        if self._async_engine:
            await self._async_engine.dispose()
            self._async_engine = None
        
        logger.info("Database connections closed")
    
    @contextmanager
    def get_session(self):
        """Get sync session (context manager)"""
        session = self.get_session_maker()()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

# Global database instance
_db = None

def get_db() -> Database:
    """Get or create database instance"""
    global _db
    if _db is None:
        _db = Database()
    return _db

async def init_db():
    """Initialize database connections"""
    db = get_db()
    await db.get_pool()
    await db.get_redis()
    logger.info("✅ Database initialized")

async def close_db():
    """Close database connections"""
    db = get_db()
    await db.close()
    logger.info("Database closed")