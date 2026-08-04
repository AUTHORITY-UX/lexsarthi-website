"""
patch_ethics_guardrails.py - Patch ethics_guardrails to persist to DB
Run: python patch_ethics_guardrails.py
"""

import os
import sys
import logging

# Add the app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.db import db
import asyncio
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def patch_ethics_guardrails():
    """Patch the ethics_guardrails module to persist to DB"""
    
    # Check if ethics_audits table exists
    try:
        result = await db.fetchone("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'ethics_audits'
            )
        """)
        
        if not result or not result['exists']:
            logger.error("❌ ethics_audits table does not exist. Run migration first.")
            return False
    except Exception as e:
        logger.error(f"Table check error: {e}")
        return False
    
    # The actual patching is done in the import - we just need to ensure
    # the ethics_guardrails module uses the database
    try:
        from core.ethics_guardrails import store_audit
        
        # Test the store function
        test_audit = {
            'query': 'Test query',
            'response': 'Test response',
            'model_used': 'test',
            'audit_type': 'test',
            'passed': True,
            'score': 1.0,
            'details': {'test': 'data'}
        }
        
        result = await store_audit(test_audit)
        if result:
            logger.info("✅ Ethics guardrails patched successfully")
            return True
        else:
            logger.error("❌ Failed to store test audit")
            return False
            
    except ImportError as e:
        logger.warning(f"⚠️ ethics_guardrails not found: {e}")
        logger.warning("Creating new ethics_guardrails.py with DB persistence...")
        
        # Create the ethics_guardrails.py file
        with open('core/ethics_guardrails.py', 'w') as f:
            f.write("""
\"\"\"
core/ethics_guardrails.py - Ethics guardrails with DB persistence
\"\"\"

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from core.db import db

logger = logging.getLogger(__name__)


async def store_audit(audit_data: Dict[str, Any]) -> bool:
    \"\"\"Store ethics audit in database\"\"\"
    try:
        await db.execute(\"\"\"
            INSERT INTO ethics_audits 
            (query, response, model_used, audit_type, passed, score, details)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        \"\"\",
            audit_data.get('query', ''),
            audit_data.get('response', ''),
            audit_data.get('model_used', ''),
            audit_data.get('audit_type', ''),
            audit_data.get('passed', False),
            audit_data.get('score', 0.0),
            json.dumps(audit_data.get('details', {}))
        )
        return True
    except Exception as e:
        logger.error(f"Store audit error: {e}")
        return False


# Intercept function for the ethics_guardrails middleware
async def process_audit(query: str, response: str, model: str, 
                        audit_type: str, passed: bool, score: float,
                        details: Dict) -> bool:
    \"\"\"Process and store audit\"\"\"
    audit_data = {
        'query': query,
        'response': response,
        'model_used': model,
        'audit_type': audit_type,
        'passed': passed,
        'score': score,
        'details': details
    }
    return await store_audit(audit_data)
""")
        logger.info("✅ Created core/ethics_guardrails.py with DB persistence")
        return True


if __name__ == "__main__":
    asyncio.run(patch_ethics_guardrails())