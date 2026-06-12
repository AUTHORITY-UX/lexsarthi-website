import os
from pathlib import Path
from pypdf import PdfReader
from llama_index.llms.groq import Groq
import gradio as gr

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
    # Simple prompt with the whole document (truncated to 8000 chars to avoid token limits)
    context = DOCUMENT[:8000]
    prompt = f"""You are a legal assistant. Use the following document to answer. If the answer isn't there, say so.

Document:
{context}

Question: {message}
Answer:"""
    response = llm.complete(prompt)
    return response.text

# Create Gradio chat interface
gr.ChatInterface(
    fn=chat,
    title="LexSarthi – Legal AI Assistant",
    description="Ask questions about the DPDPA Act (uploaded document).",
).launch(server_name="0.0.0.0", server_port=7860)