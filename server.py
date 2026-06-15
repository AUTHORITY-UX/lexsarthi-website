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

# ---------- LLM (Groq) – using supported model ----------
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not set")
Settings.llm = OpenAILike(
    model="llama-3.3-70b-versatile",   # changed from mixtral
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

# ---------- Contract risk analysis (polished corporate lawyer) ----------
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

        # Parse PDF in thread to avoid event loop issues
        def parse_sync(path):
            return parser.load_data(path)
        try:
            docs = await asyncio.to_thread(parse_sync, temp_path)
            if not docs:
                raise ValueError("LlamaParse returned empty documents")
            print(f"✅ Parsed {len(docs)} chunks via LlamaParse")
        except Exception as parse_err:
            print(f"⚠️ LlamaParse failed: {parse_err}. Falling back to PyPDF2.")
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

        from llama_index.core.node_parser import SentenceSplitter
        splitter = SentenceSplitter(chunk_size=2048, chunk_overlap=256)
        temp_index = VectorStoreIndex.from_documents(docs, transformations=[splitter])
        engine = temp_index.as_query_engine()

        # Polished corporate lawyer prompt
        prompt = """
        prompt = """
You are a senior corporate lawyer with 40 years of experience. Analyse the attached contract **clause by clause** and produce a **risk register** in JSON format.

### Required output schema:
{
  "contract_type": "string",
  "overall_risk": "High/Medium/Low",
  "clause_analysis": [
    {
      "clause_number": "string (e.g., 'Clause 11')",
      "clause_title": "string (if any)",
      "risk_level": "High/Medium/Low",
      "legal_basis": "cite exact section of Indian statute (e.g., 'Section 27, Indian Contract Act, 1872')",
      "reason": "detailed explanation",
      "suggested_redline": "exact wording to replace the clause"
    }
  ],
  "missing_clauses": [
    {
      "clause_name": "string (e.g., 'Limitation of Liability')",
      "risk_level": "High",
      "proposed_text": "full clause text to insert"
    }
  ],
  "summary": "executive summary (max 3 lines)"
}

### Instructions:
- Analyse **every** clause that has legal significance (indemnity, liability, termination, non‑compete, non‑solicit, data protection, arbitration, governing law, force majeure, notice, etc.).
- For missing essential clauses, add them to `missing_clauses` with a **draft clause**.
- For the `suggested_redline`, provide **exact wording** as you would in a tracked‑changes document.
- Be brutal – flag even moderate risks.

### Contract text:
{context}
"""

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
        raw = raw.strip()
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
            # Optional: add email code here (use your SMTP settings)

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

# ========== Additional Agents ==========
@app.post("/dpdp-check")
async def dpdp_check(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    os.makedirs("temp_uploads", exist_ok=True)
    temp_path = f"temp_uploads/{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
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
            "- missing_clauses: list of DPDP requirements not met\n"
            "- observations: brief remarks"
        )
        response = engine.query(prompt)
        return {"filename": file.filename, "report": str(response)}
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

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
    response = Settings.llm.complete(prompt)
    return {"notice": response.text}

@app.post("/due-diligence")
async def due_diligence(zip_file: UploadFile = File(...)):
    contents = await zip_file.read()
    results = []
    with zipfile.ZipFile(io.BytesIO(contents)) as z:
        for name in z.namelist():
            if name.lower().endswith('.pdf'):
                results.append({"file": name, "risk": "pending review"})
    return {"results": results}

@app.post("/nda-triage")
async def nda_triage(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    os.makedirs("temp_uploads", exist_ok=True)
    temp_path = f"temp_uploads/{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        docs = await asyncio.to_thread(parser.load_data, temp_path)
        if not docs:
            reader = PdfReader(temp_path)
            text = "".join(page.extract_text() or "" for page in reader.pages)
            docs = [Document(text=text)]
        temp_index = VectorStoreIndex.from_documents(docs)
        engine = temp_index.as_query_engine()
        prompt = "Classify this NDA as green (low risk), amber (medium risk), or red (high risk) based on Indian contract law. Return only the word."
        response = engine.query(prompt)
        answer = response.response if hasattr(response, 'response') else str(response)
        return {"filename": file.filename, "risk_level": answer.strip()}
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/weekly-digest")
async def weekly_digest():
    if index is None:
        raise HTTPException(503, detail="Legal index not loaded. Please add PDFs to legal_docs/.")
    queries = [
        "What are the latest amendments to the DPDP Act in the past month?",
        "Recent changes in the Indian Contract Act, 1872",
        "Updates to the Insolvency and Bankruptcy Code (IBC)",
        "New rules or notifications under the Companies Act, 2013",
        "Recent judgments or regulatory changes affecting contract law in India"
    ]
    digest = []
    for q in queries:
        try:
            response = index.as_query_engine().query(q)
            answer = response.response if hasattr(response, 'response') else str(response)
            digest.append({"topic": q, "summary": answer})
        except Exception as e:
            digest.append({"topic": q, "error": str(e)})
    formatted = "# Weekly Regulatory Digest\n\n"
    for item in digest:
        formatted += f"## {item['topic']}\n"
        if "summary" in item:
            formatted += f"{item['summary']}\n\n"
        else:
            formatted += f"Error: {item['error']}\n\n"
    return {"digest": formatted}

@app.post("/consent-form")
async def consent_form(request: Request):
    data = await request.json()
    business_name = data.get("business_name", "Your Organization")
    purpose = data.get("purpose", "Service provision")
    data_types = data.get("data_types", ["name", "email", "phone"])
    retention_days = data.get("retention_days", 180)
    prompt = f"""
You are a legal document drafter. Generate a **Consent Form** under the Digital Personal Data Protection Act (DPDP Act), 2023 (India).  
The form must include:
- Header: "Consent Form – DPDP Act, 2023"
- Business name: {business_name}
- Purpose of data collection: {purpose}
- Types of personal data collected: {', '.join(data_types)}
- Retention period: {retention_days} days
- Data principal rights (access, correction, erasure, grievance)
- Withdrawal of consent notice
- Grievance redressal contact (placeholder)
- Signature line (date and name)

Format the output as clean HTML or plain text with clear headings.
"""
    response = Settings.llm.complete(prompt)
    form_html = response.text if hasattr(response, 'text') else str(response)
    return {"consent_form": form_html}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=7860)