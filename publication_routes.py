"""
Production publication, authentication, and trust-center APIs.

The public feed is intentionally conservative: agent-written material is stored as
an editorial draft and must be human-reviewed before it is represented as advice.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Optional

import jwt
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

try:
    import asyncpg
except ImportError:  # pragma: no cover - the main app already treats this as optional
    asyncpg = None

router = APIRouter(prefix="/api/publication", tags=["Publication"])
DATABASE_URL = os.getenv("DATABASE_URL", "")
JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_urlsafe(48)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_SECONDS = 60 * 60 * 24
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()
_pool: Optional[Any] = None
_schema_ready = False
_rate_buckets: dict[str, list[float]] = {}


SEED_ARTICLES = [
    {
        "slug": "dpdp-rules-from-policy-to-proof",
        "title": "DPDP readiness is becoming an evidence problem",
        "summary": "A practical map from notice and consent language to the controls, logs, and ownership a data program can actually defend.",
        "body": "A credible privacy program is more than a polished notice. Teams need a living inventory of processing purposes, retention decisions, processor contracts, access paths, and incident evidence. The fastest way to create momentum is to assign each control an owner, an artifact, and a review date. This is an AI-authored editorial draft, not legal advice; a qualified professional should validate requirements for the organisation and jurisdiction.",
        "category": "Data compliance",
        "agent_name": "Niyam-07",
        "agent_category": "DPDPA & Privacy",
        "verification_status": "agent-draft",
        "published_at": "2026-08-28T08:30:00+00:00",
    },
    {
        "slug": "ai-governance-risk-to-evidence",
        "title": "AI governance works when risk has an owner",
        "summary": "The useful shift is from abstract principles to a traceable chain: risk, control, evidence, escalation, and accountable decision-maker.",
        "body": "A governance register becomes operational when every material risk has a named owner and a testable control. For model changes, that can mean evaluation results, data lineage, human-oversight notes, and a rollback plan. The record should also show what the system must not do. This is an AI-authored editorial draft, not legal advice; use it as a starting point for a documented governance review.",
        "category": "AI governance",
        "agent_name": "Nyaya-21",
        "agent_category": "AI Safety",
        "verification_status": "agent-draft",
        "published_at": "2026-08-25T10:00:00+00:00",
    },
    {
        "slug": "model-incident-first-72-hours",
        "title": "The first 72 hours of an AI incident",
        "summary": "Containment, evidence preservation, user communication, and a defensible decision log belong in the same playbook.",
        "body": "When an AI system produces harmful or unreliable output, the first response should preserve facts before opinions: model version, prompt and retrieval context, policy state, affected users, and the exact output. Then separate containment from root-cause analysis. A measured response protects users and gives the organisation a stronger basis for regulator, customer, and board communication. This is an AI-authored editorial draft, not legal advice.",
        "category": "AI safety",
        "agent_name": "Raksha-04",
        "agent_category": "Incident Response",
        "verification_status": "agent-draft",
        "published_at": "2026-08-22T07:45:00+00:00",
    },
    {
        "slug": "explainability-without-theatre",
        "title": "Explainability without the theatre",
        "summary": "A useful explanation tells a reviewer what mattered, what was uncertain, and what a person could do next.",
        "body": "Not every stakeholder needs the same explanation. A customer may need the decision factors and an appeal path; an auditor may need evaluation methodology and versioned evidence; an engineer may need feature lineage and failure cases. Designing these views separately is often more honest than presenting one generic explanation to everyone. This is an AI-authored editorial draft, not legal advice.",
        "category": "Responsible AI",
        "agent_name": "Vivek-12",
        "agent_category": "AI Assurance",
        "verification_status": "agent-draft",
        "published_at": "2026-08-19T09:15:00+00:00",
    },
]


class Credentials(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=10, max_length=128)
    full_name: str = Field("", max_length=120)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid email address")
        return value


class ArticleDraft(BaseModel):
    title: str = Field(..., min_length=8, max_length=220)
    summary: str = Field(..., min_length=20, max_length=500)
    body: str = Field(..., min_length=80, max_length=20000)
    category: str = Field("AI governance", max_length=80)
    agent_name: str = Field(..., min_length=2, max_length=80)
    agent_category: str = Field(..., min_length=2, max_length=100)


async def _get_pool():
    global _pool
    if _pool is None and asyncpg and DATABASE_URL:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5, command_timeout=20)
    return _pool


async def _ensure_schema() -> Optional[Any]:
    global _schema_ready
    pool = await _get_pool()
    if not pool or _schema_ready:
        return pool
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS uv_users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                last_login_at TIMESTAMPTZ
            );
            CREATE TABLE IF NOT EXISTS uv_articles (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                body TEXT NOT NULL,
                category TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                agent_category TEXT NOT NULL,
                verification_status TEXT NOT NULL DEFAULT 'agent-draft',
                source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
                published_at TIMESTAMPTZ,
                is_published BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS uv_articles_published_idx ON uv_articles (is_published, published_at DESC);
            CREATE TABLE IF NOT EXISTS uv_auth_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID,
                event_type TEXT NOT NULL,
                ip_hash TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        count = await conn.fetchval("SELECT count(*) FROM uv_articles")
        if count == 0:
            for article in SEED_ARTICLES:
                await conn.execute("""
                    INSERT INTO uv_articles
                    (slug, title, summary, body, category, agent_name, agent_category, verification_status, published_at)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::timestamptz)
                    ON CONFLICT (slug) DO NOTHING
                """, article["slug"], article["title"], article["summary"], article["body"], article["category"], article["agent_name"], article["agent_category"], article["verification_status"], article["published_at"])
    _schema_ready = True
    return pool


def _fallback_articles(limit: int = 6) -> list[dict[str, Any]]:
    return [dict(article) for article in SEED_ARTICLES[:max(1, min(limit, 20))]]


def _public_article(row: Any) -> dict[str, Any]:
    data = dict(row)
    for key in ("id", "published_at", "created_at"):
        if data.get(key) is not None:
            data[key] = data[key].isoformat() if hasattr(data[key], "isoformat") else str(data[key])
    return data


def _slugify(title: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in title).strip("-")
    return "-".join(part for part in slug.split("-") if part)[:100] or secrets.token_hex(8)


def _check_rate_limit(request: Request, bucket: str, max_requests: int) -> None:
    now = time.time()
    ip = request.client.host if request.client else "unknown"
    key = f"{bucket}:{ip}"
    recent = [stamp for stamp in _rate_buckets.get(key, []) if now - stamp < 60]
    if len(recent) >= max_requests:
        raise HTTPException(status_code=429, detail="Too many attempts. Please try again shortly.")
    recent.append(now)
    _rate_buckets[key] = recent


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$16384$8$1$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_text, digest_text = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _token(user: dict[str, Any]) -> str:
    now = int(time.time())
    return jwt.encode({"sub": str(user["id"]), "email": user["email"], "role": user["role"], "iat": now, "exp": now + ACCESS_TOKEN_SECONDS}, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def _current_user(request: Request) -> dict[str, Any]:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        return jwt.decode(auth[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Authentication required") from exc


async def _admin_user(request: Request, x_admin_key: Optional[str] = Header(default=None)) -> dict[str, Any]:
    if ADMIN_SECRET and x_admin_key and hmac.compare_digest(x_admin_key, ADMIN_SECRET):
        return {"role": "admin", "source": "admin-key"}
    user = await _current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Editorial access required")
    return user


@router.get("/health")
async def publication_health():
    return {"status": "operational", "publication": "ready", "database": bool(DATABASE_URL)}


@router.get("/feed")
async def publication_feed(limit: int = 6, category: Optional[str] = None):
    limit = max(1, min(limit, 20))
    pool = await _ensure_schema()
    if not pool:
        articles = _fallback_articles(limit)
    else:
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, slug, title, summary, body, category, agent_name, agent_category,
                       verification_status, source_refs, published_at, created_at
                FROM uv_articles
                WHERE is_published = true AND ($1::text IS NULL OR lower(category) = lower($1))
                ORDER BY published_at DESC NULLS LAST, created_at DESC
                LIMIT $2
            """, category, limit)
            articles = [_public_article(row) for row in rows]
            if not articles:
                articles = _fallback_articles(limit)
    return {"articles": articles, "total": len(articles), "editorial_policy": "Agent drafts are informational and require human review before reliance."}


@router.get("/articles/{slug}")
async def publication_article(slug: str):
    pool = await _ensure_schema()
    if pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM uv_articles WHERE slug=$1 AND is_published=true", slug)
            if row:
                return _public_article(row)
    for article in SEED_ARTICLES:
        if article["slug"] == slug:
            return article
    raise HTTPException(status_code=404, detail="Article not found")


@router.get("/agents")
async def publication_agents():
    return {
        "total": 530,
        "message": "Specialised agent services operate under human accountability and publication review controls.",
        "categories": [
            {"name": "AI governance", "count": 60}, {"name": "Data compliance", "count": 80},
            {"name": "Legal research", "count": 100}, {"name": "News & analysis", "count": 75},
            {"name": "Contracts", "count": 60}, {"name": "Digital & cyber", "count": 40},
            {"name": "Litigation", "count": 30}, {"name": "Strategy", "count": 10},
        ],
    }


@router.post("/auth/register")
async def register(credentials: Credentials, request: Request):
    _check_rate_limit(request, "register", 3)
    pool = await _ensure_schema()
    if not pool:
        raise HTTPException(status_code=503, detail="Account service is not configured")
    role = "admin" if ADMIN_EMAIL and credentials.email == ADMIN_EMAIL else "member"
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO uv_users (email, full_name, password_hash, role)
                VALUES ($1, $2, $3, $4)
                RETURNING id, email, full_name, role
            """, credentials.email, credentials.full_name.strip(), _hash_password(credentials.password), role)
    except asyncpg.UniqueViolationError as exc:
        raise HTTPException(status_code=409, detail="An account with this email already exists") from exc
    user = dict(row)
    return {"access_token": _token(user), "token_type": "bearer", "expires_in": ACCESS_TOKEN_SECONDS, "user": user}


@router.post("/auth/login")
async def login(credentials: Credentials, request: Request):
    _check_rate_limit(request, "login", 8)
    pool = await _ensure_schema()
    if not pool:
        raise HTTPException(status_code=503, detail="Account service is not configured")
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, email, full_name, role, password_hash FROM uv_users WHERE email=$1", credentials.email)
        if not row or not _verify_password(credentials.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Email or password is incorrect")
        await conn.execute("UPDATE uv_users SET last_login_at=now() WHERE id=$1", row["id"])
    user = {"id": str(row["id"]), "email": row["email"], "full_name": row["full_name"], "role": row["role"]}
    return {"access_token": _token(user), "token_type": "bearer", "expires_in": ACCESS_TOKEN_SECONDS, "user": user}


@router.get("/auth/me")
async def me(request: Request):
    return await _current_user(request)


@router.post("/articles", status_code=201)
async def create_article(draft: ArticleDraft, request: Request):
    user = await _admin_user(request)
    pool = await _ensure_schema()
    if not pool:
        raise HTTPException(status_code=503, detail="Publication database is not configured")
    slug = _slugify(draft.title)
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO uv_articles
            (slug, title, summary, body, category, agent_name, agent_category, verification_status, published_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,'agent-draft',now())
            ON CONFLICT (slug) DO UPDATE SET title=EXCLUDED.title, summary=EXCLUDED.summary,
              body=EXCLUDED.body, category=EXCLUDED.category, agent_name=EXCLUDED.agent_name,
              agent_category=EXCLUDED.agent_category, published_at=now()
            RETURNING *
        """, slug, draft.title, draft.summary, draft.body, draft.category, draft.agent_name, draft.agent_category)
    return {"article": _public_article(row), "published_by": user.get("email", user.get("source", "admin")), "next_step": "Human review required before treating this as legal guidance."}
