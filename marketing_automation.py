# marketing_automation.py
"""
Complete Marketing Automation Suite for Unknown Verdict
Includes: LinkedIn, Twitter, Blog, Email, Lead Nurturing
"""

import os
import json
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("marketing_auto")

# ─── SOCIAL MEDIA CONTENT GENERATORS ──────────────────────────────

@dataclass
class SocialContent:
    """Social media content structure"""
    text: str
    hashtags: List[str]
    images: Optional[List[str]] = None
    link: Optional[str] = None
    platform: str = "linkedin"
    created_at: datetime = field(default_factory=datetime.now)

class ContentGenerator:
    """AI-powered content generation for marketing"""
    
    def __init__(self, llm_caller):
        self.llm = llm_caller
        
    async def generate_linkedin_post(self, topic: str, style: str = "professional") -> SocialContent:
        """Generate LinkedIn post"""
        prompt = f"""
        Write a professional LinkedIn post about {topic}.
        Style: {style}
        
        Requirements:
        - Catchy opening
        - 2-3 key insights
        - Personal or professional angle
        - Call to action
        - 3 relevant hashtags
        - 150-200 words
        """
        
        response = await self.llm("You are a professional content writer.", prompt)
        
        # Extract hashtags
        hashtags = re.findall(r'#\w+', response)
        
        # Clean text (remove hashtags from body)
        text = re.sub(r'#\w+', '', response).strip()
        
        return SocialContent(
            text=text,
            hashtags=hashtags,
            platform="linkedin"
        )
    
    async def generate_twitter_thread(self, topic: str, num_tweets: int = 5) -> List[SocialContent]:
        """Generate Twitter thread"""
        prompt = f"""
        Create a Twitter thread about {topic}.
        Number of tweets: {num_tweets}
        
        Each tweet should:
        - Be under 280 characters
        - Have a key insight
        - Be numbered (1/{num_tweets}, 2/{num_tweets}, etc.)
        - End with #thread
        """
        
        response = await self.llm("You are a Twitter content expert.", prompt)
        
        tweets = []
        for line in response.strip().split('\n'):
            if line.strip() and not line.startswith('#'):
                tweets.append(SocialContent(
                    text=line.strip(),
                    hashtags=['thread', 'AI', 'LegalTech'],
                    platform="twitter"
                ))
        
        return tweets
    
    async def generate_blog_post(self, topic: str, length: str = "medium") -> Dict:
        """Generate blog post"""
        word_count = {"short": 500, "medium": 1000, "long": 2000}
        
        prompt = f"""
        Write a blog post about {topic}.
        Length: {word_count.get(length, 1000)} words
        
        Structure:
        - SEO-friendly title
        - Introduction
        - 3-5 main points with subheadings
        - Conclusion
        - Keywords: legal tech, AI, {topic.lower()}
        """
        
        response = await self.llm("You are a legal tech blog writer.", prompt)
        
        # Extract title (first line)
        lines = response.strip().split('\n')
        title = lines[0] if lines else f"Understanding {topic}"
        content = '\n'.join(lines[1:]) if len(lines) > 1 else response
        
        return {
            "title": title,
            "content": content,
            "word_count": len(content.split()),
            "topic": topic
        }

# ─── SOCIAL MEDIA POSTING ──────────────────────────────────────────

class SocialMediaPoster:
    """Post content to social media platforms"""
    
    def __init__(self):
        self.linkedin_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.linkedin_user_id = os.getenv("LINKEDIN_USER_ID")
        self.twitter_api_key = os.getenv("TWITTER_API_KEY")
        self.twitter_api_secret = os.getenv("TWITTER_API_SECRET")
        self.twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        
    async def post_to_linkedin(self, content: SocialContent) -> bool:
        """Post to LinkedIn"""
        if not self.linkedin_token:
            logger.warning("LinkedIn token not configured")
            return False
        
        # Prepare message with hashtags
        message = content.text
        if content.hashtags:
            message += f"\n\n{' '.join(content.hashtags)}"
        
        if content.link:
            message += f"\n\n{content.link}"
        
        # In production, use LinkedIn API
        logger.info(f"Posting to LinkedIn: {message[:100]}...")
        return True
    
    async def post_to_twitter(self, contents: List[SocialContent]) -> bool:
        """Post Twitter thread"""
        if not self.twitter_access_token:
            logger.warning("Twitter access token not configured")
            return False
        
        # Post each tweet in thread
        for content in contents:
            logger.info(f"Posting to Twitter: {content.text[:50]}...")
        
        return True
    
    async def post_to_blog(self, post: Dict) -> bool:
        """Post to blog"""
        os.makedirs("blog", exist_ok=True)
        
        filename = f"blog/{datetime.now().strftime('%Y%m%d')}_{post['title'].replace(' ', '_')[:30]}.md"
        
        with open(filename, "w") as f:
            f.write(f"# {post['title']}\n\n")
            f.write(f"*Published: {datetime.now().strftime('%B %d, %Y')}*\n\n")
            f.write(post['content'])
        
        logger.info(f"Blog post saved: {filename}")
        return True

# ─── LEAD NURTURING ──────────────────────────────────────────────────

class LeadNurturing:
    """Lead nurturing automation"""
    
    def __init__(self, database):
        self.db = database
        
    async def capture_lead(self, email: str, source: str, data: Dict = None) -> Dict:
        """Capture lead from various sources"""
        # Check if lead exists
        existing = await self.db.fetch_one(
            "SELECT * FROM leads WHERE email = $1", email
        )
        
        if existing:
            # Update existing lead
            await self.db.execute(
                "UPDATE leads SET last_active = NOW(), source = $2 WHERE email = $1",
                email, source
            )
            return {"status": "updated", "email": email}
        
        # Create new lead
        await self.db.execute(
            "INSERT INTO leads (email, source, data, created_at) VALUES ($1, $2, $3, NOW())",
            email, source, json.dumps(data or {})
        )
        
        # Send welcome sequence
        await self.send_welcome_sequence(email)
        
        return {"status": "created", "email": email}
    
    async def send_welcome_sequence(self, email: str):
        """Send welcome email sequence"""
        emails = [
            {
                "subject": "Welcome to Unknown Verdict! 🏛️",
                "body": "Thank you for joining Unknown Verdict...",
                "delay_hours": 0
            },
            {
                "subject": "How Unknown Verdict Can Help You",
                "body": "Here are 5 ways Unknown Verdict can transform your legal work...",
                "delay_hours": 24
            },
            {
                "subject": "Exclusive: Free Legal Templates",
                "body": "As a thank you, here are 10 legal templates...",
                "delay_hours": 72
            }
        ]
        
        for email_data in emails:
            # In production, send actual email
            logger.info(f"Sending email to {email}: {email_data['subject']}")
            await asyncio.sleep(0.1)  # Simulate sending
    
    async def score_lead(self, email: str, activity: Dict) -> float:
        """Score lead based on activity"""
        score = 0
        actions = {
            "visited_website": 5,
            "viewed_pricing": 20,
            "started_free_trial": 30,
            "used_api": 10,
            "subscribed_newsletter": 15,
            "booked_demo": 50
        }
        
        for action, points in actions.items():
            if activity.get(action):
                score += points
        
        # Update lead score in database
        await self.db.execute(
            "UPDATE leads SET score = $1 WHERE email = $2",
            score, email
        )
        
        return score

# ─── MARKETING AUTOMATION PIPELINE ────────────────────────────────

class MarketingAutomation:
    """Main marketing automation pipeline"""
    
    def __init__(self, llm_caller, database):
        self.content_gen = ContentGenerator(llm_caller)
        self.social_poster = SocialMediaPoster()
        self.lead_nurturing = LeadNurturing(database)
        self.db = database
        
    async def run_daily_pipeline(self):
        """Run daily marketing automation tasks"""
        logger.info("📢 Running daily marketing pipeline...")
        
        # 1. Generate content
        topics = [
            "The Future of AI in Legal Practice",
            "How Edge AI Transforms Courtroom Proceedings",
            "AI-Powered Contract Review: Best Practices",
            "Legal Tech Trends 2026",
            "Constitutional AI: The New Standard"
        ]
        
        # Generate LinkedIn post
        topic = random.choice(topics)
        linkedin_post = await self.content_gen.generate_linkedin_post(topic)
        await self.social_poster.post_to_linkedin(linkedin_post)
        
        # Generate Twitter thread
        twitter_thread = await self.content_gen.generate_twitter_thread(topic)
        await self.social_poster.post_to_twitter(twitter_thread)
        
        # Generate blog post
        blog_post = await self.content_gen.generate_blog_post(topic, "medium")
        await self.social_poster.post_to_blog(blog_post)
        
        # 2. Nurture leads
        leads = await self.db.fetch_all(
            "SELECT email FROM leads WHERE created_at > NOW() - INTERVAL '7 days'"
        )
        for lead in leads:
            await self.lead_nurturing.send_welcome_sequence(lead['email'])
        
        # 3. Update analytics
        await self.update_analytics()
        
        logger.info("✅ Daily marketing pipeline complete")
    
    async def update_analytics(self):
        """Update marketing analytics"""
        # Get stats
        total_leads = await self.db.fetch_val("SELECT COUNT(*) FROM leads")
        active_leads = await self.db.fetch_val(
            "SELECT COUNT(*) FROM leads WHERE created_at > NOW() - INTERVAL '30 days'"
        )
        
        # Save analytics
        await self.db.execute(
            """
            INSERT INTO marketing_analytics (date, total_leads, active_leads)
            VALUES (NOW(), $1, $2)
            """,
            total_leads, active_leads
        )

# ─── SCHEDULED TASKS ────────────────────────────────────────────────

async def schedule_marketing_tasks(scheduler):
    """Schedule marketing automation tasks"""
    
    marketing = MarketingAutomation(call_llm, database)
    
    # Daily marketing pipeline at 8 AM IST
    scheduler.add_job(
        marketing.run_daily_pipeline,
        CronTrigger(hour=8, minute=0, timezone="Asia/Kolkata"),
        id="daily_marketing"
    )
    
    # Weekly blog post at 10 AM IST on Monday
    scheduler.add_job(
        marketing.social_poster.post_to_blog,
        CronTrigger(day_of_week=0, hour=10, minute=0, timezone="Asia/Kolkata"),
        id="weekly_blog"
    )
    
    logger.info("📅 Marketing automation scheduled")