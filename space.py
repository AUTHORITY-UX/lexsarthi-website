# space.py - Hugging Face Space Entry Point
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE

import os
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s  | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("unknown_verdict.space")

# Import app
try:
    from app import app
    logger.info("✅ Successfully imported app")
except Exception as e:
    logger.error(f"❌ Failed to import app: {e}")
    raise

# Create a simple wrapper for HF Spaces
def main():
    """Main entry point for Hugging Face Space"""
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    
    logger.info("=" * 60)
    logger.info("🚀 Unknown Verdict v40.0 - Hugging Face Space")
    logger.info("=" * 60)
    logger.info(f"   ├─ Port: {port}")
    logger.info(f"   ├─ Version: 40.0")
    logger.info(f"   ├─ Status: 🟢 Starting")
    logger.info("=" * 60)
    logger.info("🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE")
    logger.info("⚖️ THE ADVOCACY – Global Law Firm")
    logger.info("=" * 60)
    
    # Run the app
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()