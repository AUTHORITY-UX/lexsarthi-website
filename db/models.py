"""
db/models.py
=============
Database models and schema definitions for Unknown Verdict v41.0.

This file documents the database schema. The actual table creation
happens in core/db.py via the MIGRATION_SQL constant (runs on startup).

Use this file for reference and for ORM-style queries if you add
SQLAlchemy later. For now, queries go through core/db.py directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class User:
    id: int
    email: str
    name: str = ""
    plan: str = "free"
    queries_today: int = 0
    created_at: Optional[datetime] = None


@dataclass
class Conversation:
    id: str
    user_id: Optional[int] = None
    title: str = ""
    messages: list = field(default_factory=list)
    created_at: Optional[datetime] = None


@dataclass
class LegalDocument:
    id: str
    title: str = ""
    doc_type: str = ""
    jurisdiction: str = "india"
    content: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None


@dataclass
class Verdict:
    id: str
    user_id: Optional[int] = None
    query: str = ""
    verdict: str = ""
    confidence: float = 0.0
    metadata: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None


@dataclass
class MoatAgent:
    id: str
    name: str = ""
    specialty: str = ""
    model: str = "sarvam-30b"
    config: dict = field(default_factory=dict)
    is_active: bool = True
    created_at: Optional[datetime] = None


@dataclass
class MoatVerifier:
    id: str
    name: str = ""
    version: str = "41.0"
    accuracy: float = 0.0
    config: dict = field(default_factory=dict)
    is_active: bool = True
    created_at: Optional[datetime] = None


@dataclass
class MoatJudgeRuling:
    id: str
    query: str = ""
    analysis: str = ""
    verdict: str = ""
    confidence: float = 0.0
    dissenting: list = field(default_factory=list)
    created_at: Optional[datetime] = None


@dataclass
class MoatIPAsset:
    id: str
    asset_type: str = ""
    title: str = ""
    content: str = ""
    hash: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None


@dataclass
class MoatInventoryItem:
    id: str
    item_type: str = ""
    name: str = ""
    count: int = 1
    metadata: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None


# ─── Table list for reference ───
ALL_TABLES = [
    "users", "conversations", "legal_documents", "verdicts", "api_keys",
    "moat_intelligence", "moat_evolution", "moat_knowledge",
    "moat_verifiers", "moat_agents", "moat_judge",
    "moat_feedback", "moat_ip_vault", "moat_inventory",
    "moat_patterns", "moat_audit_log", "moat_cache_meta",
]

CORE_TABLES = ["users", "conversations", "legal_documents", "verdicts", "api_keys"]
MOAT_TABLES = [t for t in ALL_TABLES if t.startswith("moat_")]


def get_table_list() -> List[str]:
    """Return all table names that the migration creates."""
    return ALL_TABLES


def get_moat_table_count() -> int:
    """Return the number of moat tables."""
    return len(MOAT_TABLES)
