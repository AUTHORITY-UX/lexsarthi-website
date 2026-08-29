"""
Unified Offline Stack Manager – Loads all offline components lazily.
Supports 32.5M ZVec vectors, Local LLM, Graph RAG, and Audio.
"""

import logging
from typing import Optional, Dict, Any
from core.config import Config

logger = logging.getLogger(__name__)

class OfflineStack:
    """Manages all offline components: LLM, RAG, Agents, Audio, Graph."""

    def __init__(self):
        self._llm = None
        self._rag = None
        self._audio = None
        self._graph = None
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize all offline components."""
        if self._initialized:
            return True

        try:
            # Load LLM
            from core.llm.local_model import get_llm
            self._llm = get_llm()
            logger.info("✅ Offline LLM loaded")

            # Load RAG
            from core.rag.free_indian_rag import get_rag
            self._rag = get_rag()
            logger.info("✅ Offline RAG loaded")

            # Load Audio Agent (optional)
            if Config.ENABLE_AUDIO_AGENT:
                from core.agents.audio_agent import get_audio_agent
                self._audio = get_audio_agent()
                logger.info("✅ Audio Agent loaded")

            # Load Graph RAG (optional)
            if Config.ENABLE_GRAPH_RAG:
                from core.rag.graph_rag import get_graph_rag
                self._graph = get_graph_rag()
                logger.info("✅ Graph RAG loaded")

            self._initialized = True
            logger.info("✅ Offline stack initialized")
            return True

        except Exception as e:
            logger.error(f"❌ Offline stack init failed: {e}")
            return False

    def get_llm(self):
        return self._llm

    def get_rag(self):
        return self._rag

    def get_audio(self):
        return self._audio

    def get_graph(self):
        return self._graph

    def is_ready(self) -> bool:
        return self._initialized


# Singleton
_offline_stack = None

def get_offline_stack() -> OfflineStack:
    global _offline_stack
    if _offline_stack is None:
        _offline_stack = OfflineStack()
        _offline_stack.initialize()
    return _offline_stack