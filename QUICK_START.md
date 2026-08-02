# 🔱 Moat v41.0 — Quick Start (Go Live in 15 Minutes)

## What's in This Package

| File | Purpose |
|------|---------|
| `deploy.sh` | One-shot deployment script — copies moat/, patches app.py, updates requirements |
| `moat/` | The 17-module moat package (db, embeddings, evolution, reasoning, RAG, judge, etc.) |
| `moat/integration.py` | EvolutionMiddleware — auto-captures every /api/chat interaction |
| `flywheel_bootstrap.py` | Processes your deliberations table — seeds historical learnings |
| `moat_dashboard.html` | Live monitoring dashboard (copy into static/) |
| `lens_fix.py` | Diagnoses + fixes the /api/lens/agents 400 bug |
| `migration.sql` | Creates 12 moat_* tables in Neon (run in SQL Editor) |
| `DEPLOY.md` | Detailed deployment guide |
| `FRONTEND_INTEGRATION.md` | HTML/JS snippets for your existing index.html |

## Step-by-Step

### 1. Run Neon Migration (2 min)
Open https://console.neon.tech → SQL Editor → paste `migration.sql` → Run.
Creates 12 `moat_*` tables with `vector(384)`. Your existing tables are untouched.

### 2. Run deploy.sh (2 min)
```bash
cd /path/to/your/hf-space-repo
bash deploy.sh
```
This copies `moat/` into `unknown_verdict/moat/`, patches `app.py` with:
```python
from unknown_verdict.moat import install_moat
install_moat(app)
from unknown_verdict.moat.integration import EvolutionMiddleware
app.add_middleware(EvolutionMiddleware)
```
And adds `asyncpg` + `sentence-transformers` to requirements.txt.

### 3. Fix the Lens Bug (2 min)
Replace the `lens_agents` function in your `routes.py` (line ~1123) with the
version inside `lens_fix.py` (the `LENS_AGENTS_REPLACEMENT` variable).
The new version handles both agent search (query) and compliance scan (url)
instead of always requiring url.

### 4. Deploy to HF Spaces (1 min)
```bash
git add -A
git commit -m "feat: Moat v41.0 — self-evolving intelligence + evolution loop"
git push
```
Your space rebuilds. Check /docs for new /api/moat/* endpoints.

### 5. Seed the Flywheel (5 min)
```bash
export DATABASE_URL='your-neon-connection-string'
python flywheel_bootstrap.py --dry-run     # test first
python flywheel_bootstrap.py               # seed historical data
```
Processes your `deliberations` table, generates embeddings, seeds `moat_learnings`
and `agent_memories` with historical interactions.

### 6. Add the Dashboard (1 min)
Copy `moat_dashboard.html` into your `static/` directory.
Visit: https://upamnyu12-lex.hf.space/static/moat_dashboard.html

## What Happens After Deploy

Every `POST /api/chat` now automatically:
1. Runs your existing handler (agent, RAG, Sarvam, verifiers, judge) — unchanged
2. Middleware captures the response (agent_response, verdict.score, agent_id)
3. Background task: embeds the interaction, stores in moat_learnings + agent_memories
4. If confidence < 0.5: runs knowledge gap detection
5. Zero added latency to the user response (fire-and-forget)

The flywheel compounds: every interaction makes the next one smarter.
