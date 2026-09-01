from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
import os

router = APIRouter(tags=["Documentation"])
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@router.get("/api-docs", include_in_schema=False)
async def api_docs():
    return FileResponse(os.path.join(BASE_DIR, "static", "api-docs.html"))

@router.get("/api-docs/pdf", include_in_schema=False)
async def api_docs_pdf():
    return FileResponse(os.path.join(BASE_DIR, "docs", "advocacy_ai_api_reference.pdf"), media_type="application/pdf", filename="advocacy_ai_api_reference.pdf")

@router.get("/api-docs/openapi", include_in_schema=False)
async def api_docs_openapi(request: Request):
    return request.app.openapi()
