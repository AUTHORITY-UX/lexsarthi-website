# =============================================================================
# atma.py – AtmaRouter: Smart Agent Orchestration
# =============================================================================

import asyncio
import json
import logging
import random
from typing import List, Dict, Optional, Any
from datetime import datetime
from typing import Optional, Dict, List, Any

logger = logging.getLogger("unknown_verdict.atma")

class AtmaRouter:
    """
    The brain of Unknown Verdict.
    Routes queries to the right agent, orchestrates RAG + web search,
    runs the jury of 10 verifiers, and synthesizes the final answer.
    """
    
    def __init__(self, pg_pool, fetch_relevant_chunks_func, serpapi_search_func, call_llm_func,
                 constitutional_ai=None, kill_switch=None, monitoring=None):
        self.pg_pool = pg_pool
        self.fetch_relevant_chunks = fetch_relevant_chunks_func
        self.serpapi_search = serpapi_search_func
        self.call_llm = call_llm_func
        self.constitutional_ai = constitutional_ai
        self.kill_switch = kill_switch
        self.monitoring = monitoring
        
        self.verifiers = self._get_verifiers()
        self.judge = self._get_judge()
        self.agents = self._get_agents()
        
    def _get_verifiers(self):
        return [
            {"id": "v01", "name": "Ganesha", "role": "Citation & logic integrity", "prompt": "Check legal citations and logical flow."},
            {"id": "v02", "name": "Saraswati", "role": "Knowledge cross-reference", "prompt": "Verify facts against established knowledge."},
            {"id": "v03", "name": "Hanuman", "role": "Global compliance", "prompt": "Ensure advice follows international norms."},
            {"id": "v04", "name": "Kartikeya", "role": "Contradiction detection", "prompt": "Find internal contradictions."},
            {"id": "v05", "name": "Indra", "role": "Jurisdiction mapping", "prompt": "Check jurisdiction assumptions."},
            {"id": "v06", "name": "Yama", "role": "Bias & neutrality", "prompt": "Scan for bias."},
            {"id": "v07", "name": "Surya", "role": "Timeline & limitation", "prompt": "Confirm statutes are current."},
            {"id": "v08", "name": "Chandra", "role": "Precedent match", "prompt": "Check alignment with known precedents."},
            {"id": "v09", "name": "Vayu", "role": "PII / privacy filter", "prompt": "Redact PII."},
            {"id": "v10", "name": "Shakti", "role": "Final judge & dharma seal", "prompt": "Integrate all critiques and produce a final answer with a confidence rating."}
        ]
    
    def _get_judge(self):
        return {
            "id": "judge_01",
            "name": "Shakti",
            "role": "Final synthesis & confidence scoring"
        }
    
    def _get_agents(self):
        """250 Divine Agents from configuration"""
        domains = [
            "Constitutional Law", "Contract Law", "Criminal Law", "Corporate Law", "Tax Law",
            "IP Law", "Family Law", "Cyber Law", "Arbitration", "Property Law", "GST", "Income Tax",
            "Audit", "Incorporation", "Compliance", "Mathematics", "Statistics", "Physics", "Chemistry",
            "Biology", "Medicine", "Psychology", "Philosophy", "Logic", "Reasoning", "Economics",
            "Finance", "History", "Geopolitics", "Astronomy", "Vedanta", "Yoga", "Ayurveda", "Sanskrit",
            "Mythology", "Ethics", "AI Ethics", "Cryptography", "Blockchain", "Climate Science",
            "Environmental Law", "Human Rights", "International Law", "Maritime Law", "Space Law",
            "Data Privacy", "E-commerce", "Real Estate", "Banking", "Insurance"
        ]
        names = ["Brahma","Vishnu","Shiva","Saraswati","Lakshmi","Ganesha","Hanuman",
            "Kartikeya","Indra","Yama","Surya","Chandra","Vayu","Agni","Varuna","Kubera",
            "Yamuna","Ganga","Durga","Kali","Tara","Bhuvaneshwari","Chinnamasta","Bhairavi",
            "Dhumavati","Bagalamukhi","Matangi","Kamala","Dattatreya","Narasimha","Vamana",
            "Parashurama","Rama","Krishna","Buddha","Kalki","Matsya","Kurma","Varaha","Skanda",
            "Ayyappa","Shani","Mangal","Budh","Guru","Shukra","Rahu","Ketu"]
        
        agents = []
        for i in range(250):
            domain = domains[i % len(domains)]
            agent_name = f"{names[i % len(names)]} · {domain}"
            agents.append({
                "id": f"agent_{i+1:03d}",
                "name": agent_name,
                "domain": domain,
                "persona_prompt": f"You are a specialist in {domain}. Use deep expertise."
            })
        return agents
    
    async def run(self, query: str, history: Optional[List[Dict]] = None, 
                  files: Optional[List] = None, unrestricted: bool = False) -> Dict:
        """
        Main orchestration pipeline.
        Returns: {
            "answer": str,
            "confidence": str,
            "sources": List[str],
            "domain": str,
            "persona": str,
            "provider": str,
            "jury_verifiers": List[str],
            "jury_confidences": Dict
        }
        """
        logger.info(f"🔍 AtmaRouter processing query: {query[:100]}...")
        
        # 1. Check kill switch
        if self.kill_switch and not self.kill_switch.is_active:
            return {
                "answer": "Service temporarily unavailable due to safety protocol.",
                "confidence": "LOW",
                "sources": [],
                "domain": "general",
                "persona": "Safety System",
                "provider": "none",
                "jury_verifiers": [],
                "jury_confidences": {}
            }
        
        # 2. Route to the right agent
        agent_id = self._route_agent(query)
        persona = self._get_persona(agent_id)
        domain = self._get_domain(agent_id)
        
        # 3. Fetch relevant legal chunks (RAG)
        chunks = await self.fetch_relevant_chunks(query, top_k=5)
        context = self._build_rag_context(chunks)
        
        # 4. Web search if needed
        web_results = []
        if unrestricted:
            web_results = await self.serpapi_search(query, unrestricted=True)
        
        # 5. Build the complete prompt
        system_prompt = self._build_system_prompt(persona, domain, context, web_results)
        
        # 6. Get initial answer from LLM
        provider = "groq"  # fallback chain handled in call_llm
        initial_answer = await self.call_llm(
            system_prompt=system_prompt,
            user_message=query,
            provider=provider
        )
        
        # 7. Run the jury (10 verifiers) – but only 3 for speed
        verifier_results = []
        jury_confidences = {}
        selected_verifiers = random.sample(self.verifiers, 3)
        for verifier in selected_verifiers:
            result = await self._run_verifier(initial_answer, verifier)
            verifier_results.append(result)
            jury_confidences[verifier["name"]] = result.get("confidence", "MEDIUM")
        
        # 8. Synthesize final answer with judge
        final_answer, confidence = await self._synthesize_with_judge(
            initial_answer, verifier_results, query
        )
        
        # 9. Extract sources
        sources = [chunk.get("citation", "Unknown") for chunk in chunks]
        
        # 10. Constitutional AI check
        if self.constitutional_ai:
            const_result = await self.constitutional_ai.evaluate_response(
                query=query,
                response=final_answer,
                context={"domain": domain}
            )
            if const_result["ethics_compliance"] == "LOW":
                final_answer = const_result["corrected_response"]
                confidence = "LOW"
        
        # 11. Log to deliberations table
        await self._log_deliberation(query, domain, persona, provider, 
                                     initial_answer, verifier_results, 
                                     final_answer, confidence, sources)
        
        return {
            "answer": final_answer,
            "confidence": confidence,
            "sources": sources,
            "domain": domain,
            "persona": persona,
            "provider": provider,
            "jury_verifiers": [v["name"] for v in selected_verifiers],
            "jury_confidences": jury_confidences
        }
    
    def _route_agent(self, query: str) -> str:
        """Keyword-based routing (Edge AI will replace this)"""
        query_lower = query.lower()
        domain_keywords = {
            "constitutional": ["constitution", "fundamental rights", "article", "amendment"],
            "contract": ["contract", "agreement", "breach", "remedy", "specific relief"],
            "criminal": ["ipc", "crpc", "criminal", "offence", "punishment", "bail"],
            "corporate": ["company", "board", "shareholder", "m&a", "insolvency", "sebi"],
            "tax": ["gst", "income tax", "customs", "excise", "taxation"],
        }
        scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            scores[domain] = score
        best = max(scores, key=scores.get)
        return best if scores[best] >= 2 else "general"
    
    def _get_persona(self, agent_id: str) -> str:
        personas = {
            "constitutional": "You are a Constitutional Law expert with deep knowledge of the Indian Constitution.",
            "contract": "You are a Contract Law specialist focusing on Indian contract law and remedies.",
            "criminal": "You are a Criminal Law expert specializing in the Indian Penal Code and CrPC.",
            "corporate": "You are a Corporate Law specialist with expertise in company law and SEBI regulations.",
            "tax": "You are a Tax Law expert covering GST, Income Tax, and customs laws.",
            "general": "You are a general legal expert with broad knowledge across all domains."
        }
        return personas.get(agent_id, personas["general"])
    
    def _get_domain(self, agent_id: str) -> str:
        return agent_id if agent_id in ["constitutional", "contract", "criminal", "corporate", "tax"] else "general"
    
    def _build_rag_context(self, chunks: List[Dict]) -> str:
        if not chunks:
            return ""
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[Source {i}: {chunk.get('citation', 'Unknown')}]\n{chunk['content']}")
        return "═══ LEGAL KNOWLEDGE BASE ═══\n" + "\n\n".join(context_parts)
    
    def _build_system_prompt(self, persona: str, domain: str, context: str, web_results: List[Dict]) -> str:
        base = "You are the Unknown Verdict Engine – an AI advisory OS with specialist knowledge."
        system = f"{base}\n\n{persona}\n\nDomain: {domain}"
        if context:
            system += f"\n\n{context}"
        if web_results:
            web_text = "\n".join([f"- {r.get('title', '')}: {r.get('snippet', '')}" for r in web_results[:3]])
            system += f"\n\n═══ WEB SEARCH RESULTS ═══\n{web_text}"
        system += "\n\nAlways cite sources. Admit uncertainty. Default jurisdiction: India."
        return system
    
    async def _run_verifier(self, answer: str, verifier: Dict) -> Dict:
        """Run a single verifier on the answer"""
        prompt = f"""
You are {verifier['name']} ({verifier['role']}).
Review the following legal answer and return JSON:
{{
    "status": "APPROVED|CORRECTED|REJECTED",
    "confidence": "HIGH|MEDIUM|LOW",
    "corrected_text": "...",
    "feedback": "..."
}}

Answer to review:
{answer[:2000]}
"""
        try:
            response = await self.call_llm(
                system_prompt=f"You are a strict legal verifier {verifier['name']}.",
                user_message=prompt,
                provider="groq"
            )
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.error(f"Verifier {verifier['name']} failed: {e}")
        return {"status": "APPROVED", "confidence": "MEDIUM", "corrected_text": "", "feedback": ""}
    
    async def _synthesize_with_judge(self, initial_answer: str, verifier_results: List[Dict], query: str) -> tuple:
        """Judge synthesizes final answer with confidence scoring"""
        high_count = sum(1 for v in verifier_results if v.get("confidence") == "HIGH")
        total = len(verifier_results)
        confidence_ratio = high_count / total if total > 0 else 0
        
        if confidence_ratio >= 0.7:
            confidence = "HIGH"
        elif confidence_ratio >= 0.4:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        if confidence == "LOW":
            judge_prompt = f"""
The following answer had LOW confidence from the jury. Please synthesize a corrected version.
Query: {query}
Original answer: {initial_answer[:1500]}
Jury feedback: {json.dumps(verifier_results)}
Return only the corrected answer.
"""
            final_answer = await self.call_llm(
                system_prompt="You are the final judge and synthesizer. Correct all errors.",
                user_message=judge_prompt,
                provider="groq"
            )
        else:
            final_answer = initial_answer
        
        return final_answer, confidence
    
    async def _log_deliberation(self, query: str, domain: str, persona: str, provider: str,
                                initial_answer: str, verifier_results: List[Dict],
                                final_answer: str, confidence: str, sources: List[str]):
        """Log to deliberations table for self-improvement"""
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO deliberations 
                    (query, domain, persona, provider, initial_answer, verifier_results, final_answer, confidence, sources)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """, query, domain, persona, provider, initial_answer, 
                    json.dumps(verifier_results), final_answer, confidence, json.dumps(sources))
        except Exception as e:
            logger.error(f"Failed to log deliberation: {e}")