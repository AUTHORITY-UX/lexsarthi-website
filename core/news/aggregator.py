"""
core/news/aggregator.py - AI News Corner
Auto-updated news using httpx (no aiohttp dependency)
"""

import json
import logging
import asyncio
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
import httpx

from core.db import db
from core.llm import LLMMessage, get_router

logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    """News article structure"""
    id: str
    title: str
    source: str
    url: str
    summary: str
    content: str = ""
    category: str = "general"
    published_date: datetime = field(default_factory=datetime.now)
    author: str = ""
    tags: List[str] = field(default_factory=list)
    sentiment: float = 0.0
    importance_score: float = 0.0


class AINewsAggregator:
    """Aggregate AI news from multiple sources using httpx"""
    
    SOURCES = {
        'techcrunch_ai': {
            'url': 'https://techcrunch.com/category/artificial-intelligence/feed/',
            'source': 'TechCrunch AI'
        },
        'venturebeat_ai': {
            'url': 'https://venturebeat.com/category/ai/feed/',
            'source': 'VentureBeat AI'
        },
        'aitoday': {
            'url': 'https://www.aitoday.com/feed/',
            'source': 'AI Today'
        },
        'law_ai': {
            'url': 'https://www.law.com/legaltechnews/ai/feed/',
            'source': 'LegalTech AI'
        },
        'ai_governance': {
            'url': 'https://www.ai-governance.com/feed/',
            'source': 'AI Governance'
        },
        'eu_ai_act': {
            'url': 'https://artificialintelligenceact.eu/feed/',
            'source': 'EU AI Act'
        },
        'india_ai': {
            'url': 'https://indiaai.gov.in/rss/feed/',
            'source': 'India AI'
        },
        'openai_news': {
            'url': 'https://openai.com/news/rss',
            'source': 'OpenAI'
        },
        'deepmind': {
            'url': 'https://deepmind.com/blog/feed',
            'source': 'DeepMind'
        },
        'huggingface': {
            'url': 'https://huggingface.co/blog/feed',
            'source': 'HuggingFace'
        }
    }
    
    def __init__(self):
        self.router = get_router()
        self.articles = []
        self.last_update = None
        self._client = None
    
    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
            )
        return self._client
    
    async def fetch_rss_feed(self, url: str) -> List[Dict]:
        """Fetch and parse RSS feed using httpx"""
        try:
            client = await self.get_client()
            response = await client.get(url)
            response.raise_for_status()
            
            feed = feedparser.parse(response.text)
            articles = []
            
            for entry in feed.entries[:10]:
                article = {
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', ''),
                    'published': entry.get('published', datetime.now().isoformat()),
                    'author': entry.get('author', ''),
                    'tags': [t.get('term', '') for t in entry.get('tags', [])]
                }
                articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed {url}: {e}")
            return []
    
    async def fetch_web_content(self, url: str) -> str:
        """Fetch and extract content from webpage using httpx"""
        try:
            client = await self.get_client()
            response = await client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get main content
            content = soup.get_text(separator='\n')
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            return ' '.join(lines[:50])  # First 50 lines
            
        except Exception as e:
            logger.error(f"Error fetching content {url}: {e}")
            return ""
    
    async def classify_article(self, title: str, summary: str) -> str:
        """Classify article category using AI"""
        messages = [
            LLMMessage(role="system", content="""Classify this AI news article into one category:
            - ai_law: Laws, regulations, compliance
            - legal_tech: Legal technology, tools
            - ai_governance: AI governance, ethics, policy
            - research: AI research, breakthroughs
            - policy: Government policy, international agreements
            - general: Other AI news
            
            Return only the category name."""),
            LLMMessage(role="user", content=f"Title: {title}\nSummary: {summary[:300]}")
        ]
        
        try:
            response = await self.router.chat(messages, complexity="simple")
            category = response.content.strip().lower()
            valid_categories = ['ai_law', 'legal_tech', 'ai_governance', 'research', 'policy', 'general']
            return category if category in valid_categories else 'general'
        except:
            return 'general'
    
    async def calculate_importance(self, article: Dict) -> float:
        """Calculate importance score for article"""
        score = 0.5  # Base score
        
        important_keywords = [
            'breakthrough', 'landmark', 'significant', 'historic',
            'regulation', 'act', 'law', 'governance', 'compliance',
            'scandal', 'investigation', 'policy', 'international'
        ]
        
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        
        for keyword in important_keywords:
            if keyword in text:
                score += 0.1
        
        return min(score, 1.0)
    
    async def get_news(self, limit: int = 20, category: str = None) -> List[NewsArticle]:
        """Get aggregated news with optional category filter"""
        
        # Check cache
        cache_key = f"news_{category if category else 'all'}"
        try:
            cached = await db.fetchone(
                "SELECT value, expires_at FROM moat_cache WHERE key = $1",
                cache_key
            )
            
            if cached and cached.get('expires_at') and cached['expires_at'] > datetime.now():
                articles_data = json.loads(cached['value'])
                return [NewsArticle(**a) for a in articles_data]
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        
        # Fetch fresh news
        all_articles = []
        
        for source_name, source_info in self.SOURCES.items():
            try:
                articles = await self.fetch_rss_feed(source_info['url'])
                for article in articles:
                    # Get full content if available
                    content = await self.fetch_web_content(article.get('link', ''))
                    
                    # Classify article
                    category_ai = await self.classify_article(
                        article.get('title', ''),
                        article.get('summary', '')
                    )
                    
                    # Calculate importance
                    importance = await self.calculate_importance(article)
                    
                    # Parse date
                    pub_date = datetime.now()
                    try:
                        if article.get('published'):
                            pub_date = datetime.fromisoformat(article['published'].replace('Z', '+00:00'))
                    except:
                        pass
                    
                    # Create article
                    news_article = NewsArticle(
                        id=f"{source_name}_{hash(article.get('link', ''))}",
                        title=article.get('title', ''),
                        source=source_info['source'],
                        url=article.get('link', ''),
                        summary=article.get('summary', '')[:300],
                        content=content[:1000],
                        category=category_ai,
                        published_date=pub_date,
                        author=article.get('author', ''),
                        tags=article.get('tags', []),
                        importance_score=importance
                    )
                    
                    if category is None or category == category_ai:
                        all_articles.append(news_article)
                        
            except Exception as e:
                logger.error(f"Error processing {source_name}: {e}")
        
        # Sort by importance and date
        all_articles.sort(key=lambda x: (x.importance_score, x.published_date), reverse=True)
        
        # Cache results
        try:
            await db.execute("""
                INSERT INTO moat_cache (key, value, expires_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (key) DO UPDATE SET value = $2, expires_at = $3
            """, cache_key, json.dumps([a.__dict__ for a in all_articles]), datetime.now() + timedelta(hours=1))
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
        
        self.articles = all_articles[:limit]
        self.last_update = datetime.now()
        
        return self.articles
    
    async def get_latest_updates(self) -> Dict:
        """Get latest AI news updates"""
        articles = await self.get_news(limit=10)
        
        return {
            'count': len(articles),
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'categories': {
                'ai_law': len([a for a in articles if a.category == 'ai_law']),
                'legal_tech': len([a for a in articles if a.category == 'legal_tech']),
                'ai_governance': len([a for a in articles if a.category == 'ai_governance']),
                'research': len([a for a in articles if a.category == 'research']),
                'policy': len([a for a in articles if a.category == 'policy']),
                'general': len([a for a in articles if a.category == 'general'])
            },
            'articles': articles[:10]
        }
    
    async def start_background_updater(self, interval_minutes: int = 15):
        """Start background news updater"""
        while True:
            try:
                logger.info("🔄 Updating AI news...")
                await self.get_news(limit=50)
                logger.info("✅ AI news updated successfully")
            except Exception as e:
                logger.error(f"Error updating news: {e}")
            await asyncio.sleep(interval_minutes * 60)
    
    async def close(self):
        """Close HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton instance
_news_aggregator: Optional[AINewsAggregator] = None

def get_news_aggregator() -> AINewsAggregator:
    """Get news aggregator singleton"""
    global _news_aggregator
    if _news_aggregator is None:
        _news_aggregator = AINewsAggregator()
    return _news_aggregator