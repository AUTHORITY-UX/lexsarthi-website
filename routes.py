# routes.py - All API endpoints for Unknown Verdict v40.0
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE

import asyncio
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request, File, UploadFile, Form
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel

from core import get_core, get_verifiers, get_judge, get_agent_status

logger = logging.getLogger("unknown_verdict.routes")

# ─── ROUTER ──────────────────────────────────────────────────────────

router = APIRouter(prefix="/api", tags=["Unknown Verdict v40.0"])

# ─── MODELS ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    jurisdiction: Optional[str] = "IN"
    age_group: Optional[str] = "adult"
    case_type: Optional[str] = "general"
    user_id: Optional[str] = None
    unrestricted: Optional[bool] = False
    files: Optional[List[str]] = None

class MarketRequest(BaseModel):
    symbol: str = "AAPL"
    timeframe: Optional[str] = "1d"

class ComplianceRequest(BaseModel):
    text: str
    jurisdiction: Optional[str] = "IN"
    categories: Optional[List[str]] = None
    risk_level: Optional[str] = "medium"

# ─── ENDPOINTS ──────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    core = get_core()
    return {
        "status": "healthy",
        "version": "40.0",
        "timestamp": datetime.now().isoformat(),
        "agents": {
            "total": len(core.agents),
            "active": sum(1 for a in core.agents if a["status"] == "active")
        },
        "verifiers": {
            "total": len(core.verifiers),
            "active": sum(1 for v in core.verifiers if v.status == "active")
        },
        "judge": core.judge.get_stats()
    }

@router.post("/chat")
async def chat(request: ChatRequest):
    """Main chat endpoint - processes legal queries"""
    core = get_core()
    
    try:
        # Analyze the legal case
        result = await core.analyze_legal_case(
            query=request.query,
            jurisdiction=request.jurisdiction,
            age_group=request.age_group,
            case_type=request.case_type,
            user_id=request.user_id
        )
        
        # Add verifiers and judge info
        result["verifiers"] = [v.to_dict() for v in core.verifiers]
        result["judge"] = core.judge.get_stats()
        
        return JSONResponse({
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint"""
    core = get_core()
    
    async def generate():
        try:
            # Start with acknowledgment
            yield f"data: {json.dumps({'type': 'start', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Process query
            result = await core.analyze_legal_case(
                query=request.query,
                jurisdiction=request.jurisdiction,
                age_group=request.age_group,
                case_type=request.case_type,
                user_id=request.user_id
            )
            
            # Stream chunks of the response
            chunks = [
                "Legal analysis initiated...",
                "🔍 Reviewing case details...",
                "⚖️ Applying legal framework...",
                "📚 Cross-referencing precedents...",
                "✅ Analysis complete"
            ]
            
            for chunk in chunks:
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                await asyncio.sleep(0.5)
            
            # Final result
            yield f"data: {json.dumps({'type': 'complete', 'result': result})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )

@router.post("/compliance")
async def check_compliance(request: ComplianceRequest):
    """Check legal compliance"""
    core = get_core()
    
    try:
        result = await core.check_compliance(
            text=request.text,
            jurisdiction=request.jurisdiction,
            categories=request.categories,
            risk_level=request.risk_level
        )
        
        return JSONResponse({
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Compliance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents")
async def get_agents():
    """Get all agent status"""
    core = get_core()
    return JSONResponse({
        "status": "success",
        "data": get_agent_status(),
        "timestamp": datetime.now().isoformat()
    })

@router.get("/verifiers")
async def get_all_verifiers():
    """Get all verifiers"""
    return JSONResponse({
        "status": "success",
        "data": get_verifiers(),
        "timestamp": datetime.now().isoformat()
    })

@router.get("/judge")
async def get_judge_info():
    """Get judge information"""
    return JSONResponse({
        "status": "success",
        "data": get_judge(),
        "timestamp": datetime.now().isoformat()
    })

@router.get("/stats")
async def get_stats():
    """Get system statistics"""
    core = get_core()
    return JSONResponse({
        "status": "success",
        "data": core.get_system_stats(),
        "timestamp": datetime.now().isoformat()
    })

@router.post("/market/quote")
async def get_market_quote(request: MarketRequest):
    """Get market quote"""
    core = get_core()
    
    try:
        result = await core.get_market_quote(request.symbol)
        return JSONResponse({
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Market error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/news")
async def get_news(
    category: str = "general",
    limit: int = 10,
    source: Optional[str] = None
):
    """Get news"""
    core = get_core()
    
    try:
        result = await core.get_news(category, limit, source)
        return JSONResponse({
            "status": "success",
            "data": result,
            "count": len(result),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"News error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Unknown Verdict v40.0",
        "version": "40.0",
        "status": "online",
        "firm": "THE ADVOCACY – Global Law Firm",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/docs/status")
async def docs_status():
    """API documentation status"""
    return {
        "status": "available",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json"
    }