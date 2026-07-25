# ============================================
# MODELS.PY - FIXED (Renamed 'metadata' to 'meta')
# ============================================

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, 
    Float, JSON, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    chat_history = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="sessions")

class LegalDocument(Base):
    __tablename__ = "legal_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    jurisdiction = Column(String(100), nullable=True)
    document_type = Column(String(50), nullable=True)
    meta = Column(JSON, nullable=True)  # ← RENAMED from 'metadata'
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(String(100), nullable=False, index=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    agent_name = Column(String(100), nullable=True)
    verifier_score = Column(Float, nullable=True)
    meta = Column(JSON, nullable=True)  # ← RENAMED from 'metadata'
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chat_history")

class ComplianceRecord(Base):
    __tablename__ = "compliance_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    framework = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    score = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")

class TradeData(Base):
    __tablename__ = "trade_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=False)
    change = Column(Float, nullable=True)
    change_percent = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    source = Column(String(50), nullable=True)

class NewsArticle(Base):
    __tablename__ = "news_articles"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    url = Column(String(500), nullable=True)
    category = Column(String(50), nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

class LensScan(Base):
    __tablename__ = "lens_scans"
    
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(100), nullable=False)
    agent_name = Column(String(100), nullable=False)
    status = Column(String(50), default="active")
    results = Column(JSON, nullable=True)
    scanned_at = Column(DateTime, default=func.now())

# ============================================
# DATABASE INITIALIZATION
# ============================================

def init_db(database_url):
    """Initialize database with all tables"""
    from sqlalchemy import create_engine
    engine = create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    return engine

async def init_async_db(database_url):
    """Initialize async database"""
    from sqlalchemy.ext.asyncio import create_async_engine
    async_db_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_db_url, echo=False, pool_size=5, max_overflow=10)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine

# Export all models
__all__ = [
    'Base', 'User', 'Session', 'LegalDocument', 'ChatHistory', 
    'ComplianceRecord', 'TradeData', 'NewsArticle', 'LensScan',
    'init_db', 'init_async_db'
]