# routes/routes.py

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import os
import json
from datetime import datetime

# Import your core components
from core import database, redis_pool
from agents import DIVINE_AGENTS, VERIFIERS
from agent_debate import AgentDebate
from knowledge_graph import LegalKnowledgeGraph
from document_generator import SmartDocumentGenerator
from analytics import AnalyticsDashboard
from multi_modal_processor import MultiModalProcessor

# Initialize components
agent_debate = AgentDebate()
knowledge_graph = LegalKnowledgeGraph()
document_generator = SmartDocumentGenerator()
analytics = AnalyticsDashboard()
multi_modal_processor = MultiModalProcessor()

# Pydantic models for request/response
class LegalQuery(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None

class DocumentProcessRequest(BaseModel):
    content: str
    document_type: str
    metadata: Optional[Dict[str, Any]] = None

class ContractRequest(BaseModel):
    contract_type: str
    parties: List[str]
    terms: Dict[str, Any]
    jurisdiction: Optional[str] = None

class AnalysisRequest(BaseModel):
    case_data: Dict[str, Any]
    analysis_type: str = "comprehensive"

def register_routes(app: FastAPI):
    """Register all routes with the FastAPI app"""
    
    # ===== HEALTH =====
    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        }
    
    # ===== STATUS =====
    @app.get("/status")
    async def system_status():
        return {
            "status": "operational",
            "version": "AGI v1.0",
            "agents": len(DIVINE_AGENTS),
            "verifiers": len(VERIFIERS),
            "judge": "Shakti",
            "knowledge_chunks": 1047,
            "database": "connected" if database else "disconnected",
            "redis": "connected" if redis_pool else "disabled"
        }
    
    # ===== DOCUMENT PROCESSING =====
    @app.post("/documents/process")
    async def process_document(
        file: UploadFile = File(...),
        document_type: Optional[str] = Query(None)
    ):
        try:
            # Read file content
            content = await file.read()
            
            # Process with multi-modal processor if needed
            if document_type in ["pdf", "image", "audio"]:
                result = await multi_modal_processor.process(content, file.content_type)
            else:
                # Text processing
                result = {
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "size": len(content),
                    "processed": True,
                    "timestamp": datetime.now().isoformat()
                }
            
            return JSONResponse(content=result, status_code=200)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # ===== LEGAL QUERY =====
    @app.post("/query")
    async def legal_query(request: LegalQuery):
        try:
            # Use knowledge graph and agent debate for comprehensive response
            knowledge_results = await knowledge_graph.search(request.query)
            
            # Trigger agent debate for complex queries
            if len(knowledge_results.get("results", [])) > 0:
                debate_result = await agent_debate.conduct_debate(
                    query=request.query,
                    context=request.context,
                    knowledge=knowledge_results
                )
            else:
                debate_result = {"debate": "No relevant knowledge found"}
            
            return {
                "query": request.query,
                "knowledge": knowledge_results,
                "debate": debate_result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # ===== KNOWLEDGE SEARCH =====
    @app.get("/knowledge/search")
    async def search_knowledge(
        query: str = Query(..., description="Search query"),
        limit: int = Query(10, ge=1, le=100)
    ):
        try:
            results = await knowledge_graph.search(query, limit=limit)
            return {
                "query": query,
                "results": results,
                "count": len(results.get("results", [])),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # ===== CONTRACT GENERATION =====
    @app.post("/contracts/generate")
    async def generate_contract(request: ContractRequest):
        try:
            contract = await document_generator.generate_contract(
                contract_type=request.contract_type,
                parties=request.parties,
                terms=request.terms,
                jurisdiction=request.jurisdiction
            )
            
            return {
                "contract_id": f"CTR-{datetime.now().strftime('%Y%m%d')}-{hash(str(request))}",
                "contract": contract,
                "type": request.contract_type,
                "generated_at": datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # ===== LEGAL ANALYSIS =====
    @app.post("/analyze")
    async def analyze_case(request: AnalysisRequest):
        try:
            # Perform multi-modal analysis
            analysis = await multi_modal_processor.analyze(
                data=request.case_data,
                analysis_type=request.analysis_type
            )
            
            # Add knowledge graph insights
            insights = await knowledge_graph.get_case_insights(
                request.case_data
            )
            
            return {
                "analysis": analysis,
                "insights": insights,
                "analysis_type": request.analysis_type,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # ===== AGENT MANAGEMENT =====
    @app.get("/agents")
    async def list_agents():
        return {
            "agents": [
                {
                    "name": agent.name,
                    "type": agent.__class__.__name__,
                    "status": "active"
                }
                for agent in DIVINE_AGENTS
            ],
            "count": len(DIVINE_AGENTS)
        }
    
    @app.get("/agents/{agent_name}/status")
    async def agent_status(agent_name: str):
        for agent in DIVINE_AGENTS:
            if agent.name == agent_name:
                return {
                    "name": agent_name,
                    "status": "active",
                    "verifiers": len(VERIFIERS),
                    "timestamp": datetime.now().isoformat()
                }
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
    
    # ===== ANALYTICS =====
    @app.get("/analytics/dashboard")
    async def get_analytics(
        timeframe: str = Query("day", regex="^(day|week|month|year)$")
    ):
        try:
            stats = await analytics.get_dashboard_stats(timeframe)
            return {
                "timeframe": timeframe,
                "stats": stats,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/analytics/usage")
    async def get_usage_metrics():
        try:
            metrics = await analytics.get_usage_metrics()
            return {
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # ===== DOCUMENT GENERATION =====
    @app.post("/documents/generate")
    async def generate_document(request: Dict[str, Any]):
        try:
            document = await document_generator.generate_document(request)
            return {
                "document": document,
                "generated_at": datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # ===== MULTI-MODAL PROCESSING =====
    @app.post("/multimodal/process")
    async def process_multimodal(
        files: List[UploadFile] = File(...),
        processing_type: str = Query("extract", regex="^(extract|analyze|summarize)$")
    ):
        try:
            results = []
            for file in files:
                content = await file.read()
                processed = await multi_modal_processor.process_multimodal(
                    content=content,
                    file_type=file.content_type,
                    processing_type=processing_type
                )
                results.append({
                    "filename": file.filename,
                    "result": processed
                })
            
            return {
                "processed": results,
                "count": len(results),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # ===== BATCH PROCESSING =====
    @app.post("/batch/process")
    async def batch_process(documents: List[Dict[str, Any]]):
        try:
            results = []
            for doc in documents:
                if doc.get("type") == "query":
                    result = await knowledge_graph.search(doc.get("content", ""))
                elif doc.get("type") == "document":
                    result = await document_generator.generate_document(doc)
                else:
                    result = {"error": "Unknown document type"}
                
                results.append({
                    "id": doc.get("id", len(results)),
                    "result": result
                })
            
            return {
                "processed": len(results),
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # ===== SYSTEM MANAGEMENT =====
    @app.post("/system/clear-cache")
    async def clear_cache():
        try:
            if redis_pool:
                await redis_pool.flushall()
            return {"status": "Cache cleared", "timestamp": datetime.now().isoformat()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/system/metrics")
    async def system_metrics():
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "database": "connected" if database else "disconnected",
                "redis": "connected" if redis_pool else "disabled",
                "agents_active": len(DIVINE_AGENTS),
                "verifiers_active": len(VERIFIERS)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

# If you want to test this file directly
if __name__ == "__main__":
    import uvicorn
    app = FastAPI()
    register_routes(app)
    uvicorn.run(app, host="0.0.0.0", port=8000)