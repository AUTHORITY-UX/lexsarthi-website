"""
core/news/aggregator_with_images.py - AI News with Images
Auto-updated news from internet with real-time images
"""

import json
import logging
import asyncio
import feedparser
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
import httpx
import base64
from urllib.parse import urljoin, urlparse

from core.db import db
from core.llm import LLMMessage, get_router

logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    """News article structure with image support"""
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
    image_url: str = ""
    image_data: str = ""  # Base64 encoded image
    image_caption: str = ""
    source_favicon: str = ""


class RealTimeNewsAggregator:
    """Real-time news aggregator with image support"""
    
    SOURCES = {
        'techcrunch_ai': {
            'url': 'https://techcrunch.com/category/artificial-intelligence/feed/',
            'source': 'TechCrunch AI',
            'icon': '🔬'
        },
        'venturebeat_ai': {
            'url': 'https://venturebeat.com/category/ai/feed/',
            'source': 'VentureBeat AI',
            'icon': '⚡'
        },
        'eu_ai_act': {
            'url': 'https://artificialintelligenceact.eu/feed/',
            'source': 'EU AI Act',
            'icon': '🇪🇺'
        },
        'openai_news': {
            'url': 'https://openai.com/news/rss',
            'source': 'OpenAI',
            'icon': '🤖'
        },
        'deepmind': {
            'url': 'https://deepmind.com/blog/feed',
            'source': 'DeepMind',
            'icon': '🧠'
        },
        'huggingface': {
            'url': 'https://huggingface.co/blog/feed',
            'source': 'HuggingFace',
            'icon': '🤗'
        },
        'india_ai': {
            'url': 'https://indiaai.gov.in/rss/feed/',
            'source': 'India AI',
            'icon': '🇮🇳'
        },
        'ai_governance': {
            'url': 'https://www.ai-governance.com/feed/',
            'source': 'AI Governance',
            'icon': '🏛️'
        },
        'law_ai': {
            'url': 'https://www.law.com/legaltechnews/ai/feed/',
            'source': 'LegalTech AI',
            'icon': '⚖️'
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
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
                follow_redirects=True
            )
        return self._client
    
    async def fetch_image(self, image_url: str) -> str:
        """Fetch image and return base64 encoded data"""
        if not image_url:
            return ""
        
        try:
            client = await self.get_client()
            response = await client.get(image_url, timeout=10.0)
            response.raise_for_status()
            
            # Determine content type
            content_type = response.headers.get('content-type', 'image/jpeg')
            if 'image' not in content_type:
                return ""
            
            # Encode to base64
            image_data = base64.b64encode(response.content).decode('utf-8')
            return f"data:{content_type};base64,{image_data}"
            
        except Exception as e:
            logger.warning(f"Could not fetch image {image_url}: {e}")
            return ""
    
    async def extract_images_from_html(self, html: str, base_url: str) -> List[str]:
        """Extract image URLs from HTML content"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            images = []
            
            # Find all img tags
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if src and not src.startswith('data:'):
                    # Convert relative URLs to absolute
                    full_url = urljoin(base_url, src)
                    if full_url.startswith('http'):
                        images.append(full_url)
            
            # Also look for og:image meta tag
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                images.append(og_image.get('content'))
            
            return images[:3]  # Limit to 3 images
            
        except Exception as e:
            logger.warning(f"Could not extract images: {e}")
            return []
    
    async def fetch_rss_feed(self, url: str) -> List[Dict]:
        """Fetch and parse RSS feed with images"""
        try:
            client = await self.get_client()
            response = await client.get(url)
            response.raise_for_status()
            
            feed = feedparser.parse(response.text)
            articles = []
            
            for entry in feed.entries[:10]:
                # Extract images from content
                content_html = entry.get('content', [{}])[0].get('value', '')
                if not content_html:
                    content_html = entry.get('summary', '')
                
                # Extract image URLs
                image_urls = await self.extract_images_from_html(content_html, url)
                
                # Get image from enclosure if available
                if not image_urls and entry.get('enclosures'):
                    for enclosure in entry.get('enclosures', []):
                        if enclosure.get('type', '').startswith('image/'):
                            image_urls.append(enclosure.get('href', ''))
                
                article = {
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', ''),
                    'published': entry.get('published', datetime.now().isoformat()),
                    'author': entry.get('author', ''),
                    'tags': [t.get('term', '') for t in entry.get('tags', [])],
                    'image_urls': image_urls,
                    'content_html': content_html[:2000]
                }
                articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed {url}: {e}")
            return []
    
    async def fetch_article_images(self, article_data: Dict) -> Dict:
        """Fetch and process images for an article"""
        image_urls = article_data.get('image_urls', [])
        images = []
        
        for img_url in image_urls[:1]:  # Only fetch first image
            if img_url:
                image_data = await self.fetch_image(img_url)
                if image_data:
                    images.append({
                        'url': img_url,
                        'data': image_data
                    })
        
        return {
            'images': images,
            'primary_image': images[0] if images else None
        }
    
    async def classify_article_with_image(self, title: str, summary: str, images: List[Dict]) -> Dict:
        """Classify article and generate image caption"""
        messages = [
            LLMMessage(role="system", content="""Analyze this news article and return JSON with:
            - category: ai_law, legal_tech, ai_governance, research, policy, general
            - importance: 0.0-1.0
            - image_caption: short description for the image"""),
            LLMMessage(role="user", content=f"Title: {title}\nSummary: {summary[:500]}")
        ]
        
        try:
            response = await self.router.chat(messages, complexity="simple")
            result = json.loads(response.content)
            return {
                'category': result.get('category', 'general'),
                'importance': result.get('importance', 0.5),
                'image_caption': result.get('image_caption', '')
            }
        except:
            return {
                'category': 'general',
                'importance': 0.5,
                'image_caption': ''
            }
    
    async def get_real_time_news(self, limit: int = 20, category: str = None) -> Dict:
        """Get real-time news with images"""
        
        # Check cache first
        cache_key = f"news_images_{category if category else 'all'}"
        try:
            cached = await db.fetchone(
                "SELECT value, expires_at FROM moat_cache WHERE key = $1",
                cache_key
            )
            if cached and cached.get('expires_at') and cached['expires_at'] > datetime.now():
                return json.loads(cached['value'])
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        
        # Fetch fresh news with images
        all_articles = []
        
        for source_name, source_info in self.SOURCES.items():
            try:
                # Fetch RSS feed with images
                feed_articles = await self.fetch_rss_feed(source_info['url'])
                
                for article_data in feed_articles[:5]:
                    # Fetch actual images
                    image_result = await self.fetch_article_images(article_data)
                    
                    # Classify the article
                    classification = await self.classify_article_with_image(
                        article_data.get('title', ''),
                        article_data.get('summary', ''),
                        image_result.get('images', [])
                    )
                    
                    # Parse date
                    pub_date = datetime.now()
                    try:
                        if article_data.get('published'):
                            pub_date = datetime.fromisoformat(article_data['published'].replace('Z', '+00:00'))
                    except:
                        pass
                    
                    # Create article with image
                    news_article = {
                        'id': f"{source_name}_{hash(article_data.get('link', ''))}",
                        'title': article_data.get('title', ''),
                        'source': source_info['source'],
                        'source_icon': source_info.get('icon', '📰'),
                        'url': article_data.get('link', ''),
                        'summary': article_data.get('summary', '')[:400],
                        'content': article_data.get('content_html', '')[:1000],
                        'category': classification.get('category', 'general'),
                        'published_date': pub_date.isoformat(),
                        'author': article_data.get('author', ''),
                        'tags': article_data.get('tags', []),
                        'importance_score': classification.get('importance', 0.5),
                        'image_url': image_result.get('primary_image', {}).get('url', ''),
                        'image_data': image_result.get('primary_image', {}).get('data', ''),
                        'image_caption': classification.get('image_caption', ''),
                        'source_favicon': ''  # Could be fetched separately
                    }
                    
                    if category is None or category == news_article['category']:
                        all_articles.append(news_article)
                        
            except Exception as e:
                logger.error(f"Error processing {source_name}: {e}")
        
        # Sort by importance and date
        all_articles.sort(key=lambda x: (x.get('importance_score', 0), x.get('published_date', '')), reverse=True)
        
        # Limit results
        result_articles = all_articles[:limit]
        
        # Prepare response
        response = {
            'articles': result_articles,
            'total': len(result_articles),
            'last_update': datetime.now().isoformat(),
            'categories': {
                'ai_law': len([a for a in result_articles if a['category'] == 'ai_law']),
                'legal_tech': len([a for a in result_articles if a['category'] == 'legal_tech']),
                'ai_governance': len([a for a in result_articles if a['category'] == 'ai_governance']),
                'research': len([a for a in result_articles if a['category'] == 'research']),
                'policy': len([a for a in result_articles if a['category'] == 'policy']),
                'general': len([a for a in result_articles if a['category'] == 'general'])
            },
            'sources': list(self.SOURCES.keys()),
            'has_images': len([a for a in result_articles if a.get('image_data')]) > 0
        }
        
        # Cache results
        try:
            await db.execute("""
                INSERT INTO moat_cache (key, value, expires_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (key) DO UPDATE SET value = $2, expires_at = $3
            """, cache_key, json.dumps(response), datetime.now() + timedelta(minutes=15))
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
        
        self.articles = result_articles
        self.last_update = datetime.now()
        
        return response
    
    async def start_background_updater(self, interval_minutes: int = 5):
        """Start background news updater with images"""
        while True:
            try:
                logger.info("🔄 Updating real-time news with images...")
                await self.get_real_time_news(limit=50)
                logger.info("✅ News with images updated successfully")
            except Exception as e:
                logger.error(f"Error updating news: {e}")
            await asyncio.sleep(interval_minutes * 60)
    
    async def close(self):
        """Close HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton instance
_news_aggregator: Optional[RealTimeNewsAggregator] = None

def get_news_aggregator() -> RealTimeNewsAggregator:
    """Get news aggregator singleton"""
    global _news_aggregator
    if _news_aggregator is None:
        _news_aggregator = RealTimeNewsAggregator()
    return _news_aggregator