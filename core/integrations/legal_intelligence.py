"""
Legal Intelligence System - No Reddit API Required
Uses web scraping, RSS feeds, and alternative legal sources
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import feedparser
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging
import json
import re
from urllib.parse import urlparse, quote_plus
import random
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class LegalSource:
    """Legal content source"""
    title: str
    url: str
    type: str  # 'rss', 'web', 'news', 'blog'
    category: str  # 'case_law', 'legislation', 'legal_news', 'analysis'
    jurisdiction: str
    last_fetch: Optional[datetime] = None
    active: bool = True

@dataclass
class LegalContent:
    """Legal content from any source"""
    id: str
    title: str
    text: str
    source: str
    url: str
    published: datetime
    authors: List[str]
    categories: List[str]  # Legal topics
    jurisdiction: str
    legal_relevance: float  # 0-1
    entities: List[Dict]  # Legal entities with confidence
    summary: Optional[str] = None
    sentiment: Optional[float] = None  # -1 to 1
    citations: List[str] = None  # Legal citations
    court: Optional[str] = None
    case_number: Optional[str] = None
    
    def __post_init__(self):
        if self.citations is None:
            self.citations = []

class LegalIntelligence:
    """
    Comprehensive legal intelligence system
    Scrapes legal content from multiple sources without Reddit API
    """
    
    # LEGAL RSS FEEDS (No API needed)
    LEGAL_RSS_FEEDS = [
        # India
        {"url": "https://www.livelaw.in/rss", "jurisdiction": "India", "category": "legal_news"},
        {"url": "https://www.barandbench.com/rss", "jurisdiction": "India", "category": "legal_news"},
        {"url": "https://www.scconline.com/blog/feed", "jurisdiction": "India", "category": "case_law"},
        {"url": "https://indiankanoon.org/feeds", "jurisdiction": "India", "category": "case_law"},
        
        # US
        {"url": "https://www.scotusblog.com/feed", "jurisdiction": "US", "category": "case_law"},
        {"url": "https://www.law.cornell.edu/wex/feed", "jurisdiction": "US", "category": "legal_reference"},
        {"url": "https://www.abajournal.com/rss", "jurisdiction": "US", "category": "legal_news"},
        {"url": "https://www.law360.com/rss", "jurisdiction": "US", "category": "legal_news"},
        {"url": "https://www.justia.com/blogs/feed", "jurisdiction": "US", "category": "legal_blogs"},
        
        # UK
        {"url": "https://www.lawgazette.co.uk/rss", "jurisdiction": "UK", "category": "legal_news"},
        {"url": "https://www.bailii.org/feeds", "jurisdiction": "UK", "category": "case_law"},
        {"url": "https://ukhumanrightsblog.com/feed", "jurisdiction": "UK", "category": "human_rights"},
        
        # EU
        {"url": "https://curia.europa.eu/feeds", "jurisdiction": "EU", "category": "case_law"},
        {"url": "https://www.europeanlawblog.eu/feed", "jurisdiction": "EU", "category": "legal_analysis"},
        
        # International
        {"url": "https://www.icj-cij.org/en/feeds", "jurisdiction": "International", "category": "case_law"},
        {"url": "https://www.un.org/en/feeds", "jurisdiction": "International", "category": "legal_news"},
    ]
    
    # LEGAL WEBSITES TO SCRAPE (No API)
    LEGAL_WEBSITES = [
        {"url": "https://www.livelaw.in", "jurisdiction": "India", "category": "legal_news"},
        {"url": "https://www.barandbench.com", "jurisdiction": "India", "category": "legal_news"},
        {"url": "https://www.scotusblog.com", "jurisdiction": "US", "category": "case_law"},
        {"url": "https://www.law.com", "jurisdiction": "US", "category": "legal_news"},
        {"url": "https://www.lawgazette.co.uk", "jurisdiction": "UK", "category": "legal_news"},
    ]
    
    # LEGAL SUBREDDITS (Scraped via old.reddit.com - no API)
    LEGAL_SUBREDDITS = [
        'legaladvice', 'law', 'lawsuit', 'legal', 'lawyers',
        'legaltech', 'scotus', 'supremecourt', 'eulaw',
        'LegalAdviceIndia', 'uklaw', 'auslaw'
    ]
    
    # LEGAL KEYWORDS FOR RELEVANCE
    LEGAL_KEYWORDS = [
        'lawsuit', 'court', 'judge', 'attorney', 'lawyer', 'legal',
        'defendant', 'plaintiff', 'appeal', 'verdict', 'trial',
        'evidence', 'contract', 'breach', 'negligence', 'defamation',
        'tort', 'intellectual property', 'copyright', 'patent',
        'trademark', 'employment', 'discrimination', 'harassment',
        'landlord', 'tenant', 'eviction', 'bankruptcy',
        'inheritance', 'custody', 'divorce', 'immigration',
        'criminal', 'felony', 'misdemeanor', 'arrest', 'bail',
        'sentence', 'probation', 'parole', 'regulatory',
        'compliance', 'consumer protection', 'antitrust',
        'arbitration', 'mediation', 'due diligence', 'liability',
        'indemnity', 'warranty', 'force majeure'
    ]
    
    def __init__(self):
        self.sources = []
        self.cache = {}
        self.stats = defaultdict(int)
        self.session = None
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15'
        ]
        
    async def initialize(self):
        """Initialize HTTP session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("✅ Legal Intelligence system initialized")
        return True
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Closed Legal Intelligence session")
    
    def _get_headers(self) -> Dict:
        """Get random headers for requests"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    async def fetch_rss_feeds(self, limit: int = 50) -> List[LegalContent]:
        """Fetch legal content from RSS feeds"""
        results = []
        
        for feed_info in self.LEGAL_RSS_FEEDS:
            try:
                async with self.session.get(feed_info['url'], headers=self._get_headers()) as response:
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        
                        for entry in feed.entries[:limit]:
                            # Extract content
                            text = self._extract_text_from_entry(entry)
                            
                            # Calculate legal relevance
                            relevance = self._calculate_legal_relevance(text)
                            
                            if relevance > 0.3:  # Only keep relevant content
                                legal_content = LegalContent(
                                    id=hashlib.md5(entry.link.encode()).hexdigest(),
                                    title=entry.title,
                                    text=text,
                                    source=feed_info['url'],
                                    url=entry.link,
                                    published=datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.now(),
                                    authors=self._extract_authors(entry),
                                    categories=self._extract_legal_categories(text),
                                    jurisdiction=feed_info['jurisdiction'],
                                    legal_relevance=relevance,
                                    entities=self._extract_legal_entities(text),
                                    summary=self._generate_summary(text),
                                    sentiment=await self._analyze_sentiment(text),
                                    citations=self._extract_legal_citations(text)
                                )
                                results.append(legal_content)
                                self.stats[f"rss_{feed_info['jurisdiction']}"] += 1
                                
                        logger.info(f"✅ Fetched {len(feed.entries)} entries from {feed_info['url']}")
                        
            except Exception as e:
                logger.error(f"❌ Error fetching RSS feed {feed_info['url']}: {e}")
                
            await asyncio.sleep(0.5)  # Rate limiting
            
        return results
    
    async def scrape_legal_websites(self) -> List[LegalContent]:
        """Scrape legal websites for content"""
        results = []
        
        for site in self.LEGAL_WEBSITES:
            try:
                async with self.session.get(site['url'], headers=self._get_headers()) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extract articles
                        articles = self._extract_articles(soup, site['url'])
                        
                        for article in articles[:10]:  # Limit per site
                            relevance = self._calculate_legal_relevance(article['text'])
                            
                            if relevance > 0.3:
                                legal_content = LegalContent(
                                    id=hashlib.md5(article['url'].encode()).hexdigest(),
                                    title=article['title'],
                                    text=article['text'],
                                    source=site['url'],
                                    url=article['url'],
                                    published=article.get('published', datetime.now()),
                                    authors=article.get('authors', []),
                                    categories=self._extract_legal_categories(article['text']),
                                    jurisdiction=site['jurisdiction'],
                                    legal_relevance=relevance,
                                    entities=self._extract_legal_entities(article['text']),
                                    summary=self._generate_summary(article['text']),
                                    sentiment=await self._analyze_sentiment(article['text']),
                                    citations=self._extract_legal_citations(article['text'])
                                )
                                results.append(legal_content)
                                self.stats[f"scrape_{site['jurisdiction']}"] += 1
                                
                        logger.info(f"✅ Scraped {len(articles)} articles from {site['url']}")
                        
            except Exception as e:
                logger.error(f"❌ Error scraping {site['url']}: {e}")
                
            await asyncio.sleep(1)  # Rate limiting
            
        return results
    
    async def crawl_legal_subreddits(self) -> List[LegalContent]:
        """Crawl legal subreddits using old.reddit.com (no API)"""
        results = []
        
        for subreddit in self.LEGAL_SUBREDDITS:
            try:
                url = f"https://old.reddit.com/r/{subreddit}/.json"
                async with self.session.get(url, headers=self._get_headers()) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for post in data.get('data', {}).get('children', []):
                            post_data = post.get('data', {})
                            text = f"{post_data.get('title', '')} {post_data.get('selftext', '')}"
                            
                            relevance = self._calculate_legal_relevance(text)
                            
                            if relevance > 0.3:
                                legal_content = LegalContent(
                                    id=post_data.get('id'),
                                    title=post_data.get('title'),
                                    text=post_data.get('selftext', ''),
                                    source=f"r/{subreddit}",
                                    url=f"https://reddit.com{post_data.get('permalink')}",
                                    published=datetime.fromtimestamp(post_data.get('created_utc', 0)),
                                    authors=[post_data.get('author', 'deleted')],
                                    categories=self._extract_legal_categories(text),
                                    jurisdiction=self._guess_jurisdiction(text),
                                    legal_relevance=relevance,
                                    entities=self._extract_legal_entities(text),
                                    summary=self._generate_summary(text),
                                    sentiment=await self._analyze_sentiment(text),
                                    citations=self._extract_legal_citations(text)
                                )
                                results.append(legal_content)
                                self.stats[f"reddit_{subreddit}"] += 1
                                
                        logger.info(f"✅ Crawled r/{subreddit} - {len(data.get('data', {}).get('children', []))} posts")
                        
            except Exception as e:
                logger.error(f"❌ Error crawling r/{subreddit}: {e}")
                
            await asyncio.sleep(1.5)  # Rate limiting (respect Reddit)
            
        return results
    
    async def google_legal_news(self, query: str = "legal news", limit: int = 20) -> List[LegalContent]:
        """Fetch legal news using Google News RSS"""
        results = []
        
        try:
            # Google News RSS (no API key needed)
            search_query = quote_plus(query)
            url = f"https://news.google.com/rss/search?q={search_query}+law+court&hl=en-US&gl=US&ceid=US:en"
            
            async with self.session.get(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    content = await response.text()
                    feed = feedparser.parse(content)
                    
                    for entry in feed.entries[:limit]:
                        text = f"{entry.title} {self._extract_text_from_entry(entry)}"
                        
                        relevance = self._calculate_legal_relevance(text)
                        
                        if relevance > 0.3:
                            legal_content = LegalContent(
                                id=hashlib.md5(entry.link.encode()).hexdigest(),
                                title=entry.title,
                                text=self._extract_text_from_entry(entry),
                                source="Google News",
                                url=entry.link,
                                published=datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else datetime.now(),
                                authors=[entry.get('author', 'Unknown')],
                                categories=self._extract_legal_categories(text),
                                jurisdiction="International",
                                legal_relevance=relevance,
                                entities=self._extract_legal_entities(text),
                                summary=self._generate_summary(text),
                                sentiment=await self._analyze_sentiment(text),
                                citations=self._extract_legal_citations(text)
                            )
                            results.append(legal_content)
                            self.stats["google_news"] += 1
                            
                    logger.info(f"✅ Fetched {len(results)} legal news from Google")
                    
        except Exception as e:
            logger.error(f"❌ Error fetching Google News: {e}")
            
        return results
    
    async def scrape_legal_forums(self) -> List[LegalContent]:
        """Scrape legal forums and discussion boards"""
        results = []
        
        # Legal forums to scrape (no API)
        forums = [
            {"name": "Law Stack Exchange", "url": "https://law.stackexchange.com/questions?sort=active", "jurisdiction": "International"},
            {"name": "Avvo", "url": "https://www.avvo.com/questions/", "jurisdiction": "US"},
            {"name": "Justia Ask a Lawyer", "url": "https://answers.justia.com/", "jurisdiction": "US"},
            {"name": "Lawyers.com", "url": "https://www.lawyers.com/legal-info/legal-questions.html", "jurisdiction": "US"},
            {"name": "Legally India", "url": "https://www.legallyindia.com/", "jurisdiction": "India"},
        ]
        
        for forum in forums:
            try:
                async with self.session.get(forum['url'], headers=self._get_headers()) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extract questions/threads
                        questions = self._extract_forum_questions(soup, forum['url'])
                        
                        for question in questions[:10]:
                            relevance = self._calculate_legal_relevance(question['text'])
                            
                            if relevance > 0.3:
                                legal_content = LegalContent(
                                    id=hashlib.md5(question['url'].encode()).hexdigest(),
                                    title=question['title'],
                                    text=question['text'],
                                    source=forum['name'],
                                    url=question['url'],
                                    published=question.get('date', datetime.now()),
                                    authors=[question.get('author', 'Anonymous')],
                                    categories=self._extract_legal_categories(question['text']),
                                    jurisdiction=forum['jurisdiction'],
                                    legal_relevance=relevance,
                                    entities=self._extract_legal_entities(question['text']),
                                    summary=self._generate_summary(question['text']),
                                    sentiment=await self._analyze_sentiment(question['text']),
                                    citations=self._extract_legal_citations(question['text'])
                                )
                                results.append(legal_content)
                                self.stats[f"forum_{forum['name']}"] += 1
                                
                        logger.info(f"✅ Scraped forum: {forum['name']}")
                        
            except Exception as e:
                logger.error(f"❌ Error scraping forum {forum['name']}: {e}")
                
            await asyncio.sleep(1)
            
        return results
    
    def _extract_text_from_entry(self, entry) -> str:
        """Extract text from RSS entry"""
        text = ""
        
        if hasattr(entry, 'description'):
            text += entry.description
        if hasattr(entry, 'summary'):
            text += entry.summary
        if hasattr(entry, 'content'):
            for content in entry.content:
                text += content.value
        
        # Clean HTML
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text()
    
    def _extract_articles(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract articles from HTML"""
        articles = []
        
        # Common article selectors
        selectors = ['article', '.article', '.post', '.blog-post', '.entry', '.story']
        
        for selector in selectors:
            for element in soup.select(selector):
                try:
                    # Find title
                    title_elem = element.find(['h1', 'h2', 'h3', '.title', '.headline'])
                    title = title_elem.get_text().strip() if title_elem else "Untitled"
                    
                    # Find content
                    content_elem = element.find(['p', '.content', '.body', '.excerpt'])
                    text = content_elem.get_text().strip() if content_elem else ""
                    
                    # Find link
                    link_elem = element.find('a')
                    link = link_elem.get('href') if link_elem else base_url
                    
                    if text:
                        articles.append({
                            'title': title,
                            'text': text,
                            'url': link if link.startswith('http') else f"{base_url}{link}",
                            'published': datetime.now(),
                            'authors': []
                        })
                except Exception as e:
                    continue
                    
        return articles
    
    def _extract_forum_questions(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract questions from forum HTML"""
        questions = []
        
        # Common question selectors
        selectors = ['.question', '.post', '.thread', '.qa-item', '.forum-post']
        
        for selector in selectors:
            for element in soup.select(selector):
                try:
                    title_elem = element.find(['h2', 'h3', '.title', '.subject'])
                    title = title_elem.get_text().strip() if title_elem else "Question"
                    
                    text_elem = element.find(['p', '.body', '.content', '.text'])
                    text = text_elem.get_text().strip() if text_elem else ""
                    
                    author_elem = element.find(['.author', '.username', '.user'])
                    author = author_elem.get_text().strip() if author_elem else None
                    
                    if text or title:
                        questions.append({
                            'title': title,
                            'text': f"{title}\n{text}",
                            'url': base_url,
                            'author': author,
                            'date': datetime.now()
                        })
                except Exception as e:
                    continue
                    
        return questions
    
    def _calculate_legal_relevance(self, text: str) -> float:
        """Calculate legal relevance score (0-1)"""
        if not text:
            return 0.0
        
        text_lower = text.lower()
        
        # Count legal keyword matches
        matches = sum(1 for keyword in self.LEGAL_KEYWORDS if keyword.lower() in text_lower)
        
        # Check for legal citation patterns
        citation_patterns = [
            r'\d+\s+U\.S\.\s+\d+',  # US citations
            r'\d+\s+S\.C\.\s+\d+',  # Supreme Court
            r'[A-Z]+\s+v\.\s+[A-Z]+',  # Case names
            r'\[(\d{4})\]\s+\d+\s+[A-Z]+',  # UK citations
            r'AIR\s+\d{4}\s+[A-Z]+',  # Indian citations
            r'\((\d{4})\)\s+\d+\s+[A-Z]+',  # Various formats
        ]
        
        citation_score = 0
        for pattern in citation_patterns:
            if re.search(pattern, text):
                citation_score += 0.2
        
        # Calculate raw score
        raw_score = (matches / len(self.LEGAL_KEYWORDS)) + citation_score
        
        # Normalize and boost
        return min(raw_score * 5, 1.0)
    
    def _extract_legal_entities(self, text: str) -> List[Dict]:
        """Extract legal entities with confidence"""
        entities = []
        
        # Legal entity patterns
        patterns = {
            'court': [r'[A-Z][a-z]+ Court', r'Supreme Court', r'High Court', r'Circuit Court'],
            'judge': [r'Justice [A-Z][a-z]+', r'Judge [A-Z][a-z]+', r'Magistrate [A-Z][a-z]+'],
            'law': [r'[A-Z][a-z]+ Act', r'[A-Z][a-z]+ Amendment', r'Section \d+'],
            'case': [r'[A-Z]+\s+v\.\s+[A-Z]+', r'Case No\. \d+', r'Docket No\. \d+'],
            'party': [r'Plaintiff', r'Defendant', r'Appellant', r'Respondent'],
        }
        
        for entity_type, patterns_list in patterns.items():
            for pattern in patterns_list:
                matches = re.findall(pattern, text)
                for match in matches:
                    entities.append({
                        'text': match,
                        'type': entity_type,
                        'confidence': 0.7 + random.random() * 0.3  # Simulated confidence
                    })
        
        return entities
    
    def _extract_legal_categories(self, text: str) -> List[str]:
        """Extract legal categories/topics"""
        categories = []
        text_lower = text.lower()
        
        category_keywords = {
            'criminal': ['crime', 'criminal', 'arrest', 'jail', 'prosecution'],
            'civil': ['civil', 'lawsuit', 'defamation', 'negligence', 'liability'],
            'contract': ['contract', 'breach', 'agreement', 'terms', 'indemnity'],
            'family': ['divorce', 'custody', 'marriage', 'alimony', 'support'],
            'property': ['property', 'landlord', 'tenant', 'eviction', 'foreclosure'],
            'employment': ['employment', 'employee', 'discrimination', 'harassment'],
            'immigration': ['immigration', 'visa', 'citizenship', 'deportation'],
            'intellectual': ['patent', 'trademark', 'copyright', 'intellectual property'],
            'corporate': ['corporate', 'shareholder', 'bylaws', 'merger'],
            'constitutional': ['constitutional', 'fundamental rights', 'writ'],
            'tax': ['tax', 'income tax', 'gst', 'customs'],
            'environmental': ['environment', 'pollution', 'climate', 'conservation'],
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                categories.append(category)
        
        return categories
    
    def _extract_legal_citations(self, text: str) -> List[str]:
        """Extract legal citations from text"""
        citations = []
        
        # Citation patterns
        patterns = [
            r'\d+\s+U\.S\.\s+\d+',
            r'\d+\s+S\.C\.\s+\d+',
            r'[A-Z]+\s+v\.\s+[A-Z]+',
            r'\[(\d{4})\]\s+\d+\s+[A-Z]+',
            r'AIR\s+\d{4}\s+[A-Z]+',
            r'\((\d{4})\)\s+\d+\s+[A-Z]+',
            r'Section\s+\d+\s+of\s+[A-Za-z\s]+Act',
            r'Article\s+\d+\s+of\s+[A-Za-z\s]+',
            r'Rule\s+\d+\s+of\s+[A-Za-z\s]+',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            citations.extend(matches)
        
        return list(set(citations))
    
    def _extract_authors(self, entry) -> List[str]:
        """Extract authors from RSS entry"""
        authors = []
        
        if hasattr(entry, 'author'):
            authors.append(entry.author)
        if hasattr(entry, 'authors'):
            for author in entry.authors:
                if hasattr(author, 'name'):
                    authors.append(author.name)
        
        return authors
    
    def _generate_summary(self, text: str, max_length: int = 200) -> str:
        """Generate summary of text"""
        if not text:
            return ""
        
        # Simple summarization - get first few sentences
        sentences = re.split(r'[.!?]+', text)
        summary = ' '.join(sentences[:3])
        
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return summary
    
    async def _analyze_sentiment(self, text: str) -> Optional[float]:
        """Analyze sentiment of text"""
        if not text:
            return None
        
        try:
            # Simple sentiment analysis
            text_lower = text.lower()
            
            positive_words = ['good', 'great', 'excellent', 'positive', 'win', 'winning', 'success', 'favorable']
            negative_words = ['bad', 'terrible', 'negative', 'lose', 'losing', 'failure', 'unfair', 'adverse']
            
            pos_count = sum(1 for word in positive_words if word in text_lower)
            neg_count = sum(1 for word in negative_words if word in text_lower)
            
            if pos_count + neg_count > 0:
                return (pos_count - neg_count) / (pos_count + neg_count)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return None
    
    def _guess_jurisdiction(self, text: str) -> str:
        """Guess jurisdiction from text"""
        text_lower = text.lower()
        
        if 'india' in text_lower or 'supreme court of india' in text_lower:
            return 'India'
        elif 'united states' in text_lower or 'u.s.' in text_lower or 'supreme court' in text_lower:
            return 'US'
        elif 'uk' in text_lower or 'united kingdom' in text_lower or 'england' in text_lower:
            return 'UK'
        elif 'eu' in text_lower or 'european' in text_lower or 'europe' in text_lower:
            return 'EU'
        else:
            return 'International'
    
    async def get_legal_dashboard(self) -> Dict:
        """Get comprehensive legal intelligence dashboard"""
        # Fetch from all sources
        tasks = [
            self.fetch_rss_feeds(limit=20),
            self.scrape_legal_websites(),
            self.crawl_legal_subreddits(),
            self.google_legal_news(limit=15),
            self.scrape_legal_forums()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_content = []
        for result in results:
            if isinstance(result, list):
                all_content.extend(result)
            else:
                logger.error(f"Error in task: {result}")
        
        # Categorize
        categories = {
            'high_relevance': [c for c in all_content if c.legal_relevance > 0.7],
            'trending': sorted(all_content, key=lambda x: x.legal_relevance, reverse=True)[:10],
            'recent': sorted(all_content, key=lambda x: x.published, reverse=True)[:10],
            'by_jurisdiction': defaultdict(list),
            'by_category': defaultdict(list),
            'by_source': defaultdict(list)
        }
        
        for content in all_content:
            categories['by_jurisdiction'][content.jurisdiction].append(content)
            for cat in content.categories:
                categories['by_category'][cat].append(content)
            categories['by_source'][content.source].append(content)
        
        return {
            'total_content': len(all_content),
            'sources_fetched': len(self.LEGAL_RSS_FEEDS) + len(self.LEGAL_WEBSITES),
            'categories': {
                'high_relevance': len(categories['high_relevance']),
                'trending': len(categories['trending']),
                'recent': len(categories['recent']),
                'by_jurisdiction': {k: len(v) for k, v in categories['by_jurisdiction'].items()},
                'by_category': {k: len(v) for k, v in categories['by_category'].items()}
            },
            'top_content': [asdict(c) for c in categories['high_relevance'][:10]],
            'trending_content': [asdict(c) for c in categories['trending']],
            'recent_content': [asdict(c) for c in categories['recent']],
            'statistics': dict(self.stats),
            'timestamp': datetime.utcnow().isoformat()
        }

# Singleton instance
_intelligence = None

async def get_legal_intelligence() -> LegalIntelligence:
    """Get or create LegalIntelligence instance"""
    global _intelligence
    
    if _intelligence is None:
        _intelligence = LegalIntelligence()
        await _intelligence.initialize()
    
    return _intelligence

async def clear_intelligence_cache():
    """Clear cache"""
    global _intelligence
    if _intelligence:
        _intelligence.cache = {}
        _intelligence.stats = defaultdict(int)
        logger.info("🧹 Legal Intelligence cache cleared")