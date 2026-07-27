# ============================================
# ROUTES.PY – REAL ENDPOINTS
# ============================================

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger("unknown_verdict")

# ============================================
# REAL CHAT ENDPOINT
# ============================================

@router.post("/api/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        query = data.get("message", "")
        
        if not query:
            return JSONResponse({"error": "Message required"}, status_code=400)
        
        from core import get_judge
        judge = get_judge()
        result = await judge.process(query)
        
        return {
            "response": result.get("response", ""),
            "agent": result.get("agent", "AI Judge"),
            "confidence": result.get("confidence", 0.85),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# ============================================
# REAL MARKET DATA ENDPOINT
# ============================================

@router.get("/api/market/real")
async def get_real_market_data():
    try:
        from core import get_real_markets
        data = await get_real_markets()
        return {"status": "success", "data": data}
    except Exception as e:
        return {"error": str(e)}

# ============================================
# REAL NEWS ENDPOINT
# ============================================

@router.get("/api/news/real")
async def get_real_news():
    try:
        from core import get_real_news
        news = get_real_news()
        return {"status": "success", "articles": news}
    except Exception as e:
        return {"error": str(e)}

# ============================================
# REAL COMPLIANCE SCAN ENDPOINT
# ============================================

@router.post("/api/compliance/real-scan")
async def real_compliance_scan(request: Request):
    try:
        data = await request.json()
        url = data.get("url", "")
        from core import scan_website
        result = await scan_website(url)
        return {"status": "success", "url": url, "frameworks": result}
    except Exception as e:
        return {"error": str(e)}