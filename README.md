---
title: LEX v41.0 - Unknown Verdict
emoji: ⚖️
colorFrom: indigo
colorTo: purple
sdk: docker
sdk_version: "1.0"
app_file: unknown_verdict/app.py
pinned: true
---
# Unknown Verdict v41.0

AI legal platform with multi-LLM routing, 250+ legal agents, 15 verifiers, AI Judge, and a self-evolving intelligence layer (Moat).

**Live:** https://upamnyu12-lex.hf.space  
**Docs:** https://upamnyu12-lex.hf.space/docs  
**HF Repo:** https://huggingface.co/spaces/upamnyu12/LEX

## What's New in v41

- **Multi-LLM routing** — 6 providers: Sarvam, OpenAI, Gemini, Groq, DeepSeek, OpenRouter
- **Intelligent fallback** — if one provider fails, the next takes over automatically
- **Complexity classification** — simple → Groq (<2s), complex → Sarvam 105B
- **Redis caching** — 80% cost reduction for repeated queries
- **SSE streaming** — first token in <1s
- **Null-response fix** — the null cascade that crashed verifiers and judge is gone
- **JWT auth + rate limiting** — enforced on all protected endpoints
- **68 endpoints** — 36 base + 32 moat

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Run locally (needs .env with secrets)
python -m unknown_verdict.app

# Or via Docker
docker build -t unknown-verdict .
docker run -p 7860:7860 --env-file .env unknown-verdict
```

## Health Check

```bash
python health_check.py https://upamnyu12-lex.hf.space
```

## Architecture

See [DEPLOY.md](DEPLOY.md) for full deployment guide and secret mapping.

## License

Proprietary. © Unknown Verdict.
