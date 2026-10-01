import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import logger, DEFAULT_TIMEOUT, USER_AGENTS
import random
from models import Company
from .base import BaseFetcher

class GitHubFetcher(BaseFetcher):
    """
    Fetcher for GitHub organizations.
    Queries the GitHub Search API for organizations matching the country and category.
    """
    
    SEARCH_URL = "https://api.github.io/api" # Fallback or standard
    # Actually, GitHub API root is https://api.github.com
    API_ROOT = "https://api.github.com"

    async def _fetch_org_details(self, session: aiohttp.ClientSession, org_url: str, category: str, country: str) -> Optional[Company]:
        """Fetches details for a single GitHub organization."""
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with session.get(org_url, headers=headers, timeout=DEFAULT_TIMEOUT) as response:
                if response.status == 403:
                    logger.warning(f"[{self.name}] Rate limit hit when fetching org details: {org_url}")
                    return None
                if response.status != 200:
                    return None
                    
                org = await response.json()
                
                # Check location mismatch as search can be loose
                location = org.get("location", "") or ""
                if country.lower() not in location.lower() and not (country.lower() in ["united states", "usa"] and any(s in location.lower() for s in [", us", "usa", "united states"])):
                    # Allow it if it was specifically in search, but log warning
                    pass

                # Extract founding year from created_at
                created_at = org.get("created_at", "")
                founding_year = None
                if created_at:
                    try:
                        founding_year = int(created_at.split("-")[0])
                    except (ValueError, IndexError):
                        pass

                # Extract blog/website
                website = org.get("blog", "") or ""
                if website and not website.startswith("http"):
                    website = "https://" + website

                # Try to guess technologies from public repos count or description
                techs = []
                description = org.get("description", "") or org.get("bio", "") or ""
                
                # Simple tech guessing from description
                desc_lower = description.lower()
                for tech in ["python", "javascript", "typescript", "rust", "go", "react", "vue", "docker", "kubernetes", "aws", "nodejs"]:
                    if tech in desc_lower:
                        techs.append(tech.capitalize())

                return Company(
                    name=org.get("name", "") or org.get("login", ""),
                    website=website,
                    country=country,
                    city=location,
                    industry="Technology",
                    category=category,
                    description=description,
                    founding_year=founding_year,
                    employee_count=None,  # GitHub doesn't show employee count directly
                    funding_stage="Unknown",
                    total_funding="Unknown",
                    linkedin="",
                    email=org.get("email", "") or "",
                    technologies=techs,
                    source=self.name,
                    date_collected=datetime.now().strftime("%Y-%m-%d")
                )
        except Exception as e:
            logger.debug(f"[{self.name}] Error fetching details for {org_url}: {e}")
            return None

    async def fetch(self, country: str, category: str, max_results: int) -> List[Company]:
        logger.info(f"[{self.name}] Searching GitHub orgs for country: {country}, category: {category}...")
        
        # Build query: type:org location:"Saudi Arabia" "AI"
        query = f'type:org location:"{country}" "{category}"'
        search_url = f"{self.API_ROOT}/search/users?q={query}&per_page={min(max_results, 100)}"
        
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers=headers, timeout=DEFAULT_TIMEOUT) as response:
                    if response.status == 403:
                        logger.error(f"[{self.name}] GitHub API rate limit exceeded on search. Skipping GitHub fetcher.")
                        return []
                    if response.status != 200:
                        logger.error(f"[{self.name}] Failed to search GitHub: HTTP {response.status}")
                        return []
                        
                    search_results = await response.json()
                    items = search_results.get("items", [])
                    logger.info(f"[{self.name}] Found {len(items)} matching GitHub organizations.")
                    
                    if not items:
                        return []

                    # Fetch details for the first N organizations concurrently
                    tasks = []
                    for item in items[:max_results]:
                        tasks.append(self._fetch_org_details(session, item["url"], category, country))
                        
                    results = await asyncio.gather(*tasks)
                    
                    # Filter out None results
                    companies = [c for c in results if c is not None]
                    logger.info(f"[{self.name}] Successfully fetched {len(companies)} company profiles.")
                    return companies
                    
        except Exception as e:
            logger.error(f"[{self.name}] Error during fetch: {e}", exc_info=True)
            return []
