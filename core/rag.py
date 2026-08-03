"""
RAG System - Vector-based retrieval over legal documents using pgvector.
Provides document ingestion, chunking, embedding, and retrieval.
Falls back gracefully when pgvector is not available.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from unknown_verdict.config import settings


@dataclass
class Document:
    """A legal document in the RAG system."""
    doc_id: str
    title: str
    doc_type: str  # statute, case_law, regulation, contract, opinion
    jurisdiction: str = "India"
    source: str = ""
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List["DocumentChunk"] = field(default_factory=list)
    created_at: str = ""
    embedding_status: str = "pending"  # pending, embedded, failed

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "doc_type": self.doc_type,
            "jurisdiction": self.jurisdiction,
            "source": self.source,
            "content_length": len(self.content),
            "chunk_count": len(self.chunks),
            "embedding_status": self.embedding_status,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class DocumentChunk:
    """A chunk of a legal document for vector retrieval."""
    chunk_id: str
    doc_id: str
    content: str
    embedding: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_index: int = 0

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "content_preview": self.content[:200],
            "content_length": len(self.content),
            "chunk_index": self.chunk_index,
            "has_embedding": len(self.embedding) > 0,
            "metadata": self.metadata,
        }


@dataclass
class RetrievalResult:
    """A single retrieval result."""
    chunk: DocumentChunk
    document: Document
    score: float
    rank: int

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "score": round(self.score, 4),
            "doc_id": self.document.doc_id,
            "doc_title": self.document.title,
            "doc_type": self.document.doc_type,
            "content": self.chunk.content,
            "preview": self.chunk.content[:300],
            "metadata": self.chunk.metadata,
        }


class SimpleEmbedder:
    """
    Simple hash-based embedder for fallback when no external embedding API is available.
    Generates pseudo-embeddings using character-level hashing.
    In production, replace with Sarvam AI's embedding endpoint or OpenAI embeddings.
    """
    def __init__(self, dimensions: int = 1536) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> List[float]:
        """Generate a pseudo-embedding from text."""
        embedding = [0.0] * self.dimensions
        text_lower = text.lower()

        # Character-level hashing
        for i, char in enumerate(text_lower):
            idx = (ord(char) * (i + 1)) % self.dimensions
            embedding[idx] += 1.0

        # Word-level hashing for better semantic capture
        words = text_lower.split()
        for i, word in enumerate(words):
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            for j in range(min(8, self.dimensions)):
                idx = (h + j * 191) % self.dimensions
                embedding[idx] += 1.0 / (i + 1)

        # Normalize
        magnitude = sum(v * v for v in embedding) ** 0.5
        if magnitude > 0:
            embedding = [v / magnitude for v in embedding]

        return embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]


class RAGSystem:
    """
    RAG system with pgvector support.
    Falls back to in-memory storage when pgvector is not available.
    """

    def __init__(self) -> None:
        self.dimensions = settings.VECTOR_DIMENSIONS
        self.chunk_size = settings.RAG_CHUNK_SIZE
        self.chunk_overlap = settings.RAG_CHUNK_OVERLAP
        self.top_k = settings.RAG_TOP_K
        self.embedder = SimpleEmbedder(self.dimensions)

        # In-memory store (fallback)
        self.documents: Dict[str, Document] = {}
        self.chunks: Dict[str, DocumentChunk] = {}
        self._pgvector_available = False

        # Seed with sample legal documents
        self._seed_documents()

    def _seed_documents(self) -> None:
        """Seed the RAG system with sample Indian legal documents."""
        sample_docs = [
            {
                "title": "Constitution of India - Part III (Fundamental Rights)",
                "doc_type": "statute",
                "source": "Constitution of India",
                "content": (
                    "Article 12: Definition of State. In this Part, unless the context otherwise "
                    "requires, 'the State' includes the Government and Parliament of India and "
                    "the Government and the Legislature of each of the States and all local or "
                    "other authorities within the territory of India or under the control of "
                    "the Government of India.\n\n"
                    "Article 13: Laws inconsistent with or in derogation of the fundamental rights. "
                    "(1) All laws in force in the territory of India immediately before the "
                    "commencement of this Constitution, in so far as they are inconsistent with "
                    "the provisions of this Part, shall, to the extent of such inconsistency, be void.\n\n"
                    "Article 14: The State shall not deny to any person equality before the law "
                    "or the equal protection of the laws within the territory of India.\n\n"
                    "Article 19: Protection of certain rights regarding freedom of speech, etc. "
                    "(1) All citizens shall have the right to freedom of speech and expression; "
                    "to assemble peaceably and without arms; to form associations or unions; "
                    "to move freely throughout the territory of India; to reside and settle in "
                    "any part of the territory of India.\n\n"
                    "Article 21: No person shall be deprived of his life or personal liberty "
                    "except according to procedure established by law."
                ),
            },
            {
                "title": "Indian Penal Code - Key Provisions",
                "doc_type": "statute",
                "source": "Indian Penal Code, 1860",
                "content": (
                    "Section 302: Punishment for murder. Whoever commits murder shall be "
                    "punished with death, or imprisonment for life, and shall also be liable to fine.\n\n"
                    "Section 304A: Causing death by negligence. Whoever causes the death of any "
                    "person by doing any rash or negligent act not amounting to culpable homicide "
                    "shall be punished with imprisonment of either description for a term which "
                    "may extend to two years, or with fine, or with both.\n\n"
                    "Section 378: Theft. Whoever, intending to take dishonestly any movable property "
                    "out of the possession of any person without that person's consent, moves that "
                    "property in order to such taking, is said to commit theft.\n\n"
                    "Section 420: Cheating. Whoever cheats and thereby dishonestly induces the "
                    "person deceived to deliver any property to any person, or to make, alter or "
                    "destroy the whole or any part of a valuable security, shall be punished with "
                    "imprisonment of either description for a term which may extend to seven years, "
                    "and shall also be liable to fine."
                ),
            },
            {
                "title": "Digital Personal Data Protection Act, 2023 - Summary",
                "doc_type": "statute",
                "source": "DPDP Act, 2023",
                "content": (
                    "Section 4: Consent. A Data Principal shall give consent in such manner as "
                    "may be prescribed to the Data Fiduciary before the processing of her personal data.\n\n"
                    "Section 7: Legitimate Uses. A Data Fiduciary may process the personal data of "
                    "a Data Principal if such processing is necessary for a legitimate use.\n\n"
                    "Section 11: Right to Access Information. Every Data Principal shall have the "
                    "right to obtain from the Data Fiduciary confirmation whether personal data is "
                    "being processed, the summary of such personal data, and the identities of other "
                    "Data Fiduciaries with whom the personal data has been shared.\n\n"
                    "Section 12: Right to Correction and Erasure. Every Data Principal shall have "
                    "the right to correction, completion, and updating of personal data.\n\n"
                    "Section 17: Consent Manager. Every Data Principal shall have the right to "
                    "access, correct, complete, update, or erasure of personal data through a "
                    "Consent Manager."
                ),
            },
            {
                "title": "Contract Act, 1872 - Essential Elements",
                "doc_type": "statute",
                "source": "Indian Contract Act, 1872",
                "content": (
                    "Section 2(h): An agreement enforceable by law is a contract.\n\n"
                    "Section 10: What agreements are contracts. All agreements are contracts if "
                    "they are made by the free consent of parties competent to contract, for a "
                    "lawful consideration and with a lawful object, and are not hereby expressly "
                    "declared to be void.\n\n"
                    "Section 14: Free consent defined. Consent is said to be free when it is not "
                    "caused by coercion, undue influence, fraud, misrepresentation, or mistake.\n\n"
                    "Section 23: What considerations and objects are lawful. The consideration or "
                    "object of an agreement is lawful, unless it is forbidden by law; or is of such "
                    "a nature that, if permitted, it would defeat the provisions of any law; or is "
                    "fraudulent; or involves or implies injury to the person or property of another; "
                    "or is immoral or opposed to public policy.\n\n"
                    "Section 73: Compensation for loss or damage caused by breach of contract. "
                    "When a contract has been broken, the party who suffers by such breach is "
                    "entitled to receive compensation for any loss or damage caused to him thereby."
                ),
            },
            {
                "title": "Companies Act, 2013 - Key Provisions",
                "doc_type": "statute",
                "source": "Companies Act, 2013",
                "content": (
                    "Section 2(20): Company means a company incorporated under this Act or under "
                    "any previous company law.\n\n"
                    "Section 3: Formation of company. A company may be formed for any lawful purpose "
                    "by seven or more persons in the case of a public company, or by two or more "
                    "persons in the case of a private company.\n\n"
                    "Section 166: Duties of Directors. A director of a company shall act in "
                    "accordance with the articles of the company, act in good faith, promote the "
                    "objects of the company for the benefit of its members, and exercise due care.\n\n"
                    "Section 230: Power to compromise or make arrangements. Where a compromise or "
                    "arrangement is proposed between a company and its creditors or members, the "
                    "Tribunal may, on application, order a meeting of creditors or members."
                ),
            },
            {
                "title": "Consumer Protection Act, 2019",
                "doc_type": "statute",
                "source": "Consumer Protection Act, 2019",
                "content": (
                    "Section 2(7): Consumer means any person who buys any goods, hires or avails "
                    "of any service for consideration, but does not include a person who obtains "
                    "goods for resale or commercial purposes.\n\n"
                    "Section 17: The Central Consumer Protection Authority shall have jurisdiction "
                    "to investigate violations of consumer rights, unfair trade practices, and "
                    "false or misleading advertisements.\n\n"
                    "Section 35: Every complaint shall be filed with the District Forum within "
                    "two years from the date of cause of action.\n\n"
                    "Section 51: Penalties. Any manufacturer or service provider who causes a false "
                    "or misleading advertisement to be published shall be liable to penalty."
                ),
            },
        ]

        for doc_data in sample_docs:
            self.ingest_document(
                title=doc_data["title"],
                content=doc_data["content"],
                doc_type=doc_data["doc_type"],
                source=doc_data["source"],
            )

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= self.chunk_size:
            return [text]

        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            # Try to break at a sentence or paragraph boundary
            if end < len(text):
                # Look for nearest sentence boundary
                for boundary in ["\n\n", ". ", "? ", "! ", "\n"]:
                    boundary_idx = text.rfind(boundary, start, end)
                    if boundary_idx > start:
                        end = boundary_idx + len(boundary)
                        break
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - self.chunk_overlap
            if start >= len(text):
                break

        return chunks

    def _generate_doc_id(self, title: str) -> str:
        return hashlib.sha256(title.encode()).hexdigest()[:16]

    def ingest_document(
        self,
        title: str,
        content: str,
        doc_type: str = "statute",
        source: str = "",
        jurisdiction: str = "India",
        metadata: Optional[dict] = None,
    ) -> Document:
        """Ingest a document into the RAG system."""
        doc_id = self._generate_doc_id(title + str(time.time()))
        document = Document(
            doc_id=doc_id,
            title=title,
            doc_type=doc_type,
            jurisdiction=jurisdiction,
            source=source,
            content=content,
            metadata=metadata or {},
        )

        # Chunk the document
        text_chunks = self._chunk_text(content)
        for i, chunk_text in enumerate(text_chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            embedding = self.embedder.embed(chunk_text)
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                content=chunk_text,
                embedding=embedding,
                chunk_index=i,
                metadata={
                    "title": title,
                    "doc_type": doc_type,
                    "source": source,
                    "jurisdiction": jurisdiction,
                },
            )
            document.chunks.append(chunk)
            self.chunks[chunk_id] = chunk

        document.embedding_status = "embedded"
        self.documents[doc_id] = document
        return document

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x * x for x in a) ** 0.5
        mag_b = sum(y * y for y in b) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        doc_type: Optional[str] = None,
    ) -> List[RetrievalResult]:
        """Retrieve relevant document chunks for a query."""
        k = top_k or self.top_k
        query_embedding = self.embedder.embed(query)

        scored: List[Tuple[float, DocumentChunk, Document]] = []
        for chunk_id, chunk in self.chunks.items():
            doc = self.documents.get(chunk.doc_id)
            if doc is None:
                continue
            if doc_type and doc.doc_type != doc_type:
                continue
            score = self._cosine_similarity(query_embedding, chunk.embedding)
            scored.append((score, chunk, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        results: List[RetrievalResult] = []
        for rank, (score, chunk, doc) in enumerate(scored[:k], 1):
            results.append(RetrievalResult(
                chunk=chunk, document=doc, score=score, rank=rank,
            ))
        return results

    def get_context(self, query: str, top_k: Optional[int] = None) -> str:
        """Get formatted context string from retrieved documents."""
        results = self.retrieve(query, top_k=top_k)
        if not results:
            return ""
        parts: List[str] = []
        for r in results:
            parts.append(
                f"[{r.document.title} (Source: {r.document.source})]\n{r.chunk.content}"
            )
        return "\n\n---\n\n".join(parts)

    def stats(self) -> dict:
        return {
            "total_documents": len(self.documents),
            "total_chunks": len(self.chunks),
            "vector_dimensions": self.dimensions,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "top_k": self.top_k,
            "pgvector_available": self._pgvector_available,
            "embedding_model": "simple-hash-embedder (fallback)",
            "document_types": list(set(d.doc_type for d in self.documents.values())),
        }

    def list_documents(self) -> List[dict]:
        return [d.to_dict() for d in self.documents.values()]


# Singleton
rag_system = RAGSystem()
