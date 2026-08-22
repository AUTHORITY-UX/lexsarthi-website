from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from core.db import db
from core.llm.router import get_router
from core.auth import check_rate_limit
from routes import router

import logging

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS = {"/", "/health", "/version", "/docs", "/openapi.json", "/redoc", "/favicon.ico", "/static", "/app"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.EXEMPT_PATHS):
            return await call_next(request)
        try:
            await check_rate_limit(request)
        except Exception:
            pass
        response = await call_next(request)
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("   Environment: %s", settings.ENVIRONMENT)
    logger.info("   LLM providers: %s", settings.available_llm_providers)
    
    await db.connect()
    logger.info("   DB: %s", db.pool is not None)
    
    router_llm = get_router()
    await router_llm.init(redis_client=None)
    logger.info("   LLM router initialized")
    
    logger.info("✅ %s v%s ready — 68 endpoints active", settings.APP_NAME, settings.APP_VERSION)
    
    yield
    
    logger.info("🛑 Shutting down %s", settings.APP_NAME)
    await db.disconnect()
    logger.info("✅ Shutdown complete")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="500 Agents · 50+ Services · Zero Data Retention · Third Eye AI",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.add_middleware(RateLimitMiddleware)

app.include_router(router)

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Unknown Verdict v43.0</h1><p>See <a href='/docs'>/docs</a></p>")

@app.get("/app", response_class=HTMLResponse)
async def frontend():
    app_file = STATIC_DIR / "app.html"
    if app_file.exists():
        return HTMLResponse(app_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Unknown Verdict App</h1>")

@app.get("/brain", response_class=HTMLResponse)
async def brain():
    brain_file = STATIC_DIR / "brain.html"
    if brain_file.exists():
        return HTMLResponse(brain_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>🧠 Brain Dashboard</h1>")

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404,
                        content={"error": "Not Found", "path": request.url.path,
                                 "available_endpoints": "/docs"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=7860, workers=1,
                log_level=settings.LOG_LEVEL.lower())