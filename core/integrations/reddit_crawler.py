"""
core/integrations/reddit_crawler.py - Reddit Integration (Working Version)
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Graceful import - works even if asyncpraw is missing
try:
    import asyncpraw
    HAS_REDDIT = True
except ImportError:
    HAS_REDDIT = False
    logger.warning("⚠️ asyncpraw not found. Reddit features will be disabled.")


class RedditCrawler:
    """Reddit crawler with graceful fallback"""
    
    SUBREDDITS = [
        'legaladvice', 'law', 'lawyers', 'legal', 'privacy',
        'gdpr', 'cybersecurity', 'dataprotection', 'compliance',
        'regulatory', 'finance', 'banking', 'insurance',
        'corporate', 'business', 'startups', 'entrepreneur',
        'AI', 'MachineLearning', 'ArtificialIntelligence',
        'india', 'IndianLaw', 'supremecourt'
    ]
    
    def __init__(self):
        self.reddit = None
        self._initialized = False
    
    def _init_reddit(self):
        """Initialize Reddit client - lazy initialization"""
        if self._initialized:
            return
        
        self._initialized = True
        if not HAS_REDDIT:
            return
        
        try:
            import os
            client_id = os.getenv("REDDIT_CLIENT_ID", "")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
            user_agent = os.getenv("REDDIT_USER_AGENT", "UnknownVerdict/1.0")
            
            if client_id and client_secret:
                self.reddit = asyncpraw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=user_agent
                )
                logger.info("✅ Reddit client initialized")
            else:
                logger.warning("⚠️ Reddit credentials not configured")
        except Exception as e:
            logger.error(f"❌ Reddit init error: {e}")
    
    async def get_hot_posts(self, subreddit: str, limit: int = 25) -> List[Dict]:
        """Get hot posts from a subreddit"""
        self._init_reddit()
        
        if not HAS_REDDIT or not self.reddit:
            return []
        
        try:
            sub = await self.reddit.subreddit(subreddit)
            posts = []
            async for post in sub.hot(limit=limit):
                posts.append({
                    'id': post.id,
                    'title': post.title,
                    'selftext': post.selftext[:500] if post.selftext else '',
                    'score': post.score,
                    'num_comments': post.num_comments,
                    'created_utc': datetime.fromtimestamp(post.created_utc).isoformat(),
                    'url': f"https://reddit.com{post.permalink}",
                    'subreddit': subreddit,
                    'author': str(post.author) if post.author else '[deleted]'
                })
            return posts
        except Exception as e:
            logger.error(f"Error fetching r/{subreddit}: {e}")
            return []
    
    async def search_legal(self, query: str, limit: int = 50) -> List[Dict]:
        """Search across legal subreddits"""
        self._init_reddit()
        
        if not HAS_REDDIT or not self.reddit:
            return []
        
        results = []
        for subreddit in self.SUBREDDITS[:5]:
            try:
                sub = await self.reddit.subreddit(subreddit)
                async for post in sub.search(query, limit=10):
                    results.append({
                        'id': post.id,
                        'title': post.title,
                        'subreddit': subreddit,
                        'score': post.score,
                        'url': f"https://reddit.com{post.permalink}",
                        'created_utc': datetime.fromtimestamp(post.created_utc).isoformat()
                    })
            except:
                pass
        
        return sorted(results, key=lambda x: x['score'], reverse=True)[:limit]
    
    async def get_trending_legal_topics(self) -> List[Dict]:
        """Get trending legal topics"""
        self._init_reddit()
        
        if not HAS_REDDIT or not self.reddit:
            return []
        
        trending = []
        for subreddit in self.SUBREDDITS[:10]:
            try:
                sub = await self.reddit.subreddit(subreddit)
                async for post in sub.hot(limit=5):
                    if post.score > 50:
                        trending.append({
                            'title': post.title,
                            'subreddit': subreddit,
                            'score': post.score,
                            'url': f"https://reddit.com{post.permalink}",
                            'created_utc': datetime.fromtimestamp(post.created_utc).isoformat()
                        })
            except:
                pass
        
        return sorted(trending, key=lambda x: x['score'], reverse=True)[:20]
    
    async def store_reddit_data(self, posts: List[Dict]) -> int:
        """Store Reddit data in database"""
        return len(posts)  # Stub for now
    
    async def generate_reddit_insights(self) -> Dict:
        """Generate insights from Reddit data"""
        return {
            'status': 'disabled',
            'message': 'Reddit integration requires asyncpraw. Run: pip install asyncpraw'
        }


reddit_crawler = RedditCrawler()