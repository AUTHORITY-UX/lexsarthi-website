"""Unknown Verdict Moat v41.0 — Self-Evolving Legal Intelligence Layer."""
from __future__ import annotations
from .routes import moat_router
__version__ = "41.0.0"

def install_moat(app) -> None:
    app.include_router(moat_router, prefix="/api/moat")
    from loguru import logger as log
    log.info("🔱 Moat v41.0 installed — /api/moat/* endpoints active")
