import aiohttp
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from typing import List
from datetime import datetime
from config import logger, DEFAULT_TIMEOUT, USER_AGENTS
import random
from models import Company
from .base import BaseFetcher

class WellfoundFetcher(BaseFetcher):
    """
    Fetcher for Wellfound (formerly AngelList).
    Uses search engine indexing (DuckDuckGo) to discover Wellfound profiles
    for startups matching the country and category, avoiding Cloudflare restrictions.
    """

    def _clean_ddg_url(self, url: str) -> str:
        if "uddg=" in url:
            try:
                parsed = urlparse(url)
                queries = parse_qs(parsed.query)
                if "uddg" in queries:
                    return queries["uddg"][0]
            except Exception:
                pass
        return url

    async def fetch(self, country: str, category: str, max_results: int) -> List[Company]:
        logger.info(f"[{self.name}] Searching Wellfound profiles via DDG for country: {country}, category: {category}...")
        
        # Build query: site:wellfound.com/company Saudi Arabia AI
        query = f"site:wellfound.com/company {country} {category}"
        url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        
        companies: List[Company] = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT) as response:
                    if response.status != 200:
                        logger.error(f"[{self.name}] Search query failed: HTTP {response.status}")
                        return []
                        
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    results = soup.find_all("div", class_="result")
                    logger.info(f"[{self.name}] Found {len(results)} Wellfound candidates.")
                    
                    for r in results:
                        if len(companies) >= max_results:
                            break
                            
                        a_tag = r.find("a", class_="result__url")
                        if not a_tag:
                            continue
                            
                        link = self._clean_ddg_url(a_tag.get("href", ""))
                        if "wellfound.com/company/" not in link and "angel.co/company/" not in link:
                            continue
                            
                        # Extract slug
                        # e.g., https://wellfound.com/company/moyasar -> moyasar
                        match = re.search(r"company/([^/?#]+)", link)
                        if not match:
                            continue
                        slug = match.group(1)
                        
                        # Capitalize slug for company name
                        company_name = " ".join([word.capitalize() for word in slug.split("-")])
                        
                        snippet_tag = r.find("a", class_="result__snippet")
                        description = snippet_tag.text.strip() if snippet_tag else ""
                        
                        # Try to extract website from snippet
                        website = ""
                        web_match = re.search(r"\b([a-zA-Z0-9-]+\.[a-z]{2,})\b", description)
                        if web_match and "wellfound.com" not in web_match.group(0) and "angel.co" not in web_match.group(0):
                            website = "https://" + web_match.group(0)
                        else:
                            website = f"https://{slug}.com"
                            
                        # Try to extract location info from description snippet
                        city = ""
                        # E.g. "Riyadh, Saudi Arabia"
                        loc_match = re.search(r"\b([a-zA-Z\s]+),\s*" + re.escape(country), description, re.IGNORECASE)
                        if loc_match:
                            city = loc_match.group(1).strip()
                            
                        # Try to extract size
                        employee_count = None
                        size_match = re.search(r"(\d+)-(\d+)\s+employees", description, re.IGNORECASE)
                        if size_match:
                            try:
                                employee_count = int(size_match.group(2))
                            except ValueError:
                                pass
                                
                        # Create Company
                        company = Company(
                            name=company_name,
                            website=website,
                            country=country,
                            city=city,
                            industry=category,
                            category=category,
                            description=description,
                            founding_year=None,
                            employee_count=employee_count,
                            funding_stage="Unknown",
                            total_funding="Unknown",
                            linkedin="",
                            email="",
                            technologies=[],
                            source=self.name,
                            date_collected=datetime.now().strftime("%Y-%m-%d")
                        )
                        companies.append(company)
                        
                    logger.info(f"[{self.name}] Extracted {len(companies)} companies.")
                    return companies
                    
        except Exception as e:
            logger.error(f"[{self.name}] Error during fetch: {e}", exc_info=True)
            return []
