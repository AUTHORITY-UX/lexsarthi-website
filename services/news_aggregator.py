# services/news_aggregator.py - News Aggregator Service
# Copyright © 2026 THE ADVOCACY – A LAW FIRM. All rights reserved.
# 🔱 TRIDENT - PERMANENT ASSET - NEVER REMOVE

import feedparser
from datetime import datetime
from typing import List, Dict, Optional

class NewsAggregatorService:
    """Service for aggregating news from multiple sources"""
    
    def __init__(self):
        self.sources = {
            "legal": [
                "https://www.barandbench.com/feed",
                "https://www.livelaw.in/feed",
            ],
            "business": [
                "https://economictimes.indiatimes.com/rss",
                "https://www.reuters.com/rss",
            ],
            "technology": [
                "https://techcrunch.com/feed",
                "https://www.wired.com/feed",
            ],
            "ai": [
                "https://arxiv.org/rss/cs.AI",
                "https://openai.com/blog/rss.xml",
            ]
        }
    
    async def fetch_news(self, category: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Fetch news from all sources"""
        articles = []
        sources_to_fetch = self.sources.get(category, []) if category else self._all_sources()
        
        for url in sources_to_fetch[:5]:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    articles.append({
                        "title": entry.title,
                        "summary": entry.get('summary', '')[:300],
                        "link": entry.get('link', ''),
                        "source": url.split('/')[2],
                        "published": entry.get('published', datetime.now().isoformat())
                    })
            except:
                pass
        
        articles.sort(key=lambda x: x['published'], reverse=True)
        return articles[:limit]
    
    def _all_sources(self) -> List[str]:
        all_sources = []
        for sources in self.sources.values():
            all_sources.extend(sources)
        return all_sources

news_aggregator = NewsAggregatorService()