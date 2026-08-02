from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

app = FastAPI(title="Unknown Verdict v40.0", description="AI-Powered Legal Platform", version="40.0")

static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

try:
    from routes import router
    app.include_router(router, prefix="/api")
    print("✅ Routes imported")
except ImportError as e:
    print(f"⚠️ Routes not found: {e}")

try:
    from unknown_verdict.moat import install_moat
    install_moat(app)
    print("✅ Moat v41 installed")
except ImportError as e:
    print(f"⚠️ Moat not found: {e}")

@app.get("/")
async def root():
    try:
        with open(Path(__file__).parent.parent / "static" / "index.html", "r") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>⚖️ LEX v40.0</h1><p>Welcome to Unknown Verdict</p>")

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "40.0", "components": {"app": "running"}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 7860)))
