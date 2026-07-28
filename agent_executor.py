# agent_executor.py - Parallel agent execution
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ⚖️ THE ADVOCACY – Global Law Firm

import asyncio
import logging
from typing import List, Dict, Optional

from agent_registry import AgentRegistry
from llm_client import call_llm  # we'll implement a wrapper for OpenAI/Groq/Gemini

logger = logging.getLogger(__name__)

class AgentExecutor:
    def __init__(self):
        self.registry = AgentRegistry()

    async def execute_agents(
        self,
        agents: List[Dict],
        query: str,
        jurisdiction: str = "IN",
        files: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """Run each agent with its persona, memory, and domain‑specific RAG."""
        tasks = []
        for agent in agents:
            tasks.append(self._run_single_agent(agent, query, jurisdiction, files))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Filter out exceptions
        return [r for r in results if isinstance(r, dict) and 'error' not in r]

    async def _run_single_agent(self, agent: Dict, query: str, jurisdiction: str, files: List[Dict] = None) -> Dict:
        try:
            # 1. Build system prompt
            system_prompt = self._build_prompt(agent, jurisdiction)

            # 2. Retrieve relevant memories (RAG) – top‑5 from agent's memory
            memories = await self.registry.semantic_search(
                query=query,
                filters={"agent_id": agent['id']},
                top_k=5
            )
            memory_context = "\n".join([m['query'] + " → " + m['response'] for m in memories])

            # 3. If files provided, add extracted content (document intelligence)
            file_context = ""
            if files:
                from document_extractor import DocumentExtractor
                extractor = DocumentExtractor()
                extracted = await extractor.extract_from_files(files)
                file_context = "\n".join([f"Document {i+1}: {e['summary']}" for i, e in enumerate(extracted)])

            user_prompt = f"Query: {query}\nJurisdiction: {jurisdiction}"
            if memory_context:
                user_prompt += f"\nRelevant prior interactions:\n{memory_context}"
            if file_context:
                user_prompt += f"\nDocuments provided:\n{file_context}"

            # 4. Call LLM
            response_text = await call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                provider="groq"  # fallback
            )
            # 5. Store interaction in memory (async)
            asyncio.create_task(self.registry.log_memory(
                agent_id=agent['id'],
                query=query,
                response=response_text,
                verdict={"confidence": "pending"}
            ))
            return {
                "agent_id": agent['id'],
                "agent_name": agent['name'],
                "domain": agent['domain'],
                "response": response_text,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Agent {agent.get('id')} failed: {e}")
            return {"agent_id": agent.get('id'), "error": str(e)}

    def _build_prompt(self, agent: Dict, jurisdiction: str) -> str:
        base = f"You are a {agent['category']} specialist in {agent['domain']}. "
        base += agent.get('persona_prompt', 'Use deep expertise.')
        base += f" Jurisdiction: {jurisdiction}."
        if agent.get('statutes'):
            base += f" Relevant statutes: {', '.join(agent['statutes'])}."
        if agent.get('key_sections'):
            base += f" Key sections: {', '.join(agent['key_sections'])}."
        return base