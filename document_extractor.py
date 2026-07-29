# document_extractor.py - Document Intelligence (No LlamaIndex)
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ⚖️ THE ADVOCACY – Global Law Firm

import os
import json
import tempfile
import re
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger("unknown_verdict.document")

# ─── SCHEMAS ──────────────────────────────────────────────────────────

class CreditAgreement:
    """Credit Agreement schema"""
    def __init__(self, data: Dict):
        self.lender = data.get('lender', 'Unknown')
        self.borrower = data.get('borrower', 'Unknown')
        self.loan_amount = data.get('loan_amount', 0)
        self.interest_rate = data.get('interest_rate', 0)
        self.term_months = data.get('term_months', 0)
        self.collateral = data.get('collateral', 'None')
        self.default_penalty = data.get('default_penalty', 0)
        self.governing_law = data.get('governing_law', 'IN')
    
    def to_dict(self) -> Dict:
        return {
            "lender": self.lender,
            "borrower": self.borrower,
            "loan_amount": self.loan_amount,
            "interest_rate": self.interest_rate,
            "term_months": self.term_months,
            "collateral": self.collateral,
            "default_penalty": self.default_penalty,
            "governing_law": self.governing_law
        }

class ContractClause:
    """Contract Clause schema"""
    def __init__(self, data: Dict):
        self.clause_title = data.get('clause_title', 'Unknown')
        self.clause_text = data.get('clause_text', '')
        self.parties_involved = data.get('parties_involved', [])
        self.obligations = data.get('obligations', [])
        self.penalties = data.get('penalties', [])
    
    def to_dict(self) -> Dict:
        return {
            "clause_title": self.clause_title,
            "clause_text": self.clause_text,
            "parties_involved": self.parties_involved,
            "obligations": self.obligations,
            "penalties": self.penalties
        }

# ─── DOCUMENT EXTRACTOR ──────────────────────────────────────────────

class DocumentExtractor:
    """Extract structured data from legal documents (No LlamaIndex)"""
    
    def __init__(self):
        self.extractors = [
            self._extract_credit_agreement,
            self._extract_general_contract
        ]
        self._cache = {}
    
    async def extract_from_files(self, files: List[Dict]) -> List[Dict]:
        """Extract data from uploaded files"""
        results = []
        
        for file_info in files:
            try:
                # Get file content
                content = file_info.get('content', '')
                filename = file_info.get('filename', 'unknown')
                
                # If content is bytes, decode
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='ignore')
                
                # Detect document type
                doc_type = self._detect_document_type(content)
                
                # Extract based on type
                if doc_type == "credit_agreement":
                    extracted = self._extract_credit_agreement(content)
                    validation = self._validate_credit_agreement(extracted)
                else:
                    extracted = self._extract_general_contract(content)
                    validation = {"flags": [], "pass": True}
                
                results.append({
                    "filename": filename,
                    "document_type": doc_type,
                    "extracted_data": extracted,
                    "validation": validation,
                    "confidence": 0.85,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Extraction error for {file_info.get('filename', 'unknown')}: {e}")
                results.append({
                    "filename": file_info.get('filename', 'unknown'),
                    "error": str(e),
                    "status": "failed"
                })
        
        return results
    
    def _detect_document_type(self, text: str) -> str:
        """Detect document type from content"""
        text_lower = text.lower()
        if "credit" in text_lower or "loan" in text_lower:
            return "credit_agreement"
        elif "nda" in text_lower or "non-disclosure" in text_lower:
            return "nda"
        elif "employment" in text_lower:
            return "employment_contract"
        else:
            return "general_contract"
    
    def _extract_credit_agreement(self, text: str) -> Dict:
        """Extract credit agreement data using regex"""
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
    
    def _extract_general_contract(self, text: str) -> Dict:
        """Extract general contract data"""
        # Extract parties
        parties = []
        party_pattern = r"Party\s*[A-Z]:?\s*([^\n]+)"
        for match in re.finditer(party_pattern, text, re.IGNORECASE):
            parties.append(match.group(1).strip())
        
        # Extract obligations
        obligations = []
        oblig_pattern = r"(?:shall|will|must)\s+([^\.]+)"
        for match in re.finditer(oblig_pattern, text, re.IGNORECASE):
            obligations.append(match.group(1).strip()[:100])
        
        return {
            "parties": parties[:5] if parties else ["Unknown Party"],
            "obligations": obligations[:5] if obligations else ["Review obligations"],
            "clauses": len(re.findall(r"Clause\s+\d+", text, re.IGNORECASE)),
            "summary": text[:500] + "..." if len(text) > 500 else text
        }
    
    def _validate_credit_agreement(self, data: Dict) -> Dict:
        """Validate credit agreement data"""
        flags = []
        
        if data.get('interest_rate', 0) > 10:
            flags.append("Interest rate exceeds 10% (review required)")
        
        if data.get('default_penalty', 0) > 5:
            flags.append("Default penalty > 5% (review required)")
        
        if data.get('term_months', 0) > 360:
            flags.append("Term > 30 years (unusual)")
        
        if data.get('loan_amount', 0) == 0:
            flags.append("Loan amount not detected")
        
        return {
            "flags": flags,
            "pass": len(flags) == 0
        }

# ─── EXPORT ──────────────────────────────────────────────────────────

__all__ = ["DocumentExtractor", "CreditAgreement", "ContractClause"]