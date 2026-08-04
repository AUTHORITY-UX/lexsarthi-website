"""
config_updates.py — Unknown Verdict v41.0
==========================================
Centralised configuration for the new v41 additions:
  - JWT auth settings
  - Rate limiting settings
  - Streaming/SSE settings
  - LLM routing table (tiered: simple→Groq, medium→30B, complex→105B)
  - Redis/cache settings
  - Feature flags

DEPLOY: Merge these into your existing config.py or unknown_verdict/config.py,
or import this file directly:  from config_updates import LLM_ROUTING, ...

ENVIRONMENT VARIABLES (set in HF Spaces Secrets):
  JWT_SECRET=<your-secret-key>          # CHANGE THIS! minimum 32 chars
  ENFORCE_AUTH=false                     # set to true to require JWT
  RATE_LIMIT_PER_MIN=100                 # requests per minute per IP
  REDIS_URL=redis://...                  # optional, rate limiting + cache
  SARVAM_API_KEY=<your-key>
  GROQ_API_KEY=<your-key>
  DATABASE_URL=postgresql://...          # Neon connection string
"""

from __future__ import annotations

import os

# ════════════════════════════════════════════════════════════════════════
# JWT AUTHENTICATION
# ════════════════════════════════════════════════════════════════════════
JWT_SECRET = os.environ.get(
    "JWT_SECRET",
    # DO NOT use this default in production — set JWT_SECRET in HF Secrets!
    "unknown-verdict-dev-secret-change-in-production-please-set-a-real-key",
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
ENFORCE_AUTH = os.environ.get("ENFORCE_AUTH", "false").lower() == "true"

# Paths that don't require authentication
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


# ════════════════════════════════════════════════════════════════════════
# RATE LIMITING
# ════════════════════════════════════════════════════════════════════════
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "100"))
RATE_LIMIT_WINDOW = 60  # seconds
REDIS_URL = os.environ.get("REDIS_URL", os.environ.get("UPSTASH_REDIS_URL", ""))


# ════════════════════════════════════════════════════════════════════════
# TIERED LLM ROUTING — the core latency fix
# ════════════════════════════════════════════════════════════════════════
LLM_ROUTING = {
    "simple": {
        "provider": "groq",
        "model": "llama-3.1-8b-instant",
        "max_tokens": 512,
        "temperature": 0.3,
        "timeout": 10,
        "expected_latency_ms": 1000,
        "description": "Greetings, definitions, short questions (70% of queries)",
    },
    "medium": {
        "provider": "sarvam",
        "model": "sarvam-30b",
        "max_tokens": 1024,
        "temperature": 0.4,
        "timeout": 30,
        "expected_latency_ms": 8000,
        "description": "Standard legal questions requiring moderate analysis (20%)",
    },
    "complex": {
        "provider": "sarvam",
        "model": "sarvam-105b",
        "max_tokens": 2048,
        "temperature": 0.5,
        "timeout": 120,
        "expected_latency_ms": 60000,
        "description": "Case analysis, constitutional questions, multi-party disputes (10%)",
    },
}


def classify_complexity(query: str) -> str:
    """
    Classify query complexity to route to the right LLM.
    Returns: 'simple', 'medium', or 'complex'

    Heuristics:
      - Short queries (< 10 words) → simple
      - Greetings/definitions → simple
      - Case analysis, constitutional → complex
      - Everything else → medium
    """
    query_lower = query.lower().strip()
    word_count = len(query_lower.split())

    # SIMPLE: greetings, short questions, basic definitions
    simple_patterns = [
        "hello", "hi", "hey", "thanks", "thank you",
        "what is", "define", "explain briefly",
        "summarize", "list", "who is", "when did",
    ]
    if any(query_lower.startswith(p) for p in simple_patterns) or word_count < 10:
        return "simple"

    # COMPLEX: deep legal analysis
    complex_patterns = [
        "analyse", "analyze", "case analysis", "constitutional",
        "precedent", "multi-party", "appeal", "supreme court",
        "constitutional validity", "judicial review", "writ petition",
        "public interest litigation", "pil", "detailed analysis",
        "compare and contrast", "evaluate the legality",
    ]
    if any(p in query_lower for p in complex_patterns) or word_count > 100:
        return "complex"

    # MEDIUM: standard legal questions
    return "medium"


# ════════════════════════════════════════════════════════════════════════
# STREAMING / SSE
# ════════════════════════════════════════════════════════════════════════
ENABLE_STREAMING = True
SSE_HEARTBEAT_INTERVAL = 15  # seconds — send keepalive comment to prevent proxy timeout
SSE_BUFFER_SIZE = 1024  # max bytes per SSE event


# ════════════════════════════════════════════════════════════════════════
# REDIS CACHE
# ════════════════════════════════════════════════════════════════════════
CACHE_ENABLED = os.environ.get("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL_HOURS = int(os.environ.get("CACHE_TTL_HOURS", "24"))  # cache LLM responses for 24h


# ════════════════════════════════════════════════════════════════════════
# DATABASE
# ════════════════════════════════════════════════════════════════════════
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    os.environ.get("NEON_DATABASE_URL", ""),
)
DB_POOL_MIN = 2
DB_POOL_MAX = 10
DB_COMMAND_TIMEOUT = 30


# ════════════════════════════════════════════════════════════════════════
# FEATURE FLAGS
# ════════════════════════════════════════════════════════════════════════
FEATURE_FLAGS = {
    "voice_input": True,
    "voice_output": True,
    "thinking_panel": True,
    "streaming_chat": True,
    "redis_cache": bool(REDIS_URL),
    "rate_limiting": True,
    "jwt_auth": ENFORCE_AUTH,
    "moat_evolution": True,
    "agent_network": True,
    "ai_judge": True,
    "verifiers": True,
    "rag_engine": True,
}


# ════════════════════════════════════════════════════════════════════════
# SCAN ATTEMPTS — paths blocked by the catch-all route
# ════════════════════════════════════════════════════════════════════════
BLOCKED_SCANNER_PATHS = [
    "/.env",
    "/.env.local",
    "/.env.production",
    "/.streamlit/secrets.toml",
    "/file=../.env",
    "/file=../../.env",
    "/api/config",
    "/api/predict",
]


# ════════════════════════════════════════════════════════════════════════
# LLM PROVIDER KEYS (read from env — never hardcode)
# ════════════════════════════════════════════════════════════════════════
LLM_PROVIDERS = {
    "sarvam": {
        "api_key": os.environ.get("SARVAM_API_KEY", ""),
        "base_url": "https://api.sarvam.ai/v1",
        "models": ["sarvam-105b", "sarvam-30b"],
    },
    "groq": {
        "api_key": os.environ.get("GROQ_API_KEY", ""),
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"],
    },
    "openai": {
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini"],
    },
    "gemini": {
        "api_key": os.environ.get("GEMINI_API_KEY", ""),
        "base_url": "https://generativelanguage.googleapis.com/v1",
        "models": ["gemini-2.0-flash", "gemini-pro"],
    },
    "deepseek": {
        "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "openrouter": {
        "api_key": os.environ.get("OPENROUTER_API_KEY", ""),
        "base_url": "https://openrouter.ai/api/v1",
        "models": ["auto", "anthropic/claude-3.5-sonnet"],
    },
}
