# 🔱 Unknown Verdict Moat v41.0 — Deployment Guide

## What This Adds to Your v40.0

The moat package adds 11 self-evolving intelligence layers to your existing platform:

| Feature | Module | Endpoint Prefix |
|--------|--------|-----------------|
| 1. Self-Evolving Agents | `evolution.py` | `/api/moat/evolution/*` |
| 2. IRAC Reasoning Engine | `reasoning.py` | `/api/moat/irac/*` |
| 3. Dynamic RAG with Auto-Expansion | `dynamic_rag.py` | `/api/moat/rag/*` |
| 4. AI Judge Evolution | `judge_evolution.py` | `/api/moat/judge/*` |
| 5. Predictive Analytics | `predictive.py` | `/api/moat/predict/*` |
| 6. Emotion-Aware Analysis | `emotion.py` | `/api/moat/emotion/*` |
| 10. Strategy Generator | `strategy.py` | `/api/moat/strategy/*` |
| 11. IP Vault & Forensics | `vault.py` | `/api/moat/vault/*` |
| 14. Outcome-Based Pricing | `pricing.py` | `/api/moat/pricing/*` |
| 16. Auto-Publishing | `publishing.py` | `/api/moat/publishing/*` |
| 17-18. Marketplace | `marketplace.py` | `/api/moat/marketplace/*` |

All modules use your existing Neon Postgres + pgvector (384-dim) and reuse your existing `sarvam_client`.

---

## Step 1: Run the Neon Migration (2 minutes)

Open your Neon SQL Editor and run `migration.sql`. This creates 12 new `moat_*` tables alongside your existing `agents`, `knowledge_chunks`, `deliberations`, etc. Your existing tables are untouched.

```sql
-- Verify after running migration.sql:
SELECT 'moat_learnings', COUNT(*) FROM moat_learnings
UNION ALL SELECT 'moat_reasoning_patterns', COUNT(*) FROM moat_reasoning_patterns;
```

## Step 2: Copy the moat/ Package (1 minute)

Copy the `moat/` directory into your project:

```
unknown_verdict/
  ├── app.py          ← existing
  ├── config.py       ← existing
  ├── core/           ← existing
  ├── sarvam/         ← existing
  ├── routes/         ← existing
  ├── static/         ← existing
  └── moat/           ← NEW (copy this entire directory)
      ├── __init__.py
      ├── db.py
      ├── embeddings.py
      ├── sarvam.py
      ├── evolution.py
      ├── reasoning.py
      ├── dynamic_rag.py
      ├── judge_evolution.py
      ├── predictive.py
      ├── emotion.py
      ├── strategy.py
      ├── vault.py
      ├── pricing.py
      ├── publishing.py
      ├── marketplace.py
      └── routes.py
```

## Step 3: Edit app.py (2 lines)

Add these two lines to your `app.py` after your existing router include:

```python
# Existing line (already in your app.py):
app.include_router(router, prefix="/api")

# ADD THESE TWO LINES:
from unknown_verdict.moat import install_moat
install_moat(app)
```

That's it. The moat routes mount at `/api/moat/*` and the DB connection initializes on first request.

## Step 4: Add sentence-transformers to requirements.txt

```
sentence-transformers>=2.2.0
asyncpg>=0.29.0
```

If `sentence-transformers` is already in your requirements (you're using it for your existing embeddings), you only need `asyncpg`.

## Step 5: Deploy to HF Spaces

Push to your HF Space repo. The moat will auto-initialize on startup. Your existing 250 agents, 15 verifiers, AI Judge, and all 36 endpoints continue to work unchanged.

## Step 6: Add the Frontend Panel (optional)

In your `static/index.html`, add the moat navigation item and panel. See `moat_frontend.py` for the HTML/JS to paste in. Or just use the API directly at `/docs` — all moat endpoints appear in your existing Swagger docs.

---

## API Endpoints (32 new)

### Feature 1 — Self-Evolving Agents
- `POST /api/moat/evolution/record` — Record a learning from an interaction
- `POST /api/moat/evolution/recall` — Semantic search over past learnings
- `POST /api/moat/evolution/mesh` — Query the knowledge mesh (shared across all agents)
- `POST /api/moat/evolution/training-data/{agent_id}` — Generate Q&A pairs from successes
- `POST /api/moat/evolution/detect-gap` — Detect knowledge gaps and auto-create agents

### Feature 2 — IRAC Reasoning
- `POST /api/moat/irac/reason` — Generate IRAC analysis with precedent weighting
- `POST /api/moat/irac/cross-jurisdiction` — Cross-reference across jurisdictions
- `POST /api/moat/irac/search` — Search stored reasoning patterns

### Feature 3 — Dynamic RAG
- `POST /api/moat/rag/add` — Add a document with auto-chunking and embedding
- `POST /api/moat/rag/search` — Semantic search across your knowledge base
- `GET /api/moat/rag/crawl` — Trigger auto-crawl of legal sources
- `GET /api/moat/rag/versions/{citation}` — Get version history for a citation

### Feature 4 — AI Judge Evolution
- `POST /api/moat/judge/verdict` — Deliver a verdict (learns from each one)
- `POST /api/moat/judge/resolve` — Provide feedback to close the learning loop
- `GET /api/moat/judge/stats` — Judge evolution statistics

### Feature 5 — Predictive Analytics
- `POST /api/moat/predict/outcome` — Case outcome probability
- `POST /api/moat/predict/settlement` — Settlement likelihood
- `POST /api/moat/predict/timeline` — Litigation timeline estimate
- `POST /api/moat/predict/cost` — Legal cost prediction

### Feature 6 — Emotion-Aware Analysis
- `POST /api/moat/emotion/analyze` — Detect emotion and generate empathetic response

### Feature 10 — Strategy Generator
- `POST /api/moat/strategy/generate` — Generate winning strategy with opposing arguments

### Feature 11 — IP Vault & Forensics
- `GET /api/moat/vault/audit` — View forensic audit trail
- `GET /api/moat/vault/audit/{entity_id}` — Audit trail for a specific entity
- `GET /api/moat/vault/verify/{entity_id}` — Verify integrity of an audit chain
- `GET /api/moat/vault/inventory` — IP inventory count

### Feature 14 — Outcome-Based Pricing
- `POST /api/moat/pricing/case` — Generate outcome-based pricing
- `POST /api/moat/pricing/value-report` — Generate client value report

### Feature 16 — Auto-Publishing
- `POST /api/moat/publishing/article` — Generate legal article (for advocacayalawfrim.in)
- `POST /api/moat/publishing/newsletter` — Generate weekly newsletter
- `POST /api/moat/publishing/social` — Generate LinkedIn social post
- `GET /api/moat/publishing/drafts` — List content drafts

### Features 17-18 — Marketplace
- `POST /api/moat/marketplace/create` — Create a marketplace listing
- `GET /api/moat/marketplace/agents` — Browse agent marketplace
- `GET /api/moat/marketplace/templates` — Browse legal templates
- `POST /api/moat/marketplace/search` — Search marketplace
- `POST /api/moat/marketplace/match` — Match client with appropriate lawyer/agent

### System
- `GET /api/moat/status` — Moat system status and DB stats

---

## How It Connects to Your v40.0

The moat is designed as a **pure additive layer** — it does not modify any of your existing code:

- **Sarvam AI**: The moat calls `from ..sarvam.client import sarvam_client` — your existing client. No duplicate API keys.
- **Agents**: The evolution engine tries to register new agents in your `agent_registry` when gaps are detected. If your registry doesn't support `register()`/`add()`, it just logs a warning and continues.
- **Database**: Uses your existing `DATABASE_URL` from `config.py`. Creates its own `moat_*` tables. Also writes to your existing `knowledge_chunks` table for RAG.
- **Embeddings**: Uses `all-MiniLM-L6-v2` (384-dim) — the same model your existing schema uses. Falls back to hash-based embeddings if `sentence-transformers` isn't installed.
- **Frontend**: All endpoints appear in your existing `/docs` Swagger UI automatically.

## Secrets Used

All from your existing HF Space secrets:
- `DATABASE_URL` — Neon Postgres connection string
- `SARVAM_API_KEY` — for LLM reasoning
- `REDIS_URL` — optional, for caching (works without it)
- `JWT_SECRET` — your existing auth (moat doesn't override it)

No new secrets required.
