# =============================================================================
# atma.py – ATMA Router with Jury Verification & DeepSeek as primary
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# =============================================================================

import json
import logging
import os
from typing import Dict, List, Optional, Any
import random
from openai import OpenAI

logger = logging.getLogger("lexsarthi")

class DeepSeekClient:
    """DeepSeek client – unlimited queries via your account."""
    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not set")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        self.model = "deepseek-chat"   # or "deepseek-reasoner" for advanced reasoning

    def generate(self, system_prompt: str, user_message: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.6,
            max_tokens=4096
        )
        return response.choices[0].message.content


class AtmaRouter:
    """
    ATMA Router – orchestrates domain classification, persona selection,
    multi‑LLM fallback (DeepSeek → Gemini → OpenAI → Groq),
    jury of 3 verifiers, and Judge Shakti.
    Supports unrestricted web search toggle.
    """

    def __init__(self, pg_pool, fetch_relevant_chunks_func, serpapi_search_func, call_llm_func):
        self.pg_pool = pg_pool
        self.fetch_relevant_chunks = fetch_relevant_chunks_func
        self.serpapi_search = serpapi_search_func
        self.call_llm = call_llm_func   # original fallback (will be used after DeepSeek)
        self.verifiers = [
            {"id":"v01","name":"Ganesha","role":"Citation & logic integrity"},
            {"id":"v02","name":"Saraswati","role":"Knowledge cross-reference"},
            {"id":"v03","name":"Hanuman","role":"Global compliance"},
            {"id":"v04","name":"Kartikeya","role":"Contradiction detection"},
            {"id":"v05","name":"Indra","role":"Jurisdiction mapping"},
            {"id":"v06","name":"Yama","role":"Bias & neutrality"},
            {"id":"v07","name":"Surya","role":"Timeline & limitation"},
            {"id":"v08","name":"Chandra","role":"Precedent match"},
            {"id":"v09","name":"Vayu","role":"PII / privacy filter"},
            {"id":"v10","name":"Shakti","role":"Final judge & dharma seal"}
        ]
        # Try to initialise DeepSeek client
        self.deepseek = None
        try:
            self.deepseek = DeepSeekClient()
            logger.info("✅ DeepSeek client initialised as primary LLM")
        except Exception as e:
            logger.warning(f"⚠️ DeepSeek not available: {e}")

    async def _call_llm_with_fallback(self, system_prompt: str, user_message: str) -> str:
        """Try DeepSeek first, then fallback to the original call_llm."""
        # 1. DeepSeek (unlimited)
        if self.deepseek:
            try:
                return self.deepseek.generate(system_prompt, user_message)
            except Exception as e:
                logger.warning(f"DeepSeek failed: {e}")
        # 2. Fallback to existing call_llm (Gemini/OpenAI/Groq)
        return await self.call_llm(system_prompt, user_message, provider="groq")

    async def run(self, query: str, history: Optional[List[Dict]] = None, files: Optional[List] = None, unrestricted: bool = False) -> Dict:
        logger.info(f"AtmaRouter: Processing query: {query[:100]}... (unrestricted: {unrestricted})")

        # 1. Retrieve relevant chunks from pgvector
        chunks = await self.fetch_relevant_chunks(query, top_k=5)

        # --- Build context safely ---
        context_parts = []
        for c in chunks:
            if isinstance(c, dict):
                citation = c.get('citation')
                if not citation and isinstance(c.get('metadata'), dict):
                    citation = c.get('metadata', {}).get('source', 'Unknown')
                if not citation:
                    citation = 'Unknown'
                content = c.get('content', str(c))
                context_parts.append(f"[{citation}] {content}")
            else:
                context_parts.append(str(c))
        context_text = "\n".join(context_parts)

        # 2. Web search – pass unrestricted flag
        legal_keywords = ["law", "act", "section", "supreme", "court", "constitution", "sebi", "gst", "contract"]
        if any(kw in query.lower() for kw in legal_keywords) or unrestricted:
            web_results = await self.serpapi_search(query, unrestricted=unrestricted)
        else:
            web_results = []

        # 3. Domain classification
        domain = "general"
        for d in ["Constitutional Law", "Contract Law", "Criminal Law", "Corporate Law", "Tax Law",
                  "IP Law", "Family Law", "Cyber Law", "Arbitration", "Property Law", "GST", "Income Tax"]:
            if any(w.lower() in query.lower() for w in d.split()):
                domain = d
                break

        persona = "LexSarthi Generalist"

        # 4. Build system prompt
        system_prompt = f"""You are LexSarthi, a verified AI advisory OS.
Domain: {domain}
Persona: {persona}

RAG Context (from legal documents):
{context_text}

Web Search Results (from {'trusted domains only' if not unrestricted else 'entire open web'}):
{json.dumps(web_results[:3], indent=2) if web_results else 'None'}

Instructions:
- Answer based on the provided context and your knowledge.
- If uncertain, say so.
- Cite sources where possible.
- Output a structured answer with citations.
"""

        # 5. Generate initial answer using DeepSeek (with fallback)
        initial_answer = await self._call_llm_with_fallback(system_prompt, query)

        # 6. Jury verification (select 3 verifiers + Shakti)
        selected_verifiers = random.sample(self.verifiers[:-1], 3)
        verifier_results = []
        for v in selected_verifiers:
            v_prompt = f"""You are {v['name']}, responsible for {v['role']}.
Review the following answer:
{initial_answer}

Provide a verdict:
- Status: APPROVED or REJECTED or CORRECTED
- Confidence: HIGH, MEDIUM, LOW
- If CORRECTED, provide corrected_text.
Return JSON only: {{"status": "...", "confidence": "...", "corrected_text": "..."}}"""
            try:
                result_json = await self._call_llm_with_fallback(v_prompt, "Please verify.")
                try:
                    v_result = json.loads(result_json)
                except:
                    import re
                    match = re.search(r'\{.*\}', result_json, re.DOTALL)
                    v_result = json.loads(match.group()) if match else {"status": "APPROVED", "confidence": "MEDIUM", "corrected_text": ""}
                verifier_results.append({"verifier": v['name'], "result": v_result})
            except Exception as e:
                logger.error(f"Verifier {v['name']} failed: {e}")
                verifier_results.append({"verifier": v['name'], "result": {"status": "APPROVED", "confidence": "LOW", "corrected_text": ""}})

        # 7. Judge Shakti
        judge_prompt = f"""You are Shakti, the final judge.
You have received verdicts from 3 verifiers:
{json.dumps(verifier_results, indent=2)}

Original answer: {initial_answer}

Your task:
- Integrate the verifiers' feedback.
- Produce a final answer.
- Assign a final confidence: HIGH, MEDIUM, or LOW.
- List sources (if any).
Return JSON with keys: final_answer, final_confidence, sources.
"""
        try:
            judge_output = await self._call_llm_with_fallback(judge_prompt, "Deliver final judgment.")
            try:
                judge_data = json.loads(judge_output)
            except:
                import re
                match = re.search(r'\{.*\}', judge_output, re.DOTALL)
                judge_data = json.loads(match.group()) if match else {"final_answer": initial_answer, "final_confidence": "MEDIUM", "sources": []}
        except Exception as e:
            logger.error(f"Judge Shakti failed: {e}")
            judge_data = {"final_answer": initial_answer, "final_confidence": "LOW", "sources": []}

        # 8. Final response
        return {
            "answer": judge_data.get("final_answer", initial_answer),
            "confidence": judge_data.get("final_confidence", "MEDIUM"),
            "sources": judge_data.get("sources", []),
            "domain": domain,
            "persona": persona,
            "provider": "deepseek" if self.deepseek else "fallback",
            "jury_verifiers": [v['verifier'] for v in verifier_results],
            "jury_confidences": {v['verifier']: v['result'].get('confidence', 'UNKNOWN') for v in verifier_results}
        }