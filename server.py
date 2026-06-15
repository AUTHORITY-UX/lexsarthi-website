import os
import shutil
import time
import hmac
import hashlib
import asyncio
import zipfile
import io
import json
import smtplib
from email.message import EmailMessage
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Settings, Document
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_parse import LlamaParse
from pypdf import PdfReader
import razorpay

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# ---------- LLM (Groq – use Mixtral to avoid rate limit) ----------
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not set")
Settings.llm = OpenAILike(
    model="mixtral-8x7b-32768",          # changed from llama-3.3-70b-versatile
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

# ---------- Load permanent index ----------
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

# ---------- Query ----------
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

# ---------- Contract Risk Analysis (Fixed) ----------
@app.post("/analyze")
async def analyze_contract(
    file: UploadFile = File(...),
    lawyer_review: bool = Form(False)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    os.makedirs("temp_uploads", exist_ok=True)
    temp_path = f"temp_uploads/{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Parse PDF in a separate thread to avoid event loop issues
        def parse_pdf_sync(path):
            try:
                return parser.load_data(path)
            except Exception as e:
                raise e
        try:
            docs = await asyncio.to_thread(parse_pdf_sync, temp_path)
            if not docs:
                raise ValueError("LlamaParse returned empty documents")
            print(f"✅ Parsed {len(docs)} chunks via LlamaParse")
        except Exception as parse_err:
            print(f"⚠️ LlamaParse failed: {parse_err}. Falling back to PyPDF2.")
            # PyPDF2 is synchronous – run in thread
            def extract_pdf_sync(path):
                reader = PdfReader(path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                return text
            text = await asyncio.to_thread(extract_pdf_sync, temp_path)
            if not text.strip():
                return {"filename": file.filename, "risk_report": {"error": "Could not extract text."}}
            docs = [Document(text=text)]
            print("✅ Extracted text via PyPDF2 fallback")

        # Build index with larger chunk size
        from llama_index.core.node_parser import SentenceSplitter
        splitter = SentenceSplitter(chunk_size=2048, chunk_overlap=256)
        temp_index = VectorStoreIndex.from_documents(docs, transformations=[splitter])
        engine = temp_index.as_query_engine()

        # Polished corporate lawyer prompt
        prompt = """
You are a senior corporate lawyer with 40 years of experience in Indian contract law, M&A, and dispute resolution. Your task is to produce a **court‑ready, client‑facing risk report** that would be delivered by a top‑tier law firm.

### Instructions (strict):
1. Identify the contract type and governing law.
2. Assign overall risk (High/Medium/Low) with a one‑sentence justification.
3. For each problematic clause (or missing essential clause):
   - **Clause name** (exact reference)
   - **Risk level** (High/Medium/Low)
   - **Legal reasoning** – cite specific sections of the **Indian Contract Act, 1872**, **DPDP Act, 2023**, **IBC**, **Arbitration Act**, etc. Use exact wording like “Section 27 of the Indian Contract Act, 1872 voids any agreement in restraint of trade unless it falls within a statutory exception.”
   - **Suggested change** – provide the **exact redlined wording** (e.g., “Delete the words ‘any customer’ and replace with ‘customers with whom the party has had a material relationship in the preceding 12 months’”).
4. **Missing critical clauses** – flag them as high risk and propose the exact clause text (e.g., an entire limitation of liability clause).
5. **Executive summary** – no more than 3‑4 lines.

### Output format (JSON):
{
  "contract_type": "string",
  "overall_risk": "High/Medium/Low",
  "clause_analysis": [
    {
      "clause_name": "string",
      "risk_level": "High/Medium/Low",
      "reason": "string (with citations to specific sections of Indian statutes)",
      "suggested_change": "string (exact wording, as in a redline)"
    }
  ],
  "summary": "string"
}

### Contract text:
{context}
"""
        retriever = temp_index.as_retriever(similarity_top_k=10)
        nodes = retriever.retrieve(prompt)
        context = "\n\n---\n\n".join([n.node.text for n in nodes]) if nodes else ""
        if not context:
            return {"filename": file.filename, "risk_report": {"error": "Insufficient content."}}

        final_prompt = prompt.replace("{context}", context)
        response = Settings.llm.complete(final_prompt)
        raw = response.text if hasattr(response, 'text') else str(response)

        # Clean JSON
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        try:
            report = json.loads(raw)
            required = ["contract_type", "overall_risk", "clause_analysis", "summary"]
            if not all(k in report for k in required):
                raise ValueError("Missing required keys")
            if not isinstance(report["clause_analysis"], list):
                report["clause_analysis"] = []
        except Exception as e:
            return {"filename": file.filename, "risk_report": {"error": "JSON parse failed", "raw": raw, "parse_error": str(e)}}

        if lawyer_review:
            print(f"📞 LAWYER REVIEW REQUESTED for contract: {file.filename}")
            # Optional: add email code here

        return {"filename": file.filename, "risk_report": report}

    except Exception as e:
        print(f"❌ Analysis error: {str(e)}")
        raise HTTPException(500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ---------- Razorpay order creation ----------
@app.post("/api/create-order")
async def create_order(amount: int = 500):
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

# ---------- Other agents (DPDP check, legal notice, etc.) ----------
# ... (keep your existing agent endpoints here – they are unchanged)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=7860)