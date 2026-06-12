import os
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

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

bm25 = None
doc_texts = []
debug_info = ""

def load_documents_from_dir(directory: str):
    global debug_info
    docs = []
    path = Path(directory)
    if not path.exists():
        raise RuntimeError(f"Directory '{directory}' does not exist")
    for file_path in path.glob("*"):
        if file_path.suffix.lower() == ".pdf":
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            if text.strip():
                docs.append((text, {"filename": file_path.name}))
                debug_info = f"Loaded PDF '{file_path.name}': {len(text)} chars. First 200 chars:\n{text[:200]}"
            else:
                debug_info = f"WARNING: PDF '{file_path.name}' has no extractable text (scanned?)"
        elif file_path.suffix.lower() == ".txt":
            text = file_path.read_text(encoding="utf-8")
            if text.strip():
                docs.append((text, {"filename": file_path.name}))
                debug_info = f"Loaded TXT '{file_path.name}': {len(text)} chars. First 200 chars:\n{text[:200]}"
            else:
                debug_info = f"WARNING: TXT '{file_path.name}' is empty"
    return docs

def build_bm25_index():
    global bm25, doc_texts
    doc_texts = load_documents_from_dir("legal_docs")
    if not doc_texts:
        raise RuntimeError("No documents found in 'legal_docs/' (support .pdf, .txt)")
    tokenized_docs = [text.lower().split() for text, _ in doc_texts]
    bm25 = BM25Okapi(tokenized_docs)
    print(f"Indexed {len(doc_texts)} documents")
    print(debug_info)

def retrieve(query: str, top_k=1):
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    results = []
    for i in indices:
        if scores[i] > 0:
            results.append(doc_texts[i][0])
    return results, tokenized_query, scores

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading and indexing documents...")
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
async def query_endpoint(q: str = Query(...)):
    if bm25 is None:
        raise HTTPException(status_code=503, detail="Index not ready")
    retrieved_chunks, tokens, scores = retrieve(q)
    if not retrieved_chunks:
        # Show debug info in the answer
        return {
            "question": q,
            "answer": f"No relevant documents found.\n\nQuery tokens: {tokens}\n\nDocument preview (first 200 chars):\n{debug_info}"
        }
    context = "\n\n---\n\n".join(retrieved_chunks)
    prompt = f"""You are a legal assistant. Use the following context to answer the question. If the answer is not in the context, say so.

Context:
{context}

Question: {q}
Answer:"""
    response = llm.complete(prompt)
    return {"question": q, "answer": response.text}

@app.post("/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Only PDF or TXT files accepted")
    content = await file.read()
    text = ""
    if file.filename.endswith(".pdf"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            reader = PdfReader(tmp_path)
            for page in reader.pages:
                text += page.extract_text() or ""
        finally:
            os.unlink(tmp_path)
    else:  # .txt
        text = content.decode("utf-8")
    if not text.strip():
        raise HTTPException(status_code=422, detail="No extractable text")
    risk_prompt = f"""You are a legal risk analyst. Analyse the provided contract text:

{text[:3000]}

List risks, unclear clauses, missing protections, unusual obligations as bullet points."""
    response = llm.complete(risk_prompt)
    return {"filename": file.filename, "analysis": response.text}