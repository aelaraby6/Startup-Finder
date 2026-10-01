import aiohttp
import asyncio
from typing import List, Optional
from models import Company
from config import logger, DEFAULT_TIMEOUT, USER_AGENTS
import random

async def validate_single_website(session: aiohttp.ClientSession, company: Company, timeout: int = 5) -> Optional[Company]:
    """
    Validates a single company website using a quick async HEAD or GET request.
    Returns the Company if valid, or None if the website is dead.
    """
    url = company.website
    if not url:
        # If no website is specified, we consider it invalid for our startup database requirement
        logger.info(f"[Validator] Company '{company.name}' has no website. Removing.")
        return None
        
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "*/*"
    }
    
    try:
        # First, try HEAD request (much faster, consumes less bandwidth)
        try:
            async with session.head(url, headers=headers, timeout=timeout, allow_redirects=True) as response:
                if response.status < 400:
                    logger.debug(f"[Validator] '{company.name}' website {url} is LIVE (HEAD: {response.status}).")
                    return company
        except Exception:
            # Fallback to GET if HEAD is not allowed/fails
            pass
            
        # Try GET request
        async with session.get(url, headers=headers, timeout=timeout, allow_redirects=True) as response:
            if response.status < 400:
                logger.debug(f"[Validator] '{company.name}' website {url} is LIVE (GET: {response.status}).")
                return company
            else:
                logger.warning(f"[Validator] '{company.name}' website {url} returned HTTP {response.status}. Removing.")
                return None
                
    except asyncio.TimeoutError:
        logger.warning(f"[Validator] '{company.name}' website {url} timed out after {timeout}s. Removing.")
        return None
    except Exception as e:
        logger.warning(f"[Validator] '{company.name}' website {url} failed connection check: {e}. Removing.")
        return None

async def validate_companies_websites(companies: List[Company], enabled: bool = True) -> List[Company]:
    """
    Validates all company websites concurrently.
    If 'enabled' is False, website validation is skipped and the original list is returned.
    """
    if not enabled:
        logger.info("[Validator] Website validation is disabled. Skipping check.")
        return companies
        
    if not companies:
        return []
        
    logger.info(f"[Validator] Starting concurrent website validation for {len(companies)} companies...")
    
    # Configure connector to handle SSL failures gracefully
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [validate_single_website(session, c) for c in companies]
        results = await asyncio.gather(*tasks)
        
    valid_companies = [c for c in results if c is not None]
    logger.info(f"[Validator] Website validation complete. Valid: {len(valid_companies)} / {len(companies)}.")
    return valid_companies
