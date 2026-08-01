"""
Middleware Layer - Rate limiting, Prometheus metrics, Redis caching,
Gzip compression, structured logging, request tracing.
"""
from __future__ import annotations

import time
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from loguru import logger as log

from ..config import settings


# ===== In-Memory Rate Limiter (fallback when Redis not available) =====

class InMemoryRateLimiter:
    """Simple sliding window rate limiter using in-memory dict."""

    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = {}
        self._cleanup_counter = 0

    def check(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, dict]:
        """Check if request is allowed. Returns (allowed, info)."""
        now = time.time()
        window_start = now - window_seconds

        if key not in self._windows:
            self._windows[key] = []

        # Remove expired entries
        self._windows[key] = [t for t in self._windows[key] if t > window_start]

        current_count = len(self._windows[key])
        allowed = current_count < limit

        if allowed:
            self._windows[key].append(now)

        remaining = max(0, limit - len(self._windows[key]))

        # Periodic cleanup
        self._cleanup_counter += 1
        if self._cleanup_counter > 1000:
            self._cleanup()
            self._cleanup_counter = 0

        return allowed, {
            "limit": limit,
            "remaining": remaining,
            "reset_at": int(now + window_seconds),
            "window_seconds": window_seconds,
        }

    def _cleanup(self) -> None:
        """Remove expired keys."""
        now = time.time()
        to_delete = [k for k, v in self._windows.items() if not v or all(t < now - 120 for t in v)]
        for k in to_delete:
            del self._windows[k]


rate_limiter = InMemoryRateLimiter()


def parse_rate_limit(rate_str: str) -> tuple[int, int]:
    """Parse '100/minute' into (100, 60)."""
    parts = rate_str.split("/")
    limit = int(parts[0])
    unit = parts[1] if len(parts) > 1 else "minute"
    multipliers = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
    window = multipliers.get(unit, 60)
    return limit, window


# ===== Rate Limiting Middleware =====

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with per-endpoint limits."""

    def __init__(self, app, enabled: bool = True) -> None:
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for docs and health
        path = request.url.path
        if path in ("/", "/docs", "/redoc", "/openapi.json", "/health", "/metrics"):
            return await call_next(request)

        # Determine rate limit based on endpoint
        rate_str = settings.RATE_LIMIT_DEFAULT
        if "/api/chat" in path:
            rate_str = settings.RATE_LIMIT_CHAT
        elif "/auth" in path:
            rate_str = settings.RATE_LIMIT_AUTH

        limit, window = parse_rate_limit(rate_str)

        # Client identifier: API key, or IP address
        client_id = request.headers.get(settings.API_KEY_HEADER, "")
        if not client_id:
            client_id = request.client.host if request.client else "unknown"
        rate_key = f"rl:{client_id}:{path.rsplit('/', 1)[0]}"

        allowed, info = rate_limiter.check(rate_key, limit, window)

        if not allowed:
            log.warning(f"Rate limit exceeded for {client_id} on {path}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Limit: {limit} requests per {window}s",
                    "retry_after": info["reset_at"] - int(time.time()),
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset_at"]),
                    "Retry-After": str(info["reset_at"] - int(time.time())),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset_at"])
        return response


# ===== Prometheus Metrics =====

class MetricsCollector:
    """Prometheus-style metrics collector (in-memory, exportable)."""

    def __init__(self) -> None:
        self._counters: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._gauges: dict[str, float] = {}

    def inc_counter(self, name: str, labels: dict = None, value: float = 1) -> None:
        key = self._label_key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + value

    def observe_histogram(self, name: str, value: float, labels: dict = None) -> None:
        key = self._label_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)

    def set_gauge(self, name: str, value: float, labels: dict = None) -> None:
        key = self._label_key(name, labels)
        self._gauges[key] = value

    def _label_key(self, name: str, labels: dict = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def export(self) -> str:
        """Export metrics in Prometheus text format."""
        lines: list[str] = []

        # Counters
        seen_types = set()
        for key, value in sorted(self._counters.items()):
            metric_name = key.split("{")[0].split("[")[0]
            if metric_name not in seen_types:
                lines.append(f"# TYPE {metric_name} counter")
                seen_types.add(metric_name)
            lines.append(f"{key} {value}")

        # Gauges
        seen_types_g = set()
        for key, value in sorted(self._gauges.items()):
            metric_name = key.split("{")[0].split("[")[0]
            if metric_name not in seen_types_g:
                lines.append(f"# TYPE {metric_name} gauge")
                seen_types_g.add(metric_name)
            lines.append(f"{key} {value}")

        # Histograms (summary)
        seen_types_h = set()
        for key, values in sorted(self._histograms.items()):
            metric_name = key.split("{")[0].split("[")[0]
            if metric_name not in seen_types_h:
                lines.append(f"# TYPE {metric_name} histogram")
                seen_types_h.add(metric_name)
            count = len(values)
            total = sum(values)
            avg = total / count if count > 0 else 0
            sorted_vals = sorted(values)
            p50 = sorted_vals[int(count * 0.5)] if count > 0 else 0
            p95 = sorted_vals[int(count * 0.95)] if count > 0 else 0
            p99 = sorted_vals[int(count * 0.99)] if count > 0 else 0
            lines.append(f'{key}_count {count}')
            lines.append(f'{key}_sum {total:.4f}')
            lines.append(f'{key}_avg {avg:.4f}')
            lines.append(f'{key}_p50 {p50:.4f}')
            lines.append(f'{key}_p95 {p95:.4f}')
            lines.append(f'{key}_p99 {p99:.4f}')

        return "\n".join(lines) + "\n"

    def snapshot(self) -> dict:
        """Get a dict snapshot of all metrics."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: {"count": len(v), "sum": sum(v),
                     "avg": sum(v) / len(v) if v else 0}
                for k, v in self._histograms.items()
            },
        }


metrics = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect Prometheus metrics for every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        path = request.url.path
        method = request.method

        # Normalize path (remove path params)
        normalized_path = path
        for segment in path.split("/"):
            if segment and not segment.isalpha():
                normalized_path = normalized_path.replace(segment, ":id")

        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as e:
            metrics.inc_counter("http_requests_total",
                                {"method": method, "path": normalized_path, "status": "500"})
            raise

        latency = (time.time() - start) * 1000
        metrics.inc_counter("http_requests_total",
                            {"method": method, "path": normalized_path, "status": str(status)})
        metrics.observe_histogram("http_request_duration_ms", latency,
                                  {"method": method, "path": normalized_path})

        if status >= 400:
            metrics.inc_counter("http_errors_total",
                                {"method": method, "path": normalized_path, "status": str(status)})

        response.headers["X-Response-Time-ms"] = f"{latency:.2f}"
        return response


# ===== Structured Logging Setup =====

def setup_logging() -> None:
    """Configure structured logging with Loguru."""
    import sys
    from loguru import logger

    # Remove default handler
    logger.remove()

    # Console handler
    if settings.LOG_FORMAT == "json":
        fmt = (
            '{{"timestamp":"{time:YYYY-MM-DD HH:mm:ss.SSS}",'
            '"level":"{level}","logger":"{name}",'
            '"message":"{message}","function":"{function}",'
            '"line":{line}}}'
        )
    else:
        fmt = (
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} | {message}"
        )

    logger.add(
        sys.stderr, format=fmt, level=settings.LOG_LEVEL,
        colorize=settings.LOG_FORMAT == "text",
        backtrace=True, diagnose=settings.DEBUG,
    )

    # File handler with rotation
    if settings.LOG_FILE:
        import os
        log_dir = os.path.dirname(settings.LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        logger.add(
            settings.LOG_FILE, format=fmt, level=settings.LOG_LEVEL,
            rotation=settings.LOG_ROTATION, retention=settings.LOG_RETENTION,
            compression="zip",
        )

    log.info(f"📋 Logging configured: format={settings.LOG_FORMAT}, level={settings.LOG_LEVEL}")


# ===== Request Audit Middleware =====

class AuditMiddleware(BaseHTTPMiddleware):
    """Log request details for audit trail."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        path = request.url.path
        method = request.method
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")

        # Skip noise
        if path in ("/docs", "/redoc", "/openapi.json", "/metrics", "/favicon.ico"):
            return await call_next(request)

        response = await call_next(request)
        latency = (time.time() - start) * 1000

        # Log to audit (in production, write to DB)
        if path.startswith("/api/"):
            audit_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "method": method, "path": path,
                "status": response.status_code,
                "latency_ms": round(latency, 2),
                "ip": client_ip,
                "user_agent": user_agent[:200],
            }
            log.info(json.dumps(audit_entry))

            metrics.inc_counter("api_audit_total", {"path": path, "method": method})

        return response


# ===== Redis Cache (in-memory fallback) =====

class CacheManager:
    """Redis-like cache with in-memory fallback."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[any, float]] = {}
        self._redis = None
        self._connected = False

    async def connect(self) -> None:
        """Try to connect to Redis."""
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                settings.REDIS_URL, decode_responses=True,
                socket_connect_timeout=3, socket_timeout=3,
            )
            await self._redis.ping()
            self._connected = True
            log.info("✅ Redis connected")
        except Exception as e:
            self._connected = False
            log.info(f"ℹ️ Redis not available, using in-memory cache: {e}")

    async def get(self, key: str) -> Optional[any]:
        if self._connected and self._redis:
            data = await self._redis.get(key)
            return json.loads(data) if data else None
        # Fallback
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            del self._cache[key]
        return None

    async def set(self, key: str, value: any, ttl: int = 300) -> None:
        if self._connected and self._redis:
            await self._redis.setex(key, ttl, json.dumps(value, default=str))
        else:
            self._cache[key] = (value, time.time() + ttl)

    async def delete(self, key: str) -> None:
        if self._connected and self._redis:
            await self._redis.delete(key)
        elif key in self._cache:
            del self._cache[key]

    async def delete_pattern(self, pattern: str) -> None:
        if self._connected and self._redis:
            async for key in self._redis.scan_iter(pattern):
                await self._redis.delete(key)
        else:
            keys_to_delete = [k for k in self._cache if pattern.replace("*", "") in k]
            for k in keys_to_delete:
                del self._cache[k]

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            log.info("Redis connection closed")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def stats(self) -> dict:
        return {
            "connected": self._connected,
            "backend": "redis" if self._connected else "in-memory",
            "keys_cached": len(self._cache) if not self._connected else "N/A",
        }


cache = CacheManager()


def cache_key(*args) -> str:
    """Generate a cache key from arguments."""
    raw = ":".join(str(a) for a in args)
    return hashlib.md5(raw.encode()).hexdigest()


# ===== CORS Middleware (already in app.py, but centralized config) =====

def get_cors_config() -> dict:
    return {
        "allow_origins": settings.CORS_ORIGINS,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "expose_headers": ["X-RateLimit-Limit", "X-RateLimit-Remaining",
                           "X-RateLimit-Reset", "X-Response-Time-ms"],
    }


# ===== Error Handler =====

class ErrorHandler:
    """Centralized error handling."""

    @staticmethod
    async def handle(request: Request, exc: Exception) -> JSONResponse:
        log.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
        metrics.inc_counter("unhandled_errors_total",
                           {"path": request.url.path, "error": type(exc).__name__})
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
                "code": "INTERNAL_ERROR",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": str(request.url.path),
            },
        )


error_handler = ErrorHandler()
