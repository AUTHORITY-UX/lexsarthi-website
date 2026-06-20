# ===================================================================
# Copyright (c) 2026 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# LEXSARTHI IS A PROPERTY OR ASSET OF THE ADVOCACY A LAW FIRM.
# ===================================================================
# LEXSARTHI v4.0 - RUN SCRIPT
# ===================================================================

import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    host = os.getenv("HOST", "0.0.0.0")
    
    print("=" * 80)
    print("⚖️ LEXSARTHI v4.0 - THE COMPLETE LEGAL OS")
    print("=" * 80)
    print("🚀 Starting LexSarthi v4.0 API Server...")
    print(f"📡 Host: {host}")
    print(f"🔌 Port: {port}")
    print(f"🤖 Agents: 73")
    print(f"🔒 Zero Retention: 24 hours")
    print("=" * 80)
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=False,
        workers=1,
        log_level="info"
    )