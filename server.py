# ===================================================================
# LEXSARTHI v4.0 - SERVER CONFIGURATION
# ===================================================================
# Copyright (c) 2026 THE ADVOCACY A LAW FIRM. All rights reserved.
# Confidential and proprietary. Do not distribute without a license.
# LEXSARTHI IS A PROPERTY OR ASSET OF THE ADVOCACY A LAW FIRM.
# ===================================================================
# "From Contract Review to Supreme Court Judgments"
# "From Law School to Global Legal Practice"
# "One Platform. Every Legal Need. Anywhere in the World."
# ===================================================================
# Powered By THE ADVOCACY A LAW FIRM
# ===================================================================
# 🔥 USING OPENROUTER - UNLIMITED TOKENS
# 🔥 NO OPENAI DEPENDENCY - PURE FASTAPI
# ===================================================================

import os
import uvicorn
from app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        workers=1,
        reload=False,
        log_level="info"
    )