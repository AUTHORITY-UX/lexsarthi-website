"""
moat/integration.py
====================
Moat Evolution Middleware — intercepts requests/responses to learn
from patterns, building the self-evolving intelligence layer.

Non-blocking: fire-and-forget logging. Never slows down requests.
"""

from __future__ import annotations

import time
import json
import asyncio
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.db import get_db

logger = logging.getLogger(__name__)


class EvolutionMiddleware(BaseHTTPMiddleware):
    """Non-blocking middleware that records interactions for Moat evolution."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        latency_ms = (time.monotonic() - start) * 1000
        try:
            db = get_db()
            if db.is_db_connected:
                pattern_data = {"path": request.url.path, "method": request.method,
                                "status": response.status_code, "latency_ms": round(latency_ms, 2)}
                asyncio.ensure_future(self._log_pattern(db, pattern_data))
        except Exception:
            pass
        return response

    async def _log_pattern(self, db, pattern_data: dict):
        try:
            await db.execute(
                "INSERT INTO moat_patterns (pattern_type, pattern) VALUES (%s, %s)",
                ("request_flow", json.dumps(pattern_data)))
        except Exception:
            pass


class MoatEngine:
    """Aggregates learnings and triggers self-evolution cycles."""

    def __init__(self):
        self.version = "41.0"
        self.active = True

    async def get_status(self) -> dict:
        db = get_db()
        tables = ["moat_intelligence", "moat_evolution", "moat_knowledge",
                  "moat_verifiers", "moat_agents", "moat_judge",
                  "moat_feedback", "moat_ip_vault", "moat_inventory",
                  "moat_patterns", "moat_audit_log", "moat_cache_meta"]
        counts = {}
        for t in tables:
            if db.is_db_connected:
                row = await db.fetchone(f"SELECT COUNT(*) as cnt FROM {t}")
                counts[t] = row["cnt"] if row else 0
            else:
                counts[t] = 0
        return {"version": self.version, "active": self.active, "tables": counts}

    async def evolve(self, prompt: str, llm_response: str) -> dict:
        db = get_db()
        if db.is_db_connected:
            await db.execute(
                "INSERT INTO moat_evolution (version, changes) VALUES (%s, %s)",
                (self.version, json.dumps([{"prompt": prompt[:500],
                                            "response_summary": llm_response[:500]}])))
        return {"status": "evolved", "version": self.version}

    async def get_metrics(self) -> dict:
        db = get_db()
        metrics = {}
        if db.is_db_connected:
            for label, table in [("total_patterns", "moat_patterns"),
                                 ("total_verdicts", "moat_judge"),
                                 ("active_agents", "moat_agents WHERE is_active = TRUE"),
                                 ("active_verifiers", "moat_verifiers WHERE is_active = TRUE")]:
                row = await db.fetchone(f"SELECT COUNT(*) as cnt FROM {table}")
                metrics[label] = row["cnt"] if row else 0
        return metrics


moat_engine = MoatEngine()
