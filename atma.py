# atma.py
import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncpg
from pydantic import BaseModel

logger = logging.getLogger("lexsarthi.atma")

# ─── Configuration ─────────────────────────────────────────────────────
DOMAIN_PERSONAS = {
    "constitutional": {
        "name": "Constitutional Scholar",
        "prompt": "You are a constitutional law expert. Answer based on the Indian Constitution and Supreme Court rulings.",
    },
    "criminal": {
        "name": "Criminal Law Advocate",
        "prompt": "You are a criminal law expert. Refer to the Bharatiya Nagarik Suraksha Sanhita and relevant case law.",
    },
    "contract": {
        "name": "Contract Law Specialist",
        "prompt": "You are a contract law specialist. Rely on the Indian Contract Act and precedents.",
    },
    "corporate": {
        "name": "Corporate Counsel",
        "prompt": "You are a corporate law advisor. Use the Companies Act and regulatory guidelines.",
    },
    "data_protection": {
        "name": "Data Privacy Officer",
        "prompt": "You are a data protection expert. Apply DPDPA, Data Act, and AI Act principles.",
    },
    "evidence": {
        "name": "Evidence Law Expert",
        "prompt": "You are an evidence law specialist. Base your reasoning on the Indian Evidence Act.",
    },
    "general": {
        "name": "General Legal Advisor",
        "prompt": "You are a general legal advisor. Provide balanced legal information.",
    }
}

KEYWORD_DOMAINS = {
    "constitutional": ["constitution", "fundamental right", "directive principle", "article ", "supreme court"],
    "criminal": ["bnss", "bharatiya nagarik", "criminal", "offence", "penalty", "arrest", "bail"],
    "contract": ["contract", "agreement", "consideration", "breach", "indemnity", "guarantee"],
    "corporate": ["company", "director", "shareholder", "board", "sebi", "incorporation"],
    "data_protection": ["dpdpa", "data protection", "privacy", "gdpr", "data broker", "ai act"],
    "evidence": ["evidence", "proof", "witness", "admissible", "presumption"],
}

VERIFIER_PROMPTS = [
    """You are Verifier 1 – Accuracy. Check if the following claim is **fully supported** by the provided authoritative text (chunks from Supreme Court drafts, legal documents, AND the official website snippets). 
    Return a verdict: SUPPORTED, PARTIALLY_SUPPORTED, or NOT_SUPPORTED. Explain in one sentence.""",
    """You are Verifier 2 – Completeness. Does the claim omit any important legal nuance that is present in the source material (including official websites)? Answer YES/NO and give a brief reason.""",
    """You are Verifier 3 – Consistency. Does the claim contradict any part of the provided legal texts or the official website content? Answer YES/NO and point out the discrepancy if any."""
]

class DeliberationRecord(BaseModel):
    query: str
    domain: str
    persona: str
    provider: str
    initial_answer: str
    verifier_results: List[Dict[str, Any]]
    final_answer: str
    confidence: str
    sources: List[Dict[str, str]]
    timestamp: datetime

# ─── Main Router ──────────────────────────────────────────────────────
class AtmaRouter:
    def __init__(
        self,
        db_pool: asyncpg.Pool,
        fetch_relevant_chunks_func,
        serpapi_search_func,
        call_llm_func
    ):
        self.db_pool = db_pool
        self.fetch_relevant_chunks = fetch_relevant_chunks_func
        self.serpapi_search = serpapi_search_func
        self.call_llm = call_llm_func

    async def _targeted_search(self, query: str) -> List[Dict]:
        """Perform site‑restricted search on configured domains."""
        domains_str = os.getenv("TARGETED_SEARCH_DOMAINS", "")
        if not domains_str:
            return []
        domains = [d.strip() for d in domains_str.split(",") if d.strip()]
        all_results = []
        for domain in domains:
            search_q = f"{query} site:{domain}"
            try:
                results = await self.serpapi_search(search_q)
                if results:
                    all_results.extend(results[:2])
            except Exception as e:
                logger.warning(f"Targeted search failed for {domain}: {e}")
        # Deduplicate by link
        seen = set()
        unique = []
        for r in all_results:
            link = r.get("link")
            if link and link not in seen:
                seen.add(link)
                unique.append(r)
        return unique

    async def run(self, query: str, history: List[Dict] = None, files: List = None) -> Dict[str, Any]:
        # 1. Classify domain
        domain = self._classify_domain(query)
        persona = self._select_persona(domain)
        provider = self._select_provider(query, domain)

        # 2. Retrieve authoritative chunks from pgvector
        chunks = await self.fetch_relevant_chunks(query, top_k=10)

        # 3. Web search: general + targeted
        web_results = []
        if os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true":
            general = await self.serpapi_search(query)
            web_results.extend(general[:3])
            if os.getenv("ENABLE_TARGETED_SEARCH", "true").lower() == "true":
                targeted = await self._targeted_search(query)
                web_results.extend(targeted[:5])

        # 4. Build context
        context_text = "\n".join([f"[{c['metadata'].get('source','Unknown')}] {c['content']}" for c in chunks])
        web_text = "\n".join([f"[Web] {r.get('snippet', '')} (Source: {r.get('link', '')})" for r in web_results[:5]])

        system_prompt = persona["prompt"] + """
        Use the following authoritative legal texts and (optionally) web search results to answer the user's query.
        If the texts do not contain enough information, say so clearly.
        """
        user_message = f"Query: {query}\n\nAuthoritative texts:\n{context_text}\n\nWeb references:\n{web_text}"

        # 5. Initial answer (with provider fallback)
        try:
            initial_answer = await self.call_llm(
                system_prompt=system_prompt,
                user_message=user_message,
                provider=provider,
                history=history
            )
        except Exception as e:
            logger.warning(f"Provider {provider} failed: {e}. Falling back.")
            provider = "openai" if provider != "openai" else "gemini"
            initial_answer = await self.call_llm(
                system_prompt=system_prompt,
                user_message=user_message,
                provider=provider,
                history=history
            )

        # 6. Jury verification
        verifier_results = []
        for v_prompt in VERIFIER_PROMPTS:
            verifier_msg = f"""
            {v_prompt}

            Claim to verify:
            {initial_answer}

            Source texts:
            {context_text}

            Web snippets (including official websites):
            {web_text}

            Provide verdict in JSON format: {{"verdict": "...", "reason": "..."}}
            """
            try:
                verdict_json = await self.call_llm(
                    system_prompt="You are a strict legal verifier. Output only JSON.",
                    user_message=verifier_msg,
                    provider="groq",
                    temperature=0.0
                )
                verdict = json.loads(verdict_json)
            except Exception as e:
                verdict = {"verdict": "ERROR", "reason": str(e)}
            verifier_results.append(verdict)

        # 7. Judge Shakti
        chunk_sources = list(set([c['metadata'].get('source', 'Unknown') for c in chunks]))
        web_sources = [r.get('link', '') for r in web_results[:5] if r.get('link')]
        all_sources = chunk_sources + web_sources

        judge_prompt = f"""
        You are Judge Shakti, the final arbiter. Given the initial answer and the verifiers' assessments, produce a final answer that reconciles any issues.
        Also assign a confidence level: HIGH (if all verifiers support), MEDIUM (if partial support), LOW (if significant doubts).
        Provide your response in JSON: {{"final_answer": "...", "confidence": "HIGH/MEDIUM/LOW", "sources": [list of source names/links]}}.

        Initial answer: {initial_answer}
        Verifier results: {json.dumps(verifier_results)}
        All authoritative sources (chunks + web): {json.dumps(all_sources)}
        """
        judge_response = await self.call_llm(
            system_prompt="You are the final judge. Output only JSON.",
            user_message=judge_prompt,
            provider="openai",
            temperature=0.2
        )
        judge_data = json.loads(judge_response)

        # 8. Record deliberation
        record = DeliberationRecord(
            query=query,
            domain=domain,
            persona=persona["name"],
            provider=provider,
            initial_answer=initial_answer,
            verifier_results=verifier_results,
            final_answer=judge_data["final_answer"],
            confidence=judge_data["confidence"],
            sources=judge_data.get("sources", []),
            timestamp=datetime.utcnow()
        )
        await self._store_deliberation(record)

        return {
            "answer": judge_data["final_answer"],
            "confidence": judge_data["confidence"],
            "sources": judge_data.get("sources", []),
            "domain": domain,
            "persona": persona["name"],
            "provider": provider
        }

    # ─── Helper methods ──────────────────────────────────────────────────
    @staticmethod
    def _classify_domain(query: str) -> str:
        q = query.lower()
        for domain, keywords in KEYWORD_DOMAINS.items():
            if any(kw in q for kw in keywords):
                return domain
        return "general"

    @staticmethod
    def _select_persona(domain: str) -> Dict[str, str]:
        return DOMAIN_PERSONAS.get(domain, DOMAIN_PERSONAS["general"])

    @staticmethod
    def _select_provider(query: str, domain: str) -> str:
        return "openai" if len(query) > 500 else "groq"

    async def _store_deliberation(self, record: DeliberationRecord):
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO deliberations (
                    query, domain, persona, provider, initial_answer,
                    verifier_results, final_answer, confidence, sources, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                record.query,
                record.domain,
                record.persona,
                record.provider,
                record.initial_answer,
                json.dumps(record.verifier_results),
                record.final_answer,
                record.confidence,
                json.dumps(record.sources) if record.sources else None,
                record.timestamp
            )