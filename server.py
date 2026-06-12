import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# ---------- LLM (Groq) ----------
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not set")
Settings.llm = OpenAILike(
    model="llama-3.3-70b-versatile",   # updated to current model
    api_key=api_key,
    api_base="https://api.groq.com/openai/v1",
    is_chat_model=True,
    temperature=0.1,
)

# ---------- Tiny, fast embedding model (no heavy torch deps) ----------
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

# ---------- Load legal documents ----------
index = None
if os.path.exists("legal_docs") and any(os.scandir("legal_docs")):
    documents = SimpleDirectoryReader("legal_docs").load_data()
    index = VectorStoreIndex.from_documents(documents)
    print(f"Loaded {len(documents)} document chunks")
else:
    print("No PDFs found")

# ---------- Endpoints ----------
@app.get("/health")
async def health():
    return {"status": "ok", "docs_loaded": index is not None}

@app.get("/query")
async def query(q: str = Query(...)):
    if index is None:
        return {"query": q, "response": "No legal documents loaded."}
    response = index.as_query_engine().query(q)
    return {"query": q, "response": str(response)}

@app.post("/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    os.makedirs("temp_uploads", exist_ok=True)
    temp_path = f"temp_uploads/{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        docs = SimpleDirectoryReader(input_files=[temp_path]).load_data()
        temp_index = VectorStoreIndex.from_documents(docs)
        engine = temp_index.as_query_engine()
        prompt = "Analyze this contract under Indian law. Identify high-risk clauses (indemnity, liability, termination, DPDP Act, arbitration, stamp duty). Provide a structured report with risk level and suggested changes."
        report = engine.query(prompt)
        return {"filename": file.filename, "risk_report": str(report)}
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=7860)