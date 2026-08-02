"""Feature 16: Auto-Publishing & Thought Leadership."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List
from .db import db
from .sarvam import sarvam_reason

class PublishingEngine:
    async def generate_article(self, topic: str, keywords: List[str] = None) -> Dict[str, Any]:
        kw = ", ".join(keywords or [])
        raw = await sarvam_reason(
            f"Write a professional legal article about: {topic}. Keywords: {kw}. "
            f"Include an engaging title, introduction, 3-4 sections with subheadings, and a conclusion. "
            f"Target audience: Indian legal professionals and clients. "
            f"Style: authoritative but accessible. Length: 800-1200 words.",
            "You are a legal content writer for www.advocacayalawfrim.in.", 0.5, 4000)
        title = topic.title()
        if raw and "\n" in raw:
            first_line = raw.split("\n")[0]
            if len(first_line) < 200: title = first_line.strip("#* ")
        cid = await db.add_content("article", title, raw or f"Article about {topic}", keywords)
        return {"content_id":cid,"title":title,"body_md":raw or "","target_site":"https://www.advocacayalawfrim.in",
                "word_count":len((raw or "").split())}

    async def generate_newsletter(self, topics: List[str]) -> Dict[str, Any]:
        raw = await sarvam_reason(
            f"Create a weekly legal newsletter covering: {', '.join(topics)}. "
            f"Format: 1) Header 2) Brief intro 3) Key updates (2-3 sentences each) 4) This week's legal tip 5) Call to action.",
            "You are a legal newsletter editor.", 0.4, 3000)
        cid = await db.add_content("newsletter", f"Weekly Legal Brief - {datetime.now(timezone.utc).strftime('%B %d')}",
                                    raw or "", topics)
        return {"content_id":cid,"body_md":raw or ""}

    async def generate_social_post(self, topic: str) -> Dict[str, Any]:
        raw = await sarvam_reason(f"Write a LinkedIn post about: {topic}. Professional, engaging, with hashtags. Max 300 words.",
                                  "You are a legal social media manager.",0.6,800)
        cid = await db.add_content("social", f"LinkedIn: {topic}", raw or "", [topic])
        return {"content_id":cid,"body_md":raw or ""}

    async def list_drafts(self, status: str = "draft") -> List[Dict]:
        rows = await db.fetch("SELECT * FROM moat_content_drafts WHERE status=$1 ORDER BY created_at DESC LIMIT 50", status)
        return [dict(r) for r in rows]

publishing = PublishingEngine()
