# ===================================================================
# Copyright (c) 2026 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# LEXSARTHI IS A PROPERTY OR ASSET OF THE ADVOCACY A LAW FIRM.
# ===================================================================
# LEXSARTHI v4.0 - THE COMPLETE LEGAL OS
# $10B VISION - SINGLE PROVIDER FOR ALL LEGAL WORK AUTOMATION
# ===================================================================
# Powered By THE ADVOCACY A LAW FIRM
# ===================================================================

import uvicorn

if __name__ == "__main__":
    # Port 7860 is the default for Hugging Face Spaces
    # reload=False for production stability
    uvicorn.run(
        "app:app",           # app.py file, app instance
        host="0.0.0.0",      # Listen on all network interfaces
        port=7860,           # Hugging Face default port
        reload=False,        # Production mode - no auto-reload
        workers=1            # Single worker for stability
    )