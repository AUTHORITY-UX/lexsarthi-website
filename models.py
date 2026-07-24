# =============================================================================
# models.py - Database Models & Pydantic Schemas
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# =============================================================================

from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, Text, Boolean, JSON, Float, func, UniqueConstraint
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime

# ─── METADATA ──────────────────────────────────────────────────────
metadata = MetaData()

# ─── TABLE DEFINITIONS ─────────────────────────────────────────────
users = Table("users", metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String(255), unique=True, index=True),
    Column("username", String(100), unique=True),
    Column("password_hash", String(255)),
    Column("full_name", String(255)),
    Column("is_active", Boolean, server_default="true"),
    Column("is_premium", Boolean, server_default="false"),
    Column("tier", String(20), server_default="free"),
    Column("queries_used_today", Integer, server_default="0"),
    Column("last_query_reset", DateTime, server_default=func.now()),
    Column("created_at", DateTime, server_default=func.now()),
    Column("updated_at", DateTime, server_default=func.now(), onupdate=func.now()),
    Column("api_key", String(64), nullable=True, unique=True),
    Column("preferences", JSON, nullable=True),
    Column("memory", JSON, server_default="[]"),
)

queries = Table("queries", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, index=True),
    Column("query", Text),
    Column("response", Text),
    Column("metadata", JSON, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
    Column("expires_at", DateTime),
)

payments = Table("payments", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer),
    Column("razorpay_order_id", String(100)),
    Column("razorpay_payment_id", String(100), nullable=True),
    Column("razorpay_signature", String(255), nullable=True),
    Column("amount", Float),
    Column("currency", String(3), server_default="INR"),
    Column("tier", String(20)),
    Column("status", String(20), server_default="created"),
    Column("created_at", DateTime, server_default=func.now()),
)

bulk_jobs = Table("bulk_jobs", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer),
    Column("job_id", String(64), unique=True, index=True),
    Column("status", String(20), server_default="pending"),
    Column("total_files", Integer, server_default="0"),
    Column("processed_files", Integer, server_default="0"),
    Column("result_data", Text, nullable=True),
    Column("created_at", DateTime, server_default=func.now()),
    Column("expires_at", DateTime),
)

blog_posts = Table("blog_posts", metadata,
    Column("id", Integer, primary_key=True),
    Column("title", Text),
    Column("content", Text),
    Column("source_url", Text),
    Column("created_at", DateTime, server_default=func.now()),
    Column("published", Boolean, server_default="true"),
)

knowledge_chunks = Table("knowledge_chunks", metadata,
    Column("id", Integer, primary_key=True),
    Column("content", Text, nullable=False),
    Column("metadata", JSON, nullable=False),
    Column("embedding", Text, nullable=False),
)

deliberations = Table("deliberations", metadata,
    Column("id", Integer, primary_key=True),
    Column("query", Text, nullable=False),
    Column("domain", Text),
    Column("persona", Text),
    Column("provider", Text),
    Column("initial_answer", Text),
    Column("verifier_results", JSON),
    Column("final_answer", Text),
    Column("confidence", Text),
    Column("sources", JSON),
    Column("timestamp", DateTime, server_default=func.now()),
    Column("used_for_training", Boolean, server_default="false"),
)

# ─── PYDANTIC MODELS ──────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str

class UserLogin(BaseModel):
    username: str
    password: str

class PaymentCreate(BaseModel):
    tier: str

class LoginRequest(BaseModel):
    username: str
    password: str

class GenerateArticleRequest(BaseModel):
    news_id: str