# core/agents/__init__.py

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
from core.agents.self_correction import self_correction, SelfCorrectionLoop

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
    'self_correction',
    'SelfCorrectionLoop'
]