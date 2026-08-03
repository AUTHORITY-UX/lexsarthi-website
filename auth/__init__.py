"""
core/auth.py
=============
JWT authentication + Redis-backed rate limiting.
"""

from __future__ import annotations

import time
import hashlib
import logging
from typing import Optional
from collections import defaultdict

import jwt
from fastapi import Request, HTTPException, status

from core.config import settings
from core.db import get_db

logger = logging.getLogger(__name__)


class JWTManager:
    def __init__(self):
        self.secret = settings.jwt_signing_key
        self.algorithm = "HS256"
        self.expiry_seconds = 86400 * 7  # 7 days

    def create_token(self, user_id: int, email: str, plan: str = "free") -> str:
        payload = {
            "sub": str(user_id), "email": email, "plan": plan,
            "iat": int(time.time()), "exp": int(time.time()) + self.expiry_seconds,
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[dict]:
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


class RateLimiter:
    """Redis sliding-window rate limiter. Falls back to in-memory."""

    def __init__(self):
        self._memory: dict[str, list[float]] = defaultdict(list)

    async def check(self, key: str):
        limit = settings.RATE_LIMIT_REQUESTS
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        now = time.time()
        redis = get_db().redis
        if redis:
            try:
                pipe = redis.pipeline()
                rkey = f"{settings.CACHE_PREFIX}rl:{key}"
                pipe.zremrangebyscore(rkey, 0, now - window)
                pipe.zadd(rkey, {str(now): now})
                pipe.zcard(rkey)
                pipe.expire(rkey, window)
                results = await pipe.execute()
                count = results[2]
                return count <= limit, {"limit": limit, "remaining": max(0, limit - count),
                                        "reset_at": now + window, "engine": "redis"}
            except Exception:
                pass
        bucket = self._memory[key]
        self._memory[key] = [t for t in bucket if now - t < window]
        self._memory[key].append(now)
        count = len(self._memory[key])
        return count <= limit, {"limit": limit, "remaining": max(0, limit - count),
                                "reset_at": now + window, "engine": "memory"}


jwt_manager = JWTManager()
rate_limiter = RateLimiter()


async def get_current_user(request: Request) -> Optional[dict]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return jwt_manager.verify_token(auth_header[7:])


async def require_user(request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or missing authentication token",
                            headers={"WWW-Authenticate": "Bearer"})
    return user


async def require_admin(request: Request) -> dict:
    admin_key = request.headers.get("X-Admin-Key", "")
    if admin_key and admin_key in settings.admin_keys:
        return {"role": "admin", "source": "admin_key"}
    user = await get_current_user(request)
    if user and user.get("plan") == "admin":
        return {"role": "admin", "source": "jwt", "user": user}
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


async def check_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    admin_key = request.headers.get("X-Admin-Key", "")
    if admin_key and admin_key in settings.admin_keys:
        return
    allowed, info = await rate_limiter.check(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {info['limit']} requests per {settings.RATE_LIMIT_WINDOW_SECONDS}s",
            headers={"X-RateLimit-Limit": str(info["limit"]), "X-RateLimit-Remaining": "0",
                     "Retry-After": str(settings.RATE_LIMIT_WINDOW_SECONDS)})
    request.state.rate_limit = info
