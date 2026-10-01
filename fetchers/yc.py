import re
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import logger, DEFAULT_TIMEOUT
from models import Company
from .base import BaseFetcher

class YCFetcher(BaseFetcher):
    """
    Fetcher for Y Combinator startups.
    Queries the daily-synced public JSON index of all YC startups.
    """
    
    API_URL = "https://yc-oss.github.io/api/companies/all.json"
    
    # Category keyword mapping for filtering YC startups
    CATEGORY_MAPPING = {
        "AI": ["ai", "artificial intelligence", "machine learning", "deep learning", "nlp", "computer vision", "generative ai"],
        "SaaS": ["saas", "software as a service", "b2b software", "subscription", "cloud software"],
        "FinTech": ["fintech", "finance", "financial", "payments", "crypto", "banking", "lending", "insurance"],
        "HealthTech": ["healthtech", "health", "healthcare", "medical", "biotech", "telehealth", "digital health"],
        "EdTech": ["edtech", "education", "learning", "teaching", "school", "e-learning"],
        "Cybersecurity": ["cybersecurity", "security", "privacy", "encryption", "network security"],
        "Cloud": ["cloud", "cloud infrastructure", "aws", "devops", "hosting", "serverless"],
        "DevTools": ["devtools", "developer tools", "programming", "api", "git", "compiler", "debugging"],
        "E-commerce": ["e-commerce", "ecommerce", "retail", "marketplace", "shop", "d2c"],
        "Gaming": ["gaming", "game", "esports", "vr", "ar", "game development"],
        "Robotics": ["robotics", "robot", "automation", "drones", "hardware", "manufacturing"],
        "Blockchain": ["blockchain", "web3", "crypto", "cryptocurrency", "nft", "smart contracts", "defi"],
        "Data": ["data", "analytics", "database", "big data", "bi", "data engineering", "data science"],
        "Mobile": ["mobile", "mobile app", "ios", "android", "app store"],
        "Software": ["software", "applications", "b2b software", "saas", "web development"]
    }

    def _extract_year_from_batch(self, batch_str: str) -> Optional[int]:
        """Extracts a 4-digit year from batch strings like 'Winter 2012' or 'W12'."""
        if not batch_str:
            return None
        # Try to find a 4-digit year
        match = re.search(r"\b(19|20)\d{2}\b", batch_str)
        if match:
            return int(match.group(0))
        # Try to find a 2-digit year (e.g. 'W12' or 'S12')
        match2 = re.search(r"\b\d{2}\b", batch_str)
        if match2:
            year_short = int(match2.group(0))
            return 2000 + year_short if year_short < 50 else 1900 + year_short
        # Extract digits in case they are attached to letter e.g., W12 -> 12 -> 2012
        digits = "".join(filter(str.isdigit, batch_str))
        if len(digits) == 2:
            year_short = int(digits)
            return 2000 + year_short if year_short < 50 else 1900 + year_short
        elif len(digits) == 4:
            return int(digits)
        return None

    def _matches_location(self, company: Dict[str, Any], country: str) -> bool:
        """Determines if the company location matches the target country."""
        # Check all_locations string
        loc = company.get("all_locations", "").lower()
        country_lower = country.lower()
        
        # Exact match or substring check
        if country_lower in loc:
            return True
            
        # Standardize USA names
        if country_lower in ["united states", "usa", "us", "america"]:
            if any(term in loc for term in ["united states", "usa", "united states of america", "ca, ", "ny, ", "sf, "]):
                return True
                
        # Regions list
        regions = [r.lower() for r in company.get("regions", [])]
        if any(country_lower in r for r in regions):
            return True
            
        return False

    def _matches_category(self, company: Dict[str, Any], category: str) -> bool:
        """Determines if the company matches the target category based on tags and industry."""
        category_lower = category.lower()
        
        # Tags and industries associated with the company
        tags = [t.lower() for t in company.get("tags", [])]
        industry = company.get("industry", "").lower()
        subindustry = company.get("subindustry", "").lower()
        one_liner = company.get("one_liner", "").lower()
        description = company.get("long_description", "").lower()
        
        # Direct string check
        if category_lower in tags or category_lower in industry or category_lower in subindustry:
            return True
            
        # Keyword mappings check
        keywords = self.CATEGORY_MAPPING.get(category, [category_lower])
        for kw in keywords:
            if (kw in tags or 
                kw in industry or 
                kw in subindustry or 
                kw in one_liner or 
                kw in description):
                return True
                
        return False

    async def fetch(self, country: str, category: str, max_results: int) -> List[Company]:
        logger.info(f"[{self.name}] Fetching startups for country: {country}, category: {category}...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.API_URL, timeout=DEFAULT_TIMEOUT) as response:
                    if response.status != 200:
                        logger.error(f"[{self.name}] Failed to fetch data: HTTP {response.status}")
                        return []
                        
                    data = await response.json()
                    logger.info(f"[{self.name}] Downloaded {len(data)} companies from YC index.")
                    
                    results = []
                    for c in data:
                        if len(results) >= max_results:
                            break
                            
                        # Location filter
                        if not self._matches_location(c, country):
                            continue
                            
                        # Category filter
                        if not self._matches_category(c, category):
                            continue
                            
                        # Extract city from location if possible (usually 'City, Country' or 'City, State, Country')
                        city = ""
                        loc_parts = [p.strip() for p in c.get("all_locations", "").split(",") if p.strip()]
                        if len(loc_parts) >= 2:
                            city = loc_parts[0]
                            
                        # Map tags to technologies
                        techs = c.get("tags", [])
                        
                        # Create company
                        company = Company(
                            name=c.get("name", ""),
                            website=c.get("website", ""),
                            country=country,
                            city=city,
                            industry=c.get("industry", ""),
                            category=category,
                            description=c.get("long_description", "") or c.get("one_liner", ""),
                            founding_year=self._extract_year_from_batch(c.get("batch", "")),
                            employee_count=c.get("team_size"),
                            funding_stage=c.get("stage", "Unknown"),
                            total_funding="Unknown",  # YC index doesn't list total funding amount
                            linkedin="",  # Not available directly in the summary JSON
                            email="",
                            technologies=techs,
                            source=self.name,
                            date_collected=datetime.now().strftime("%Y-%m-%d")
                        )
                        results.append(company)
                        
                    logger.info(f"[{self.name}] Found {len(results)} matches.")
                    return results
                    
        except Exception as e:
            logger.error(f"[{self.name}] Error during fetch: {e}", exc_info=True)
            return []
