"""
Database Layer - SQLAlchemy async models, session pool, pgvector store.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from sqlalchemy import (
    Column, String, Integer, Float, Text, Boolean, DateTime, ForeignKey,
    JSON, Index, create_engine, text,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
from loguru import logger as log

from ..config import settings


class Base(DeclarativeBase):
    """Declarative base for all models."""
    pass


# ===== Database Engine =====

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    echo=settings.DATABASE_ECHO,
)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables and pgvector extension."""
    try:
        async with engine.begin() as conn:
            if settings.PGVECTOR_ENABLED:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
        log.info("✅ Database initialized with pgvector")
    except Exception as e:
        log.warning(f"⚠️ Database init skipped (not available): {e}")


async def close_db() -> None:
    await engine.dispose()
    log.info("Database connection pool closed")


# ===== Models =====

class UserModel(Base):
    __tablename__ = "users"
    user_id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")
    role = Column(String(50), default="user", index=True)  # admin, user, guest
    is_active = Column(Boolean, default=True)
    api_keys = Column(JSON, default=list)  # list of API key records
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)
    preferences = Column(JSON, default=dict)


class ChatHistoryModel(Base):
    __tablename__ = "chat_history"
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=True, index=True)
    conversation_id = Column(String(36), index=True)
    role = Column(String(20))  # user, assistant, system
    content = Column(Text)
    agent_id = Column(String(20), nullable=True)
    specialization = Column(String(100), nullable=True)
    model = Column(String(50), nullable=True)
    verdict_type = Column(String(50), nullable=True)
    verdict_score = Column(Float, nullable=True)
    rag_sources = Column(JSON, default=list)
    latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class DocumentModel(Base):
    __tablename__ = "rag_documents"
    doc_id = Column(String(64), primary_key=True)
    title = Column(String(500), nullable=False, index=True)
    doc_type = Column(String(50), index=True)  # statute, case_law, regulation, contract, opinion
    jurisdiction = Column(String(100), default="India")
    source = Column(String(500), default="")
    content = Column(Text)
    meta = Column("metadata", JSON, default=dict)
    embedding_status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DocumentChunkModel(Base):
    __tablename__ = "rag_document_chunks"
    chunk_id = Column(String(128), primary_key=True)
    doc_id = Column(String(64), ForeignKey("rag_documents.doc_id"), index=True)
    content = Column(Text)
    chunk_index = Column(Integer, default=0)
    meta = Column("metadata", JSON, default=dict)
    embedding = Column(JSON, nullable=True)  # fallback: JSON array; pgvector column added via migration
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_doc_chunks_doc_id", "doc_id"),
    )


class ComplianceScanModel(Base):
    __tablename__ = "compliance_scans"
    scan_id = Column(String(36), primary_key=True)
    url = Column(String(1000), index=True)
    overall_score = Column(Float)
    scores = Column(JSON, default=dict)
    issues = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    user_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class DSARRequestModel(Base):
    __tablename__ = "dsar_requests"
    request_id = Column(String(64), primary_key=True)
    user_id = Column(String(36), nullable=True)
    request_type = Column(String(50), index=True)  # access, correction, erasure, portability, objection
    data_subject_name = Column(String(255))
    data_subject_email = Column(String(255), index=True)
    status = Column(String(50), default="registered")  # registered, pending_verification, completed, rejected
    frameworks = Column(JSON, default=list)
    estimated_completion_days = Column(Integer, default=30)
    rights_exercised = Column(JSON, default=list)
    next_steps = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    completed_at = Column(DateTime, nullable=True)


class PredictionModel(Base):
    __tablename__ = "predictions"
    prediction_id = Column(String(64), primary_key=True)
    prediction_type = Column(String(50), index=True)  # case, market, risk
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    confidence = Column(Float, nullable=True)
    model_used = Column(String(50))
    user_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class SecurityAlertModel(Base):
    __tablename__ = "security_alerts"
    alert_id = Column(String(64), primary_key=True)
    alert_type = Column(String(100), index=True)
    severity = Column(String(20), index=True)  # critical, high, medium, low
    source_ip = Column(String(45))
    target = Column(String(500))
    blocked = Column(Boolean, default=True)
    action_taken = Column(String(100))
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    log_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=True, index=True)
    endpoint = Column(String(500), index=True)
    method = Column(String(10))
    status_code = Column(Integer)
    request_body = Column(JSON, nullable=True)
    response_summary = Column(String(1000), nullable=True)
    ip_address = Column(String(45))
    user_agent = Column(String(500), nullable=True)
    latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class ApiKeyModel(Base):
    __tablename__ = "api_keys"
    key_id = Column(String(36), primary_key=True)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20))  # first 8 chars for display
    user_id = Column(String(36), ForeignKey("users.user_id"), index=True)
    name = Column(String(255))  # human-readable label
    scopes = Column(JSON, default=list)  # e.g. ["chat", "legal", "compliance"]
    rate_limit = Column(String(50), default="100/minute")
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime, nullable=True)
    total_requests = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)


# ===== pgvector Store =====

class PgVectorStore:
    """
    pgvector-backed vector store for RAG embeddings.
    Falls back to in-memory when pgvector is not available.
    """

    def __init__(self) -> None:
        self._pgvector_available = False
        self._fallback_store: dict[str, list[float]] = {}

    async def init(self) -> None:
        """Initialize pgvector extension and check availability."""
        if not settings.is_database_configured:
            log.info("pgvector: database not configured, using in-memory fallback")
            return
        try:
            async with engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                # Add embedding_vector column if it doesn't exist
                await conn.execute(text(
                    "ALTER TABLE rag_document_chunks "
                    "ADD COLUMN IF NOT EXISTS embedding_vector vector(1536)"
                ))
            self._pgvector_available = True
            log.info("✅ pgvector initialized with vector(1536) column")
        except Exception as e:
            log.warning(f"⚠️ pgvector not available, using in-memory fallback: {e}")

    @property
    def is_available(self) -> bool:
        return self._pgvector_available

    async def store_embedding(self, chunk_id: str, embedding: list[float]) -> None:
        if self._pgvector_available:
            embedding_str = str(embedding)
            async with async_session_factory() as session:
                await session.execute(
                    text("UPDATE rag_document_chunks SET embedding_vector = :emb WHERE chunk_id = :cid"),
                    {"emb": embedding_str, "cid": chunk_id},
                )
                await session.commit()
        else:
            self._fallback_store[chunk_id] = embedding

    async def search_similar(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[dict]:
        """Search for similar chunks using cosine distance."""
        if self._pgvector_available:
            embedding_str = str(query_embedding)
            async with async_session_factory() as session:
                result = await session.execute(
                    text("""
                        SELECT chunk_id, doc_id, content, metadata,
                               1 - (embedding_vector <=> :emb::vector) as score
                        FROM rag_document_chunks
                        WHERE embedding_vector IS NOT NULL
                        ORDER BY embedding_vector <=> :emb::vector
                        LIMIT :k
                    """),
                    {"emb": embedding_str, "k": top_k},
                )
                return [
                    {"chunk_id": r[0], "doc_id": r[1], "content": r[2],
                     "metadata": r[3], "score": float(r[4])}
                    for r in result.fetchall()
                ]
        else:
            # In-memory cosine similarity
            import math
            results = []
            for cid, emb in self._fallback_store.items():
                dot = sum(a * b for a, b in zip(query_embedding, emb))
                mag_a = math.sqrt(sum(a * a for a in query_embedding))
                mag_b = math.sqrt(sum(b * b for b in emb))
                score = dot / (mag_a * mag_b) if mag_a > 0 and mag_b > 0 else 0.0
                results.append({"chunk_id": cid, "score": score})
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]


pgvector_store = PgVectorStore()
