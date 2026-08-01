"""
Monitoring & Health Checks
- Health checks for all services
- Prometheus metrics exporter
- Service status monitoring
- Error tracking
"""
from __future__ import annotations

import time
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from loguru import logger as log

from ..config import settings
from ..middleware import metrics, cache
from ..db import pgvector_store


class HealthChecker:
    """Health check manager for all platform services."""

    def __init__(self) -> None:
        self._start_time = time.time()
        self._checks: Dict[str, Dict[str, Any]] = {}
        self._last_check: Optional[str] = None

    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity."""
        start = time.time()
        try:
            from ..db import engine
            from sqlalchemy import text
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            latency = (time.time() - start) * 1000
            result = {"status": "healthy", "latency_ms": round(latency, 2), "type": "postgresql"}
            metrics.set_gauge("db_health", 1, {"status": "healthy"})
        except Exception as e:
            latency = (time.time() - start) * 1000
            result = {"status": "unavailable", "latency_ms": round(latency, 2),
                      "error": str(e)[:200], "type": "postgresql"}
            metrics.set_gauge("db_health", 0, {"status": "unavailable"})
        self._checks["database"] = result
        return result

    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        start = time.time()
        status = cache.stats()
        latency = (time.time() - start) * 1000
        result = {
            "status": "healthy" if cache.is_connected else "degraded",
            "latency_ms": round(latency, 2),
            "backend": status["backend"],
            "connected": cache.is_connected,
        }
        metrics.set_gauge("redis_health", 1 if cache.is_connected else 0)
        self._checks["redis"] = result
        return result

    async def check_sarvam(self) -> Dict[str, Any]:
        """Check Sarvam AI connectivity."""
        from ..sarvam.client import sarvam_client
        health = await sarvam_client.health_check()
        result = {
            "status": "healthy" if health.get("configured") else "not_configured",
            "configured": health.get("configured", False),
            "models": health.get("models", {}),
            "usage": health.get("usage", {}),
        }
        metrics.set_gauge("sarvam_health", 1 if health.get("configured") else 0)
        self._checks["sarvam"] = result
        return result

    async def check_pgvector(self) -> Dict[str, Any]:
        """Check pgvector availability."""
        result = {
            "status": "healthy" if pgvector_store.is_available else "fallback",
            "available": pgvector_store.is_available,
            "fallback": "in-memory" if not pgvector_store.is_available else None,
        }
        metrics.set_gauge("pgvector_health", 1 if pgvector_store.is_available else 0)
        self._checks["pgvector"] = result
        return result

    async def check_agents(self) -> Dict[str, Any]:
        """Check agent registry health."""
        from ..core import agent_registry
        stats = agent_registry.stats()
        result = {
            "status": "healthy" if stats["online"] > 0 else "degraded",
            "total": stats["total_agents"],
            "online": stats["online"],
            "offline": stats["offline"],
            "elite": stats["elite_agents"],
        }
        metrics.set_gauge("agents_online", stats["online"])
        metrics.set_gauge("agents_total", stats["total_agents"])
        self._checks["agents"] = result
        return result

    async def check_rag(self) -> Dict[str, Any]:
        """Check RAG system health."""
        from ..core import rag_system
        stats = rag_system.stats()
        result = {
            "status": "healthy",
            "total_documents": stats["total_documents"],
            "total_chunks": stats["total_chunks"],
            "vector_dimensions": stats["vector_dimensions"],
        }
        metrics.set_gauge("rag_documents", stats["total_documents"])
        metrics.set_gauge("rag_chunks", stats["total_chunks"])
        self._checks["rag"] = result
        return result

    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks concurrently."""
        results = await asyncio.gather(
            self.check_database(), self.check_redis(), self.check_sarvam(),
            self.check_pgvector(), self.check_agents(), self.check_rag(),
            return_exceptions=True,
        )
        services = {
            "database": results[0] if not isinstance(results[0], Exception) else {"status": "error", "detail": str(results[0])},
            "redis": results[1] if not isinstance(results[1], Exception) else {"status": "error", "detail": str(results[1])},
            "sarvam": results[2] if not isinstance(results[2], Exception) else {"status": "error", "detail": str(results[2])},
            "pgvector": results[3] if not isinstance(results[3], Exception) else {"status": "error", "detail": str(results[3])},
            "agents": results[4] if not isinstance(results[4], Exception) else {"status": "error", "detail": str(results[4])},
            "rag": results[5] if not isinstance(results[5], Exception) else {"status": "error", "detail": str(results[5])},
        }

        all_healthy = all(
            s.get("status") in ("healthy", "not_configured", "fallback", "degraded")
            for s in services.values()
        )

        overall_status = "healthy" if all_healthy else "degraded"
        if any(s.get("status") == "error" for s in services.values()):
            overall_status = "unhealthy"

        self._last_check = datetime.now(timezone.utc).isoformat()

        return {
            "status": overall_status,
            "version": settings.APP_VERSION,
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": services,
            "last_check": self._last_check,
        }

    def get_metrics(self) -> str:
        """Export Prometheus metrics."""
        return metrics.export()

    def get_metrics_snapshot(self) -> dict:
        """Get a dict snapshot of all metrics."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "metrics": metrics.snapshot(),
            "checks": self._checks,
        }


health_checker = HealthChecker()


# ===== Background Health Monitor =====

class BackgroundMonitor:
    """Runs periodic health checks in the background."""

    def __init__(self) -> None:
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._interval = settings.HEALTH_CHECK_INTERVAL

    async def start(self) -> None:
        """Start background monitoring."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        log.info(f"📊 Background health monitor started (interval: {self._interval}s)")

    async def stop(self) -> None:
        """Stop background monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("Background health monitor stopped")

    async def _run_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                report = await health_checker.check_all()
                overall = report["status"]
                metrics.set_gauge("overall_health", 1 if overall == "healthy" else 0)

                # Log warnings for degraded services
                for name, svc in report["services"].items():
                    if svc.get("status") in ("unavailable", "error", "unhealthy"):
                        log.warning(f"Health check [{name}]: {svc.get('status')} - {svc.get('error', svc.get('detail', ''))}")

            except Exception as e:
                log.error(f"Health check error: {e}")

            await asyncio.sleep(self._interval)


background_monitor = BackgroundMonitor()
