# document_extractor.py - LlamaIndex extraction with Pydantic schemas
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ⚖️ THE ADVOCACY – Global Law Firm

import os
from typing import List, Dict, Any
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.schema import Document
from llama_index.core.extractors import PydanticExtractor
from pydantic import BaseModel, Field
import json

from schemas import CreditAgreement, ContractClause  # define these

class DocumentExtractor:
    def __init__(self):
        self.extractor = PydanticExtractor()

    async def extract_from_files(self, files: List[Dict]) -> List[Dict]:
        """files: list of {filename: str, content: bytes or path}"""
        documents = []
        for f in files:
            # In production, we'd save files temporarily.
            # Here we assume f['path'] exists.
            reader = SimpleDirectoryReader(input_files=[f['path']])
            docs = reader.load_data()
            documents.extend(docs)

        # Use LlamaIndex to extract structured data
        # For each doc, run extraction with appropriate schema
        extracted = []
        for doc in documents:
            # Detect document type (simplistic)
            if 'credit' in doc.text.lower() or 'loan' in doc.text.lower():
                schema = CreditAgreement
            else:
                schema = ContractClause
            # Run extraction
            result = await self._extract_with_schema(doc, schema)
            extracted.append(result)
        return extracted

    async def _extract_with_schema(self, doc: Document, schema: BaseModel) -> Dict:
        # Use LlamaIndex PydanticExtractor (async version)
        # For simplicity, we'll do a synchronous call
        from llama_index.core.extractors import PydanticExtractor
        extractor = PydanticExtractor(schema)
        extracted = extractor.extract([doc])
        # Convert to dict and add page citations
        return {
            "data": extracted[0].dict(),
            "citations": [{"page": p} for p in range(1, 10)],  # placeholder
            "confidence": 0.9
        }