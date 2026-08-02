"""
Unknown Verdict v41.0 — Root-level entry point for HF Spaces.

This file sits at the repo root (app.py) and delegates everything to the
proper unknown_verdict package which has the full lifespan, CORS,
250 agents, 15 verifiers, AI Judge, RAG, and all 36 routes.

The moat (32 self-evolving intelligence endpoints) and the EvolutionMiddleware
(auto-captures every /api/chat interaction) are mounted here.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the repo root is on sys.path so `unknown_verdict` package resolves
_repo_root = str(Path(__file__).parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Import the REAL app (with lifespan, agents, verifiers, judge, all 36 routes)
from unknown_verdict.app import app  # noqa: E402

# Mount the Moat v41.0 self-evolving intelligence layer (32 endpoints)
try:
    from unknown_verdict.moat import install_moat
    install_moat(app)
except Exception as e:
    import logging
    logging.warning(f"Moat v41 not loaded: {e}")

# Add EvolutionMiddleware — auto-captures every /api/chat interaction
# and feeds it into the self-evolution system (fire-and-forget, zero latency)
try:
    from unknown_verdict.moat.integration import EvolutionMiddleware
    app.add_middleware(EvolutionMiddleware)
except Exception as e:
    import logging
    logging.warning(f"EvolutionMiddleware not loaded: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
