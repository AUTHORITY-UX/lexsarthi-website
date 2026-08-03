"""Sarvam LLM wrapper — reuses existing v40.0 sarvam_client.

FIX: import path corrected. The sarvam/ package lives at the repo root,
NOT inside unknown_verdict/. The old `from ..sarvam.client import` resolved
to unknown_verdict.sarvam.client (which doesn't exist), causing:
    "No module named 'unknown_verdict.sarvam'"
on every call to sarvam_reason(). Changed to absolute import.
"""
from __future__ import annotations
from loguru import logger as log

async def sarvam_reason(prompt: str, system_prompt: str = "", temperature: float = 0.3, max_tokens: int = 4096) -> str:
    try:
        from sarvam.client import sarvam_client
        if not sarvam_client.is_configured: return ""
        r = await sarvam_client.reason(prompt=prompt, system_prompt=system_prompt, temperature=temperature, max_tokens=max_tokens)
        return r.content if r.success else ""
    except Exception as e:
        log.debug(f"sarvam_reason: {e}")
        return ""

def is_sarvam_available() -> bool:
    try:
        from sarvam.client import sarvam_client
        return sarvam_client.is_configured
    except Exception:
        return False
