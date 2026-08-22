import asyncio
from typing import List, Dict, Optional
from core.agents.registry import get_agent, get_agents_by_category, get_all_agents
from core.llm.router import get_router
from core.llm.ollama_provider import LLMMessage

class AgentOrchestrator:
    def __init__(self):
        self.router = get_router()
    
    async def execute_agent(self, agent_id: str, task: str, context: Optional[Dict] = None):
        agent = get_agent(agent_id)
        if not agent:
            return {"error": f"Agent {agent_id} not found"}
        
        system_prompt = f"""
        You are {agent['name']} – a {agent['category']} expert.
        Jurisdiction: {agent['jurisdiction']}
        
        Provide:
        1. Analysis
        2. Key findings
        3. Recommendations
        4. Relevant laws/sections cited
        
        IMPORTANT: Zero data retention – this session is ephemeral.
        """
        
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=task)
        ]
        
        response = await self.router.chat(messages, complexity="complex")
        return {
            "agent_id": agent_id,
            "agent_name": agent['name'],
            "category": agent['category'],
            "response": response.content,
            "provider": response.provider,
            "latency_ms": response.latency_ms
        }
    
    async def execute_multi_agent(self, agent_ids: List[str], task: str) -> List[Dict]:
        tasks = [self.execute_agent(aid, task) for aid in agent_ids]
        results = await asyncio.gather(*tasks)
        return results
    
    async def orchestrate(self, task: str, categories: Optional[List[str]] = None):
        if categories:
            agents = {}
            for cat in categories:
                agents.update(get_agents_by_category(cat))
        else:
            agents = get_all_agents()
        
        agent_ids = list(agents.keys())[:50]
        results = await self.execute_multi_agent(agent_ids, task)
        
        return {
            "task": task,
            "agents_used": len(agent_ids),
            "total_agents": len(agents),
            "results": results,
            "zero_data_retention": True
        }

orchestrator = AgentOrchestrator()