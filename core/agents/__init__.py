# core/agents/__init__.py
# Agent package initialization

from core.agents.registry import (
    get_all_agents,
    get_agent,
    get_agents_by_category,
    get_agent_categories,
    get_agents_by_jurisdiction,
    search_agents,
    get_agent_stats
)

from core.agents.orchestrator import orchestrator, AgentOrchestrator
from core.agents.self_correction import SelfCorrection
from core.agents.verification import VerificationEngine

__all__ = [
    'get_all_agents',
    'get_agent',
    'get_agents_by_category',
    'get_agent_categories',
    'get_agents_by_jurisdiction',
    'search_agents',
    'get_agent_stats',
    'orchestrator',
    'AgentOrchestrator',
    'SelfCorrection',
    'VerificationEngine'
]