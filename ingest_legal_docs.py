# ingest_legal_docs.py
import os
import glob
import json
import hashlib
from typing import List, Dict, Any
import asyncpg
import openai
from pypdf import PdfReader
from tqdm import tqdm

# ----- CONFIG -----
PDF_DIR = "legal_docs"                # relative to project root
CHUNK_SIZE = 800                      # tokens approx
OVERLAP = 150
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
DATABASE_URL = os.environ["DATABASE_URL"]   # Neon connection string

openai.api_key = os.environ["OPENAI_API_KEY"]

# ----- HELPERS -----
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> List[str]:
    """Simple recursive character chunking with overlap."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i+chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def get_embedding(text: str) -> List[float]:
    response = openai.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding

async def ingest_pdf(file_path: str, conn: asyncpg.Connection) -> int:
    """Extract, chunk, embed, and insert. Returns number of chunks inserted."""
    reader = PdfReader(file_path)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"

    if not full_text.strip():
        print(f"⚠️ Skipping {file_path} – no text extracted.")
        return 0

    chunks = chunk_text(full_text)
    inserted = 0
    source_name = os.path.basename(file_path)

    # Check existing chunks for this source
    existing = await conn.fetchval(
        "SELECT COUNT(*) FROM knowledge_chunks WHERE metadata->>'source' = $1",
        source_name
    )
    if existing:
        print(f"📁 {source_name} already has {existing} chunks. Skipping.")
        return 0

    for idx, chunk in enumerate(tqdm(chunks, desc=f"Embedding {source_name}")):
        embedding = get_embedding(chunk)
        metadata = {
            "source": source_name,
            "chunk_index": idx,
            "total_chunks": len(chunks),
            "file_path": file_path,
            "page_count": len(reader.pages)
        }
        await conn.execute(
            """
            INSERT INTO knowledge_chunks (content, metadata, embedding)
            VALUES ($1, $2, $3)
            """,
            chunk, json.dumps(metadata), embedding
        )
        inserted += 1
    return inserted

async def main():
    conn = await asyncpg.connect(DATABASE_URL)
    pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    total = 0
    for pdf in pdf_files:
        try:
            n = await ingest_pdf(pdf, conn)
            total += n
        except Exception as e:
            print(f"❌ Error processing {pdf}: {e}")
    await conn.close()
    print(f"✅ Ingestion complete. Added {total} new chunks.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())