import os
import shutil
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings
)
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai import OpenAIEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

# ---------- FastAPI app ----------
app = FastAPI(title="LexSarthi RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Global variables ----------
PERMANENT_INDEX: Optional[VectorStoreIndex] = None
QDRANT_PATH = "./qdrant_data"
COLLECTION_NAME = "lexsarthi_permanent"
DIMENSION = 1536

def configure_llm_and_embeddings():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    api_base = os.getenv("OPENAI_API_BASE", "https://api.groq.com/openai/v1")
    model = os.getenv("LLM_MODEL_NAME", "llama3-70b-8192")
    embed_model = os.getenv("EMBED_MODEL_NAME", "text-embedding-3-small")
    Settings.llm = OpenAILike(model=model, api_key=api_key, api_base=api_base, is_chat_model=True, temperature=0.1)
    Settings.embed_model = OpenAIEmbedding(api_key=api_key, api_base=api_base, model=embed_model)

@app.on_event("startup")
async def startup_event():
    global PERMANENT_INDEX
    configure_llm_and_embeddings()
    os.makedirs(QDRANT_PATH, exist_ok=True)

    client = QdrantClient(path=QDRANT_PATH)

    try:
        client.get_collection(COLLECTION_NAME)
        print("Existing Qdrant collection found.")
    except:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=DIMENSION, distance=Distance.COSINE)
        )
        print("Created new Qdrant collection.")

    vector_store = QdrantVectorStore(client=client, collection_name=COLLECTION_NAME)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    if client.count(COLLECTION_NAME).count == 0:
        if os.path.exists("legal_docs") and any(os.scandir("legal_docs")):
            documents = SimpleDirectoryReader("legal_docs").load_data()
            PERMANENT_INDEX = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
            print(f"Built new Qdrant index with {len(documents)} documents.")
        else:
            PERMANENT_INDEX = VectorStoreIndex.from_documents([], storage_context=storage_context)
            print("Warning: './legal_docs' is empty.")
    else:
        PERMANENT_INDEX = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
        print("Loaded existing Qdrant index.")

@app.get("/query")
async def query_index(q: str = Query(...)):
    if PERMANENT_INDEX is None:
        raise HTTPException(status_code=503, detail="Index not ready.")
    response = PERMANENT_INDEX.as_query_engine().query(q)
    return {"query": q, "response": str(response)}

@app.post("/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed.")
    os.makedirs("temp_uploads", exist_ok=True)
    temp_path = f"temp_uploads/{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        documents = SimpleDirectoryReader(input_files=[temp_path]).load_data()
        temp_client = QdrantClient(":memory:")
        temp_client.create_collection(
            collection_name="temp",
            vectors_config=VectorParams(size=DIMENSION, distance=Distance.COSINE)
        )
        temp_vector_store = QdrantVectorStore(client=temp_client, collection_name="temp")
        temp_storage_context = StorageContext.from_defaults(vector_store=temp_vector_store)
        temp_index = VectorStoreIndex.from_documents(documents, storage_context=temp_storage_context)
        temp_engine = temp_index.as_query_engine()
        prompt = "Analyze this contract under Indian law. Identify high-risk clauses (indemnity, liability, termination, DPDP Act, arbitration, stamp duty). Provide a structured report with risk level and suggested changes."
        report = temp_engine.query(prompt)
        return {"filename": file.filename, "risk_report": str(report)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ---------- Entry point ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=7860)