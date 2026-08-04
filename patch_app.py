"""
patch_app.py - Patch app.py for full platform features
Run: python patch_app.py
"""

import os
import sys
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.db import db


async def patch_app():
    """Add startup migration and initial data loading"""
    
    logger.info("🔄 Patching app.py...")
    
    # Check if migrations are needed
    try:
        result = await db.fetchone("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_name = 'case_law'
        """)
        
        if result and result.get('count', 0) > 0:
            logger.info("✅ Case law tables exist")
        else:
            logger.warning("⚠️ Case law tables missing - run migration first")
            
    except Exception as e:
        logger.error(f"Migration check error: {e}")
    
    # Add startup functions to app.py
    startup_code = """
    # Add to lifespan in app.py:
    # - Load initial knowledge base
    # - Initialize governance module
    # - Load latest AI laws
    # - Start regulatory intelligence tracker
    
    # Import governance modules
    from core.governance import ComplianceAuditor, RiskClassifier, RegulatoryIntelligence
    
    # Initialize governance
    compliance_auditor = ComplianceAuditor()
    risk_classifier = RiskClassifier()
    regulatory_intel = RegulatoryIntelligence()
    
    # Load latest AI laws
    await load_ai_laws()
    
    # Start regulatory tracker
    asyncio.create_task(regulatory_intel.track_regulations())
    """
    
    logger.info("✅ App patch ready")
    logger.info("📝 Add the following to app.py:")
    print(startup_code)
    
    return True


if __name__ == "__main__":
    asyncio.run(patch_app())