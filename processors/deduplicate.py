import re
from typing import List, Dict
from models import Company
from .normalize import clean_url, normalize_company
from config import logger

def simplify_name(name: str) -> str:
    """
    Simplifies a company name for fuzzy comparison.
    Converts to lowercase, removes all non-alphanumeric characters,
    and strips common corporate suffixes like LLC, Ltd, Inc, Co, etc.
    """
    if not name:
        return ""
    # Lowercase and remove punctuation
    n = name.lower().strip()
    n = re.sub(r"[^\w\s]", "", n)
    
    # Common corporate suffixes to strip
    suffixes = {
        "llc", "ltd", "inc", "co", "corp", "corporation", 
        "limited", "incorporated", "group", "solutions", 
        "technologies", "technology", "sa", "pjsc", "company"
    }
    
    words = n.split()
    filtered_words = [w for w in words if w not in suffixes]
    
    # Reassemble or fallback if all words were suffixes
    res = "".join(filtered_words)
    return res if res else "".join(words)

def _get_stage_specificity(stage: str) -> int:
    """Helper to rank the specificity of a funding stage string."""
    s = stage.lower().strip() if stage else ""
    if not s or s in ("unknown", "none", "n/a"):
        return 1
    if any(term in s for term in ["early", "growth", "late"]):
        return 2
    return 3  # Specific rounds (Seed, Series A, Series B, etc.)

def merge_companies(c1: Company, c2: Company) -> Company:
    """
    Merges two company records, keeping the most complete information from each.
    """
    # Prefer longer name
    name = c1.name if len(c1.name) >= len(c2.name) else c2.name
    
    # Prefer active/valid website URL
    website = c1.website or c2.website
    
    # Locations
    country = c1.country or c2.country
    city = c1.city if len(c1.city) >= len(c2.city) else c2.city
    
    # Description: keep the longer, more descriptive one
    description = c1.description if len(c1.description) >= len(c2.description) else c2.description
    
    # Industry & Category
    industry = c1.industry if len(c1.industry) >= len(c2.industry) else c2.industry
    category = c1.category or c2.category
    
    # Founding Year
    founding_year = c1.founding_year or c2.founding_year
    
    # Employee Count: Prefer larger or non-null
    employee_count = c1.employee_count or c2.employee_count
    if c1.employee_count and c2.employee_count:
        employee_count = max(c1.employee_count, c2.employee_count)
        
    # Funding Stage: Prefer more specific round information (e.g. Series C over Growth or Unknown)
    funding_stage = c1.funding_stage
    c1_spec = _get_stage_specificity(c1.funding_stage)
    c2_spec = _get_stage_specificity(c2.funding_stage)
    if c2_spec > c1_spec:
        funding_stage = c2.funding_stage
        
    # Total Funding: Prefer specific over "Unknown"
    total_funding = c1.total_funding
    if total_funding == "Unknown" and c2.total_funding != "Unknown":
        total_funding = c2.total_funding
        
    # Contact Details
    linkedin = c1.linkedin or c2.linkedin
    email = c1.email or c2.email
    
    # Merge technologies list
    tech_set = set(c1.technologies + c2.technologies)
    technologies = sorted(list(tech_set))
    
    # Merge sources: comma-separated list of unique sources
    source_set = set()
    for s in (c1.source, c2.source):
        for part in s.split(","):
            part_cleaned = part.strip()
            if part_cleaned:
                source_set.add(part_cleaned)
    source = ", ".join(sorted(list(source_set)))
    
    # Date collected: earlier date
    date_collected = c1.date_collected
    if c2.date_collected and c2.date_collected < c1.date_collected:
        date_collected = c2.date_collected

    return Company(
        name=name,
        website=website,
        country=country,
        city=city,
        industry=industry,
        category=category,
        description=description,
        founding_year=founding_year,
        employee_count=employee_count,
        funding_stage=funding_stage,
        total_funding=total_funding,
        linkedin=linkedin,
        email=email,
        technologies=technologies,
        source=source,
        date_collected=date_collected
    )

def deduplicate_companies(companies: List[Company]) -> List[Company]:
    """
    Deduplicates a list of companies based on website, name, and LinkedIn URL.
    Merges duplicate records to maintain complete data.
    """
    if not companies:
        return []
        
    logger.info(f"Deduplicating {len(companies)} raw company records...")
    
    # First, normalize all records
    normalized_list = [normalize_company(c) for c in companies]
    
    merged: List[Company] = []
    
    for c in normalized_list:
        match_idx = -1
        
        c_web_clean = clean_url(c.website)
        c_name_simple = simplify_name(c.name)
        c_linkedin_clean = c.linkedin.lower().strip()
        
        for i, existing in enumerate(merged):
            ext_web_clean = clean_url(existing.website)
            ext_name_simple = simplify_name(existing.name)
            ext_linkedin_clean = existing.linkedin.lower().strip()
            
            # Check Website Match (most reliable)
            if c_web_clean and ext_web_clean and c_web_clean == ext_web_clean:
                match_idx = i
                break
                
            # Check LinkedIn Match (reliable if present)
            if c_linkedin_clean and ext_linkedin_clean and c_linkedin_clean == ext_linkedin_clean:
                match_idx = i
                break
                
            # Check Name Match (fuzzy, only if they share country/region)
            if c_name_simple and ext_name_simple and c_name_simple == ext_name_simple:
                # To reduce false positives, verify they are in the same country
                if c.country.lower() == existing.country.lower():
                    match_idx = i
                    break
        
        if match_idx != -1:
            # Duplicate found, merge records
            logger.info(f"Duplicate found: '{c.name}' matches '{merged[match_idx].name}'. Merging...")
            merged[match_idx] = merge_companies(merged[match_idx], c)
        else:
            # No duplicate, append to list
            merged.append(c)
            
    logger.info(f"Deduplication complete. Remaining records: {len(merged)} (removed {len(companies) - len(merged)} duplicates).")
    return merged
