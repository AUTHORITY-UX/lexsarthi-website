"""
core/integrations/reddit_crawler.py - Reddit Data Factory Integration
"""

import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import asyncpraw
import httpx

from core.db import db
from core.llm import LLMMessage, get_router

logger = logging.getLogger(__name__)


class RedditCrawler:
    """Reddit data crawler for legal intelligence"""
    
    SUBREDDITS = [
        'legaladvice', 'law', 'lawyers', 'legal', 'privacy',
        'gdpr', 'europrivacy', 'europeanparliament',
        'cybersecurity', 'dataprotection', 'compliance',
        'regulatory', 'finance', 'banking', 'insurance',
        'corporate', 'business', 'startups', 'entrepreneur',
        'AI', 'MachineLearning', 'ArtificialIntelligence',
        'Ethics', 'philosophy', 'politics', 'worldnews',
        'technology', 'science', 'healthcare', 'medicine'
    ]
    
    def __init__(self):
        self.router = get_router()
        self.client = None
        self.reddit = None
        self._initialize_reddit()
    
    def _initialize_reddit(self):
        """Initialize Reddit API client"""
        try:
            import os
            self.reddit = asyncpraw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID", ""),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
                user_agent=os.getenv("REDDIT_USER_AGENT", "Unknown Verdict/1.0")
            )
        except Exception as e:
            logger.error(f"Reddit init error: {e}")
    
    async def crawl_subreddit(self, subreddit: str, limit: int = 100) -> List[Dict]:
        """Crawl a subreddit for legal intelligence"""
        posts = []
        
        try:
            sub = await self.reddit.subreddit(subreddit)
            
            async for post in sub.hot(limit=limit):
                # Extract post data
                post_data = {
                    'id': post.id,
                    'title': post.title,
                    'selftext': post.selftext[:2000],
                    'score': post.score,
                    'upvote_ratio': post.upvote_ratio,
                    'num_comments': post.num_comments,
                    'created_utc': datetime.fromtimestamp(post.created_utc),
                    'url': f"https://reddit.com{post.permalink}",
                    'subreddit': subreddit,
                    'author': str(post.author),
                    'over_18': post.over_18,
                    'spoiler': post.spoiler
                }
                
                # Get top comments
                post_data['comments'] = await self._get_top_comments(post)
                
                # Analyze for legal relevance
                analysis = await self._analyze_post(post_data)
                post_data['analysis'] = analysis
                
                posts.append(post_data)
                
        except Exception as e:
            logger.error(f"Error crawling r/{subreddit}: {e}")
        
        return posts
    
    async def _get_top_comments(self, post, limit: int = 10) -> List[Dict]:
        """Get top comments from a post"""
        comments = []
        try:
            await post.comments.replace_more(limit=0)
            for comment in post.comments[:limit]:
                comments.append({
                    'body': comment.body[:1000],
                    'score': comment.score,
                    'author': str(comment.author),
                    'created_utc': datetime.fromtimestamp(comment.created_utc)
                })
        except:
            pass
        return comments
    
    async def _analyze_post(self, post: Dict) -> Dict:
        """Analyze post for legal intelligence"""
        messages = [
            LLMMessage(role="system", content="""Analyze this Reddit post for legal intelligence.
            Return JSON with:
            - legal_relevance: 0-1
            - category: [compliance, privacy, corporate, regulation, AI]
            - sentiment: [positive, negative, neutral, mixed]
            - key_topics: list of 3-5 topics
            - legal_risk: 0-1
            - suggested_action: string"""),
            LLMMessage(role="user", content=f"""
            Title: {post.get('title', '')}
            Content: {post.get('selftext', '')[:1000]}
            Comments: {len(post.get('comments', []))}
            Subreddit: {post.get('subreddit', '')}
            """)
        ]
        
        try:
            response = await self.router.chat(messages, complexity="medium")
            return json.loads(response.content)
        except:
            return {
                'legal_relevance': 0.5,
                'category': 'general',
                'sentiment': 'neutral',
                'key_topics': ['uncategorized'],
                'legal_risk': 0.3,
                'suggested_action': 'monitor'
            }
    
    async def search_legal_topics(self, query: str, limit: int = 50) -> List[Dict]:
        """Search Reddit for legal topics"""
        results = []
        
        try:
            async for post in self.reddit.subreddit('all').search(query, limit=limit):
                if post.subreddit.display_name.lower() in self.SUBREDDITS:
                    results.append({
                        'id': post.id,
                        'title': post.title,
                        'subreddit': post.subreddit.display_name,
                        'score': post.score,
                        'url': f"https://reddit.com{post.permalink}",
                        'created_utc': datetime.fromtimestamp(post.created_utc)
                    })
        except:
            pass
        
        return results
    
    async def get_trending_legal_topics(self) -> List[Dict]:
        """Get trending legal topics from Reddit"""
        topics = []
        
        for subreddit in self.SUBREDDITS[:10]:
            try:
                sub = await self.reddit.subreddit(subreddit)
                async for post in sub.hot(limit=5):
                    if post.score > 100:  # Only high engagement posts
                        topics.append({
                            'title': post.title,
                            'subreddit': subreddit,
                            'score': post.score,
                            'url': f"https://reddit.com{post.permalink}",
                            'created_utc': datetime.fromtimestamp(post.created_utc)
                        })
            except:
                pass
        
        return sorted(topics, key=lambda x: x['score'], reverse=True)[:20]
    
    async def store_reddit_data(self, posts: List[Dict]) -> int:
        """Store Reddit data in database"""
        count = 0
        
        for post in posts:
            try:
                await db.execute("""
                    INSERT INTO reddit_data 
                    (post_id, title, content, subreddit, score, url, 
                     created_at, analysis, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (post_id) DO UPDATE SET
                    score = $5, analysis = $8, updated_at = NOW()
                """,
                    post.get('id'),
                    post.get('title')[:500],
                    post.get('selftext', '')[:5000],
                    post.get('subreddit'),
                    post.get('score', 0),
                    post.get('url'),
                    post.get('created_utc'),
                    json.dumps(post.get('analysis', {})),
                    json.dumps({
                        'comments_count': len(post.get('comments', [])),
                        'upvote_ratio': post.get('upvote_ratio', 0)
                    })
                )
                count += 1
            except Exception as e:
                logger.error(f"Error storing post {post.get('id')}: {e}")
        
        return count
    
    async def generate_reddit_insights(self) -> Dict:
        """Generate insights from Reddit data"""
        try:
            # Get recent posts
            rows = await db.fetchall("""
                SELECT * FROM reddit_data 
                ORDER BY created_at DESC 
                LIMIT 100
            """)
            
            if not rows:
                return {'error': 'No Reddit data available'}
            
            # Generate insights using AI
            posts_summary = "\n".join([
                f"Title: {r['title']}\nSubreddit: {r['subreddit']}\nScore: {r['score']}"
                for r in rows[:20]
            ])
            
            messages = [
                LLMMessage(role="system", content="""Generate legal intelligence insights from these Reddit posts.
                Return JSON with:
                - top_legal_topics: list of 5 topics with frequency
                - sentiment_trend: overall trend
                - emerging_risks: list of 3-5 risks
                - compliance_alerts: list of 3-5 alerts
                - recommendation: string"""),
                LLMMessage(role="user", content=posts_summary)
            ]
            
            response = await self.router.chat(messages, complexity="complex")
            return json.loads(response.content)
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {'error': str(e)}

reddit_crawler = RedditCrawler()