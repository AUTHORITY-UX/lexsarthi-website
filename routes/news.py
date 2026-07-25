# routes/news.py
import feedparser
import aiohttp
from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api/news", tags=["News"])

NEWS_SOURCES = {
    "legal": [
        "https://www.barandbench.com/feed",
        "https://www.livelaw.in/feed",
        "https://www.scconline.com/blog/feed",
    ],
    "sports": [
        "https://www.espn.com/espn/rss/news",
        "https://www.sportskeeda.com/feed",
    ],
    "business": [
        "https://economictimes.indiatimes.com/rss",
        "https://www.business-standard.com/rss",
        "https://www.reuters.com/rss",
    ],
    "technology": [
        "https://techcrunch.com/feed",
        "https://www.wired.com/feed",
        "https://www.theverge.com/rss",
    ],
    "ai": [
        "https://arxiv.org/rss/cs.AI",
        "https://openai.com/blog/rss.xml",
        "https://deepmind.com/blog/feed.xml",
    ],
    "stocks": [
        "https://www.moneycontrol.com/rss",
        "https://www.bloomberg.com/feed",
    ]
}

@router.get("/all")
async def get_all_news(category: str = None, limit: int = 20):
    """Get aggregated news from all sources"""
    if category and category in NEWS_SOURCES:
        sources = NEWS_SOURCES[category]
    else:
        sources = []
        for src_list in NEWS_SOURCES.values():
            sources.extend(src_list)
    
    articles = []
    for url in sources[:5]:  # Limit to prevent timeout
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                articles.append({
                    "title": entry.title,
                    "summary": entry.get('summary', '')[:300],
                    "link": entry.get('link', ''),
                    "source": url.split('/')[2],
                    "published": entry.get('published', datetime.now().isoformat()),
                    "category": category or "general"
                })
        except:
            pass
    
    # Sort by date
    articles.sort(key=lambda x: x['published'], reverse=True)
    return {"status": "ok", "articles": articles[:limit], "count": len(articles)}

@router.get("/sports")
async def get_sports_news():
    """Get sports news"""
    return await get_all_news(category="sports", limit=20)

@router.get("/business")
async def get_business_news():
    """Get business news"""
    return await get_all_news(category="business", limit=20)

@router.get("/ai")
async def get_ai_news():
    """Get AI news"""
    return await get_all_news(category="ai", limit=20)