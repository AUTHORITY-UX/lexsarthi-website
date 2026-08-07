"""
Database connection management with Redis support
"""

import os
import logging
from typing import Optional
from contextlib import asynccontextmanager

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
        self.pool = None  # For app.py check
        
    async def connect(self):
        """Initialize database connections - called from app.py lifespan"""
        try:
            # Create async engine
            if settings.DATABASE_URL:
                self._async_engine = create_async_engine(
                    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
                    echo=settings.DEBUG,
                    pool_size=10,
                    max_overflow=20
                )
                self._async_session_maker = async_sessionmaker(
                    self._async_engine,
                    class_=AsyncSession,
                    expire_on_commit=False
                )
                
                # Create connection pool
                self._pool = await asyncpg.create_pool(
                    settings.DATABASE_URL,
                    min_size=2,
                    max_size=10
                )
                self.pool = self._pool  # For app.py check
                logger.info("✅ PostgreSQL pool created")
            else:
                logger.warning("⚠️ DATABASE_URL not set, running without database")
            
            # Connect to Redis
            if settings.REDIS_URL:
                try:
                    self._redis_client = redis.from_url(
                        settings.REDIS_URL,
                        decode_responses=True,
                        max_connections=10
                    )
                    await self._redis_client.ping()
                    logger.info("✅ Redis connected successfully")
                except Exception as e:
                    logger.warning(f"⚠️ Redis connection failed: {e}")
                    self._redis_client = None
            else:
                logger.info("ℹ️ Redis URL not configured, using in-memory fallback")
                
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Close all connections - called from app.py lifespan"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self.pool = None
        
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
        
        if self._async_engine:
            await self._async_engine.dispose()
            self._async_engine = None
        
        logger.info("Database connections closed")
    
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
        return self._redis_client
    
    async def get_pool(self):
        """Get asyncpg connection pool"""
        return self._pool
    
    @asynccontextmanager
    async def get_session(self):
        """Get async session (context manager)"""
        if not self._async_session_maker:
            await self.connect()
        
        async with self._async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    @contextmanager
    def get_sync_session(self):
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

# Create global database instance
db = Database()

# Helper functions
def get_db() -> Database:
    """Get database instance"""
    return db

async def init_db():
    """Initialize database connections"""
    await db.connect()
    logger.info("✅ Database initialized")

async def close_db():
    """Close database connections"""
    await db.disconnect()
    logger.info("Database closed")