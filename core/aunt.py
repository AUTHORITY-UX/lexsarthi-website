"""
unknown_verdict.core.auth
==========================
JWT authentication + Redis-backed rate limiting.

Fixes the issue where "JWT is coded but not enforced".
Now:
  - JWT tokens are verified on every protected endpoint.
  - Admin endpoints require ADMIN_KEY or ADMIN_SECRET.
  - Rate limiting is enforced via Redis (100 req/min per IP by default).
  - Falls back to in-memory rate limiting if Redis is down.
"""

from __future__ import annotations

import time
import hashlib
import logging
from typing import Optional
from collections import defaultdict

import jwt
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from unknown_verdict.core.config import settings
from unknown_verdict.core.db import get_db

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


# ─── JWT ───────────────────────────────────────────────────────────────────

class JWTManager:
    """Create and verify JWT tokens."""

    def __init__(self):
        self.secret = settings.jwt_signing_key
        self.algorithm = "HS256"
        self.expiry_seconds = 86400 * 7  # 7 days

    def create_token(self, user_id: int, email: str, plan: str = "free") -> str:
        payload = {
            "sub": str(user_id),
            "email": email,
            "plan": plan,
            "iat": int(time.time()),
            "exp": int(time.time()) + self.expiry_seconds,
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[dict]:
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


# ─── Rate limiter ──────────────────────────────────────────────────────────

class RateLimiter:
    """
    Redis-backed sliding-window rate limiter.

    Falls back to in-memory if Redis is unavailable.
    Default: 100 requests per 60 seconds per IP.
    """

    def __init__(self):
        self._memory: dict[str, list[float]] = defaultdict(list)

    async def check(self, key: str) -> tuple[bool, dict]:
        """
        Check if a request is allowed.
        Returns (allowed, info_dict).
        """
        limit = settings.RATE_LIMIT_REQUESTS
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        now = time.time()

        redis = get_db().redis
        if redis:
            # Redis sliding window via sorted set
            redis_key = f"{settings.CACHE_PREFIX}rl:{key}"
            try:
                pipe = redis.pipeline()
                pipe.zremrangebyscore(redis_key, 0, now - window)
                pipe.zadd(redis_key, {str(now): now})
                pipe.zcard(redis_key)
                pipe.expire(redis_key, window)
                results = await pipe.execute()
                count = results[2]
                allowed = count <= limit
                return allowed, {
                    "limit": limit,
                    "remaining": max(0, limit - count),
                    "reset_at": now + window,
                    "engine": "redis",
                }
            except Exception as exc:
                logger.warning("Redis rate limit failed: %s, using memory", exc)

        # In-memory fallback
        bucket = self._memory[key]
        # Remove expired entries
        self._memory[key] = [t for t in bucket if now - t < window]
        self._memory[key].append(now)
        count = len(self._memory[key])
        allowed = count <= limit
        return allowed, {
            "limit": limit,
            "remaining": max(0, limit - count),
            "reset_at": now + window,
            "engine": "memory",
        }


# ─── Dependencies ──────────────────────────────────────────────────────────

jwt_manager = JWTManager()
rate_limiter = RateLimiter()


async def get_current_user(request: Request) -> Optional[dict]:
    """Extract and verify JWT from request. Returns None if no/invalid token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    return jwt_manager.verify_token(token)


async def require_user(request: Request) -> dict:
    """Require a valid JWT — raises 401 if missing/invalid."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_admin(request: Request) -> dict:
    """Require admin key — either via header or JWT with admin claim."""
    # Check admin key in headers
    admin_key = request.headers.get("X-Admin-Key", "")
    if admin_key and admin_key in settings.admin_keys:
        return {"role": "admin", "source": "admin_key"}

    # Check JWT
    user = await get_current_user(request)
    if user and user.get("plan") == "admin":
        return {"role": "admin", "source": "jwt", "user": user}

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required",
    )


async def check_rate_limit(request: Request):
    """
    Rate-limit middleware dependency.
    Add to any router via: router.dependencies.append(Depends(check_rate_limit))
    """
    client_ip = request.client.host if request.client else "unknown"
    # Allow admin to bypass
    admin_key = request.headers.get("X-Admin-Key", "")
    if admin_key and admin_key in settings.admin_keys:
        return

    allowed, info = await rate_limiter.check(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {info['limit']} requests per {settings.RATE_LIMIT_WINDOW_SECONDS}s",
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(info["reset_at"])),
                "Retry-After": str(settings.RATE_LIMIT_WINDOW_SECONDS),
            },
        )
    # Attach info to request state for response headers
    request.state.rate_limit = info
