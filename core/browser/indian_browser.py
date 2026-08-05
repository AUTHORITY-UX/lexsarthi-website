"""
core/browser/indian_browser.py - Indian Legal Browser Module
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict
from urllib.parse import urljoin

class IndianLegalBrowser:
    """Browser that fetches and parses Indian legal websites"""
    
    SOURCES = {
        'supreme_court': 'https://www.sci.gov.in',
        'high_court_delhi': 'https://delhihighcourt.nic.in',
        'high_court_bombay': 'https://bombayhighcourt.nic.in',
        'indian_kanoon': 'https://indiankanoon.org',
        'legalaffairs': 'https://legalaffairs.gov.in'
    }
    
    async def fetch_page(self, url: str) -> Dict:
        """Fetch and parse a legal page"""
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            return {
                'title': soup.title.string if soup.title else '',
                'text': soup.get_text(),
                'links': [urljoin(url, a['href']) for a in soup.find_all('a', href=True)]
            }
    
    async def search_indian_kanoon(self, query: str) -> List[Dict]:
        """Search Indian Kanoon for cases"""
        search_url = f"https://indiankanoon.org/search/?formInput={query}"
        data = await self.fetch_page(search_url)
        # Parse results (implementation details omitted for brevity)
        return results