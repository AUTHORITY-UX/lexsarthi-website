"""
Offline Sovereign Stack for Unknown Verdict v43.0
Manages all offline components: LLM, RAG, Agents, Audio, Graph.
"""

from .offline_stack import OfflineStack, get_offline_stack

__all__ = [
    "OfflineStack",
    "get_offline_stack",
]