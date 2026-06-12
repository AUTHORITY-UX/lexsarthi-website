    import os
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader

from llama_index.core import (
    Document,
    VectorStoreIndex,
    Settings,
)
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface_api import HuggingFaceInferenceAPIEmbedding
from llama_index.core.node_parser import SimpleNodeParser

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")   # Get free token from huggingface.co/settings/tokens

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY environment variable not set")
if not HF_API_TOKEN:
    raise RuntimeError("HF_API_TOKEN environment variable not set")

Settings.llm = Groq(
    model="mixtral-8x7b-32768",
    api_key=GROQ_API_KEY,
    temperature=0.1,
)

# Free Hugging Face embedding model
Settings.embed_model = HuggingFaceInferenceAPIEmbedding(
    model_name="BAAI/bge-small-en-v1.5",
    api_key=HF_API_TOKEN,
)

# ----------------------------------------------------------------------
# Helper: load PDFs from directory
# ----------------------------------------------------------------------
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
            docs.append(Document(text=text, metadata={"filename": pdf_file.name}))
        else:
            print(f"Warning: No text extracted from {pdf_file.name}")
    return docs

# ----------------------------------------------------------------------
# Global index
# ----------------------------------------------------------------------
index = None

def build_index_from_directory():
    global index
    docs = load_pdfs_from_dir("legal_docs")
    if not docs:
        raise RuntimeError("No PDF documents found in 'legal_docs/'")
    parser = SimpleNodeParser.from_defaults()
    nodes = parser.get_nodes_from_documents(docs)
    index = VectorStoreIndex(nodes)
    print(f"Indexed {len(nodes)} nodes from {len(docs)} documents")

# ----------------------------------------------------------------------
# Lifespan
# ----------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading and indexing legal documents...")
    build_index_from_directory()
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

# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------
@app.get("/query")
async def query_endpoint(q: str = Query(..., description="Question about legal documents")):
    if index is None:
        raise HTTPException(status_code=503, detail="Index not ready")
    try:
        query_engine = index.as_query_engine()
        response = query_engine.query(q)
        return {"question": q, "answer": str(response)}
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

        doc = Document(text=text, metadata={"filename": file.filename})
        parser = SimpleNodeParser.from_defaults()
        nodes = parser.get_nodes_from_documents([doc])
        temp_index = VectorStoreIndex(nodes)

        risk_prompt = (
            "You are a legal risk analyst. Analyse the provided contract document. "
            "List all potential risks, unclear clauses, missing protections, and unusual obligations. "
            "Format the output as a bullet list with headings for each risk category. "
            "If there are no significant risks, state that clearly."
        )
        query_engine = temp_index.as_query_engine()
        response = query_engine.query(risk_prompt)

        return {
            "filename": file.filename,
            "analysis": str(response),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)