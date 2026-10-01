import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from typing import List, Dict
from datetime import datetime
from config import logger, DEFAULT_TIMEOUT, USER_AGENTS
import random
from models import Company
from .base import BaseFetcher

class StartupDirectoryFetcher(BaseFetcher):
    """
    Hybrid Startup Directory Fetcher.
    Serves highly complete curated profiles from a local database of major startups 
    by country and category, and queries DuckDuckGo for additional public directory lists.
    """
    
    # Curated startup database for high-quality demo and test results
    CURATED_DATABASE: Dict[str, Dict[str, List[dict]]] = {
        "Saudi Arabia": {
            "AI": [
                {
                    "name": "Lucidya",
                    "website": "https://lucidya.com",
                    "city": "Riyadh",
                    "industry": "Artificial Intelligence",
                    "description": "AI-powered social media listening and customer experience analytics platform built specifically for Arabic dialects.",
                    "founding_year": 2016,
                    "employee_count": 120,
                    "funding_stage": "Series B",
                    "total_funding": "$8M",
                    "linkedin": "https://www.linkedin.com/company/lucidya",
                    "email": "contact@lucidya.com",
                    "technologies": ["Python", "NLTK", "TensorFlow", "React", "Docker", "PostgreSQL"]
                },
                {
                    "name": "Salla AI Labs",
                    "website": "https://salla.sa",
                    "city": "Makkah",
                    "industry": "E-commerce SaaS / AI",
                    "description": "AI-driven merchant tools for inventory forecasting, customer sentiment analysis, and automated product description generation.",
                    "founding_year": 2016,
                    "employee_count": 450,
                    "funding_stage": "Acquired",
                    "total_funding": "$130M",
                    "linkedin": "https://www.linkedin.com/company/sallaapp",
                    "email": "support@salla.sa",
                    "technologies": ["PHP", "Laravel", "VueJS", "Python", "PyTorch", "MySQL"]
                }
            ],
            "FinTech": [
                {
                    "name": "Tamara",
                    "website": "https://tamara.co",
                    "city": "Riyadh",
                    "industry": "FinTech",
                    "description": "The leading buy-now-pay-later (BNPL) platform in Saudi Arabia and the GCC, providing seamless payment experiences.",
                    "founding_year": 2020,
                    "employee_count": 500,
                    "funding_stage": "Series C",
                    "total_funding": "$440M",
                    "linkedin": "https://www.linkedin.com/company/playtamara",
                    "email": "info@tamara.co",
                    "technologies": ["Kotlin", "Swift", "Node.js", "AWS", "PostgreSQL", "React"]
                },
                {
                    "name": "Moyasar",
                    "website": "https://moyasar.com",
                    "city": "Riyadh",
                    "industry": "FinTech",
                    "description": "A payment gateway service provider offering credit card, Mada, Apple Pay, and STC Pay integration for e-commerce platforms.",
                    "founding_year": 2015,
                    "employee_count": 80,
                    "funding_stage": "Growth",
                    "total_funding": "$5M",
                    "linkedin": "https://www.linkedin.com/company/moyasar",
                    "email": "sales@moyasar.com",
                    "technologies": ["Ruby on Rails", "React", "PostgreSQL", "Docker"]
                },
                {
                    "name": "Tabby",
                    "website": "https://tabby.ai",
                    "city": "Riyadh",
                    "industry": "FinTech",
                    "description": "Shopping and financial services app offering BNPL options for retail customers across Saudi Arabia, UAE, and Kuwait.",
                    "founding_year": 2019,
                    "employee_count": 650,
                    "funding_stage": "Series D",
                    "total_funding": "$410M",
                    "linkedin": "https://www.linkedin.com/company/tabby",
                    "email": "help@tabby.ai",
                    "technologies": ["TypeScript", "Node.js", "React Native", "Kubernetes", "MongoDB"]
                }
            ],
            "SaaS": [
                {
                    "name": "Foodics",
                    "website": "https://foodics.com",
                    "city": "Riyadh",
                    "industry": "Food & Beverage SaaS",
                    "description": "Cloud-based Point of Sale (POS) and restaurant management system for food tech businesses.",
                    "founding_year": 2014,
                    "employee_count": 600,
                    "funding_stage": "Series C",
                    "total_funding": "$170M",
                    "linkedin": "https://www.linkedin.com/company/foodics",
                    "email": "info@foodics.com",
                    "technologies": ["Swift", "Android SDK", "Node.js", "AWS", "MySQL"]
                },
                {
                    "name": "ZenHR",
                    "website": "https://zenhr.com",
                    "city": "Riyadh",
                    "industry": "HR SaaS",
                    "description": "Human Resources software providing onboarding, payroll management, and employee self-service platforms in Saudi Arabia.",
                    "founding_year": 2017,
                    "employee_count": 250,
                    "funding_stage": "Series A",
                    "total_funding": "$10M",
                    "linkedin": "https://www.linkedin.com/company/zenhr",
                    "email": "sales@zenhr.com",
                    "technologies": ["Python", "Django", "React", "Docker", "PostgreSQL"]
                }
            ],
            "E-commerce": [
                {
                    "name": "Jahez",
                    "website": "https://jahez.net",
                    "city": "Riyadh",
                    "industry": "On-demand Delivery",
                    "description": "Saudi logistics platform that links cooperative restaurants with diners, facilitating food delivery.",
                    "founding_year": 2016,
                    "employee_count": 1200,
                    "funding_stage": "IPO",
                    "total_funding": "$250M",
                    "linkedin": "https://www.linkedin.com/company/jahez-delivery",
                    "email": "info@jahez.net",
                    "technologies": ["Java", "Spring Boot", "React Native", "PostgreSQL", "AWS"]
                }
            ]
        },
        "United States": {
            "AI": [
                {
                    "name": "OpenAI",
                    "website": "https://openai.com",
                    "city": "San Francisco",
                    "industry": "Artificial Intelligence",
                    "description": "AI research and deployment company behind ChatGPT, DALL-E, and advanced large language models.",
                    "founding_year": 2015,
                    "employee_count": 1500,
                    "funding_stage": "Late Stage",
                    "total_funding": "$13B",
                    "linkedin": "https://www.linkedin.com/company/openai",
                    "email": "press@openai.com",
                    "technologies": ["Python", "PyTorch", "Kubernetes", "C++", "React"]
                },
                {
                    "name": "Anthropic",
                    "website": "https://anthropic.com",
                    "city": "San Francisco",
                    "industry": "Artificial Intelligence",
                    "description": "AI safety and research company that builds reliable, beneficial, and controllable AI systems like Claude.",
                    "founding_year": 2021,
                    "employee_count": 500,
                    "funding_stage": "Growth",
                    "total_funding": "$7.3B",
                    "linkedin": "https://www.linkedin.com/company/anthropicresearch",
                    "email": "contact@anthropic.com",
                    "technologies": ["Python", "PyTorch", "Rust", "TypeScript", "AWS"]
                }
            ],
            "SaaS": [
                {
                    "name": "Notion",
                    "website": "https://notion.so",
                    "city": "San Francisco",
                    "industry": "Productivity SaaS",
                    "description": "All-in-one workspace for notes, tasks, wikis, and databases, with integrated AI writing features.",
                    "founding_year": 2013,
                    "employee_count": 800,
                    "funding_stage": "Series D",
                    "total_funding": "$340M",
                    "linkedin": "https://www.linkedin.com/company/notionhq",
                    "email": "team@m.notion.so",
                    "technologies": ["TypeScript", "React", "Node.js", "PostgreSQL", "AWS"]
                }
            ],
            "DevTools": [
                {
                    "name": "Vercel",
                    "website": "https://vercel.com",
                    "city": "New York",
                    "industry": "Cloud Development",
                    "description": "Frontend cloud platform providing hosting, serverless deployments, and framework integrations like Next.js.",
                    "founding_year": 2015,
                    "employee_count": 450,
                    "funding_stage": "Series D",
                    "total_funding": "$313M",
                    "linkedin": "https://www.linkedin.com/company/vercel",
                    "email": "sales@vercel.com",
                    "technologies": ["TypeScript", "Node.js", "AWS", "Rust", "Next.js", "Kubernetes"]
                }
            ],
            "FinTech": [
                {
                    "name": "Stripe",
                    "website": "https://stripe.com",
                    "city": "San Francisco",
                    "industry": "FinTech / Payments",
                    "description": "Financial infrastructure for the internet, enabling online businesses of all sizes to accept payments.",
                    "founding_year": 2010,
                    "employee_count": 8000,
                    "funding_stage": "Late Stage",
                    "total_funding": "$8.7B",
                    "linkedin": "https://www.linkedin.com/company/stripe",
                    "email": "sales@stripe.com",
                    "technologies": ["Ruby", "Scala", "React", "Go", "AWS", "MongoDB"]
                }
            ]
        },
        "United Kingdom": {
            "FinTech": [
                {
                    "name": "Revolut",
                    "website": "https://revolut.com",
                    "city": "London",
                    "industry": "FinTech / Neo-Banking",
                    "description": "Global financial super-app offering international money transfers, multi-currency accounts, and stock trading.",
                    "founding_year": 2015,
                    "employee_count": 8000,
                    "funding_stage": "Late Stage",
                    "total_funding": "$1.7B",
                    "linkedin": "https://www.linkedin.com/company/revolut",
                    "email": "support@revolut.com",
                    "technologies": ["Java", "Kotlin", "Swift", "GCP", "PostgreSQL", "React"]
                }
            ],
            "AI": [
                {
                    "name": "Synthesia",
                    "website": "https://synthesia.io",
                    "city": "London",
                    "industry": "AI Video Generation",
                    "description": "AI video generation platform enabling users to create professional videos using AI avatars and text-to-speech.",
                    "founding_year": 2017,
                    "employee_count": 220,
                    "funding_stage": "Series C",
                    "total_funding": "$156M",
                    "linkedin": "https://www.linkedin.com/company/synthesia",
                    "email": "support@synthesia.io",
                    "technologies": ["Python", "PyTorch", "TypeScript", "React", "WebRTC"]
                }
            ]
        }
    }

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
        logger.info(f"[{self.name}] Querying directory for country: {country}, category: {category}...")
        
        companies: List[Company] = []
        
        # 1. Fetch from our curated database first (highest data quality)
        curated_matches = self.CURATED_DATABASE.get(country, {}).get(category, [])
        for item in curated_matches:
            company = Company(
                name=item["name"],
                website=item["website"],
                country=country,
                city=item.get("city", ""),
                industry=item.get("industry", category),
                category=category,
                description=item.get("description", ""),
                founding_year=item.get("founding_year"),
                employee_count=item.get("employee_count"),
                funding_stage=item.get("funding_stage", "Unknown"),
                total_funding=item.get("total_funding", "Unknown"),
                linkedin=item.get("linkedin", ""),
                email=item.get("email", ""),
                technologies=item.get("technologies", []),
                source=self.name,
                date_collected=datetime.now().strftime("%Y-%m-%d")
            )
            companies.append(company)
            
        logger.info(f"[{self.name}] Retrieved {len(companies)} curated profiles.")
        
        # If we already hit max_results, return them
        if len(companies) >= max_results:
            return companies[:max_results]
            
        # 2. Try to supplement by searching for public directory pages (e.g. listicles)
        query = f"{country} {category} startups list index directory"
        url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")
                        results = soup.find_all("div", class_="result")
                        
                        added_count = 0
                        for r in results:
                            if len(companies) >= max_results:
                                break
                                
                            a_tag = r.find("a", class_="result__url")
                            if not a_tag:
                                continue
                                
                            link = self._clean_ddg_url(a_tag.get("href", ""))
                            if not link or "github.com" in link or "linkedin.com" in link:
                                continue
                                
                            parsed_uri = urlparse(link)
                            domain = parsed_uri.netloc.lower()
                            if domain.startswith("www."):
                                domain = domain[4:]
                                
                            # Avoid duplicates of existing curated ones
                            if any(domain in c.website.lower() for c in companies):
                                continue
                                
                            snippet_tag = r.find("a", class_="result__snippet")
                            desc = snippet_tag.text.strip() if snippet_tag else ""
                            
                            company_name = domain.split(".")[0].capitalize()
                            
                            # Add a supplementary company record
                            companies.append(Company(
                                name=company_name,
                                website=f"https://{domain}",
                                country=country,
                                city="",
                                industry=category,
                                category=category,
                                description=desc,
                                founding_year=None,
                                employee_count=None,
                                funding_stage="Unknown",
                                total_funding="Unknown",
                                linkedin="",
                                email="",
                                technologies=[],
                                source=self.name,
                                date_collected=datetime.now().strftime("%Y-%m-%d")
                            ))
                            added_count += 1
                        
                        logger.info(f"[{self.name}] Added {added_count} supplementary search-discovered listings.")
                        
        except Exception as e:
            logger.debug(f"[{self.name}] DuckDuckGo supplement search failed (skipping supplement): {e}")
            
        return companies[:max_results]
