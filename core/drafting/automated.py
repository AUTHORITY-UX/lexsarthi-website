"""
core/drafting/automated.py - Automated Legal Document Drafting
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.llm import LLMMessage, get_router
from core.db import db

logger = logging.getLogger(__name__)


class AutomatedLegalDrafting:
    """Automated legal document drafting with templates"""
    
    TEMPLATES = {
        'contract': {
            'name': 'Contract',
            'sections': ['Parties', 'Recitals', 'Definitions', 'Terms', 'Payment', 'Termination', 'Signatures'],
            'prompt': 'Draft a contract between {party_a} and {party_b} for {purpose}'
        },
        'petition': {
            'name': 'Petition',
            'sections': ['Title', 'Parties', 'Facts', 'Grounds', 'Prayer'],
            'prompt': 'Draft a petition for {court} regarding {matter}'
        },
        'affidavit': {
            'name': 'Affidavit',
            'sections': ['Title', 'Deponent', 'Statement of Facts', 'Verification'],
            'prompt': 'Draft an affidavit for {case} regarding {facts}'
        },
        'notice': {
            'name': 'Legal Notice',
            'sections': ['Title', 'Recipient', 'Content', 'Action Required', 'Deadline'],
            'prompt': 'Draft a legal notice regarding {matter} to {recipient}'
        },
        'agreement': {
            'name': 'Agreement',
            'sections': ['Parties', 'Purpose', 'Terms', 'Payment', 'Termination', 'Signatures'],
            'prompt': 'Draft an agreement between {party_a} and {party_b} for {purpose}'
        },
        'pleading': {
            'name': 'Pleading',
            'sections': ['Caption', 'Jurisdiction', 'Parties', 'Facts', 'Causes of Action', 'Prayer'],
            'prompt': 'Draft a pleading for {court} in {case_type}'
        },
        'will': {
            'name': 'Will',
            'sections': ['Introduction', 'Executor', 'Beneficiaries', 'Assets', 'Guardianship', 'Signatures'],
            'prompt': 'Draft a will for {testator} with beneficiaries {beneficiaries}'
        }
    }
    
    def __init__(self):
        self.router = get_router()
    
    async def draft_document(self, template_type: str, context: Dict, style: str = 'formal') -> Dict:
        """Draft legal document from template"""
        template = self.TEMPLATES.get(template_type)
        if not template:
            return {'error': f'Template {template_type} not found'}
        
        # Build prompt
        try:
            prompt = template['prompt'].format(**context)
        except KeyError as e:
            return {'error': f'Missing context: {e}'}
        
        # Generate draft
        messages = [
            LLMMessage(role="system", content=f"""You are an expert legal drafter specializing in {template_type}s.
            Draft a professional {template_type} with the following sections: {', '.join(template['sections'])}
            Use {style} legal language, proper citations, and clear structure.
            Include all necessary legal elements and clauses.
            Format with proper headings and numbering."""),
            LLMMessage(role="user", content=prompt)
        ]
        
        response = await self.router.chat(messages, complexity="complex")
        
        return {
            'template': template_type,
            'sections': template['sections'],
            'content': response.content,
            'generated_at': datetime.now().isoformat(),
            'style': style,
            'word_count': len(response.content.split())
        }
    
    async def redline_document(self, document: str, changes: List[Dict]) -> str:
        """Redline document with proposed changes"""
        messages = [
            LLMMessage(role="system", content="""You are a legal document reviewer.
            Redline the document with the proposed changes.
            Show additions with [ADD], deletions with [DEL], and comments with [COMMENT]."""),
            LLMMessage(role="user", content=f"Document:\n{document}\n\nChanges:\n{json.dumps(changes, indent=2)}")
        ]
        
        response = await self.router.chat(messages, complexity="complex")
        return response.content
    
    async def review_document(self, document: str, jurisdiction: str = 'india') -> Dict:
        """Review document for legal issues"""
        messages = [
            LLMMessage(role="system", content=f"""Review this legal document for {jurisdiction} law.
            Identify:
            1. Key clauses and obligations
            2. Missing standard clauses
            3. Potential risks and liabilities
            4. Compliance issues
            5. Recommendations for improvement"""),
            LLMMessage(role="user", content=document)
        ]
        
        response = await self.router.chat(messages, complexity="complex")
        
        return {
            'document_length': len(document.split()),
            'review': response.content,
            'jurisdiction': jurisdiction,
            'reviewed_at': datetime.now().isoformat()
        }
    
    async def get_templates(self) -> Dict:
        """Get all available templates"""
        return self.TEMPLATES


legal_drafting = AutomatedLegalDrafting()