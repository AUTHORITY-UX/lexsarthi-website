"""Feature 3: Dynamic RAG with Auto-Expansion."""
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from loguru import logger as log
from .db import db
from .embeddings import embed
from .sarvam import sarvam_reason

CRAWL_SOURCES = [
    {"name":"Supreme Court of India","url":"https://main.sci.gov.in/judgments","jurisdiction":"IN"},
    {"name":"Indian Kanoon","url":"https://indiankanoon.org","jurisdiction":"IN"},
    {"name":"eCourts","url":"https://judgments.ecourts.gov.in","jurisdiction":"IN"},
]

class DynamicRAG:
    async def add_document(self, content: str, source_url: str = "", title: str = "",
        citation: str = "", jurisdiction: str = "IN", court: str = "") -> Dict[str, Any]:
        summary = await self._summarize(content)
        holdings = await self._extract_holdings(content)
        jid = await db.add_judgment_doc(source_url,title or summary[:100],citation,jurisdiction,court,
                                         summary,content[:50000],holdings)
        chunks = self._chunk(content)
        cids = []
        for i, ch in enumerate(chunks):
            emb = await embed(ch)
            cid = await db.insert_vec("knowledge_chunks",
                {"content":ch[:8000],"metadata":json.dumps({"source":source_url,"title":title,
                    "judgment_id":jid,"chunk_index":i,"jurisdiction":jurisdiction})}, emb)
            if cid: cids.append(cid)
        await db.audit("rag","document_indexed","judgment_doc",jid,{"chunks":len(cids),"citation":citation})
        return {"judgment_id":jid,"summary":summary,"key_holdings":holdings,"chunks_indexed":len(cids)}

    async def search(self, query: str, top_k: int = 8) -> List[Dict]:
        qv = await embed(query)
        rows = await db.vector_search("knowledge_chunks","embedding",qv,top_k)
        out = []
        for r in rows:
            meta = r.get("metadata",{})
            if isinstance(meta, str):
                try: meta = json.loads(meta)
                except: meta = {}
            out.append({"content":r.get("content","")[:1000],"source":meta.get("source",""),
                        "title":meta.get("title",""),"similarity":round(r.get("similarity",0),4),
                        "jurisdiction":meta.get("jurisdiction","IN")})
        return out

    async def _summarize(self, text: str) -> str:
        if len(text) < 200: return text[:500]
        r = await sarvam_reason(f"Summarize in 3-4 sentences:\n{text[:4000]}","You are a legal summarizer.",0.3,500)
        return r or text[:500]

    async def _extract_holdings(self, text: str) -> List[str]:
        r = await sarvam_reason(f"Extract 3-5 key holdings as JSON array:\n{text[:3000]}",
                                "Output JSON array only.",0.2,800)
        if r:
            try:
                m = re.search(r'\[.*?\]', r, re.DOTALL)
                if m: return json.loads(m.group(0))
            except: pass
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s for s in sentences if any(k in s.lower() for k in ["held","ruled","decided","directed"])][:5]

    def _chunk(self, text: str, sz: int = 1024, overlap: int = 128) -> List[str]:
        if len(text) <= sz: return [text]
        chunks, start = [], 0
        while start < len(text):
            chunks.append(text[start:start+sz]); start = start + sz - overlap
        return chunks

    async def auto_crawl(self) -> Dict[str, Any]:
        for s in CRAWL_SOURCES:
            await db.audit("rag","crawl_attempt","source",s["url"],s)
        return {"sources_checked":len(CRAWL_SOURCES),"timestamp":datetime.now(timezone.utc).isoformat()}

    async def get_version_history(self, citation: str) -> List[Dict]:
        rows = await db.fetch("SELECT id,version,superseded_by,summary,created_at FROM moat_judgment_docs WHERE citation=$1 ORDER BY version DESC", citation)
        return [dict(r) for r in rows]

dynamic_rag = DynamicRAG()
