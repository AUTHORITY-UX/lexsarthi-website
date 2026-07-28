# agent_registry.py - Agent persistence with vector embeddings
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ⚖️ THE ADVOCACY – Global Law Firm

import asyncpg
import json
import logging
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

class AgentRegistry:
    def __init__(self, dsn: str = None):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        self.pool = None
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')  # 384‑dim

    async def connect(self):
        self.pool = await asyncpg.create_pool(self.dsn, min_size=5, max_size=20)

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def create_agent(self, agent_data: Dict) -> int:
        """Insert a new agent with its embedding."""
        async with self.pool.acquire() as conn:
            # Generate embedding from persona_prompt + domain
            text = f"{agent_data['domain']} {agent_data['persona_prompt']}"
            embedding = self.encoder.encode(text).tolist()
            agent_id = await conn.fetchval("""
                INSERT INTO agents (
                    name, domain, category, jurisdiction, experience_level,
                    persona_prompt, key_sections, statutes, embedding
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """, agent_data['name'], agent_data['domain'], agent_data['category'],
                agent_data.get('jurisdiction', 'IN'),
                agent_data.get('experience_level', 'mid'),
                agent_data['persona_prompt'],
                agent_data.get('key_sections', []),
                agent_data.get('statutes', []),
                embedding
            )
            return agent_id

    async def get_agent(self, agent_id: int) -> Dict:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM agents WHERE id = $1", agent_id)
            return dict(row) if row else None

    async def semantic_search(self, query: str, filters: Dict = None, top_k: int = 15) -> List[Dict]:
        """Find top‑k agents by cosine similarity of embeddings."""
        query_emb = self.encoder.encode(query).tolist()
        async with self.pool.acquire() as conn:
            # Use pgvector for cosine distance
            # Assumes pgvector extension installed
            sql = """
                SELECT id, name, domain, category, jurisdiction, experience_level,
                       persona_prompt, key_sections, statutes,
                       1 - (embedding <=> $1) AS similarity
                FROM agents
            """
            conditions = []
            params = [query_emb]
            if filters:
                if filters.get('jurisdiction'):
                    conditions.append("jurisdiction = $" + str(len(params)+1))
                    params.append(filters['jurisdiction'])
                if filters.get('category'):
                    conditions.append("category = $" + str(len(params)+1))
                    params.append(filters['category'])
                if filters.get('min_experience'):
                    conditions.append("experience_level IN ('mid','senior')")  # simplistic
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += " ORDER BY similarity DESC LIMIT $" + str(len(params)+1)
            params.append(top_k)
            rows = await conn.fetch(sql, *params)
            return [dict(r) for r in rows]

    async def log_memory(self, agent_id: int, query: str, response: str, verdict: Dict):
        """Store interaction for future RAG."""
        async with self.pool.acquire() as conn:
            # We'll store as JSON in a 'memories' table with embedding for retrieval
            await conn.execute("""
                INSERT INTO agent_memories (agent_id, query, response, verdict, embedding)
                VALUES ($1, $2, $3, $4, $5)
            """, agent_id, query, response, json.dumps(verdict),
                self.encoder.encode(query + " " + response).tolist())

    async def count_agents(self) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM agents")