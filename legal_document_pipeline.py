# legal_document_pipeline.py
"""
Complete Legal Document Automation Pipeline
Automates ingestion, processing, and updating of legal documents
"""

import os
import json
import hashlib
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("legal_docs")

class LegalDocumentPipeline:
    """Automated legal document processing pipeline"""
    
    def __init__(self, embedding_model, database):
        self.embedding_model = embedding_model
        self.db = database
        self.doc_sources = {
            "constitution": {
                "url": "https://legislative.gov.in/constitution-of-india",
                "files": ["constitution_of_india.pdf"],
                "priority": 1
            },
            "ipc": {
                "url": "https://devgan.in/ipc/",
                "files": ["indian_penal_code.pdf"],
                "priority": 2
            },
            "crpc": {
                "url": "https://devgan.in/crpc/",
                "files": ["code_of_criminal_procedure.pdf"],
                "priority": 2
            },
            "contract_act": {
                "url": "https://devgan.in/contract_act/",
                "files": ["indian_contract_act.pdf"],
                "priority": 2
            },
            "companies_act": {
                "url": "https://mca.gov.in/",
                "files": ["companies_act_2013.pdf"],
                "priority": 3
            },
            "gst_act": {
                "url": "https://cbic-gst.gov.in/",
                "files": ["gst_act.pdf"],
                "priority": 3
            }
        }
        
        self.update_frequency = {
            1: "daily",
            2: "weekly",
            3: "monthly"
        }
    
    async def process_all_documents(self):
        """Process all legal documents"""
        logger.info("📚 Starting legal document processing...")
        
        results = {}
        for doc_name, doc_config in self.doc_sources.items():
            try:
                logger.info(f"Processing {doc_name}...")
                result = await self.process_document(doc_name, doc_config)
                results[doc_name] = result
                logger.info(f"✅ Processed {doc_name}")
            except Exception as e:
                logger.error(f"❌ Failed to process {doc_name}: {e}")
                results[doc_name] = {"status": "failed", "error": str(e)}
        
        return results
    
    async def process_document(self, doc_name: str, config: Dict) -> Dict:
        """Process a single legal document"""
        
        # 1. Check for updates
        version_info = await self.check_for_updates(doc_name, config)
        
        if not version_info['updated']:
            return {
                "status": "skipped",
                "reason": "No updates found"
            }
        
        # 2. Download document
        pdf_path = await self.download_document(doc_name, config)
        
        # 3. Extract text
        text = await self.extract_text(pdf_path)
        
        # 4. Chunk and embed
        chunks = await self.chunk_and_embed(text, doc_name)
        
        # 5. Store in database
        await self.store_chunks(chunks, doc_name, version_info)
        
        # 6. Update knowledge base
        await self.update_knowledge_base(doc_name, version_info)
        
        return {
            "status": "success",
            "chunks": len(chunks),
            "version": version_info['version'],
            "updated_at": datetime.now().isoformat()
        }
    
    async def check_for_updates(self, doc_name: str, config: Dict) -> Dict:
        """Check if document has been updated"""
        # In production, check via API or file hash
        # For now, check by file modification time
        for pdf_file in config['files']:
            pdf_path = Path(f"legal_docs/{pdf_file}")
            if pdf_path.exists():
                # Get current version from database
                current_version = await self.db.fetch_val(
                    "SELECT version FROM document_versions WHERE name = $1",
                    doc_name
                )
                
                # Calculate file hash
                with open(pdf_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                
                # Check if version changed
                if current_version != file_hash:
                    return {
                        "updated": True,
                        "version": file_hash,
                        "previous_version": current_version
                    }
                else:
                    return {
                        "updated": False,
                        "version": current_version
                    }
        
        # New document
        return {
            "updated": True,
            "version": "initial",
            "previous_version": None
        }
    
    async def download_document(self, doc_name: str, config: Dict) -> Path:
        """Download document from source"""
        # In production, download from URL
        # For now, use existing local files
        for pdf_file in config['files']:
            pdf_path = Path(f"legal_docs/{pdf_file}")
            if pdf_path.exists():
                return pdf_path
        
        # Create placeholder if not exists
        os.makedirs("legal_docs", exist_ok=True)
        pdf_path = Path(f"legal_docs/{doc_name}.pdf")
        pdf_path.touch()
        return pdf_path
    
    async def extract_text(self, pdf_path: Path) -> str:
        """Extract text from PDF"""
        import pdfplumber
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    async def chunk_and_embed(self, text: str, doc_name: str) -> List[Dict]:
        """Chunk text and generate embeddings"""
        chunks = []
        words = text.split()
        chunk_size = 800
        overlap = 150
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk_text = " ".join(words[i:i+chunk_size])
            if chunk_text:
                embedding = self.embedding_model.encode(chunk_text).tolist()
                chunks.append({
                    "content": chunk_text,
                    "embedding": embedding,
                    "metadata": {
                        "source": doc_name,
                        "chunk_index": len(chunks),
                        "total_chunks": len(words) // (chunk_size - overlap) + 1
                    }
                })
        
        return chunks
    
    async def store_chunks(self, chunks: List[Dict], doc_name: str, version_info: Dict):
        """Store chunks in database"""
        for chunk in chunks:
            await self.db.execute(
                """
                INSERT INTO knowledge_chunks (content, metadata, embedding)
                VALUES ($1, $2, $3)
                ON CONFLICT DO NOTHING
                """,
                chunk['content'],
                json.dumps(chunk['metadata']),
                json.dumps(chunk['embedding'])
            )
        
        # Update document version
        await self.db.execute(
            """
            INSERT INTO document_versions (name, version, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (name) DO UPDATE
            SET version = $2, updated_at = NOW()
            """,
            doc_name,
            version_info['version']
        )
    
    async def update_knowledge_base(self, doc_name: str, version_info: Dict):
        """Update knowledge base with new document"""
        # Trigger knowledge base rebuild
        logger.info(f"Knowledge base updated: {doc_name}")

class LegalUpdateMonitor:
    """Monitor legal document updates"""
    
    def __init__(self, pipeline: LegalDocumentPipeline):
        self.pipeline = pipeline
        
    async def monitor_continuous(self):
        """Continuously monitor for updates"""
        while True:
            try:
                logger.info("🔍 Checking for legal document updates...")
                results = await self.pipeline.process_all_documents()
                
                # Log results
                updated = [name for name, result in results.items() 
                          if result.get('status') == 'success']
                
                if updated:
                    logger.info(f"✅ Updated documents: {', '.join(updated)}")
                else:
                    logger.info("No updates found")
                
                # Wait 1 hour before next check
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(60)

async def schedule_legal_updates(scheduler):
    """Schedule legal document updates"""
    
    pipeline = LegalDocumentPipeline(embedding_model, database)
    
    # Hourly check for updates
    scheduler.add_job(
        pipeline.process_all_documents,
        IntervalTrigger(hours=1),
        id="legal_updates"
    )
    
    logger.info("📚 Legal document updates scheduled")

# ─── LEGAL DOCUMENT SEARCH ENHANCEMENT ────────────────────────────

class LegalSearchEngine:
    """Enhanced legal document search with Edge AI"""
    
    def __init__(self, embedding_model, edge_ai):
        self.embedding_model = embedding_model
        self.edge_ai = edge_ai
    
    async def search(self, query: str, use_edge: bool = True) -> List[Dict]:
        """Search legal documents with optional Edge AI enhancement"""
        
        # 1. Vector search
        results = await self.vector_search(query)
        
        # 2. Edge AI enhancement
        if use_edge and self.edge_ai:
            enhanced_results = await self.edge_ai_enhance(results)
            results = enhanced_results
        
        # 3. Rank results
        results = sorted(results, key=lambda x: x.get('relevance', 0), reverse=True)
        
        return results[:5]  # Top 5 results
    
    async def vector_search(self, query: str) -> List[Dict]:
        """Traditional vector search"""
        embedding = self.embedding_model.encode(query).tolist()
        
        # Search database
        results = await self.db.fetch_all(
            """
            SELECT content, metadata, 1 - (embedding <=> $1) as relevance
            FROM knowledge_chunks
            ORDER BY embedding <=> $1
            LIMIT 10
            """,
            json.dumps(embedding)
        )
        
        return [dict(r) for r in results]
    
    async def edge_ai_enhance(self, results: List[Dict]) -> List[Dict]:
        """Enhance search results with Edge AI"""
        for result in results:
            # Classify document type
            doc_type = await self.edge_ai.process_legal_document(
                result['content'].encode(),
                "search_result"
            )
            result['document_type'] = doc_type.get('classification')
            result['edge_confidence'] = doc_type.get('confidence')
            result['relevance'] = (result.get('relevance', 0) + 
                                  doc_type.get('confidence', 0)) / 2
        
        return results