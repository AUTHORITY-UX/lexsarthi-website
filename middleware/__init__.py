"""
middleware.py — Unknown Verdict v41.0
======================================
Production middleware:
  1. JWTAuthMiddleware — enforces JWT auth on protected endpoints
  2. RateLimitMiddleware — Redis-backed, 100 req/min per IP

DESIGN:
  - PUBLIC_PATHS are exempt from auth (health, docs, static, auth/token)
  - Auth can be DISABLED by setting ENFORCE_AUTH=false (for dev/testing)
  - Rate limiting uses Redis if available, falls back to in-memory dict
  - Rate limiting ALWAYS runs (even without auth) to protect against abuse
  - Both middlewares are graceful — they never crash the app if Redis/JWT fails

DEPLOY: Place at repo root (next to app.py / routes.py)
"""

from __future__ import annotations

import os
import time
import json
import logging
from collections import defaultdict, deque
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("middleware")

# ──────────────────────────────────────────────────────────────────────────
# Configuration (from env vars, with sensible defaults)
# ──────────────────────────────────────────────────────────────────────────
JWT_SECRET = os.environ.get("JWT_SECRET", "unknown-verdict-secret-change-me")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ENFORCE_AUTH = os.environ.get("ENFORCE_AUTH", "false").lower() == "true"
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "100"))
RATE_LIMIT_WINDOW = 60  # seconds
REDIS_URL = os.environ.get("REDIS_URL", os.environ.get("UPSTASH_REDIS_URL", ""))

# ──────────────────────────────────────────────────────────────────────────
# Public paths — exempt from authentication
# ──────────────────────────────────────────────────────────────────────────
PUBLIC_PATHS = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/api/status",
    "/auth/token",
}

PUBLIC_PREFIXES = (
    "/static/",
    "/docs/",
    "/redoc/",
)


def is_public(path: str) -> bool:
    """Check if a path is public (exempt from auth)."""
    if path in PUBLIC_PATHS:
        return True
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


# ──────────────────────────────────────────────────────────────────────────
# Redis connection (shared)
# ──────────────────────────────────────────────────────────────────────────
_redis_client = None

async def get_redis():
    """Get or create a Redis client. Returns None if unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not REDIS_URL:
        return None
    try:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
        # Test the connection
        await _redis_client.ping()
        logger.info("✅ Redis connected for rate limiting")
        return _redis_client
    except Exception as e:
        logger.warning(f"⚠️ Redis unavailable for rate limiting: {e}")
        _redis_client = None
        return None


# ════════════════════════════════════════════════════════════════════════
# JWT AUTH MIDDLEWARE
# ════════════════════════════════════════════════════════════════════════
class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Enforces JWT authentication on all non-public endpoints.

    Set ENFORCE_AUTH=true to enable. When disabled (default), the middleware
    still runs but does not block requests — it just logs auth status.

    Token format: Bearer <jwt_token>
    Header: Authorization: Bearer eyJhbGc...

    To get a token: POST /auth/token
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Always allow public paths
        if is_public(path):
            return await call_next(request)

        # If auth is not enforced, pass through (but try to decode for context)
        if not ENFORCE_AUTH:
            # Still try to extract user info if token is present
            token = self._extract_token(request)
            if token:
                user = self._decode_token(token)
                if user:
                    request.state.user = user
            return await call_next(request)

        # Auth IS enforced — require valid token
        token = self._extract_token(request)
        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated", "error": "missing_token"},
            )

        user = self._decode_token(token)
        if not user:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token", "error": "invalid_token"},
            )

        # Attach user info to request state for downstream handlers
        request.state.user = user

        return await call_next(request)

    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract Bearer token from Authorization header."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        # Also accept token as query param (for SSE/streaming — browsers can't set headers on EventSource)
        token = request.query_params.get("token")
        if token:
            return token
        return None

    def _decode_token(self, token: str) -> Optional[dict]:
        """Decode and validate a JWT token."""
        try:
            import jwt
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            # Check expiry
            if payload.get("exp", 0) < time.time():
                return None
            return payload
        except Exception as e:
            logger.debug(f"Token decode failed: {e}")
            return None


# ════════════════════════════════════════════════════════════════════════
# RATE LIMIT MIDDLEWARE
# ════════════════════════════════════════════════════════════════════════
class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-backed rate limiting: 100 requests per minute per IP.
    Falls back to in-memory dict if Redis is unavailable.

    Returns 429 Too Many Requests when the limit is exceeded.
    Includes RateLimit headers in every response:
      X-RateLimit-Limit:     100
      X-RateLimit-Remaining:  87
      X-RateLimit-Reset:     60
    """

    # In-memory fallback: {ip: deque[timestamps]}
    _memory_store: dict[str, deque] = defaultdict(lambda: deque(maxlen=200))

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip rate limiting for static assets and docs
        if path.startswith("/static/") or path in ("/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        redis = await get_redis()

        # Check rate limit
        allowed, remaining, reset_in = await self._check_rate_limit(client_ip, redis)

        # Process the request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_PER_MIN)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(reset_in)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "error": "rate_limited",
                    "retry_after": reset_in,
                    "limit": RATE_LIMIT_PER_MIN,
                    "window": f"{RATE_LIMIT_WINDOW}s",
                },
                headers={
                    "X-RateLimit-Limit": str(RATE_LIMIT_PER_MIN),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_in),
                    "Retry-After": str(reset_in),
                },
            )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, accounting for proxies."""
        # Check X-Forwarded-For (HF Spaces uses this)
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        # Check X-Real-IP
        real_ip = request.headers.get("X-Real-For", "")
        if real_ip:
            return real_ip.strip()
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"

    async def _check_rate_limit(self, ip: str, redis) -> tuple[bool, int, int]:
        """
        Check if the IP is within the rate limit.
        Returns: (allowed, remaining, reset_in_seconds)
        """
        if redis:
            return await self._check_redis(ip, redis)
        return self._check_memory(ip)

    async def _check_redis(self, ip: str, redis) -> tuple[bool, int, int]:
        """Redis-based rate limiting using a sliding window."""
        key = f"ratelimit:{ip}"
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW

        try:
            pipe = redis.pipeline()
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            # Count current entries
            pipe.zcard(key)
            # Add current request
            pipe.zadd(key, {str(now): now})
            # Set expiry on the key
            pipe.expire(key, RATE_LIMIT_WINDOW + 1)
            results = await pipe.execute()

            current_count = results[1]  # zcard result
            remaining = max(0, RATE_LIMIT_PER_MIN - current_count)
            reset_in = RATE_LIMIT_WINDOW

            if current_count > RATE_LIMIT_PER_MIN:
                logger.warning(f"Rate limit exceeded for {ip}: {current_count}/{RATE_LIMIT_PER_MIN}")
                return False, 0, reset_in
            return True, remaining, reset_in
        except Exception as e:
            logger.warning(f"Redis rate limit failed, falling back to memory: {e}")
            return self._check_memory(ip)

    def _check_memory(self, ip: str) -> tuple[bool, int, int]:
        """In-memory rate limiting fallback (per-process, not shared across workers)."""
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW

        # Get the deque for this IP
        timestamps = self._memory_store[ip]

        # Remove expired entries
        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()

        # Check limit
        current_count = len(timestamps)
        if current_count >= RATE_LIMIT_PER_MIN:
            remaining = 0
            reset_in = int(timestamps[0] + RATE_LIMIT_WINDOW - now) + 1
            logger.warning(f"Rate limit exceeded for {ip}: {current_count}/{RATE_LIMIT_PER_MIN}")
            return False, remaining, reset_in

        # Add current request
        timestamps.append(now)
        remaining = max(0, RATE_LIMIT_PER_MIN - current_count - 1)
        reset_in = RATE_LIMIT_WINDOW
        return True, remaining, reset_in


# ════════════════════════════════════════════════════════════════════════
# CORS MIDDLEWARE (bonus — needed for browser-based API access)
# ════════════════════════════════════════════════════════════════════════
class CORSMiddleware(BaseHTTPMiddleware):
    """Simple CORS middleware for cross-origin browser requests."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        origin = request.headers.get("Origin", "*")
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type, X-Requested-With, Accept, Origin"
        )
        response.headers["Access-Control-Max-Age"] = "3600"
        return response

