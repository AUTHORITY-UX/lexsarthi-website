# Unknown Verdict v40.0 — Deployment Guide

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ with pgvector extension
- Redis 7+
- Sarvam AI API key (optional but recommended)

## Quick Start (Development)

```bash
# 1. Clone and install
git clone <your-repo-url>
cd unknown_verdict
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings

# 3. Run database migrations
alembic upgrade head

# 4. Start the server
uvicorn unknown_verdict.app:app --host 0.0.0.0 --port 7860 --reload

# 5. Run tests
pytest unknown_verdict/tests/ -v
```

## Production Deployment (Docker)

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "7860:7860"
    env_file: .env
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: unknown_verdict
      POSTGRES_USER: uv_user
      POSTGRES_PASSWORD: uv_password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

```bash
docker-compose up -d
```

### Hugging Face Spaces

The app is configured for HF Spaces (port 7860):

```bash
# The Procfile handles startup:
# web: uvicorn unknown_verdict.app:app --host 0.0.0.0 --port 7860
```

Set these secrets in HF Spaces Settings:
- `SARVAM_API_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `RAZORPAY_KEY_ID`

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SARVAM_API_KEY` | No | (empty) | Sarvam AI API key |
| `DATABASE_URL` | No | (localhost) | PostgreSQL connection string |
| `REDIS_URL` | No | (localhost) | Redis connection string |
| `JWT_SECRET` | **Yes** | (default) | JWT signing secret — CHANGE IN PRODUCTION |
| `RAZORPAY_KEY_ID` | No | (test) | Razorpay key ID |
| `INDIAN_KANOON_API_KEY` | No | (empty) | Indian Kanoon API key |
| `PORT` | No | 7860 | Server port |
| `LOG_LEVEL` | No | INFO | Logging level |
| `RATE_LIMIT_ENABLED` | No | True | Enable rate limiting |

## Authentication

### Default Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@unknownverdict.ai | admin123 |
| Guest | guest@unknownverdict.ai | guest123 |

**Change these immediately in production.**

### Using JWT

```bash
# Login to get tokens
curl -X POST http://localhost:7860/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@unknownverdict.ai", "password": "admin123"}'

# Use the access token
curl http://localhost:7860/api/agents/status \
  -H "Authorization: Bearer <your-access-token>"
```

### Using API Keys

```bash
# Create an API key
curl -X POST http://localhost:7860/api/auth/api-keys \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Key", "scopes": ["chat", "legal"]}'

# Use the API key
curl http://localhost:7860/api/chat \
  -H "X-API-Key: uv_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Article 21?"}'
```

## Monitoring

### Health Check

```bash
curl http://localhost:7860/health
```

### Prometheus Metrics

```bash
curl http://localhost:7860/metrics
```

## Database Migrations (Alembic)

```bash
# Generate a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Testing

```bash
# Run all tests
pytest unknown_verdict/tests/ -v

# Run only endpoint tests
pytest unknown_verdict/tests/test_endpoints.py -v

# Run with coverage
pytest unknown_verdict/tests/ --cov=unknown_verdict --cov-report=html

# Run performance tests
pytest unknown_verdict/tests/test_performance.py -v
```
