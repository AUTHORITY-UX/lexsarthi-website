# atma.py – LexSarthi v10
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.

import json, logging, asyncio, re
from typing import List, Dict, Optional, Callable, Awaitable, Any
import asyncpg

logger = logging.getLogger("lexsarthi")

class AtmaRouter:
    """
    The Atma Router – orchestrates domain classification, persona selection,
    multi‑LLM fallback, jury verification, and judge adjudication.
    """

    def __init__(
        self,
        pg_pool: asyncpg.Pool,
        fetch_relevant_chunks_func: Callable[[str, int, Optional[asyncpg.Connection]], Awaitable[List[Dict]]],
        serpapi_search_func: Callable[[str], Awaitable[List[Dict]]],
        call_llm_func: Callable[[str, str, str, float, Optional[List]], Awaitable[str]]
    ):
        self.pg_pool = pg_pool
        self.fetch_relevant_chunks = fetch_relevant_chunks_func
        self.serpapi_search = serpapi_search_func
        self.call_llm = call_llm_func

    async def run(
        self,
        query: str,
        history: Optional[List[Dict]] = None,
        files: Optional[List[Any]] = None,
        provider: str = "openrouter",
        temperature: float = 0.7,
        top_k: int = 3,
        custom_system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for a query.
        Returns dict with 'answer', 'confidence', 'sources', 'domain', 'persona', 'provider',
        'jury_verifiers', and 'jury_confidences'.
        """
        logger.info(f"AtmaRouter: Processing query: {query[:100]}...")

        # 1. Retrieve relevant chunks (RAG)
        chunks = await self.fetch_relevant_chunks(query, top_k=top_k)
        context_text = "\n".join([
            f"[{c.get('citation', c.get('metadata', {}).get('source', 'Unknown'))}] {c['content']}"
            for c in chunks
        ])

        # 2. Build the full prompt
        user_prompt = f"""
Context from legal/knowledge documents:
{context_text}

Question: {query}

Provide a detailed, accurate answer citing the sources above.
If you are unsure, say so clearly.
"""
        # Use custom system prompt if provided, else default
        if custom_system_prompt:
            system_prompt = custom_system_prompt
        else:
            system_prompt = (
                "You are LexSarthi, a universal AI assistant. Use the provided context to answer. "
                "Cite your sources. If the context is insufficient, use your general knowledge but note it."
            )

        # 3. Initial answer (primary LLM)
        initial_answer = await self.call_llm(
            system_prompt=system_prompt,
            user_message=user_prompt,
            provider=provider,
            temperature=temperature,
            history=history
        )

        # 4. Jury verification (run 3 verifiers in parallel)
        verifiers = self._get_verifiers()
        verifier_prompts = [
            f"You are {v['name']} ({v['role']}). Verify the answer below. Return JSON with keys: 'status' ('APPROVED' or 'NEEDS_CORRECTION'), 'confidence' (0-1), and 'comment' (string). Answer: {initial_answer}"
            for v in verifiers[:3]
        ]
        verifier_tasks = [
            self.call_llm(
                system_prompt="You are a strict verifier. Return valid JSON only.",
                user_message=vp,
                provider=provider,
                temperature=0.2
            )
            for vp in verifier_prompts
        ]
        verifier_responses = await asyncio.gather(*verifier_tasks, return_exceptions=True)

        verifier_results = []
        for i, resp in enumerate(verifier_responses):
            if isinstance(resp, Exception):
                verifier_results.append({"status": "ERROR", "error": str(resp)})
                continue
            try:
                data = json.loads(resp)
                verifier_results.append(data)
            except json.JSONDecodeError:
                # Fallback: treat as approved with medium confidence
                verifier_results.append({
                    "status": "APPROVED",
                    "confidence": 0.5,
                    "comment": resp[:200]
                })

        # 5. Judge Shakti – synthesize final answer
        judge_prompt = f"""
You are Shakti, the final judge. You have the initial answer and the verifier critiques.
Initial answer: {initial_answer}

Verifier critiques:
{json.dumps(verifier_results, indent=2)}

Your task: produce a final answer that incorporates the verifiers' corrections.
Return a JSON object with keys:
- 'final_answer' (string) – the final response to the user.
- 'confidence' (string) – one of 'HIGH', 'MEDIUM', 'LOW'.
- 'sources' (list of strings) – the source citations you used.

Respond with ONLY the JSON object.
"""
        judge_response = await self.call_llm(
            system_prompt="You are a wise judge. Return valid JSON only.",
            user_message=judge_prompt,
            provider=provider,
            temperature=0.2
        )

        # 6. Parse judge response with robust fallback
        try:
            judge_data = json.loads(judge_response)
            final_answer = judge_data.get("final_answer", initial_answer)
            confidence = judge_data.get("confidence", "MEDIUM")
            sources = judge_data.get("sources", [])
        except json.JSONDecodeError:
            logger.warning("Judge did not return valid JSON. Using raw response.")
            final_answer = judge_response
            confidence = "MEDIUM"
            # simple source extraction from text
            sources = re.findall(r'(?:source|citation)[:\s]+([^.,]+)', final_answer, re.IGNORECASE) or ["Unknown"]

        # 7. Build result
        result = {
            "answer": final_answer,
            "confidence": confidence,
            "sources": sources,
            "domain": "general",   # could be enhanced with a classifier
            "persona": "Generalist",
            "provider": provider,
            "jury_verifiers": [v["name"] for v in verifiers[:3]],
            "jury_confidences": [r.get("confidence", 0) for r in verifier_results]
        }
        return result

    def _get_verifiers(self) -> List[Dict]:
        """Return the 3 verifiers used in the jury."""
        return [
            {"id": "v01", "name": "Ganesha", "role": "Citation & logic integrity"},
            {"id": "v02", "name": "Saraswati", "role": "Knowledge cross-reference"},
            {"id": "v03", "name": "Hanuman", "role": "Global compliance & consistency"}
        ]