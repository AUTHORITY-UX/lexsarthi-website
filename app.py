import os
from pathlib import Path
from pypdf import PdfReader
from llama_index.llms.groq import Groq
import gradio as gr
from fastapi.responses import JSONResponse   # new import

# Load API key from secrets
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set")

llm = Groq(
    model="llama-3.3-70b-versatile",   # active model
    api_key=GROQ_API_KEY,
    temperature=0.1,
)

# Load the PDF once
def load_document():
    legal_docs = Path("legal_docs")
    for file in legal_docs.glob("*"):
        if file.suffix.lower() == ".pdf":
            reader = PdfReader(file)
            text = "".join(page.extract_text() or "" for page in reader.pages)
            return text
        elif file.suffix.lower() == ".txt":
            return file.read_text(encoding="utf-8")
    raise FileNotFoundError("No PDF or TXT found in legal_docs/")

DOCUMENT = load_document()
print(f"Loaded document: {len(DOCUMENT)} chars")

def chat(message, history):
    context = DOCUMENT[:8000]   # truncate to avoid token limits
    prompt = f"""You are a legal assistant. Use the following document to answer. If the answer isn't there, say so.

Document:
{context}

Question: {message}
Answer:"""
    response = llm.complete(prompt)
    return response.text

# Create Gradio chat interface
chatbot = gr.ChatInterface(
    fn=chat,
    title="LexSarthi – Legal AI Assistant",
    description="Ask questions about the DPDPA Act (uploaded document).",
)

# ---------- NEW: Add a GET /analyze handler ----------
chatbot.app.add_route(
    "/analyze",
    lambda: JSONResponse({
        "message": "The /analyze endpoint does not exist in this demo. "
                   "Use the Gradio chat interface at / to ask legal questions.",
        "docs": "Visit /docs for API documentation if available.",
        "live_demo": "https://advocacyalawfrim.in"
    }),
    methods=["GET"]
)
# -----------------------------------------------------

# Launch (Hugging Face will call this via run.py or directly)
chatbot.queue()
chatbot.launch(server_name="0.0.0.0", server_port=7860)