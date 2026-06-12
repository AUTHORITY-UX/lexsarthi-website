import os
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from llama_index.llms.groq import Groq

# --------------------------------------------------------------
# Configuration & Lifespan
# --------------------------------------------------------------
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY environment variable not set")

# Using a known active model
ACTIVE_GROQ_MODEL = "llama-3.3-70b-versatile"

try:
    llm = Groq(model=ACTIVE_GROQ_MODEL, api_key=GROQ_API_KEY, temperature=0.1)
except Exception as e:
    raise RuntimeError(f"Failed to initialize Groq model '{ACTIVE_GROQ_MODEL}': {e}")

full_text = ""

def load_document_text():
    global full_text
    legal_docs_path = Path("legal_docs")
    if not legal_docs_path.exists():
        raise RuntimeError("'legal_docs' folder not found")

    for file_path in legal_docs_path.glob("*"):
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
            with open(file_path, 'r', encoding='utf-8') as f:
                full_text = f.read()
            if full_text.strip():
                print(f"Loaded TXT {file_path.name}: {len(full_text)} chars")
                return

    raise RuntimeError("No readable document found in 'legal_docs/'")

def split_text(text: str, chunk_size: int = 6000):
    """Splits text into chunks of roughly 'chunk_size' characters."""
    words = text.split()
    chunks = []
    current_chunk = []
    current_len = 0
    for word in words:
        if current_len + len(word) + 1 <= chunk_size:
            current_chunk.append(word)
            current_len += len(word) + 1
        else:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_len = len(word) + 1
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

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

# --------------------------------------------------------------
# API Endpoints
# --------------------------------------------------------------
@app.get("/query")
async def query_endpoint(q: str = Query(...)):
    if not full_text:
        raise HTTPException(status_code=503, detail="Document not loaded")

    # Split the document into chunks
    chunks = split_text(full_text)
    best_answer = None
    best_score = -1

    # Iterate through chunks and query the model for each
    for idx, chunk in enumerate(chunks):
        prompt = f"""
You are a legal assistant. Based **only** on the following context, answer the question.
If the answer cannot be found in the context, state "I cannot find the answer in the provided document."

Context:
{chunk}

Question: {q}
Answer:
"""
        try:
            response = llm.complete(prompt)
            # Check if the model found an answer (simple heuristic)
            if "cannot find the answer" not in response.text.lower():
                # Return the first chunk that provides a meaningful answer
                return {"question": q, "answer": response.text}
        except Exception as e:
            print(f"Error processing chunk {idx}: {e}")

    # If no answer found in any chunk
    return {"question": q, "answer": "No relevant answer could be found in the document."}


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
    return {
        "filename": file.filename,
        "analysis": response.text,
    }
