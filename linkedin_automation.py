# =============================================================================
# linkedin_automation.py – LinkedIn Automation Pipeline
# =============================================================================

import os
import json
import logging
from typing import Optional, Dict, List

import httpx

logger = logging.getLogger("unknown_verdict.linkedin")

class LinkedInAutomation:
    """
    LinkedIn automation for posting legal AI news and updates.
    """
    
    def __init__(self):
        self.token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.user_id = os.getenv("LINKEDIN_USER_ID")
        self.base_url = "https://api.linkedin.com/v2"
        
        # Fix URN format
        if self.user_id and self.user_id.startswith("urn:li:member:"):
            self.user_id = self.user_id.replace("urn:li:member:", "urn:li:person:")
            logger.info(f"✅ Fixed LinkedIn author URN: {self.user_id}")
    
    async def post(self, content: str) -> Dict:
        """
        Post content to LinkedIn.
        Returns: {"status": "success", "post_id": str} or {"status": "error", "error": str}
        """
        if not self.token:
            return {"status": "error", "error": "Missing LinkedIn access token"}
        
        if not self.user_id:
            return {"status": "error", "error": "Missing LinkedIn user ID"}
        
        url = f"{self.base_url}/ugcPosts"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        payload = {
            "author": self.user_id,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content[:3000]  # LinkedIn max 3000 chars
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code in [200, 201]:
                    post_id = response.headers.get("x-restli-id", "unknown")
                    logger.info(f"✅ Posted to LinkedIn successfully: {post_id}")
                    return {"status": "success", "post_id": post_id}
                else:
                    error_msg = f"LinkedIn API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {"status": "error", "error": error_msg}
                    
        except Exception as e:
            error_msg = f"LinkedIn post failed: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "error": error_msg}
    
    async def check_credentials(self) -> Dict:
        """
        Check if LinkedIn credentials are valid.
        """
        if not self.token:
            return {"valid": False, "error": "Missing access token"}
        
        if not self.user_id:
            return {"valid": False, "error": "Missing user ID"}
        
        try:
            url = f"{self.base_url}/people/(id:{self.user_id})"
            headers = {"Authorization": f"Bearer {self.token}"}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return {"valid": True, "user": response.json()}
                else:
                    return {"valid": False, "error": f"Invalid credentials: {response.status_code}"}
                    
        except Exception as e:
            return {"valid": False, "error": str(e)}