# agent_executor.py (updated) – with safety interception

from safety_monitor import get_safety_monitor, ActionType

class AgentExecutor:
    # ...

    async def _run_single_agent(self, agent: Dict, query: str, jurisdiction: str, files=None):
        safety = get_safety_monitor()

        # 1. Intercept LLM call
        llm_payload = {
            "prompt": query,
            "agent_id": agent['id'],
            "model": "groq"
        }
        verdict = await safety.intercept_action(
            agent_id=agent['id'],
            action_type=ActionType.LLM_CALL,
            payload=llm_payload
        )
        if verdict['verdict'] in ['blocked', 'killed']:
            return {"agent_id": agent['id'], "error": verdict['reason']}

        # 2. Proceed with LLM call (as before)
        # ... call_llm ...

        # 3. Intercept any file writes (if any)
        # Example: if response contains file path, check
        # ...

        # 4. Return result
        return {
            "agent_id": agent['id'],
            "response": response_text,
            "safety_verdict": verdict['verdict'],
            "timestamp": datetime.now().isoformat()
        }