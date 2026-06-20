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
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)
    