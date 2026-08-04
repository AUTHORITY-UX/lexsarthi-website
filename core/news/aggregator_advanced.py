"""
core/news/aggregator_advanced.py - Advanced News with Videos, Conferences & Agent Analytics
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
from urllib.parse import urljoin, urlparse, parse_qs

from core.db import db
from core.llm import LLMMessage, get_router

logger = logging.getLogger(__name__)


@dataclass
class MediaContent:
    """Rich media content"""
    type: str  # 'video', 'image', 'audio', 'conference'
    url: str
    thumbnail: str = ""
    title: str = ""
    description: str = ""
    duration: str = ""
    platform: str = ""  # 'youtube', 'vimeo', 'twitter', 'linkedin'
    embed_code: str = ""
    transcript: str = ""


@dataclass
class ConferenceSession:
    """Conference session data"""
    title: str
    speaker: str
    organization: str
    date: datetime
    description: str
    video_url: str = ""
    slides_url: str = ""
    key_takeaways: List[str] = field(default_factory=list)
    category: str = ""


@dataclass
class AdvancedNewsArticle:
    """Advanced news with rich media"""
    id: str
    title: str
    source: str
    source_icon: str
    url: str
    summary: str
    content: str
    category: str
    published_date: datetime
    author: str
    tags: List[str]
    importance_score: float
    media: List[MediaContent] = field(default_factory=list)
    conference: Optional[ConferenceSession] = None
    agent_analysis: str = ""
    agent_rating: float = 0.0
    trending_score: float = 0.0
    related_topics: List[str] = field(default_factory=list)


class AdvancedNewsAggregator:
    """Advanced news aggregator with videos, conferences, and agent analytics"""
    
    # News sources with video support
    SOURCES = {
        'techcrunch_ai': {
            'url': 'https://techcrunch.com/category/artificial-intelligence/feed/',
            'source': 'TechCrunch AI',
            'icon': '🔬',
            'has_video': True
        },
        'venturebeat_ai': {
            'url': 'https://venturebeat.com/category/ai/feed/',
            'source': 'VentureBeat AI',
            'icon': '⚡',
            'has_video': True
        },
        'eu_ai_act': {
            'url': 'https://artificialintelligenceact.eu/feed/',
            'source': 'EU AI Act',
            'icon': '🇪🇺',
            'has_video': False
        },
        'openai_news': {
            'url': 'https://openai.com/news/rss',
            'source': 'OpenAI',
            'icon': '🤖',
            'has_video': True
        },
        'deepmind': {
            'url': 'https://deepmind.com/blog/feed',
            'source': 'DeepMind',
            'icon': '🧠',
            'has_video': True
        },
        'ai_governance': {
            'url': 'https://www.ai-governance.com/feed/',
            'source': 'AI Governance',
            'icon': '🏛️',
            'has_video': False
        },
        'law_ai': {
            'url': 'https://www.law.com/legaltechnews/ai/feed/',
            'source': 'LegalTech AI',
            'icon': '⚖️',
            'has_video': False
        },
        'neural_news': {
            'url': 'https://neuralnews.ai/feed/',
            'source': 'Neural News',
            'icon': '🧬',
            'has_video': True
        },
        'ai_weekly': {
            'url': 'https://aiweekly.co/feed/',
            'source': 'AI Weekly',
            'icon': '📊',
            'has_video': False
        },
        'mit_ai': {
            'url': 'https://news.mit.edu/topic/artificial-intelligence2-rss.xml',
            'source': 'MIT AI News',
            'icon': '🎓',
            'has_video': True
        },
        'stanford_ai': {
            'url': 'https://ai.stanford.edu/blog/feed.xml',
            'source': 'Stanford AI',
            'icon': '🏫',
            'has_video': True
        },
        'berkeley_ai': {
            'url': 'https://bair.berkeley.edu/blog/feed.xml',
            'source': 'Berkeley AI',
            'icon': '🐻',
            'has_video': True
        }
    }
    
    # YouTube channels for AI conferences
    CONFERENCE_SOURCES = {
        'neurips': {
            'url': 'https://www.youtube.com/feeds/videos.xml?channel_id=UCmifBKYb5f7g7J5JjKtCg9A',
            'name': 'NeurIPS Conference',
            'icon': '🧠'
        },
        'icml': {
            'url': 'https://www.youtube.com/feeds/videos.xml?channel_id=UCg0m9HdM6HBl0n6V4V4lC4A',
            'name': 'ICML Conference',
            'icon': '📊'
        },
        'cvpr': {
            'url': 'https://www.youtube.com/feeds/videos.xml?channel_id=UCV5e0mUwK3VkCqQD_45pXlQ',
            'name': 'CVPR Conference',
            'icon': '🖼️'
        },
        'acl': {
            'url': 'https://www.youtube.com/feeds/videos.xml?channel_id=UC2CjX85h3J5wBpt5GjLJq2Q',
            'name': 'ACL Conference',
            'icon': '📝'
        },
        'aaai': {
            'url': 'https://www.youtube.com/feeds/videos.xml?channel_id=UCrUe5wqXlKJqoM9K-ZwM3Yg',
            'name': 'AAAI Conference',
            'icon': '🎯'
        },
        'openai_events': {
            'url': 'https://www.youtube.com/feeds/videos.xml?channel_id=UCUeQ7h3WzF8Z5nZI1M_yjYQ',
            'name': 'OpenAI Events',
            'icon': '🤖'
        },
        'google_ai': {
            'url': 'https://www.youtube.com/feeds/videos.xml?channel_id=UCVgya8ZPYDlXQsg2nFj3OKw',
            'name': 'Google AI',
            'icon': '🔵'
        },
        'microsoft_ai': {
            'url': 'https://www.youtube.com/feeds/videos.xml?channel_id=UCGhDdhgDZQwZgUZfZqWYzJg',
            'name': 'Microsoft AI',
            'icon': '💻'
        }
    }
    
    def __init__(self):
        self.router = get_router()
        self.articles = []
        self.conferences = []
        self.videos = []
        self.last_update = None
        self._client = None
    
    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_connections=30, max_keepalive_connections=15),
                follow_redirects=True
            )
        return self._client
    
    async def extract_video_id(self, url: str) -> Optional[Dict]:
        """Extract video ID from URL"""
        video_info = {'platform': '', 'id': '', 'embed': ''}
        
        # YouTube
        youtube_patterns = [
            r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'youtu\.be/([a-zA-Z0-9_-]+)',
            r'youtube\.com/embed/([a-zA-Z0-9_-]+)',
            r'youtube\.com/v/([a-zA-Z0-9_-]+)'
        ]
        for pattern in youtube_patterns:
            match = re.search(pattern, url)
            if match:
                video_info['platform'] = 'youtube'
                video_info['id'] = match.group(1)
                video_info['embed'] = f'https://www.youtube.com/embed/{match.group(1)}'
                return video_info
        
        # Vimeo
        vimeo_pattern = r'vimeo\.com/(\d+)'
        match = re.search(vimeo_pattern, url)
        if match:
            video_info['platform'] = 'vimeo'
            video_info['id'] = match.group(1)
            video_info['embed'] = f'https://player.vimeo.com/video/{match.group(1)}'
            return video_info
        
        # Twitter/X
        twitter_pattern = r'twitter\.com/i/web/status/(\d+)'
        match = re.search(twitter_pattern, url)
        if match:
            video_info['platform'] = 'twitter'
            video_info['id'] = match.group(1)
            return video_info
        
        return None
    
    async def fetch_conference_videos(self) -> List[Dict]:
        """Fetch conference videos from YouTube channels"""
        videos = []
        
        for source_key, source_info in self.CONFERENCE_SOURCES.items():
            try:
                client = await self.get_client()
                response = await client.get(source_info['url'])
                response.raise_for_status()
                
                feed = feedparser.parse(response.text)
                
                for entry in feed.entries[:5]:
                    # Extract video ID
                    video_url = entry.get('link', '')
                    video_data = await self.extract_video_id(video_url)
                    
                    if video_data:
                        videos.append({
                            'id': f"conf_{hash(entry.get('link', ''))}",
                            'title': entry.get('title', ''),
                            'source': source_info['name'],
                            'icon': source_info['icon'],
                            'url': entry.get('link', ''),
                            'embed': video_data.get('embed', ''),
                            'platform': video_data.get('platform', ''),
                            'published': entry.get('published', datetime.now().isoformat()),
                            'summary': entry.get('summary', '')[:300],
                            'category': 'conference'
                        })
                        
            except Exception as e:
                logger.warning(f"Could not fetch {source_key}: {e}")
        
        return videos
    
    async def analyze_article_with_agent(self, title: str, content: str, media: List[Dict]) -> Dict:
        """Have an AI agent analyze and review the article"""
        messages = [
            LLMMessage(role="system", content="""You are a legal AI analyst. Analyze this news article and provide:
            1. Summary (2-3 sentences)
            2. Key legal implications (if any)
            3. Importance rating (1-10)
            4. Related legal topics
            5. Suggested action items
            
            Return as JSON.""",),
            LLMMessage(role="user", content=f"Title: {title}\nContent: {content[:1000]}")
        ]
        
        try:
            response = await self.router.chat(messages, complexity="complex")
            result = json.loads(response.content)
            return {
                'analysis': result.get('summary', ''),
                'rating': result.get('importance', 5),
                'topics': result.get('related_topics', []),
                'implications': result.get('legal_implications', ''),
                'actions': result.get('actions', [])
            }
        except:
            return {
                'analysis': 'No analysis available',
                'rating': 5,
                'topics': [],
                'implications': 'None identified',
                'actions': []
            }
    
    async def get_advanced_news(self, limit: int = 30, category: str = None) -> Dict:
        """Get advanced news with videos and conference data"""
        
        # Fetch regular news
        news_articles = []
        for source_name, source_info in self.SOURCES.items():
            try:
                client = await self.get_client()
                response = await client.get(source_info['url'])
                response.raise_for_status()
                
                feed = feedparser.parse(response.text)
                
                for entry in feed.entries[:5]:
                    # Extract media
                    media_list = []
                    content_html = entry.get('content', [{}])[0].get('value', '')
                    if not content_html:
                        content_html = entry.get('summary', '')
                    
                    # Check for videos
                    video_urls = re.findall(r'(https?://[^\s]+\.(?:mp4|webm|mov)|youtube\.com/watch\?v=[^\s]+|youtu\.be/[^\s]+)', content_html)
                    for vid_url in video_urls[:2]:
                        video_data = await self.extract_video_id(vid_url)
                        if video_data:
                            media_list.append({
                                'type': 'video',
                                'url': vid_url,
                                'embed': video_data.get('embed', ''),
                                'platform': video_data.get('platform', ''),
                                'title': entry.get('title', '')
                            })
                    
                    # Check for images
                    img_urls = re.findall(r'<img[^>]+src="([^">]+)"', content_html)
                    for img_url in img_urls[:2]:
                        if img_url.startswith('http'):
                            media_list.append({
                                'type': 'image',
                                'url': img_url,
                                'title': entry.get('title', '')
                            })
                    
                    # Parse date
                    pub_date = datetime.now()
                    try:
                        if entry.get('published'):
                            pub_date = datetime.fromisoformat(entry['published'].replace('Z', '+00:00'))
                    except:
                        pass
                    
                    # Agent analysis
                    agent_analysis = await self.analyze_article_with_agent(
                        entry.get('title', ''),
                        entry.get('summary', ''),
                        media_list
                    )
                    
                    article = {
                        'id': f"{source_name}_{hash(entry.get('link', ''))}",
                        'title': entry.get('title', ''),
                        'source': source_info['source'],
                        'source_icon': source_info.get('icon', '📰'),
                        'url': entry.get('link', ''),
                        'summary': entry.get('summary', '')[:400],
                        'content': content_html[:1000],
                        'category': agent_analysis.get('topics', ['general'])[0] if agent_analysis.get('topics') else 'general',
                        'published_date': pub_date.isoformat(),
                        'author': entry.get('author', ''),
                        'media': media_list,
                        'agent_analysis': agent_analysis.get('analysis', ''),
                        'agent_rating': agent_analysis.get('rating', 5),
                        'agent_implications': agent_analysis.get('implications', ''),
                        'agent_actions': agent_analysis.get('actions', []),
                        'has_video': len(media_list) > 0
                    }
                    
                    if category is None or category == article['category']:
                        news_articles.append(article)
                        
            except Exception as e:
                logger.warning(f"Error fetching {source_name}: {e}")
        
        # Fetch conference videos
        conference_videos = await self.fetch_conference_videos()
        
        # Combine and sort
        all_items = news_articles + conference_videos
        all_items.sort(key=lambda x: x.get('published_date', ''), reverse=True)
        
        # Limit results
        result_items = all_items[:limit]
        
        response = {
            'articles': result_items,
            'total': len(result_items),
            'has_videos': len([a for a in result_items if a.get('has_video') or a.get('platform')]),
            'has_conferences': len([a for a in result_items if a.get('category') == 'conference']),
            'last_update': datetime.now().isoformat(),
            'categories': self._get_category_counts(result_items)
        }
        
        return response
    
    def _get_category_counts(self, items: List[Dict]) -> Dict:
        """Get category counts"""
        categories = {}
        for item in items:
            cat = item.get('category', 'general')
            categories[cat] = categories.get(cat, 0) + 1
        return categories


_news_aggregator: Optional[AdvancedNewsAggregator] = None

def get_news_aggregator() -> AdvancedNewsAggregator:
    global _news_aggregator
    if _news_aggregator is None:
        _news_aggregator = AdvancedNewsAggregator()
    return _news_aggregator