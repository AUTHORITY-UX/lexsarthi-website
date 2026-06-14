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
import asyncio
from pypdf import PdfReader
import os
import shutil
import time
import hmac
import hashlib
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from llama_index.core import VectorStoreIndex, Settings
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_parse import LlamaParse
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

# ---------- Load legal documents using LlamaParse ----------
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

# ---------- Endpoints ----------
@app.get("/health")
async def health():
    return {"status": "ok", "docs_loaded": index is not None}

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

@app.post("/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    os.makedirs("temp_uploads", exist_ok=True)
    temp_path = f"temp_uploads/{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Parse PDF – run synchronous LlamaParse in a thread to avoid event loop issues
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

        # Build temporary index and query engine
        temp_index = VectorStoreIndex.from_documents(docs)
        engine = temp_index.as_query_engine()

        # Improved prompt to encourage non‑empty answer
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
async def analyze_contract(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files allowed")
    os.makedirs("temp_uploads", exist_ok=True)
    temp_path = f"temp_uploads/{file.filename}"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        docs = parser.load_data(temp_path)
        temp_index = VectorStoreIndex.from_documents(docs)
        engine = temp_index.as_query_engine()
        prompt = "Analyze this contract under Indian law. Identify high-risk clauses (indemnity, liability, termination, DPDP Act, arbitration, stamp duty). Provide a structured report with risk level and suggested changes."
        report = engine.query(prompt)
        return {"filename": file.filename, "risk_report": str(report)}
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/create-order")
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

@app.post("/razorpay-webhook")
async def razorpay_webhook(request: Request):
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
    # Payment verified – you can log or store transaction
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=7860)
    # Add these imports at the top of your server.py file
import razorpay
import hmac
import hashlib

# Add this code before your existing endpoints (@app.get...)
# Initialize the Razorpay client with your test keys from the environment
razorpay_client = razorpay.Client(auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")))

@app.post("/api/create-order")
async def create_order(amount: int = 2):
    """
    Endpoint to create a Razorpay order.
    Minimum amount is 100 paise (₹1) for testing.
    """
    # Validate amount
    if amount < 1:
        raise HTTPException(status_code=400, detail="Minimum amount is 100 paise (₹1)")

    try:
        # Prepare order data. Amount is in paise.
        order_data = {
            "amount": amount * 100,
            "currency": "INR",
            "receipt": f"order_rcpt_{int(time.time())}",
            "payment_capture": 1
        }
        # Create order on Razorpay
        order = razorpay_client.order.create(data=order_data)
        # Return the order details to the frontend
        return {"order_id": order["id"], "amount": amount, "currency": "INR"}
    except Exception as e:
        # Log the error for debugging
        print(f"Order creation failed: {e}")
        # Raise an HTTP 500 error
        raise HTTPException(status_code=500, detail="Failed to create payment order")

@app.post("/api/verify-payment")
async def verify_payment(request: Request):
    """
    Endpoint to verify the payment signature after a transaction.
    """
    try:
        # Get the JSON body from the request
        body = await request.json()
        
        # Extract the required fields
        razorpay_order_id = body.get('razorpay_order_id')
        razorpay_payment_id = body.get('razorpay_payment_id')
        razorpay_signature = body.get('razorpay_signature')

        # Validate that all fields are present
        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            raise HTTPException(status_code=400, detail="Missing payment verification fields")

        # Create the signature string in the order expected by Razorpay
        message = f"{razorpay_order_id}|{razorpay_payment_id}"
        
        # Generate the expected signature using HMAC-SHA256
        secret = os.getenv("RAZORPAY_KEY_SECRET")
        expected_signature = hmac.new(
            key=secret.encode('utf-8'),
            msg=message.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Compare the signatures
        if not hmac.compare_digest(expected_signature, razorpay_signature):
            print(f"Signature mismatch. Expected: {expected_signature}, Received: {razorpay_signature}")
            raise HTTPException(status_code=400, detail="Invalid payment signature")
        
        # If valid, you can mark the order as paid in your database here
        return {"status": "success", "message": "Payment verified successfully"}
        
    except Exception as e:
        print(f"Payment verification failed: {e}")
        raise HTTPException(status_code=500, detail="Payment verification failed")