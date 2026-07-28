# document_extractor.py - Fixed LlamaIndex Extraction
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ⚖️ THE ADVOCACY – Global Law Firm

import os
import json
import tempfile
from typing import List, Dict, Any, Optional
from datetime import datetime

# LlamaIndex imports - FIXED
from llama_index.core import SimpleDirectoryReader, Document
from llama_index.core.schemas import BaseNode
from llama_index.core.extractors import (
    TitleExtractor,
    SummaryExtractor,
    KeywordExtractor,
    EntityExtractor,
)
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter

# Pydantic for schemas
from pydantic import BaseModel, Field
from typing import Optional, List

# ─── SCHEMAS ──────────────────────────────────────────────────────────

class CreditAgreement(BaseModel):
    lender: str = Field(description="Name of the lender")
    borrower: str = Field(description="Name of the borrower")
    loan_amount: float = Field(description="Principal amount in USD")
    interest_rate: float = Field(description="Annual interest rate in percentage")
    term_months: int = Field(description="Loan term in months")
    collateral: Optional[str] = Field(description="Collateral description")
    default_penalty: Optional[float] = Field(description="Penalty rate after default")
    governing_law: str = Field(description="Governing jurisdiction")

class ContractClause(BaseModel):
    clause_title: str = Field(description="Title of the clause")
    clause_text: str = Field(description="Full text of the clause")
    parties_involved: List[str] = Field(description="Parties affected")
    obligations: List[str] = Field(description="Obligations imposed")
    penalties: List[str] = Field(description="Penalties for breach")

# ─── EXTRACTOR ──────────────────────────────────────────────────────

class DocumentExtractor:
    """Extract structured data from legal documents using LlamaIndex."""
    
    def __init__(self):
        self.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        self.extractors = [
            TitleExtractor(),
            SummaryExtractor(summaries=["self", "prev", "next"]),
            KeywordExtractor(keywords=10),
            EntityExtractor(prediction_threshold=0.5),
        ]
        self.pipeline = IngestionPipeline(
            transformations=[self.node_parser] + self.extractors
        )

    async def extract_from_files(self, files: List[Dict]) -> List[Dict]:
        """
        Extract structured data from uploaded files.
        files: list of {filename: str, path: str, content: bytes}
        """
        results = []
        for file_info in files:
            try:
                # Load document
                path = file_info.get('path')
                if not path and file_info.get('content'):
                    # Write content to temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(file_info['content'])
                        path = tmp.name

                if not path or not os.path.exists(path):
                    continue

                # Read with LlamaIndex
                reader = SimpleDirectoryReader(input_files=[path])
                docs = reader.load_data()

                # Run extraction pipeline
                nodes = self.pipeline.run(documents=docs)

                # Extract key information
                extracted = self._extract_structured_data(nodes, docs)

                # Detect document type
                doc_type = self._detect_document_type(docs)

                results.append({
                    "filename": file_info.get('filename', 'unknown'),
                    "document_type": doc_type,
                    "extracted_data": extracted,
                    "summary": self._generate_summary(docs),
                    "pages": len(docs),
                    "entities": self._extract_entities(nodes),
                    "keywords": self._extract_keywords(nodes),
                    "confidence": 0.85,  # Placeholder
                    "timestamp": datetime.now().isoformat()
                })

                # Cleanup temp file
                if path and path.startswith(tempfile.gettempdir()):
                    os.unlink(path)

            except Exception as e:
                results.append({
                    "filename": file_info.get('filename', 'unknown'),
                    "error": str(e),
                    "status": "failed"
                })

        return results

    def _extract_structured_data(self, nodes: List[BaseNode], docs: List[Document]) -> Dict:
        """Extract structured data from nodes."""
        # Combine all text
        full_text = "\n".join([doc.text for doc in docs])
        
        # Try to detect and extract based on document type
        if "credit" in full_text.lower() or "loan" in full_text.lower():
            return self._extract_credit_agreement(full_text)
        else:
            return self._extract_general_contract(full_text)

    def _extract_credit_agreement(self, text: str) -> Dict:
        """Extract credit agreement fields using simple pattern matching."""
        # This is a simplified version - in production, use LLM or regex
        import re
        
        def extract_field(pattern, text, default="Unknown"):
            match = re.search(pattern, text, re.IGNORECASE)
            return match.group(1).strip() if match else default

        return {
            "lender": extract_field(r"Lender:?\s*([^\n]+)", text),
            "borrower": extract_field(r"Borrower:?\s*([^\n]+)", text),
            "loan_amount": float(extract_field(r"Amount:?\s*\$?([\d,]+)", text).replace(",", "") or 0),
            "interest_rate": float(extract_field(r"Interest Rate:?\s*([\d.]+)%", text) or 0),
            "term_months": int(extract_field(r"Term:?\s*(\d+)\s*months", text) or 0),
            "collateral": extract_field(r"Collateral:?\s*([^\n]+)", text),
            "default_penalty": float(extract_field(r"Default Penalty:?\s*([\d.]+)%", text) or 0),
            "governing_law": extract_field(r"Governing Law:?\s*([^\n]+)", text, "IN")
        }

    def _extract_general_contract(self, text: str) -> Dict:
        """Extract general contract data."""
        return {
            "parties": [],
            "clauses": [],
            "obligations": [],
            "penalties": []
        }

    def _detect_document_type(self, docs: List[Document]) -> str:
        """Detect document type from content."""
        full_text = "\n".join([doc.text for doc in docs]).lower()
        if "credit" in full_text or "loan" in full_text:
            return "credit_agreement"
        elif "nda" in full_text or "non-disclosure" in full_text:
            return "nda"
        elif "employment" in full_text:
            return "employment_contract"
        else:
            return "general_contract"

    def _generate_summary(self, docs: List[Document]) -> str:
        """Generate a summary of the document."""
        if not docs:
            return "No content found"
        text = docs[0].text[:500] if docs else ""
        return f"Document contains {len(docs)} pages. Preview: {text[:200]}..."

    def _extract_entities(self, nodes: List[BaseNode]) -> List[str]:
        """Extract entities from nodes."""
        entities = set()
        for node in nodes:
            if hasattr(node, 'metadata') and 'entities' in node.metadata:
                entities.update(node.metadata['entities'])
        return list(entities)[:20]

    def _extract_keywords(self, nodes: List[BaseNode]) -> List[str]:
        """Extract keywords from nodes."""
        keywords = set()
        for node in nodes:
            if hasattr(node, 'metadata') and 'keywords' in node.metadata:
                keywords.update(node.metadata['keywords'])
        return list(keywords)[:20]