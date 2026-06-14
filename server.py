import os
import shutil
import time
import hmac
import hashlib
import asyncio
import zipfile
import io
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
        return {"query": q, "response": "No legal documents loaded. Please upload PDFs to legal_docs/."}
    try:
        # Create a retriever with higher top_k
        retriever = index.as_retriever(similarity_top_k=10)
        nodes = retriever.retrieve(q)
        if not nodes:
            return {"query": q, "response": "No relevant information found in the indexed documents."}
        
        context = "\n\n---\n\n".join([n.node.text for n in nodes])
        sources = [f"Section from {n.node.metadata.get('source', 'unknown')}" for n in nodes]
        
        prompt = f"""You are a legal AI assistant for LexSarthi. Answer the user's query based **only** on the provided legal documents. 
If the answer is not in the documents, say "The documents do not contain this information."
Do not use general knowledge.

### Retrieved legal text:
{context}

### User query:
{q}

### Instructions:
- Be precise, cite specific sections or clauses when possible.
- If the query asks for a section number, return the exact wording from the documents.

Answer:"""
        
        response = Settings.llm.complete(prompt)
        answer = response.text if hasattr(response, 'text') else str(response)
        return {"query": q, "response": answer, "sources": sources}
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

        # Build temporary index (using increased chunk size if configured globally)
        temp_index = VectorStoreIndex.from_documents(docs)
        engine = temp_index.as_query_engine()

        # Structured prompt for contract analysis (MSA, Share Subscription, etc.)
        prompt = """
You are a legal risk analyst for LexSarthi, an AI‑native law firm. Analyze the given contract and produce a structured risk report in JSON format. Follow this schema exactly:

{
  "contract_type": "MSA / Share Subscription / NDA / etc. (infer from content)",
  "overall_risk": "High / Medium / Low",
  "clause_analysis": [
    {
      "clause_name": "e.g., Indemnity, Limitation of Liability, Termination, Confidentiality, Governing Law, etc.",
      "risk_level": "High / Medium / Low",
      "reason": "Why this clause is risky (reference specific wording from the contract).",
      "suggested_change": "Concrete, legally valid alternative wording under Indian law."
    }
  ],
  "summary": "Brief overall assessment and recommended next steps."
}

Instructions:
- Extract only clauses that are present and material.
- For MSAs: focus on indemnity, limitation of liability, termination, service levels (SLA), data protection (DPDP Act), dispute resolution (arbitration).
- For share subscription agreements: focus on representations & warranties, indemnity, closing conditions, drag‑along/tag‑along, anti‑dilution, governing law.
- Use the actual contract text to justify each risk.
- Provide actionable, precise suggested changes (model clauses) suitable for Indian law.
- If a standard clause is missing (e.g., no arbitration clause), flag as high risk and suggest addition.

Contract text:
{context}
"""
        # Retrieve the most relevant chunks (use same retriever as /query)
        retriever = temp_index.as_retriever(similarity_top_k=10)
        nodes = retriever.retrieve(prompt)
        context = "\n\n---\n\n".join([n.node.text for n in nodes]) if nodes else ""
        if not context:
            return {"filename": file.filename, "risk_report": "Unable to extract sufficient content from the PDF. Please ensure it is text‑based."}
        
        # Replace placeholder with actual context
        final_prompt = prompt.replace("{context}", context)

        # Call LLM (ensure you have Groq or other provider)
        response = Settings.llm.complete(final_prompt)
        raw = response.text if hasattr(response, 'text') else str(response)
        
        # Attempt to parse the JSON; if fails, return raw but indicate error
        try:
            import json
            # Clean potential markdown code fences
            if raw.startswith("```json"):
                raw = raw[7:-3]
            if raw.startswith("```"):
                raw = raw[3:-3]
            report_json = json.loads(raw.strip())
            # Ensure all expected keys exist
            if not all(k in report_json for k in ["contract_type", "overall_risk", "clause_analysis", "summary"]):
                raise ValueError("Missing required keys")
            return {"filename": file.filename, "risk_report": report_json}
        except Exception as e:
            # Fallback: return raw text with error note
            return {"filename": file.filename, "risk_report": {"error": "Could not parse structured output", "raw": raw, "parse_error": str(e)}}

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

# ========== AGENTS ==========

# Agent 1: DPDP Act Compliance Checker
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
            os.remove(temp_path)

# Agent 2: Legal Notice Drafter
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

# Agent 3: Due Diligence (Multi-PDF)
@app.post("/due-diligence")
async def due_diligence(zip_file: UploadFile = File(...)):
    contents = await zip_file.read()
    results = []
    with zipfile.ZipFile(io.BytesIO(contents)) as z:
        for name in z.namelist():
            if name.lower().endswith('.pdf'):
                # For simplicity, just return the file name and a placeholder risk
                results.append({"file": name, "risk": "pending review"})
    return {"results": results}

# Agent 4: NDA Triage
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

# Agent 5: Weekly Regulatory Digest
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=7860)