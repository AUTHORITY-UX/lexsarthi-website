import os
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from llama_index.llms.groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY missing")

llm = Groq(
    model="llama3-70b-8192",   # active model (change if needed)
    api_key=GROQ_API_KEY,
    temperature=0.1,
)

full_text = ""

def load_document():
    global full_text
    path = Path("legal_docs")
    if not path.exists():
        raise RuntimeError("'legal_docs' folder not found")
    for file in path.glob("*"):
        if file.suffix.lower() == ".pdf":
            reader = PdfReader(file)
            text = "".join(page.extract_text() or "" for page in reader.pages)
            if text.strip():
                full_text = text
                print(f"Loaded PDF {file.name}: {len(full_text)} chars")
                return
        elif file.suffix.lower() == ".txt":
            full_text = file.read_text(encoding="utf-8")
            if full_text.strip():
                print(f"Loaded TXT {file.name}: {len(full_text)} chars")
                return
    raise RuntimeError("No readable document found")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading document...")
    load_document()
    print("Ready.")
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# HTML form at root
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LexSarthi – Legal AI Assistant</title>
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            input, button { padding: 10px; font-size: 16px; }
            input { width: 70%; }
            button { width: 20%; }
            #answer { margin-top: 20px; padding: 15px; background: #f5f5f5; border-radius: 5px; white-space: pre-wrap; }
        </style>
    </head>
    <body>
        <h1>LexSarthi – Legal AI Assistant</h1>
        <form onsubmit="ask(event)">
            <input type="text" id="question" placeholder="Ask a question about the legal document" size="60">
            <button type="submit">Ask</button>
        </form>
        <div id="answer"></div>
        <script>
            async function ask(event) {
                event.preventDefault();
                const q = document.getElementById('question').value;
                const answerDiv = document.getElementById('answer');
                answerDiv.innerHTML = "Thinking...";
                try {
                    const response = await fetch(`/query?q=${encodeURIComponent(q)}`);
                    const data = await response.json();
                    answerDiv.innerHTML = data.answer || "No answer";
                } catch (err) {
                    answerDiv.innerHTML = "Error: " + err;
                }
            }
        </script>
    </body>
    </html>
    """

@app.get("/query")
async def query_endpoint(q: str = Query(...)):
    if not full_text:
        raise HTTPException(status_code=503, detail="Document not loaded")
    # Truncate to 8000 chars to avoid token limits
    context = full_text[:8000]
    prompt = f"""You are a legal assistant. Use the following document to answer the question. If the answer is not in the document, say so.

Document:
{context}

Question: {q}
Answer:"""
    response = llm.complete(prompt)
    return {"question": q, "answer": response.text}

@app.post("/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".txt")):
        raise HTTPException(400, "Only PDF or TXT")
    content = await file.read()
    text = ""
    if file.filename.endswith(".pdf"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            reader = PdfReader(tmp_path)
            text = "".join(page.extract_text() or "" for page in reader.pages)
        finally:
            os.unlink(tmp_path)
    else:
        text = content.decode("utf-8")
    if not text.strip():
        raise HTTPException(422, "No extractable text")
    prompt = f"You are a legal risk analyst. Analyse this contract:\n\n{text[:3000]}\n\nList risks, unclear clauses, missing protections, unusual obligations as bullet points."
    response = llm.complete(prompt)
    return {"filename": file.filename, "analysis": response.text}