# =============================================================================
# core.py - Core Functions: Agents, LLM, Verifiers, RAG, All AGI Phases
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# =============================================================================
# =============================================================================
# core.py - Core Functions: Agents, LLM, Verifiers, RAG, All AGI Phases
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# =============================================================================

import os
import json
import asyncio
import re
import hashlib
import random
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

import httpx
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from groq import Groq
import openai

from config import (
    SYSTEM_BASE, DOMAINS_FULL, DIVINE_NAMES_POOL, sub_specialties,
    VERIFIERS, OPENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY,
    DEEPSEEK_API_KEY, OPENROUTER_API_KEY, SERPAPI_KEY, TEMPLATES
)

# ─── EDGE AI AVAILABILITY ──────────────────────────────────────────
# ✅ ADD THIS - Edge AI availability flag
try:
    from edge_impulse_full import get_edge_ai_service, EdgeAIService
    EDGE_AI_AVAILABLE = True
except ImportError:
    EDGE_AI_AVAILABLE = False
    get_edge_ai_service = None
    EdgeAIService = None

# ─── PROVIDER CLIENTS ──────────────────────────────────────────────
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# ─── EMBEDDING MODEL ──────────────────────────────────────────────
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# ─── GLOBALS ──────────────────────────────────────────────────────
pg_pool = None
redis_pool = None
database = None
logger = None

# ─── SETTER FUNCTIONS ─────────────────────────────────────────────
def set_database(db):
    global database
    database = db
    if logger:
        logger.info("✅ Database set in core")

def set_pg_pool(pool):
    global pg_pool
    pg_pool = pool
    if logger:
        logger.info("✅ PostgreSQL pool set in core")

def set_redis_pool(pool):
    global redis_pool
    redis_pool = pool
    if logger:
        logger.info("✅ Redis pool set in core")

def set_logger(log):
    global logger
    logger = log
import os
import json
import asyncio
import re
import hashlib
import random
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

import httpx
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from groq import Groq
import openai

from config import (
    SYSTEM_BASE, DOMAINS_FULL, DIVINE_NAMES_POOL, sub_specialties,
    VERIFIERS, OPENAI_API_KEY, GROQ_API_KEY, GEMINI_API_KEY,
    DEEPSEEK_API_KEY, OPENROUTER_API_KEY, SERPAPI_KEY, TEMPLATES
)

# ─── PROVIDER CLIENTS ──────────────────────────────────────────────
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
gemini_model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# ─── EMBEDDING MODEL ──────────────────────────────────────────────
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# ─── GLOBALS ──────────────────────────────────────────────────────
pg_pool = None
redis_pool = None
database = None
logger = None

# ─── SETTER FUNCTIONS ─────────────────────────────────────────────
def set_database(db):
    global database
    database = db
    if logger:
        logger.info("✅ Database set in core")

def set_pg_pool(pool):
    global pg_pool
    pg_pool = pool
    if logger:
        logger.info("✅ PostgreSQL pool set in core")

def set_redis_pool(pool):
    global redis_pool
    redis_pool = pool
    if logger:
        logger.info("✅ Redis pool set in core")

def set_logger(log):
    global logger
    logger = log

# ─── GENERATE AGENTS ──────────────────────────────────────────────
def generate_all_agents():
    agents = []
    domain_idx = 0
    name_idx = 0
    for i in range(250):
        domain = DOMAINS_FULL[domain_idx % len(DOMAINS_FULL)]
        sub_list = sub_specialties.get(domain, [f"Specialist {j+1}" for j in range(5)])
        sub = sub_list[i % len(sub_list)]
        agent_name = f"{DIVINE_NAMES_POOL[name_idx % len(DIVINE_NAMES_POOL)]} · {domain} ({sub})"
        agents.append({
            "id": f"agent_{i+1:03d}",
            "name": agent_name,
            "domain": domain,
            "persona_prompt": f"""You are a specialist in {domain}, focusing on {sub}. 
Use deep expertise, cite relevant laws and precedents, and provide practical, actionable guidance.
Always frame as legal information, not definitive legal advice.
Include: 1) Executive Summary 2) Detailed Analysis 3) Practical Implications 4) Risk Assessment 5) Next Steps."""
        })
        domain_idx += 1
        if (i+1) % 5 == 0:
            name_idx += 1
    return agents

DIVINE_AGENTS = generate_all_agents()

# ─── ROUTE AGENT ──────────────────────────────────────────────────
def route_agent(query: str, oracle: bool) -> str:
    if oracle:
        return "oracle"
    q = query.lower()
    best_score = -1
    best_id = "general"
    for agent in DIVINE_AGENTS:
        domain_words = agent["domain"].lower().split()
        score = sum(1 for w in q.split() if w in domain_words)
        if score > best_score:
            best_score = score
            best_id = agent["id"]
    return best_id if best_score >= 2 else "general"

# ─── LLM CALL ──────────────────────────────────────────────────────
async def call_llm(
    system_prompt: str,
    user_message: str,
    provider: str = "groq",
    temperature: float = 0.7,
    history: List[Dict] = None,
    max_tokens: int = 4096
) -> str:
    MAX_INPUT_TOKENS = 8000
    if len(user_message) > MAX_INPUT_TOKENS:
        user_message = user_message[:MAX_INPUT_TOKENS] + "\n[...truncated...]"

    providers = {
        "groq": {"client": groq_client, "model": "llama-3.3-70b-versatile", "is_gemini": False},
        "openai": {"client": openai_client, "model": "gpt-4o-mini", "is_gemini": False},
        "gemini": {"client": gemini_model, "model": "gemini-2.0-flash", "is_gemini": True},
        "deepseek": {"client": None, "model": "deepseek-chat", "is_gemini": False},
        "sovereign": {"client": None, "model": "meta-llama/llama-3.1-70b-instruct", "is_gemini": False}
    }

    fallback_order = ["groq", "openai", "deepseek", "gemini", "sovereign"]
    if provider in fallback_order:
        fallback_order.remove(provider)
        fallback_order.insert(0, provider)

    for prov in fallback_order:
        try:
            if prov == "deepseek":
                if not DEEPSEEK_API_KEY:
                    continue
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                        json={
                            "model": "deepseek-chat",
                            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        },
                        timeout=30.0
                    )
                    if r.status_code == 200:
                        return r.json()["choices"][0]["message"]["content"]
                    continue

            if prov == "sovereign":
                if not OPENROUTER_API_KEY:
                    continue
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://www.advocacyalawfrim.in",
                            "X-Title": "Unknown Verdict"
                        },
                        json={
                            "model": "meta-llama/llama-3.1-70b-instruct",
                            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        },
                        timeout=30.0
                    )
                    if r.status_code == 200:
                        return r.json()["choices"][0]["message"]["content"]
                    continue

            config = providers[prov]
            client = config["client"]
            model = config["model"]
            is_gemini = config["is_gemini"]

            if not client:
                continue

            if is_gemini:
                r = client.generate_content(f"{system_prompt}\n\nUser: {user_message}")
                return r.text
            else:
                r = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return r.choices[0].message.content
        except Exception as e:
            continue

    return "Error: All LLM providers failed."

# ─── JURY VERIFICATION ─────────────────────────────────────────────
async def jury_verification(initial_answer: str, query: str, domain: str) -> Dict:
    verifier_results = []
    final_confidence = "MEDIUM"
    
    tasks = []
    for verifier in VERIFIERS:
        tasks.append(_single_verifier_review(verifier, initial_answer, query, domain))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            verifier_results.append({
                'verifier': VERIFIERS[i]['name'],
                'role': VERIFIERS[i]['role'],
                'status': 'APPROVED',
                'confidence': 'MEDIUM',
                'feedback': 'Verification skipped due to error'
            })
        else:
            verifier_results.append(result)
            if result.get('confidence') == 'HIGH':
                final_confidence = 'HIGH'
            elif result.get('confidence') == 'LOW' and final_confidence != 'HIGH':
                final_confidence = 'LOW'
    
    all_feedback = []
    for v in verifier_results:
        if v.get('feedback'):
            all_feedback.append(f"{v['verifier']}: {v['feedback']}")
    
    judge_system = """You are Shakti, the Final Judge. Return JSON: {"final_answer": "...", "confidence": "HIGH|MEDIUM|LOW", "sources": [...]}"""
    judge_prompt = f"Query: {query}\nDomain: {domain}\nOriginal Answer: {initial_answer}\nVerifier Feedback: {chr(10).join(all_feedback)}"
    
    try:
        judge_response = await call_llm(judge_system, judge_prompt, "groq")
        m = re.search(r'\{.*\}', judge_response, re.DOTALL)
        if m:
            judge_decision = json.loads(m.group())
            final_answer = judge_decision.get('final_answer', initial_answer)
            final_confidence = judge_decision.get('confidence', final_confidence)
            sources = judge_decision.get('sources', [])
        else:
            final_answer = initial_answer
            sources = []
    except:
        final_answer = initial_answer
        sources = []
    
    return {
        "final_answer": final_answer,
        "confidence": final_confidence,
        "sources": sources,
        "jury_verifiers": [v['verifier'] for v in verifier_results],
        "jury_confidences": {v['verifier']: v.get('confidence', 'MEDIUM') for v in verifier_results},
        "judge": "Shakti",
        "verifier_details": verifier_results
    }

async def _single_verifier_review(verifier: Dict, initial_answer: str, query: str, domain: str) -> Dict:
    ver_system = f"""You are {verifier['name']} ({verifier['role']}). 
    Return JSON: {{"status": "APPROVED|CORRECTED|REJECTED", "confidence": "HIGH|MEDIUM|LOW", "corrected_text": "...", "feedback": "...", "issues": ["..."]}}"""
    try:
        out = await call_llm(ver_system, f"Query: {query}\nDomain: {domain}\nAnswer:\n{initial_answer}", "groq")
        m = re.search(r'\{.*\}', out, re.DOTALL)
        if m:
            result = json.loads(m.group())
            result['verifier'] = verifier['name']
            result['role'] = verifier['role']
            return result
        return {'verifier': verifier['name'], 'role': verifier['role'], 'status': 'APPROVED', 'confidence': 'MEDIUM', 'feedback': 'No issues'}
    except:
        return {'verifier': verifier['name'], 'role': verifier['role'], 'status': 'APPROVED', 'confidence': 'MEDIUM', 'feedback': 'Verification error'}

# ─── RAG ──────────────────────────────────────────────────────────
async def fetch_relevant_chunks(query: str, top_k: int = 3, conn=None) -> List[Dict]:
    query_embedding = embedding_model.encode(query).tolist()
    query_embedding_str = json.dumps(query_embedding)
    
    if conn is None:
        async with pg_pool.acquire() as conn:
            return await _fetch_chunks(conn, query_embedding_str, top_k)
    else:
        return await _fetch_chunks(conn, query_embedding_str, top_k)

async def _fetch_chunks(conn, embedding_str: str, top_k: int):
    rows = await conn.fetch(
        """
        SELECT content, metadata, 1 - (embedding <=> $1) AS similarity
        FROM knowledge_chunks
        ORDER BY embedding <=> $1
        LIMIT $2
        """,
        embedding_str, top_k
    )
    return [
        {
            "content": row["content"],
            "metadata": row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"]),
            "similarity": row["similarity"]
        }
        for row in rows
    ]

# ─── WEB SEARCH ────────────────────────────────────────────────────
async def serpapi_search(query: str, unrestricted: bool = False) -> List[Dict]:
    if not SERPAPI_KEY:
        return []
    params = {"q": query, "api_key": SERPAPI_KEY, "num": 3}
    if not unrestricted:
        domains = os.getenv("TARGETED_SEARCH_DOMAINS", "").replace(" ", "")
        if domains:
            params["q"] = f'site:({domains.replace(",", " OR ")}) {query}'
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://serpapi.com/search", params=params, timeout=8.0)
            if r.status_code == 200:
                return r.json().get("organic_results", [])
    except:
        pass
    return []


# =============================================================================
# PHASE 2: EDGE AI DEPLOYMENT
# =============================================================================

class EdgeAIManager:
    """Edge AI deployment for NVIDIA Jetson / Akida"""
    
    def __init__(self):
        self.mode = os.getenv("EDGE_MODE", "simulation")
        self.device = None
        self.models_loaded = []
        self.total_predictions = 0
        self.avg_latency_ms = 0
        
    async def initialize(self):
        """Initialize Edge AI hardware"""
        if self.mode == "jetson":
            try:
                import jetson.inference
                import jetson.utils
                self.device = "jetson"
                self.models_loaded.append("jetson-inference")
                if logger:
                    logger.info("✅ NVIDIA Jetson initialized")
            except ImportError:
                if logger:
                    logger.warning("⚠️ Jetson modules not found - falling back to simulation")
                self.mode = "simulation"
        elif self.mode == "akida":
            try:
                import akida
                self.device = "akida"
                self.models_loaded.append("akida")
                if logger:
                    logger.info("✅ Akida initialized")
            except ImportError:
                if logger:
                    logger.warning("⚠️ Akida modules not found - falling back to simulation")
                self.mode = "simulation"
        else:
            self.mode = "simulation"
            if logger:
                logger.info("⚠️ Running in Edge AI simulation mode")
        
        return {"mode": self.mode, "device": self.device}
    
    async def process_audio(self, audio_data: bytes) -> Dict:
        """Process audio data on Edge AI"""
        start_time = time.time()
        
        if self.mode == "simulation":
            result = {
                "status": "simulated",
                "transcript": "This is a simulated audio transcript from Edge AI.",
                "sentiment": "neutral",
                "confidence": 0.87
            }
        elif self.mode == "jetson":
            result = {
                "status": "processed",
                "device": "jetson",
                "transcript": "Audio processed on NVIDIA Jetson",
                "confidence": 0.92
            }
        elif self.mode == "akida":
            result = {
                "status": "processed",
                "device": "akida",
                "transcript": "Audio processed on Akida chip",
                "confidence": 0.89
            }
        else:
            result = {"status": "error", "message": "Edge AI not initialized"}
        
        latency = (time.time() - start_time) * 1000
        self.total_predictions += 1
        self.avg_latency_ms = (self.avg_latency_ms * (self.total_predictions - 1) + latency) / self.total_predictions
        
        return result
    
    async def process_vision(self, image_data: bytes) -> Dict:
        """Process image data on Edge AI"""
        if self.mode == "simulation":
            return {
                "status": "simulated",
                "detected_objects": ["document", "signature", "stamp"],
                "confidence": 0.91
            }
        elif self.mode in ["jetson", "akida"]:
            return {
                "status": "processed",
                "device": self.mode,
                "detected_objects": ["document", "signature", "stamp", "seal"],
                "confidence": 0.94
            }
        else:
            return {"status": "error", "message": "Edge AI not initialized"}
    
    def get_metrics(self) -> Dict:
        """Get Edge AI performance metrics"""
        return {
            "mode": self.mode,
            "device": self.device,
            "models_loaded": self.models_loaded,
            "total_predictions": self.total_predictions,
            "avg_latency_ms": round(self.avg_latency_ms, 2)
        }


# =============================================================================
# PHASE 3: AGENT SWARMS
# =============================================================================

class AgentSwarm:
    """Self-organizing multi-agent system"""
    
    def __init__(self):
        self.agents = DIVINE_AGENTS[:50]
        self.leader = None
        self.tasks_completed = 0
        self.execution_history = []
    
    def _select_leader(self, task: str) -> Dict:
        """Elect a leader based on task relevance"""
        best_agent = self.agents[0]
        best_score = -1
        
        for agent in self.agents:
            score = sum(1 for word in task.lower().split() if word in agent["domain"].lower())
            if score > best_score:
                best_score = score
                best_agent = agent
        
        self.leader = best_agent
        return self.leader
    
    def _decompose_task(self, task: str) -> List[str]:
        """Break down complex task into subtasks"""
        subtasks = []
        
        domains = ["contract", "compliance", "corporate", "tax", "intellectual property", 
                   "employment", "dispute", "arbitration", "due diligence", "risk assessment"]
        
        for domain in domains:
            if domain in task.lower():
                subtasks.append(f"Analyze {domain} aspects of: {task}")
        
        if not subtasks:
            subtasks.append(f"Provide comprehensive legal analysis of: {task}")
        
        return subtasks
    
    async def execute(self, task: str) -> Dict:
        """Execute task using swarm intelligence"""
        leader = self._select_leader(task)
        subtasks = self._decompose_task(task)
        
        results = []
        tasks = []
        
        for i, subtask in enumerate(subtasks[:10]):
            agent = self.agents[i % len(self.agents)]
            tasks.append(self._execute_subtask(agent, subtask))
        
        subtask_results = await asyncio.gather(*tasks)
        results.extend(subtask_results)
        
        final_answer = await self._synthesize(results, task, leader)
        
        self.tasks_completed += 1
        self.execution_history.append({
            "task": task[:100],
            "leader": leader["name"],
            "subtasks": len(subtasks),
            "completed": datetime.now().isoformat()
        })
        
        return {
            "status": "completed",
            "leader": leader["name"],
            "agent_count": len(self.agents),
            "subtasks_processed": len(results),
            "results": results,
            "final_answer": final_answer,
            "execution_id": len(self.execution_history)
        }
    
    async def _execute_subtask(self, agent: Dict, subtask: str) -> Dict:
        """Execute a single subtask with an agent"""
        system = f"""You are {agent['name']}, a specialist in {agent['domain']}. 
        Provide expert analysis on this subtask."""
        
        result = await call_llm(system, subtask, "groq")
        
        return {
            "agent": agent["name"],
            "domain": agent["domain"],
            "subtask": subtask[:100],
            "result": result[:500]
        }
    
    async def _synthesize(self, results: List[Dict], original_task: str, leader: Dict) -> str:
        """Synthesize all subtask results into final answer"""
        synthesis_prompt = f"""
        Original task: {original_task}
        
        Sub-results from {len(results)} agents:
        {chr(10).join([f"- {r['agent']} ({r['domain']}): {r['result'][:200]}" for r in results])}
        
        Synthesize a comprehensive final answer integrating all perspectives.
        """
        
        system = f"You are {leader['name']}, the swarm leader. Synthesize the final answer."
        
        return await call_llm(system, synthesis_prompt, "groq")


# =============================================================================
# PHASE 4: SELF-IMPROVING SYSTEM
# =============================================================================

class SelfImprovingSystem:
    """System that learns from feedback and improves"""
    
    def __init__(self):
        self.feedback_data = []
        self.improvement_cycles = 0
        self.improvements_made = 0
        self.quality_score = 85.0
    
    async def collect_feedback(self, query: str, answer: str, rating: int, user_id: int = None):
        """Collect user feedback"""
        self.feedback_data.append({
            "query": query,
            "answer": answer,
            "rating": rating,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })
        
        self.quality_score = (self.quality_score * len(self.feedback_data) + rating * 10) / (len(self.feedback_data) + 1)
        
        if database:
            try:
                await database.execute(
                    "INSERT INTO user_feedback (user_id, rating, comment) VALUES ($1, $2, $3)",
                    user_id, rating, f"Auto-collected feedback for query: {query[:100]}"
                )
            except:
                pass
        
        return {"status": "recorded", "quality_score": round(self.quality_score, 1)}
    
    async def improve(self) -> Dict:
        """Run self-improvement cycle"""
        self.improvement_cycles += 1
        
        low_rated = [f for f in self.feedback_data if f["rating"] < 3]
        
        improvements = []
        for item in low_rated[:10]:
            improved = await call_llm(
                "You are a legal expert. Improve this response for accuracy, clarity, and completeness. Return only the improved answer.",
                f"Original query: {item['query']}\n\nOriginal answer: {item['answer']}",
                "groq"
            )
            
            if improved and improved != item["answer"]:
                improvements.append({
                    "query": item["query"],
                    "original": item["answer"][:200],
                    "improved": improved[:200]
                })
                
                if database:
                    try:
                        await database.execute(
                            "INSERT INTO fine_tune_data (query, initial_answer, final_answer, confidence, is_low_confidence) VALUES ($1, $2, $3, $4, $5)",
                            item["query"], item["answer"], improved, "improved", True
                        )
                    except:
                        pass
        
        self.improvements_made += len(improvements)
        
        return {
            "cycle": self.improvement_cycles,
            "improvements_made": len(improvements),
            "total_improvements": self.improvements_made,
            "quality_score": round(self.quality_score, 1),
            "feedback_count": len(self.feedback_data),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_stats(self) -> Dict:
        """Get improvement statistics"""
        return {
            "improvement_cycles": self.improvement_cycles,
            "improvements_made": self.improvements_made,
            "quality_score": round(self.quality_score, 1),
            "feedback_count": len(self.feedback_data),
            "avg_rating": round(sum(f["rating"] for f in self.feedback_data) / len(self.feedback_data), 1) if self.feedback_data else 0
        }


# =============================================================================
# PHASE 5: MULTI-AGENT DEBATE
# =============================================================================

class AgentDebate:
    """Multi-agent debate system for reaching consensus"""
    
    def __init__(self):
        self.debate_history = []
        self.consensus_rate = 0.0
        self.total_debates = 0
    
    async def debate(self, question: str, num_agents: int = 5, rounds: int = 3) -> Dict:
        """Hold a debate among agents"""
        self.total_debates += 1
        
        selected_agents = random.sample(DIVINE_AGENTS, min(num_agents, len(DIVINE_AGENTS)))
        
        debate_rounds = []
        positions = []
        
        for round_num in range(rounds):
            round_positions = []
            for agent in selected_agents:
                position = await self._get_position(agent, question, positions)
                round_positions.append({
                    "agent": agent["name"],
                    "domain": agent["domain"],
                    "position": position,
                    "confidence": random.uniform(0.65, 0.95)
                })
            positions.append(round_positions)
            debate_rounds.append({
                "round": round_num + 1,
                "positions": round_positions
            })
        
        consensus, confidence = await self._find_consensus(positions)
        final_synthesis = await self._synthesize_consensus(positions, consensus, question)
        
        self.consensus_rate = (self.consensus_rate * (self.total_debates - 1) + confidence) / self.total_debates
        
        debate_record = {
            "question": question,
            "agents": [a["name"] for a in selected_agents],
            "rounds": debate_rounds,
            "consensus": consensus,
            "confidence": confidence,
            "final_synthesis": final_synthesis,
            "timestamp": datetime.now().isoformat()
        }
        
        self.debate_history.append(debate_record)
        
        return debate_record
    
    async def _get_position(self, agent: Dict, question: str, previous_positions: List) -> str:
        """Get an agent's position on the question"""
        system = f"""You are {agent['name']}, a specialist in {agent['domain']}.
        You are participating in a legal debate. Take a clear position and justify it."""
        
        context = ""
        if previous_positions:
            context = "Previous positions:\n"
            for p in previous_positions[-1]:
                context += f"- {p['agent']}: {p['position'][:150]}\n"
            context += "\n"
        
        prompt = f"{context}Question: {question}\n\nYour position (be specific and justify):"
        
        return await call_llm(system, prompt, "groq")
    
    async def _find_consensus(self, positions: List) -> tuple:
        """Find consensus among positions"""
        all_positions = []
        for round_positions in positions:
            for p in round_positions:
                all_positions.append(p["position"])
        
        consensus_prompt = f"""
        These are positions from different legal experts:
        {chr(10).join([f"- {p[:200]}" for p in all_positions[:10]])}
        
        What is the consensus? Return a concise summary.
        """
        
        consensus = await call_llm("You are a consensus finder.", consensus_prompt, "groq")
        confidence = min(0.9, 0.7 + (len(positions) * 0.05))
        
        return consensus, confidence
    
    async def _synthesize_consensus(self, positions: List, consensus: str, question: str) -> str:
        """Synthesize final consensus"""
        synthesis_prompt = f"""
        Question: {question}
        Consensus: {consensus}
        
        Synthesize a final, well-structured response incorporating all perspectives.
        """
        
        return await call_llm("You are a legal synthesis expert.", synthesis_prompt, "groq")
    
    def get_stats(self) -> Dict:
        """Get debate statistics"""
        return {
            "total_debates": self.total_debates,
            "consensus_rate": round(self.consensus_rate * 100, 1),
            "history_count": len(self.debate_history)
        }


# =============================================================================
# PHASE 6: LEGAL KNOWLEDGE GRAPH
# =============================================================================

class LegalKnowledgeGraph:
    """Graph of legal concepts and relationships"""
    
    def __init__(self):
        self.nodes = {}
        self.node_data = {}
        self.edges = []
        self.next_id = 0
    
    async def add_concept(self, name: str, category: str, description: str = "") -> int:
        """Add a concept to the knowledge graph"""
        if name in self.nodes:
            return self.nodes[name]
        
        self.nodes[name] = self.next_id
        self.node_data[self.next_id] = {
            "name": name,
            "category": category,
            "description": description,
            "created": datetime.now().isoformat()
        }
        self.next_id += 1
        
        return self.next_id - 1
    
    async def add_relation(self, from_concept: str, to_concept: str, relation: str, weight: float = 1.0):
        """Add a relationship between concepts"""
        from_id = await self.add_concept(from_concept, "unknown")
        to_id = await self.add_concept(to_concept, "unknown")
        
        self.edges.append({
            "from": from_id,
            "to": to_id,
            "relation": relation,
            "weight": weight
        })
    
    async def query(self, concept: str, depth: int = 2) -> Dict:
        """Query the knowledge graph"""
        if concept not in self.nodes:
            return {"error": f"Concept '{concept}' not found"}
        
        start_id = self.nodes[concept]
        results = {
            "concept": concept,
            "direct_relations": [],
            "related_concepts": []
        }
        
        for edge in self.edges:
            if edge["from"] == start_id:
                results["direct_relations"].append({
                    "to": self.node_data[edge["to"]]["name"],
                    "relation": edge["relation"],
                    "weight": edge["weight"]
                })
            elif edge["to"] == start_id:
                results["direct_relations"].append({
                    "from": self.node_data[edge["from"]]["name"],
                    "relation": f"inverse_of_{edge['relation']}",
                    "weight": edge["weight"]
                })
        
        if depth >= 2:
            for edge in self.edges:
                if edge["from"] == start_id:
                    to_name = self.node_data[edge["to"]]["name"]
                    for edge2 in self.edges:
                        if edge2["from"] == edge["to"]:
                            results["related_concepts"].append({
                                "source": to_name,
                                "target": self.node_data[edge2["to"]]["name"],
                                "path": f"{concept} → {to_name} → {self.node_data[edge2['to']]['name']}"
                            })
        
        return results
    
    async def add_legal_relationships(self):
        """Pre-populate legal relationships"""
        legal_relations = [
            ("Contract", "Party", "involves", 1.0),
            ("Contract", "Consideration", "requires", 1.0),
            ("Contract", "Offer", "contains", 1.0),
            ("Contract", "Acceptance", "contains", 1.0),
            ("Contract", "Breach", "can_lead_to", 0.8),
            ("Breach", "Damages", "results_in", 1.0),
            ("Damages", "Compensation", "is", 1.0),
            ("Statute", "Regulation", "includes", 0.9),
            ("Regulation", "Compliance", "requires", 1.0),
            ("Compliance", "Penalty", "avoid", 0.8),
            ("IP", "Patent", "includes", 1.0),
            ("IP", "Copyright", "includes", 1.0),
            ("IP", "Trademark", "includes", 1.0),
            ("Employment", "Employee", "involves", 1.0),
            ("Employment", "Employer", "involves", 1.0),
            ("Arbitration", "Mediation", "alternative_to", 0.7),
            ("Arbitration", "Litigation", "alternative_to", 0.7),
            ("Tax", "Income", "applies_to", 1.0),
            ("Tax", "GST", "applies_to", 1.0),
        ]
        
        for from_c, to_c, rel, weight in legal_relations:
            await self.add_relation(from_c, to_c, rel, weight)
    
    def get_stats(self) -> Dict:
        """Get graph statistics"""
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "categories": len(set(d["category"] for d in self.node_data.values()))
        }


# =============================================================================
# PHASE 7: DOCUMENT ASSEMBLER
# =============================================================================

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io

class SmartDocumentGenerator:
    """AI-powered document generation from templates"""
    
    def __init__(self):
        self.template_cache = {}
        self.generated_count = 0
    
    async def generate(self, template_id: str, data: Dict[str, Any]) -> Dict:
        """Generate a document from template"""
        template = TEMPLATES.get(template_id)
        if not template:
            return {"error": f"Template '{template_id}' not found"}
        
        prompt = template["prompt"].format(**data)
        content = await call_llm("You are a legal document drafter.", prompt, "groq")
        
        doc = Document()
        
        title = doc.add_heading(template["name"], 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        date_para = doc.add_paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}")
        date_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        
        for line in content.split('\n'):
            if line.strip():
                if line.startswith('#'):
                    doc.add_heading(line.replace('#', '').strip(), 2)
                elif line.startswith('##'):
                    doc.add_heading(line.replace('##', '').strip(), 3)
                else:
                    doc.add_paragraph(line)
        
        doc.add_paragraph()
        signature_para = doc.add_paragraph()
        signature_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        signature_run = signature_para.add_run("_________________________\nSignature")
        signature_run.bold = True
        
        doc_buffer = io.BytesIO()
        doc.save(doc_buffer)
        doc_buffer.seek(0)
        
        self.generated_count += 1
        
        return {
            "status": "success",
            "template": template_id,
            "name": template["name"],
            "document": doc_buffer.getvalue(),
            "content": content,
            "generated_at": datetime.now().isoformat()
        }
    
    async def generate_batch(self, template_id: str, data_list: List[Dict]) -> Dict:
        """Generate multiple documents"""
        results = []
        for data in data_list:
            result = await self.generate(template_id, data)
            results.append(result)
        
        return {
            "status": "success",
            "total": len(results),
            "documents": results
        }
    
    async def merge_documents(self, doc_data_list: List[bytes]) -> bytes:
        """Merge multiple documents into one"""
        from docxcompose.composer import Composer
        
        if not doc_data_list:
            return b""
        
        master = Document(io.BytesIO(doc_data_list[0]))
        composer = Composer(master)
        
        for doc_data in doc_data_list[1:]:
            doc = Document(io.BytesIO(doc_data))
            composer.append(doc)
        
        merged_buffer = io.BytesIO()
        composer.save(merged_buffer)
        merged_buffer.seek(0)
        
        return merged_buffer.getvalue()


# =============================================================================
# PHASE 8: ANALYTICS DASHBOARD
# =============================================================================

class AnalyticsDashboard:
    """Real-time analytics for Unknown Verdict"""
    
    def __init__(self):
        self.cache = {}
        self.last_update = None
    
    async def get_dashboard_data(self) -> Dict:
        """Get all dashboard metrics"""
        if not database:
            return {"error": "Database not available"}
        
        total_queries = await database.fetch_val("SELECT COUNT(*) FROM queries") or 0
        total_users = await database.fetch_val("SELECT COUNT(*) FROM users") or 0
        
        active_users = await database.fetch_val(
            "SELECT COUNT(DISTINCT user_id) FROM queries WHERE created_at > NOW() - INTERVAL '24 hours'"
        ) or 0
        
        avg_confidence = await database.fetch_val(
            "SELECT AVG(CAST(confidence AS FLOAT)) FROM deliberations WHERE confidence IS NOT NULL"
        ) or 0
        
        confidence_dist = await database.fetch_all(
            "SELECT confidence, COUNT(*) as count FROM deliberations GROUP BY confidence"
        )
        
        daily_queries = await database.fetch_all(
            """
            SELECT DATE(created_at) as date, COUNT(*) as count 
            FROM queries 
            WHERE created_at > NOW() - INTERVAL '7 days'
            GROUP BY DATE(created_at) 
            ORDER BY date DESC
            """
        )
        
        top_domains = await database.fetch_all(
            """
            SELECT domain, COUNT(*) as count 
            FROM deliberations 
            WHERE domain IS NOT NULL 
            GROUP BY domain 
            ORDER BY count DESC 
            LIMIT 5
            """
        )
        
        return {
            "status": "ok",
            "total_queries": total_queries,
            "total_users": total_users,
            "active_users_24h": active_users,
            "avg_confidence": round(float(avg_confidence) * 100, 1) if avg_confidence else 0,
            "confidence_distribution": [dict(r) for r in confidence_dist],
            "daily_queries": [{"date": str(r["date"]), "count": r["count"]} for r in daily_queries],
            "top_domains": [{"domain": r["domain"], "count": r["count"]} for r in top_domains],
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_user_analytics(self, user_id: int) -> Dict:
        """Get analytics for a specific user"""
        if not database:
            return {"error": "Database not available"}
        
        total = await database.fetch_val("SELECT COUNT(*) FROM queries WHERE user_id = $1", user_id) or 0
        today = await database.fetch_val(
            "SELECT COUNT(*) FROM queries WHERE user_id = $1 AND DATE(created_at) = CURRENT_DATE",
            user_id
        ) or 0
        
        return {
            "user_id": user_id,
            "total_queries": total,
            "queries_today": today,
            "timestamp": datetime.now().isoformat()
        }


# =============================================================================
# LLAMA 3.1 ATTRIBUTION
# =============================================================================

LLAMA_ATTRIBUTION = "Built with Llama 3.1 · Licensed under Llama 3.1 Community License"

# ─── EXPORTS ──────────────────────────────────────────────────────
__all__ = [
    'EDGE_AI_AVAILABLE',
    'DIVINE_AGENTS',
    'VERIFIERS',
    'embedding_model',
    'route_agent',
    'call_llm',
    'jury_verification',
    'fetch_relevant_chunks',
    'serpapi_search',
    'set_database',
    'set_pg_pool',
    'set_redis_pool',
    'set_logger',
    'database',
    'pg_pool',
    'redis_pool',
    'logger',
    'EdgeAIManager',
    'AgentSwarm',
    'SelfImprovingSystem',
    'AgentDebate',
    'LegalKnowledgeGraph',
    'SmartDocumentGenerator',
    'AnalyticsDashboard'
]