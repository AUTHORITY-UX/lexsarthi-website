   import os
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from rank_bm25 import BM25Okapi
from llama_index.llms.groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY environment variable not set")

llm = Groq(
    model="mixtral-8x7b-32768",
    api_key=GROQ_API_KEY,
    temperature=0.1,
)

# Global BM25 index
bm25 = None
doc_texts = []  # list of (text, metadata)

def load_pdfs_from_dir(directory: str):
    docs = []
    path = Path(directory)
    if not path.exists():
        raise RuntimeError(f"Directory '{directory}' does not exist")
    for pdf_file in path.glob("*.pdf"):
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        if text.strip():
            docs.append((text, {"filename": pdf_file.name}))
    return docs

def build_bm25_index():
    global bm25, doc_texts
    doc_texts = load_pdfs_from_dir("legal_docs")
    if not doc_texts:
        raise RuntimeError("No PDF documents found in 'legal_docs/'")
    # Tokenize each document (simple whitespace split)
    tokenized_docs = [text.lower().split() for text, _ in doc_texts]
    bm25 = BM25Okapi(tokenized_docs)
    print(f"Indexed {len(doc_texts)} documents")

def retrieve(query: str, top_k=3):
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    # Get top_k indices
    indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    results = []
    for i in indices:
        if scores[i] > 0:
            results.append(doc_texts[i][0])
    return results

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading and indexing legal documents (BM25)...")
    build_bm25_index()
    print("Ready.")
    yield
    print("Shutting down.")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/query")
async def query_endpoint(q: str = Query(..., description="Question about legal documents")):
    if bm25 is None:
        raise HTTPException(status_code=503, detail="Index not ready")
    try:
        retrieved_chunks = retrieve(q)
        if not retrieved_chunks:
            return {"question": q, "answer": "No relevant documents found."}
        context = "\n\n---\n\n".join(retrieved_chunks)
        prompt = f"""You are a legal assistant. Use the following context from Indian legal documents to answer the question. If the answer is not in the context, say so.

Context:
{context}

Question: {q}
Answer:"""
        response = llm.complete(prompt)
        return {"question": q, "answer": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.post("/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        reader = PdfReader(tmp_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        if not text.strip():
            raise HTTPException(status_code=422, detail="No text extracted from PDF")

        risk_prompt = f"""You are a legal risk analyst. Analyse the provided contract document.

Contract text (excerpt):
{text[:3000]}

List all potential risks, unclear clauses, missing protections, and unusual obligations. Format as bullet points. If no significant risks, state that clearly."""
        response = llm.complete(risk_prompt)
        return {
            "filename": file.filename,
            "analysis": response.text,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)