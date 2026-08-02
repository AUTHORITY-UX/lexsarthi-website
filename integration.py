"""EvolutionMiddleware — auto-captures every /api/chat interaction.

This is the connective tissue between your live traffic and the self-evolving
intelligence layer.  It sits as a pure-ASGI middleware (no Starlette dependency,
no body-consumption bugs) and does exactly one thing:

    After a POST /api/chat response is fully sent to the client, it
    fire-and-forgets a learning record into moat_learnings via the
    evolution engine.

Design goals:
  * Zero latency impact — capture happens after the response is sent,
    via asyncio.create_task (truly fire-and-forget).
  * Never breaks a request — every code path is wrapped in try/except;
    if the DB is down, the moat is unavailable, or the response is not
    JSON, the user still gets their answer.
  * No new dependencies — uses only the existing evolution engine + db.
  * Zero moat imports in routes.py (the moat is mounted separately).
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

from loguru import logger as log

# Paths that should be captured (extend as you wire more endpoints)
CAPTURE_PATHS = {"/api/chat"}

# Map AI-Judge verdict types → evolution outcomes
_VERDICT_TO_OUTCOME: Dict[str, str] = {
    "approved": "success",
    "approved_with_notes": "success",
    "needs_revision": "neutral",
    "rejected": "failure",
    "escalated": "failure",
}


class EvolutionMiddleware:
    """Pure-ASGI middleware — works with ``app.add_middleware(EvolutionMiddleware)``."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Dict[str, Any],
        receive: Callable[[], Awaitable[Dict[str, Any]]],
        send: Callable[[Dict[str, Any]], Awaitable[None]],
    ) -> None:
        # Only intercept HTTP POST to capture paths; pass everything else through
        if (
            scope.get("type") != "http"
            or scope.get("method") != "POST"
            or scope.get("path") not in CAPTURE_PATHS
        ):
            await self.app(scope, receive, send)
            return

        await self._intercept(scope, receive, send)

    # ------------------------------------------------------------------
    # Core interception logic
    # ------------------------------------------------------------------

    async def _intercept(
        self,
        scope: Dict[str, Any],
        receive: Callable[[], Awaitable[Dict[str, Any]]],
        send: Callable[[Dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Buffer request + response, then fire a background learning task."""

        # --- 1. Buffer the request body (so we can replay it to the app) ---
        request_body = b""
        try:
            more_body = True
            while more_body:
                msg = await receive()
                if msg["type"] == "http.request":
                    request_body += msg.get("body", b"")
                    more_body = msg.get("more_body", False)
                elif msg["type"] == "http.disconnect":
                    # Client disconnected — just pass through
                    await self.app(scope, receive, send)
                    return
        except Exception:
            # If we can't read the request body, fall back to passthrough
            await self.app(scope, receive, send)
            return

        # Build a replay callable so the app gets its body
        replayed = False

        async def replay_receive() -> Dict[str, Any]:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {
                    "type": "http.request",
                    "body": request_body,
                    "more_body": False,
                }
            # Subsequent calls (shouldn't happen for non-streaming, but be safe)
            return {"type": "http.request", "body": b"", "more_body": False}

        # --- 2. Wrap send to capture the response body ---
        response_chunks: List[bytes] = []
        response_status = 200

        async def send_wrapper(message: Dict[str, Any]) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message.get("status", 200)
            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                if chunk:
                    response_chunks.append(chunk)
            # Always forward to the real send immediately — zero added latency
            await send(message)

        # --- 3. Run the actual app ---
        await self.app(scope, replay_receive, send_wrapper)

        # --- 4. Fire-and-forget learning capture (after response is sent) ---
        if response_status == 200 and response_chunks:
            response_body = b"".join(response_chunks)
            # create_task = truly non-blocking; errors are swallowed inside
            try:
                asyncio.create_task(
                    self._capture_learning(request_body, response_body)
                )
            except RuntimeError:
                # No running loop (shouldn't happen in ASGI, but be safe)
                pass

    # ------------------------------------------------------------------
    # Learning capture (runs in background, never raises)
    # ------------------------------------------------------------------

    async def _capture_learning(
        self, request_body: bytes, response_body: bytes
    ) -> None:
        """Parse the request/response pair and record a learning."""
        try:
            req = json.loads(request_body) if request_body.strip() else {}
            resp = json.loads(response_body) if response_body.strip() else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return  # Not JSON — nothing to capture

        try:
            query = req.get("message", "") or req.get("query", "")
            agent_response = resp.get("response", "")
            agent_id = resp.get("agent_id", "unknown")
            agent_name = resp.get("agent_name", "")
            specialization = resp.get("specialization", "")
            conversation_id = resp.get("conversation_id", "")

            verdict = resp.get("verdict", {})
            verdict_type = verdict.get("verdict_type", "unknown")
            score = float(verdict.get("score", 0.5))

            # Map verdict → outcome
            outcome = _VERDICT_TO_OUTCOME.get(verdict_type, "neutral")

            # Confidence delta: positive for success, negative for failure
            if outcome == "success":
                confidence_delta = max(0.0, score - 0.5)
            elif outcome == "failure":
                confidence_delta = -max(0.0, 0.5 - score)
            else:
                confidence_delta = 0.0

            if not query or not agent_response:
                return  # Nothing meaningful to learn from

            # Lazy-import to avoid circular dependencies at module load time
            from .evolution import evolution
            from .db import db

            if not db.available:
                # DB pool not initialised — silently skip.
                # The moat router's startup event should have called db.init(),
                # but if it failed (no DATABASE_URL) we don't want to crash.
                return

            result = await evolution.record_interaction(
                agent_id=agent_id,
                query=query,
                response=agent_response,
                outcome=outcome,
                confidence_delta=confidence_delta,
                interaction_id=conversation_id,
            )

            log.debug(
                f"🧬 Learning captured: agent={agent_id} "
                f"outcome={outcome} verdict={verdict_type} "
                f"stored={result.get('vector_indexed', False)}"
            )

        except Exception as e:
            # Never let capture failures leak to the user
            log.debug(f"EvolutionMiddleware capture error (suppressed): {e}")


# ----------------------------------------------------------------------
# Standalone helper — call from anywhere to manually record an interaction
# ----------------------------------------------------------------------

async def capture_interaction(
    agent_id: str,
    query: str,
    response: str,
    verdict_type: str = "unknown",
    score: float = 0.5,
    interaction_id: str = "",
) -> Optional[str]:
    """Manually record a learning outside the middleware.

    Useful for endpoints other than /api/chat (e.g. /api/legal/research)
    where you want the same auto-learning behaviour.

    Returns the learning_id, or None if capture failed.
    """
    try:
        from .evolution import evolution
        from .db import db

        if not db.available:
            return None

        outcome = _VERDICT_TO_OUTCOME.get(verdict_type, "neutral")
        delta = max(0.0, score - 0.5) if outcome == "success" else 0.0

        result = await evolution.record_interaction(
            agent_id=agent_id,
            query=query,
            response=response,
            outcome=outcome,
            confidence_delta=delta,
            interaction_id=interaction_id,
        )
        return result.get("learning_id")
    except Exception as e:
        log.debug(f"capture_interaction error: {e}")
        return None
