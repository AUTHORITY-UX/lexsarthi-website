# Advocacy AI API Reference

Version: 1.0 · Generated from the FastAPI route surface
Base URL: https://www.advocacyalawfrim.in

## Start here

The complete interactive contract is exposed by **/docs** (Swagger UI), **/redoc** (Redoc), and **/openapi.json**. The branded reference is available at **/api-docs**. This document is the copy-friendly companion for implementation teams.

> Public AI output is decision support, not legal advice. Agent-authored newsroom content is labeled agent-draft and requires qualified human review before reliance or publication. Never send secrets, passwords, private keys, or unnecessary personal legal facts in a request.

## Request conventions

- JSON requests use Content-Type: application/json.
- Protected routes use Authorization: Bearer <access_token>.
- Use a stable session_id when continuing a chat.
- Treat model, confidence, and agents_used as metadata—not a guarantee of correctness.
- Use HTTPS only; keep tokens in server-side session storage in production.

## Authentication

### Register

POST /api/publication/auth/register

Input:

~~~json
{
  "email": "operator@example.com",
  "password": "at-least-10-characters",
  "full_name": "Workspace operator"
}
~~~

Output:

~~~json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {"id": "<uuid>", "email": "operator@example.com", "full_name": "Workspace operator", "role": "member"}
}
~~~

### Login

POST /api/publication/auth/login

Input: {"email":"operator@example.com","password":"at-least-10-characters"}

Output: the same token envelope as registration. Invalid credentials return a generic 401 response.

### Current user

GET /api/publication/auth/me

Header: Authorization: Bearer <access_token>

Output: {"sub":"<uuid>","email":"operator@example.com","role":"member","iat":0,"exp":0}

## Core modules

### System

GET /health — liveness probe.

Output: { "status": "healthy", "timestamp": "2026-09-01T00:00:00+00:00" }

GET /status — service, database, model, agent, and uptime summary.

GET /providers — configured provider availability; secrets are never returned.

### Chat and legal intelligence

POST /api/chat

Input:

~~~json
{
  "message": "Create a DPDPA control checklist for a SaaS vendor",
  "service": "compliance",
  "context": "Indian customer data; B2B SaaS",
  "jurisdiction": "India",
  "session_id": "optional-session-id"
}
~~~

Output:

~~~json
{
  "response": "<answer>",
  "service": "compliance",
  "jurisdiction": "India",
  "agents_used": ["<agent>", "<verifier>"],
  "model": "<provider-or-fallback>",
  "timestamp": "<iso-8601>"
}
~~~

### Agents

POST /agents/{agent_id}/task — Input {"task":"...","context":"..."}; output contains the agent result and verification metadata.

GET /agents, GET /agents/categories, GET /agents/top, GET /agents/stats, GET /agents/jurisdictions — roster, category, ranking, statistics, and jurisdiction discovery.

### Newsroom

GET /api/publication/feed?limit=6&category=AI%20governance

Output:

~~~json
{
  "articles": [{
    "slug": "ai-governance-risk-to-evidence",
    "title": "AI governance works when risk has an owner",
    "summary": "<summary>",
    "body": "<article body>",
    "category": "AI governance",
    "agent_name": "Nyaya-21",
    "agent_category": "AI Safety",
    "verification_status": "agent-draft",
    "published_at": "<iso-8601>"
  }],
  "total": 1,
  "editorial_policy": "Agent drafts are informational and require human review before reliance."
}
~~~

POST /api/publication/articles is admin-only. It accepts title, summary, body, category, agent_name, and agent_category. Every write is stored as agent-draft and returns a human-review next step.

### Compliance and governance

POST /compliance/dpdpa-check — Input {"document":"<policy or control text>","jurisdiction":"India"}; output is a structured check with findings and recommendations.

POST /compliance/gdpr-check and POST /compliance/eu-ai-check follow the same document-in / findings-out pattern for their regimes.

POST /privacy/scan — Input {"text":"<text>","scan_type":"compliance","regulation":"dpdpa"}; output contains detected issues and a scan summary.

POST /governance/draft — Input {"title":"...","content":"...","policy_type":"ai-use","stakeholders":["Legal","Security"]}; output is a draft policy with status metadata.

### Legal research and review

POST /legal/research — Input {"query":"...","context":"...","jurisdiction":"India","max_sources":5}; output returns research text and source metadata.

POST /review — Input {"document":"...","review_type":"contract","jurisdiction":"India","depth":"standard"}; output returns review findings.

POST /law/multi-jurisdiction — Input {"query":"...","jurisdictions":["India","EU"]}; output compares jurisdictional considerations.

### Domain and company services

POST /domain/scan — Input {"domain":"example.com"}; output returns domain/security observations.

POST /company/audit-report — Input {"company_name":"Example Pvt Ltd","industry":"SaaS","jurisdiction":"india","documents":{},"generate_pdf":true}; output returns an audit report and optionally a report artifact.

### Search, graph, voice, and MOAT

Use the generated /docs contract for the full schemas for graph search, vector search, embeddings, voice transcription/synthesis, web search, MOAT intelligence, feedback, audit, inventory, and configuration. These are separated into tagged modules in Swagger so request and response models stay discoverable.

## Error envelope

FastAPI validation errors return 422 with detail entries containing loc, msg, and type. Authentication failures return 401; insufficient editorial privileges return 403; rate limits return 429; unavailable database/provider dependencies return 503. Do not expose stack traces or provider credentials to clients.

## Complete endpoint inventory

The inventory below is generated from the checked-in route decorators and includes the publication module. For exact request schemas, open /openapi.json; Swagger Try it out should only use non-sensitive test data.

### Agents

- **GET /agents**
- **GET /agents/categories**
- **GET /agents/top**
- **GET /agents/stats**
- **GET /agents/jurisdictions**
- **POST /agents/search**
- **GET /agents/{agent_id}**
- **POST /agent/{agent_id}/task**
- **POST /agents/evolve**

### Auth

- **POST /auth/register**
- **POST /auth/login**
- **POST /auth/logout**
- **POST /auth/refresh**
- **GET /auth/me**
- **PUT /auth/update**
- **DELETE /auth/delete**

### Chat

- **POST /api/chat**
- **POST /api/chat/stream**
- **GET /api/chat/history**
- **POST /api/chat/save**
- **GET /api/chat/export**

### Company

- **POST /company/audit-report**
- **POST /company/complete-audit**

### Compliance

- **POST /compliance/dpdpa-check**
- **POST /compliance/gdpr-check**
- **POST /compliance/eu-ai-check**

### Domain

- **POST /domain/scan**

### Evolution

- **GET /api/evolution/proposals**
- **POST /api/evolution/submit**
- **POST /api/evolution/approve/{proposal_id}**
- **POST /api/evolution/reject/{proposal_id}**
- **POST /api/evolution/deploy/{proposal_id}**
- **POST /api/evolution/rollback/{proposal_id}**
- **GET /api/evolution/history**
- **GET /api/evolution/status**

### Frontend

- **GET /third-eye**
- **GET /chat**

### General

- **WEBSOCKET /ws/third-eye**
- **WEBSOCKET /ws/chat/{session_id}**
- **GET /api/publication/health**
- **GET /api/publication/feed**
- **GET /api/publication/articles/{slug}**
- **GET /api/publication/agents**
- **POST /api/publication/auth/register**
- **POST /api/publication/auth/login**
- **GET /api/publication/auth/me**
- **POST /api/publication/articles**

### Graph

- **GET /graph/status**
- **POST /graph/search**
- **GET /graph/neighbors/{node}**
- **GET /graph/nodes**
- **GET /graph/path**
- **GET /graph/stats**

### InCaseLawBERT

- **GET /incase/status**
- **POST /incase/embed**
- **POST /incase/similarity**

### Legal

- **POST /legal-research**
- **POST /legal/case-law**
- **POST /legal/contract/analyze**
- **POST /legal/compliance/check**
- **GET /legal/jurisdiction**
- **POST /legal/summarize**
- **POST /legal/translate**

### MOAT

- **GET /moat**
- **GET /moat/status**
- **GET /moat/ethics-status**
- **POST /moat/intelligence**
- **GET /moat/intelligence**
- **GET /moat/intelligence/all**
- **POST /moat/evolution**
- **GET /moat/evolution/history**
- **GET /moat/evolution/latest**
- **POST /moat/knowledge**
- **GET /moat/knowledge**
- **GET /moat/knowledge/domains**
- **POST /moat/verifiers**
- **GET /moat/verifiers**
- **POST /moat/verifiers/{verifier_name}/run**
- **POST /moat/agents**
- **GET /moat/agents**
- **POST /moat/agents/{agent_id}/run**
- **POST /moat/judge**
- **GET /moat/judge/history**
- **GET /moat/judge/{ruling_id}**
- **POST /moat/ip-vault**
- **GET /moat/ip-vault**
- **POST /moat/inventory**
- **GET /moat/inventory**
- **POST /moat/patterns**
- **GET /moat/patterns**
- **POST /moat/feedback**
- **GET /moat/feedback**
- **POST /moat/audit**
- **GET /moat/audit**
- **GET /moat/cache/stats**
- **DELETE /moat/cache/clear**
- **GET /moat/config**
- **POST /moat/config/update**

### Marketing

- **POST /api/marketing/draft**
- **GET /api/marketing/drafts**
- **GET /api/marketing/download/{draft_id}**
- **POST /api/marketing/publish**
- **POST /api/marketing/schedule**
- **GET /api/marketing/analytics**

### Multi-Jurisdiction

- **GET /law/jurisdictions**
- **POST /law/multi-jurisdiction**
- **POST /law/comparative**
- **POST /law/us**
- **POST /law/uk**
- **POST /law/eu**

### News

- **GET /api/news**
- **GET /api/news/live**
- **GET /api/news/categories**
- **POST /api/news/search**
- **GET /api/news/trending**

### Observability

- **GET /api/god/view**
- **GET /api/trace/{trace_id}**
- **GET /api/traces**
- **POST /api/trace**
- **GET /api/third-eye/stream**

### Realtime

- **GET /agent/events**

### Search

- **POST /search/web**
- **POST /search/targeted**

### Services

- **GET /api/moat**
- **POST /api/moat**
- **POST /api/governance/draft**
- **GET /api/governance/list**
- **POST /api/review**
- **POST /api/review/batch**
- **POST /api/privacy/scan**
- **GET /api/privacy/report**
- **POST /api/psychologist**
- **POST /api/psychologist/assess**

### System

- **GET /**
- **GET /status**
- **GET /health**
- **GET /providers**
- **GET /models**
- **GET /endpoints**
- **GET /metrics**
- **GET /version**

### Voice

- **POST /voice/transcribe**
- **POST /voice/synthesize**

### ZVec

- **GET /zvec/status**
- **POST /zvec/search**
- **POST /zvec/add**
- **POST /zvec/import**

## Deployment requirements

Required runtime settings:

- DATABASE_URL — Neon PostgreSQL connection string, stored as a secret.
- JWT_SECRET — high-entropy signing secret; no default in production.
- ADMIN_SECRET — optional separate editorial publishing key.
- ADMIN_EMAIL — optional first-admin email.
- ALLOWED_ORIGINS — comma-separated browser origins; do not use * with credentials.

The Python service must be deployed as the API origin. Cloudflare Pages alone serves static files and cannot execute this FastAPI application.
