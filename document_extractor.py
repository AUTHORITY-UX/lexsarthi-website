# document_extractor.py - Fixed without external extractors
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ⚖️ THE ADVOCACY – Global Law Firm

import os
import json
import tempfile
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

# LlamaIndex imports
from llama_index.core import SimpleDirectoryReader, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.extractors import (
    TitleExtractor,
    SummaryExtractor,
    KeywordExtractor,
)
from llama_index.core.ingestion import IngestionPipeline

# Pydantic
from pydantic import BaseModel, Field

# ─── SCHEMAS ──────────────────────────────────────────────────────────

class CreditAgreement(BaseModel):
    lender: str = Field(description="Name of the lender")
    borrower: str = Field(description="Name of the borrower")
    loan_amount: float = Field(description="Principal amount in USD")
    interest_rate: float = Field(description="Annual interest rate in percentage")
    term_months: int = Field(description="Loan term in months")
    collateral: Optional[str] = Field(description="Collateral description")
    default_penalty: Optional[float] = Field(description="Penalty rate after default")
    governing_law: str = Field(description="Governing jurisdiction", default="IN")

# ─── EXTRACTOR ──────────────────────────────────────────────────────

class DocumentExtractor:
    """Extract structured data from legal documents."""
    
    def __init__(self):
        self.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        self.extractors = [
            TitleExtractor(),
            SummaryExtractor(summaries=["self", "prev", "next"]),
            KeywordExtractor(keywords=10),
        ]
        self.pipeline = IngestionPipeline(
            transformations=[self.node_parser] + self.extractors
        )

    async def extract_from_files(self, files: List[Dict]) -> List[Dict]:
        """Extract structured data from uploaded files."""
        results = []
        for file_info in files:
            try:
                path = file_info.get('path')
                if not path and file_info.get('content'):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(file_info['content'])
                        path = tmp.name

                if not path or not os.path.exists(path):
                    continue

                reader = SimpleDirectoryReader(input_files=[path])
                docs = reader.load_data()

                # Extract using pipeline
                nodes = self.pipeline.run(documents=docs)
                
                # Combine text for analysis
                full_text = "\n".join([doc.text for doc in docs])

                results.append({
                    "filename": file_info.get('filename', 'unknown'),
                    "document_type": self._detect_document_type(full_text),
                    "extracted_data": self._extract_credit_agreement(full_text),
                    "summary": self._generate_summary(docs),
                    "pages": len(docs),
                    "keywords": self._extract_keywords(nodes),
                    "confidence": 0.85,
                    "timestamp": datetime.now().isoformat()
                })

                if path and path.startswith(tempfile.gettempdir()):
                    os.unlink(path)

            except Exception as e:
                results.append({
                    "filename": file_info.get('filename', 'unknown'),
                    "error": str(e),
                    "status": "failed"
                })

        return results

    def _extract_credit_agreement(self, text: str) -> Dict:
        """Extract credit agreement fields using regex."""
        def extract(pattern, default="Unknown"):
            match = re.search(pattern, text, re.IGNORECASE)
            return match.group(1).strip() if match else default

        def extract_float(pattern, default=0.0):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(",", ""))
                except:
                    return default
            return default

        def extract_int(pattern, default=0):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1).replace(",", ""))
                except:
                    return default
            return default

        return {
            "lender": extract(r"Lender:?\s*([^\n]+)", "Unknown Lender"),
            "borrower": extract(r"Borrower:?\s*([^\n]+)", "Unknown Borrower"),
            "loan_amount": extract_float(r"Amount:?\s*\$?([\d,]+\.?[\d]*)", 0),
            "interest_rate": extract_float(r"Interest Rate:?\s*([\d.]+)%", 0),
            "term_months": extract_int(r"Term:?\s*(\d+)\s*months", 0),
            "collateral": extract(r"Collateral:?\s*([^\n]+)", "None"),
            "default_penalty": extract_float(r"Default Penalty:?\s*([\d.]+)%", 0),
            "governing_law": extract(r"Governing Law:?\s*([^\n]+)", "IN")
        }

    def _detect_document_type(self, text: str) -> str:
        """Detect document type."""
        text_lower = text.lower()
        if "credit" in text_lower or "loan" in text_lower:
            return "credit_agreement"
        elif "nda" in text_lower or "non-disclosure" in text_lower:
            return "nda"
        elif "employment" in text_lower:
            return "employment_contract"
        else:
            return "general_contract"

    def _generate_summary(self, docs: List[Document]) -> str:
        if not docs:
            return "No content found"
        text = docs[0].text[:500] if docs else ""
        return f"Document with {len(docs)} pages. Preview: {text[:200]}..."

    def _extract_keywords(self, nodes) -> List[str]:
        keywords = set()
        for node in nodes:
            if hasattr(node, 'metadata') and 'keywords' in node.metadata:
                if isinstance(node.metadata['keywords'], list):
                    keywords.update(node.metadata['keywords'])
                elif isinstance(node.metadata['keywords'], str):
                    keywords.add(node.metadata['keywords'])
        return list(keywords)[:20]