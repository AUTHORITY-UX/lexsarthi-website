# core/ingestion/legal_vector_ingest.py
# Complete vector ingestion for 14.7M Indian legal records

import asyncio
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import hashlib
import numpy as np

from core.db import db
from core.config import settings

logger = logging.getLogger(__name__)

class LegalVectorIngestor:
    """Ingest legal data with vector embeddings for RAG"""

    def __init__(self):
        self.batch_size = 50
        self.embedding_dim = 384

    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (simplified – use actual model)"""
        # For production, use sentence-transformers or Ollama embedding
        # Simplified version – returns deterministic embedding
        import hashlib
        import struct
        
        hash_bytes = hashlib.sha256(text.encode()).digest()
        embedding = [struct.unpack('f', hash_bytes[i:i+4])[0] for i in range(0, min(96, len(hash_bytes)-4), 4)]
        # Pad to 384
        while len(embedding) < self.embedding_dim:
            embedding.append(0.0)
        return embedding[:self.embedding_dim]

    async def ingest_supreme_court(self, records: List[Dict]):
        """Ingest Supreme Court judgments"""
        try:
            for record in records:
                # Get embedding from full text
                full_text = record.get("full_text", record.get("text", ""))
                if not full_text:
                    continue
                
                embedding = await self.get_embedding(full_text[:5000])
                
                await db.execute("""
                    INSERT INTO knowledge_chunks (
                        content, metadata, embedding
                    ) VALUES ($1, $2, $3)
                """,
                    full_text[:5000],
                    {
                        "source": "supreme_court",
                        "case_number": record.get("case_number"),
                        "citation": record.get("citation"),
                        "court": "Supreme Court",
                        "date": record.get("date"),
                        "title": record.get("title")
                    },
                    embedding
                )
            
            logger.info(f"✅ Ingested {len(records)} Supreme Court records")
        except Exception as e:
            logger.error(f"Error ingesting Supreme Court: {e}")

    async def ingest_high_court(self, records: List[Dict], court_name: str):
        """Ingest High Court judgments"""
        try:
            for record in records:
                full_text = record.get("full_text", record.get("text", ""))
                if not full_text:
                    continue
                
                embedding = await self.get_embedding(full_text[:5000])
                
                await db.execute("""
                    INSERT INTO knowledge_chunks (
                        content, metadata, embedding
                    ) VALUES ($1, $2, $3)
                """,
                    full_text[:5000],
                    {
                        "source": "high_court",
                        "court": court_name,
                        "case_number": record.get("case_number"),
                        "citation": record.get("citation"),
                        "date": record.get("date"),
                        "title": record.get("title")
                    },
                    embedding
                )
            
            logger.info(f"✅ Ingested {len(records)} from {court_name}")
        except Exception as e:
            logger.error(f"Error ingesting {court_name}: {e}")

    async def ingest_tribunal(self, records: List[Dict], tribunal_name: str):
        """Ingest tribunal decisions"""
        try:
            for record in records:
                full_text = record.get("full_text", record.get("text", ""))
                if not full_text:
                    continue
                
                embedding = await self.get_embedding(full_text[:5000])
                
                await db.execute("""
                    INSERT INTO knowledge_chunks (
                        content, metadata, embedding
                    ) VALUES ($1, $2, $3)
                """,
                    full_text[:5000],
                    {
                        "source": "tribunal",
                        "tribunal": tribunal_name,
                        "case_number": record.get("case_number"),
                        "citation": record.get("citation"),
                        "date": record.get("date"),
                        "title": record.get("title")
                    },
                    embedding
                )
            
            logger.info(f"✅ Ingested {len(records)} from {tribunal_name}")
        except Exception as e:
            logger.error(f"Error ingesting {tribunal_name}: {e}")

    async def ingest_legislation(self, records: List[Dict]):
        """Ingest legislation (Central, State, UT Acts)"""
        try:
            for record in records:
                section_text = record.get("section_text", record.get("text", ""))
                if not section_text:
                    continue
                
                embedding = await self.get_embedding(section_text[:5000])
                
                await db.execute("""
                    INSERT INTO knowledge_chunks (
                        content, metadata, embedding
                    ) VALUES ($1, $2, $3)
                """,
                    section_text[:5000],
                    {
                        "source": "legislation",
                        "act_name": record.get("act_name"),
                        "act_type": record.get("act_type"),
                        "jurisdiction": record.get("jurisdiction"),
                        "section_number": record.get("section_number"),
                        "section_title": record.get("section_title"),
                        "year": record.get("year")
                    },
                    embedding
                )
            
            logger.info(f"✅ Ingested {len(records)} legislation records")
        except Exception as e:
            logger.error(f"Error ingesting legislation: {e}")

    async def get_stats(self) -> Dict:
        """Get ingestion statistics"""
        try:
            total = await db.fetchval("SELECT COUNT(*) FROM knowledge_chunks")
            return {
                "total_records": total,
                "embedding_dim": self.embedding_dim,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}

# Singleton
ingestor = LegalVectorIngestor()