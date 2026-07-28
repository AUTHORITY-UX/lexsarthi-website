# routes.py - All API endpoints for Unknown Verdict v40.0
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE
# ⚖️ THE ADVOCACY – Global Law Firm

import asyncio
import json
import logging
import random
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
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

# ─── ROOT ENDPOINT ──────────────────────────────────────────────────

@router.get("/")
async def api_root():
    """API root endpoint"""
    return {
        "name": "Unknown Verdict v40.0",
        "version": "40.0",
        "status": "online",
        "firm": "THE ADVOCACY – Global Law Firm",
        "endpoints": {
            "chat": "/api/chat",
            "health": "/api/health",
            "agents": "/api/agents",
            "verifiers": "/api/verifiers",
            "judge": "/api/judge",
            "stats": "/api/stats",
            "compliance": "/api/compliance",
            "market": "/api/market/quote",
            "news": "/api/news",
            "info": "/api/info",
            "docs": "/docs"
        },
        "timestamp": datetime.now().isoformat()
    }

# ─── HEALTH CHECK ──────────────────────────────────────────────────

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
        "judge": core.judge.get_stats() if hasattr(core, 'judge') else {"status": "active"}
    }

# ─── CHAT ENDPOINT ──────────────────────────────────────────────────

@router.post("/chat")
async def chat(request: ChatRequest):
    """Main chat endpoint - processes legal queries"""
    core = get_core()
    
    try:
        query = request.query
        jurisdiction = request.jurisdiction or "IN"
        
        logger.info(f"📨 Chat request: {query[:50]}... (jurisdiction: {jurisdiction})")
        
        result = await core.analyze_legal_case(
            query=query,
            jurisdiction=jurisdiction,
            age_group=request.age_group or "adult",
            case_type=request.case_type or "general",
            user_id=request.user_id
        )
        
        result["verifiers"] = [v.to_dict() for v in core.verifiers]
        result["judge"] = core.judge.get_stats() if hasattr(core, 'judge') else {"status": "active"}
        
        return JSONResponse({
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ─── CHAT STREAM ENDPOINT ──────────────────────────────────────────

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint"""
    core = get_core()
    
    async def generate():
        try:
            yield f"data: {json.dumps({'type': 'start', 'timestamp': datetime.now().isoformat()})}\n\n"
            
            result = await core.analyze_legal_case(
                query=request.query,
                jurisdiction=request.jurisdiction or "IN",
                age_group=request.age_group or "adult",
                case_type=request.case_type or "general",
                user_id=request.user_id
            )
            
            chunks = [
                "🔍 Analyzing your legal query...",
                "⚖️ Reviewing relevant laws...",
                "📚 Checking precedents...",
                "✅ Analysis complete"
            ]
            
            for chunk in chunks:
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                await asyncio.sleep(0.5)
            
            yield f"data: {json.dumps({'type': 'complete', 'result': result})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )

# ─── AGENTS ENDPOINT ──────────────────────────────────────────────────

@router.get("/agents")
async def get_agents():
    """Get all agent status"""
    core = get_core()
    return JSONResponse({
        "status": "success",
        "data": {
            "total": len(core.agents),
            "active": sum(1 for a in core.agents if a["status"] == "active"),
            "agents": core.agents[:20]
        },
        "timestamp": datetime.now().isoformat()
    })

# ─── VERIFIERS ENDPOINT ──────────────────────────────────────────────

@router.get("/verifiers")
async def get_all_verifiers():
    """Get all verifiers"""
    core = get_core()
    return JSONResponse({
        "status": "success",
        "data": [v.to_dict() for v in core.verifiers],
        "timestamp": datetime.now().isoformat()
    })

# ─── JUDGE ENDPOINT ──────────────────────────────────────────────────

@router.get("/judge")
async def get_judge_info():
    """Get judge information"""
    core = get_core()
    return JSONResponse({
        "status": "success",
        "data": core.judge.get_stats() if hasattr(core, 'judge') else {"status": "active"},
        "timestamp": datetime.now().isoformat()
    })

# ─── STATS ENDPOINT ──────────────────────────────────────────────────

@router.get("/stats")
async def get_stats():
    """Get system statistics"""
    core = get_core()
    return JSONResponse({
        "status": "success",
        "data": core.get_system_stats(),
        "timestamp": datetime.now().isoformat()
    })

# ─── COMPLIANCE ENDPOINT ──────────────────────────────────────────────

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

# ─── MARKET QUOTE ENDPOINT ──────────────────────────────────────────

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

# ─── NEWS ENDPOINT ──────────────────────────────────────────────────

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

# ─── API INFO ENDPOINT ──────────────────────────────────────────────

@router.get("/info")
async def get_api_info():
    """Get comprehensive API information"""
    core = get_core()
    return {
        "name": "Unknown Verdict v40.0",
        "version": "40.0",
        "firm": "THE ADVOCACY – Global Law Firm",
        "description": "Complete AGI Legal Platform with 250+ Agents",
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "system": {
            "agents": {
                "total": len(core.agents),
                "active": sum(1 for a in core.agents if a["status"] == "active")
            },
            "verifiers": {
                "total": len(core.verifiers),
                "active": sum(1 for v in core.verifiers if v.status == "active")
            },
            "judge": core.judge.get_stats() if hasattr(core, 'judge') else {"status": "active"}
        },
        "endpoints": {
            "GET /api/": "API root",
            "GET /api/health": "Health check",
            "POST /api/chat": "Chat with AI agents",
            "POST /api/chat/stream": "Streaming chat",
            "GET /api/agents": "List all agents",
            "GET /api/verifiers": "List all verifiers",
            "GET /api/judge": "Judge information",
            "GET /api/stats": "System statistics",
            "POST /api/compliance": "Check compliance",
            "POST /api/market/quote": "Get market quote",
            "GET /api/news": "Get news",
            "GET /api/info": "This information"
        },
        "docs": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "trident": "🔱 PERMANENT ASSET - NEVER REMOVE",
        "branding": "⚖️ THE ADVOCACY – Global Law Firm"
    }

# ─── DOCS STATUS ENDPOINT ──────────────────────────────────────────

@router.get("/docs/status")
async def docs_status():
    """API documentation status"""
    return {
        "status": "available",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
        "api_base": "/api"
    }

# ─── FALLBACK FOR 404 ──────────────────────────────────────────────

@router.get("/{path:path}")
async def catch_all(path: str):
    """Catch all undefined routes with helpful message"""
    return JSONResponse(
        status_code=404,
        content={
            "status": "error",
            "detail": f"Endpoint '/api/{path}' not found",
            "available_endpoints": [
                "/api/",
                "/api/health",
                "/api/chat",
                "/api/chat/stream",
                "/api/agents",
                "/api/verifiers",
                "/api/judge",
                "/api/stats",
                "/api/compliance",
                "/api/market/quote",
                "/api/news",
                "/api/info",
                "/api/docs/status"
            ],
            "docs": "/docs",
            "redoc": "/redoc",
            "suggestion": "Visit /docs for interactive API documentation"
        }
    ) 
# Add document intelligence routes
from document_extractor import DocumentExtractor
from policies import validate_credit_agreement
from fastapi import UploadFile, File, Form

@router.post("/document/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a legal document for extraction."""
    # Save file temporarily
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    # Extract using LlamaIndex
    extractor = DocumentExtractor()
    result = await extractor.extract_from_files([{"path": tmp_path, "filename": file.filename}])
    os.unlink(tmp_path)
    return {"status": "success", "extracted": result}

@router.post("/document/analyze")
async def analyze_document(data: Dict):
    """Run AGI analysis on extracted document data."""
    # Validate business rules
    if "credit_agreement" in data:
        validation = validate_credit_agreement(data["credit_agreement"])
        data["validation"] = validation
    # Now run the agents on the document content
    core = get_core()
    query = "Analyze this legal document: " + json.dumps(data)
    result = await core.analyze_legal_case(query=query, files=[data])
    return {"status": "success", "analysis": result}
# ─── API INFO ENDPOINT ──────────────────────────────────────────────

@router.get("/info")
async def get_api_info():
    """Get comprehensive API information"""
    core = get_core()
    return {
        "name": "Unknown Verdict v40.0",
        "version": "40.0",
        "firm": "THE ADVOCACY – Global Law Firm",
        "description": "Complete AGI Legal Platform with 250+ Agents",
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "system": {
            "agents": {
                "total": len(core.agents),
                "active": sum(1 for a in core.agents if a["status"] == "active")
            },
            "verifiers": {
                "total": len(core.verifiers),
                "active": sum(1 for v in core.verifiers if v.status == "active")
            },
            "judge": core.judge.get_stats() if hasattr(core, 'judge') else {"status": "active"}
        },
        "endpoints": {
            "GET /api/": "API root",
            "GET /api/health": "Health check",
            "POST /api/chat": "Chat with AI agents",
            "GET /api/agents": "List all agents",
            "GET /api/verifiers": "List all verifiers",
            "GET /api/judge": "Judge information",
            "GET /api/stats": "System statistics",
            "POST /api/compliance": "Check compliance",
            "POST /api/market/quote": "Get market quote",
            "GET /api/news": "Get news",
            "GET /api/info": "This information"
        },
        "docs": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "trident": "🔱 PERMANENT ASSET - NEVER REMOVE",
        "branding": "⚖️ THE ADVOCACY – Global Law Firm"
    }