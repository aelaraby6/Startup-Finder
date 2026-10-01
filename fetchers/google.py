import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from typing import List
from datetime import datetime
from config import logger, DEFAULT_TIMEOUT, USER_AGENTS
import random
from models import Company
from .base import BaseFetcher

class GoogleFetcher(BaseFetcher):
    """
    Fetcher that scrapes search engines (using DuckDuckGo HTML)
    to find company websites and names for a given country and category.
    """

    # Filter out common blog/news/directory platforms to find actual company websites
    EXCLUDED_DOMAINS = {
        "linkedin.com", "crunchbase.com", "wellfound.com", "angellist.com",
        "github.com", "twitter.com", "facebook.com", "youtube.com",
        "medium.com", "techcrunch.com", "reddit.com", "wikipedia.org",
        "ycombinator.com", "glassdoor.com", "indeed.com", "pinterest.com",
        "quora.com", "instagram.com", "tracxn.com", "pitchbook.com",
        "duckduckgo.com", "google.com", "yahoo.com", "bing.com"
    }

    def _clean_ddg_url(self, url: str) -> str:
        """DuckDuckGo HTML results sometimes redirect. This cleans those URLs."""
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
        logger.info(f"[{self.name}] Searching search engines for country: {country}, category: {category}...")
        
        # Build search query
        query = f"{country} {category} startups list website"
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
                    
                    # Parse results
                    results = soup.find_all("div", class_="result")
                    logger.info(f"[{self.name}] Found {len(results)} search snippets in DuckDuckGo.")
                    
                    for r in results:
                        if len(companies) >= max_results:
                            break
                            
                        # Find title and link
                        a_tag = r.find("a", class_="result__url")
                        if not a_tag:
                            continue
                            
                        title_tag = r.find("a", class_="result__snippet")
                        description = title_tag.text.strip() if title_tag else ""
                        
                        link = self._clean_ddg_url(a_tag.get("href", ""))
                        if not link:
                            continue
                            
                        parsed_uri = urlparse(link)
                        domain = parsed_uri.netloc.lower()
                        # Remove www.
                        if domain.startswith("www."):
                            domain = domain[4:]
                            
                        # Filter out common platforms
                        if domain in self.EXCLUDED_DOMAINS or any(domain.endswith("." + d) for d in self.EXCLUDED_DOMAINS):
                            continue
                            
                        # Guess company name from domain or title
                        # Title is usually like "Company Name - Description" or "Company: Category"
                        title = r.find("a", class_="result__snippet") or r.find("h2", class_="result__title")
                        raw_title = title.text.strip() if title else ""
                        
                        # Extract a clean company name from search title
                        # e.g., "Moyasar - FinTech" -> "Moyasar"
                        company_name = raw_title.split("-")[0].split("|")[0].split(":")[0].strip()
                        if len(company_name) > 50 or not company_name or "startup" in company_name.lower():
                            # Fallback to domain name capitalized
                            company_name = domain.split(".")[0].capitalize()
                            
                        # Create Company
                        company = Company(
                            name=company_name,
                            website=f"https://{domain}",
                            country=country,
                            city="",
                            industry=category,
                            category=category,
                            description=description,
                            founding_year=None,
                            employee_count=None,
                            funding_stage="Unknown",
                            total_funding="Unknown",
                            linkedin="",
                            email="",
                            technologies=[],
                            source=self.name,
                            date_collected=datetime.now().strftime("%Y-%m-%d")
                        )
                        companies.append(company)
                        
                    logger.info(f"[{self.name}] Found {len(companies)} valid company websites.")
                    return companies
                    
        except Exception as e:
            logger.error(f"[{self.name}] Error during fetch: {e}", exc_info=True)
            return []
