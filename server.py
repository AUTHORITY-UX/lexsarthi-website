import os
import shutil
import time
import hmac
import hashlib
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Settings, Document
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_parse import LlamaParse
from pypdf import PdfReader
import razorpay

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# ---------- LLM (Groq) ----------
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not set")
Settings.llm = OpenAILike(
    model="llama-3.3-70b-versatile",
    api_key=api_key,
    api_base="https://api.groq.com/openai/v1",
    is_chat_model=True,
    temperature=0.1,
)

# ---------- Embeddings ----------
Settings.embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

# ---------- LlamaParse parser ----------
parser = LlamaParse(
    api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
    result_type="markdown",
    verbose=True,
)

# ---------- Razorpay client ----------
razorpay_key_id = os.getenv("RAZORPAY_KEY_ID")
razorpay_key_secret = os.getenv("RAZORPAY_KEY_SECRET")
razorpay_webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

if not razorpay_key_id or not razorpay_key_secret:
    print("Warning: Razorpay keys not set – /create-order will not work")
else:
    razorpay_client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))

# ---------- Load legal documents (DPDP Act, etc.) ----------
index = None
if os.path.exists("legal_docs") and any(os.scandir("legal_docs")):
    documents = []
    for file in os.listdir("legal_docs"):
        if file.lower().endswith(".pdf"):
            file_path = os.path.join("legal_docs", file)
            docs = parser.load_data(file_path)
            documents.extend(docs)
    if documents:
        index = VectorStoreIndex.from_documents(documents)
        print(f"Loaded {len(documents)} document chunks")
    else:
        print("No valid PDFs found in legal_docs/")
else:
    print("No PDFs found in legal_docs/")

# ---------- Health ----------
@app.get("/health")
async def health():
    return {"status": "ok", "docs_loaded": index is not None}

# ---------- Query permanent index ----------
@app.get("/query")
async def query(q: str = Query(...)):
    if index is None:
        return {"query": q, "response": "No legal documents loaded."}
    try:
        response = index.as_query_engine().query(q)
        answer = response.response if hasattr(response, 'response') else str(response)
        return {"query": q, "response": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Contract risk analysis (payment protected) ----------
@app.post("/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    os.makedirs("temp_uploads", exist_ok=True)
    temp_path = f"temp_uploads/{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Parse PDF (async safe)
        try:
            docs = await asyncio.to_thread(parser.load_data, temp_path)
            if not docs:
                raise ValueError("LlamaParse returned empty documents")
            print(f"✅ Parsed {len(docs)} chunks via LlamaParse")
        except Exception as parse_err:
            print(f"⚠️ LlamaParse failed: {parse_err}. Falling back to PyPDF2.")
            reader = PdfReader(temp_path)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
            if not text.strip():
                return {"filename": file.filename, "risk_report": "Could not extract text from PDF. Please ensure it is a text‑based PDF."}
            docs = [Document(text=text)]
            print("✅ Extracted text via PyPDF2 fallback")

        temp_index = VectorStoreIndex.from_documents(docs)
        engine = temp_index.as_query_engine()

        prompt = (
            "Analyze this contract under Indian law. "
            "Identify high‑risk clauses such as indemnity, liability, termination, DPDP Act compliance, arbitration, and stamp duty. "
            "If you cannot find any such clauses, state that clearly and provide a summary of the document. "
            "Return a structured report with risk level (High/Medium/Low) and suggested changes."
        )
        response = engine.query(prompt)
        answer = response.response if hasattr(response, 'response') else str(response)
        if not answer or answer.strip() == "":
            answer = "The AI could not generate a risk report. Please try a different PDF or contact support."

        return {"filename": file.filename, "risk_report": answer}

    except Exception as e:
        print(f"❌ Analysis error: {str(e)}")
        raise HTTPException(500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ---------- Razorpay order creation ----------
@app.post("/api/create-order")
async def create_order(amount: int = 2):
    if not razorpay_key_id or not razorpay_key_secret:
        raise HTTPException(500, detail="Razorpay not configured")
    try:
        order_data = {
            "amount": amount * 100,
            "currency": "INR",
            "payment_capture": 1,
            "receipt": f"order_rcpt_{int(time.time())}"
        }
        order = razorpay_client.order.create(data=order_data)
        return {"order_id": order["id"], "amount": amount, "currency": "INR"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Payment verification ----------
@app.post("/api/verify-payment")
async def verify_payment(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    if not razorpay_webhook_secret:
        raise HTTPException(500, detail="Webhook secret not set")
    expected = hmac.new(
        razorpay_webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    return {"status": "success"}
@app.post("/dpdp-check")
async def dpdp_check(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    os.makedirs("temp_uploads", exist_ok=True)
    temp_path = f"temp_uploads/{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        # Parse PDF (async safe)
        docs = await asyncio.to_thread(parser.load_data, temp_path)
        if not docs:
            reader = PdfReader(temp_path)
            text = "".join(page.extract_text() or "" for page in reader.pages)
            docs = [Document(text=text)]
        temp_index = VectorStoreIndex.from_documents(docs)
        engine = temp_index.as_query_engine()
        prompt = (
            "You are a DPDP Act compliance auditor. Analyze the given document against the Digital Personal Data Protection Act 2023. "
            "Return a JSON with:\n"
            "- compliance_score: 0-100\n"
            "- missing_clauses: list of DPDP requirements not met (e.g., consent, data breach notification, data principal rights)\n"
            "- observations: brief remarks\n"
            "Do not include recommendations or suggested changes."
        )
        response = engine.query(prompt)
        return {"filename": file.filename, "report": response.response}
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
@app.post("/legal-notice")
async def legal_notice(request: Request):
    data = await request.json()
    parties = data.get("parties", [])
    facts = data.get("facts", "")
    law = data.get("applicable_law", "Indian Contract Act, 1872")
    prompt = f"""Generate a formal legal notice under {law}.
    Parties: {', '.join(parties) if parties else 'Not specified'}.
    Facts: {facts}
    Format as a legal notice with:
    - Subject line
    - Date
    - Recipient details (placeholders)
    - Body explaining breach/demand
    - Deadline for compliance
    - Signature block (placeholder)
    Do not include advice or commentary."""
    # Direct LLM call (no RAG needed, but can use index for templates)
    response = Settings.llm.complete(prompt)
    return {"notice": response.text}            os.remove(temp_path)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=7860)