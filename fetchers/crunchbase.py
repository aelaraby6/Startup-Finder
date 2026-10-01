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

class CrunchbaseFetcher(BaseFetcher):
    """
    Fetcher for Crunchbase.
    Uses search engine indexing (DuckDuckGo) to discover Crunchbase profiles
    for startups matching the country and category, bypassing Cloudflare blocks.
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
        logger.info(f"[{self.name}] Searching Crunchbase profiles via DDG for country: {country}, category: {category}...")
        
        # Build query: site:crunchbase.com/organization Saudi Arabia AI
        query = f"site:crunchbase.com/organization {country} {category}"
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
                    logger.info(f"[{self.name}] Found {len(results)} Crunchbase candidates.")
                    
                    for r in results:
                        if len(companies) >= max_results:
                            break
                            
                        a_tag = r.find("a", class_="result__url")
                        if not a_tag:
                            continue
                            
                        link = self._clean_ddg_url(a_tag.get("href", ""))
                        if "crunchbase.com/organization/" not in link:
                            continue
                            
                        # Extract slug
                        # e.g., https://www.crunchbase.com/organization/moyasar -> moyasar
                        match = re.search(r"crunchbase\.com/organization/([^/?#]+)", link)
                        if not match:
                            continue
                        slug = match.group(1)
                        
                        # Capitalize slug for company name
                        # e.g. moyasar-financial -> Moyasar Financial
                        company_name = " ".join([word.capitalize() for word in slug.split("-")])
                        
                        snippet_tag = r.find("a", class_="result__snippet")
                        description = snippet_tag.text.strip() if snippet_tag else ""
                        
                        # Try to guess/extract website from snippet (if it contains ".com", ".sa", etc.)
                        website = ""
                        web_match = re.search(r"\b([a-zA-Z0-9-]+\.[a-z]{2,})\b", description)
                        if web_match and "crunchbase.com" not in web_match.group(0):
                            website = "https://" + web_match.group(0)
                        else:
                            # Fallback guess
                            website = f"https://{slug}.com"
                            
                        # Try to extract employee count from snippet if mentioned (e.g. "11-50 employees" or "100-250")
                        employee_count = None
                        emp_match = re.search(r"(\d+)-(\d+)\s+employees", description, re.IGNORECASE)
                        if emp_match:
                            try:
                                employee_count = int(emp_match.group(2))
                            except ValueError:
                                pass
                                
                        # Try to extract funding stage
                        funding_stage = "Unknown"
                        for stage in ["Seed", "Series A", "Series B", "Series C", "Pre-Seed", "Series D", "IPO", "Acquired"]:
                            if stage.lower() in description.lower():
                                funding_stage = stage
                                break
                                
                        # Create Company
                        company = Company(
                            name=company_name,
                            website=website,
                            country=country,
                            city="",
                            industry=category,
                            category=category,
                            description=description,
                            founding_year=None,
                            employee_count=employee_count,
                            funding_stage=funding_stage,
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
