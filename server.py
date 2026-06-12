import os
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from llama_index.llms.groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY environment variable not set")

llm = Groq(
    model="mixtral-8x7b-32768",
    api_key=GROQ_API_KEY,
    temperature=0.1,
)

# Store full document text
full_text = ""

def load_document_text():
    global full_text
    path = Path("legal_docs")
    if not path.exists():
        raise RuntimeError("'legal_docs' folder not found")
    for file_path in path.glob("*"):
        if file_path.suffix.lower() == ".pdf":
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            if text.strip():
                full_text = text
                print(f"Loaded PDF {file_path.name}: {len(full_text)} chars")
                return
        elif file_path.suffix.lower() == ".txt":
            full_text = file_path.read_text(encoding="utf-8")
            if full_text.strip():
                print(f"Loaded TXT {file_path.name}: {len(full_text)} chars")
                return
    raise RuntimeError("No readable document found in 'legal_docs/'")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading document...")
    load_document_text()
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
    if not full_text:
        raise HTTPException(status_code=503, detail="Document not loaded")
    prompt = f"""You are a legal assistant. Use the following document to answer the question. If the answer is not in the document, say so.

Document:
{full_text}

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
    else:
        text = content.decode("utf-8")
    if not text.strip():
        raise HTTPException(status_code=422, detail="No extractable text")
    risk_prompt = f"""You are a legal risk analyst. Analyse the provided contract text:

{text[:3000]}

List risks, unclear clauses, missing protections, unusual obligations as bullet points."""
    response = llm.complete(risk_prompt)
    return {"filename": file.filename, "analysis": response.text}