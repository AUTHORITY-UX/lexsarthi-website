"""Embedding service: 384-dim all-MiniLM-L6-v2 (matches your Neon schema)."""
from __future__ import annotations
import asyncio, hashlib
import numpy as np
from typing import List
from loguru import logger as log

_DIM = 384
_model = None

def _load():
    global _model
    if _model is not None: return _model
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        log.info("✅ Moat embeddings loaded (384-dim)")
    except Exception as e:
        log.warning(f"sentence-transformers unavailable: {e}")
    return _model

def _hash_embed(text, dim=_DIM):
    v = np.zeros(dim, dtype=np.float32)
    for i in range(0, dim, 8):
        h = hashlib.sha256(f"{text}:{i}".encode()).digest()
        for j in range(min(8, dim-i)): v[i+j] = (h[j]/255.0-0.5)*2
    n = np.linalg.norm(v)
    return (v/n).tolist() if n > 0 else v.tolist()

async def embed(text: str) -> List[float]:
    text = (text or "")[:8000]
    m = _load()
    if m is None: return _hash_embed(text)
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: m.encode(text).tolist())
    except Exception:
        return _hash_embed(text)

def get_dim() -> int:
    return _DIM
