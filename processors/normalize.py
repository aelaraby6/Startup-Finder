import re
from typing import List, Optional
from models import Company

def clean_url(url: str) -> str:
    """
    Cleans a URL by removing protocols, www., and trailing slashes.
    Used for reliable matching and comparisons.
    """
    if not url:
        return ""
    # Lowercase
    url = url.strip().lower()
    # Remove protocol
    url = re.sub(r"^https?://", "", url)
    # Remove www.
    url = re.sub(r"^www\.", "", url)
    # Remove trailing slash
    if url.endswith("/"):
        url = url[:-1]
    return url

def format_website(url: str) -> str:
    """Ensures a website starts with https:// if it has a valid format."""
    cleaned = url.strip()
    if not cleaned:
        return ""
    if cleaned.startswith("http://"):
        cleaned = "https://" + cleaned[7:]
    elif not cleaned.startswith("https://"):
        cleaned = "https://" + cleaned
    return cleaned

def clean_linkedin(url: str) -> str:
    """Normalizes LinkedIn company URLs."""
    if not url:
        return ""
    url = url.strip().lower()
    # If it is just a slug, expand it
    if not url.startswith("http"):
        if "linkedin.com/company/" not in url:
            url = f"https://linkedin.com/company/{url}"
        else:
            url = "https://" + url
    # Ensure secure protocol
    if url.startswith("http://"):
        url = "https://" + url[7:]
    # Replace www.linkedin.com with linkedin.com
    url = url.replace("https://www.linkedin.com", "https://linkedin.com")
    return url

def normalize_funding(funding: str) -> str:
    """Standardizes funding strings like '$1,500,000' or '8.5M' to a clean '$X' representation."""
    if not funding:
        return "Unknown"
    funding = funding.strip()
    if funding.lower() in ("unknown", "none", "", "n/a"):
        return "Unknown"
        
    # Check if already in standard formatted form (e.g. $10M)
    if funding.startswith("$") and funding[-1].upper() in ("M", "B", "K"):
        return funding
        
    # Clean digits and common suffixes
    try:
        # Check if millions or billions
        multiplier = 1
        clean_str = re.sub(r"[^\d\.\,kKmMbB]", "", funding)
        
        if clean_str[-1].upper() == "M":
            multiplier = 1_000_000
            clean_str = clean_str[:-1]
        elif clean_str[-1].upper() == "B":
            multiplier = 1_000_000_000
            clean_str = clean_str[:-1]
        elif clean_str[-1].upper() == "K":
            multiplier = 1_000
            clean_str = clean_str[:-1]
            
        clean_str = clean_str.replace(",", "")
        val = float(clean_str) * multiplier
        
        if val >= 1_000_000_000:
            return f"${val / 1_000_000_000:.1f}B".replace(".0B", "B")
        elif val >= 1_000_000:
            return f"${val / 1_000_000:.1f}M".replace(".0M", "M")
        elif val >= 1_000:
            return f"${val / 1_000:.1f}K".replace(".0K", "K")
        else:
            return f"${val:.0f}"
    except (ValueError, IndexError):
        return funding  # Return raw if parsing fails

def normalize_company(company: Company) -> Company:
    """
    Normalizes all fields of a Company instance.
    Returns a new normalized Company instance.
    """
    # Name normalization
    name = company.name.strip()
    if name:
        # Capitalize words but keep abbreviations like AI, SaaS, LLC
        words = name.split()
        normalized_words = []
        for w in words:
            w_upper = w.upper()
            if w_upper in ("AI", "SAAS", "IT", "BNPL", "POS", "F&B", "GCC", "HR", "LLC"):
                normalized_words.append(w_upper)
            elif "-" in w:
                parts = []
                for p in w.split("-"):
                    if p:
                        # Capitalize first letter, leave rest (handles CamelCase)
                        parts.append(p[0].upper() + p[1:] if len(p) > 1 else p.upper())
                    else:
                        parts.append("")
                normalized_words.append("-".join(parts))
            else:
                # Capitalize first letter, leave rest (handles CamelCase)
                normalized_words.append(w[0].upper() + w[1:] if len(w) > 1 else w.upper())
        name = " ".join(normalized_words)

    # Clean and standardize website
    website = format_website(company.website)

    # Location normalization
    country = company.country.strip().title()
    # Fix standard cases
    if country.lower() in ("united states", "usa", "us", "united states of america"):
        country = "United States"
    elif country.lower() in ("united arab emirates", "uae"):
        country = "United Arab Emirates"
    elif country.lower() in ("united kingdom", "uk"):
        country = "United Kingdom"

    city = company.city.strip()
    if city:
        city = ", ".join([p.strip().title() for p in city.split(",") if p.strip()])

    # Funding and stage normalization
    funding_stage = company.funding_stage.strip()
    if funding_stage:
        # Standardize capitalization
        funding_stage = " ".join([w.capitalize() for w in funding_stage.split()])
    else:
        funding_stage = "Unknown"

    total_funding = normalize_funding(company.total_funding)

    # Social links
    linkedin = clean_linkedin(company.linkedin)
    email = company.email.strip().lower()
    if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        email = ""  # Invalid email format

    # Tech stack cleaning: unique, capitalized, non-empty
    seen_techs = set()
    cleaned_techs = []
    for tech in company.technologies:
        t = tech.strip()
        if not t:
            continue
        # Title case
        t_normalized = t.title()
        # Capitalize specific acronyms/languages
        if t.upper() in ("AI", "JS", "TS", "AWS", "GCP", "API", "POS", "F&B", "UI", "UX", "PHP", "SQL", "HTML", "CSS", "BNPL"):
            t_normalized = t.upper()
        elif t.lower() == "vuejs":
            t_normalized = "VueJS"
        elif t.lower() == "nodejs":
            t_normalized = "Node.js"
        elif t.lower() == "reactnative":
            t_normalized = "React Native"
            
        if t_normalized.lower() not in seen_techs:
            seen_techs.add(t_normalized.lower())
            cleaned_techs.append(t_normalized)

    return Company(
        name=name,
        website=website,
        country=country,
        city=city,
        industry=company.industry.strip().title() or company.category,
        category=company.category,
        description=company.description.strip(),
        founding_year=company.founding_year,
        employee_count=company.employee_count,
        funding_stage=funding_stage,
        total_funding=total_funding,
        linkedin=linkedin,
        email=email,
        technologies=sorted(cleaned_techs),
        source=company.source,
        date_collected=company.date_collected
    )
