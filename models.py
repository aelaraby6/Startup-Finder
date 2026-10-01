from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime

@dataclass
class Company:
    name: str
    website: str
    country: str
    city: str = ""
    industry: str = ""
    category: str = ""
    description: str = ""
    founding_year: Optional[int] = None
    employee_count: Optional[int] = None
    funding_stage: str = "Unknown"
    total_funding: str = "Unknown"
    linkedin: str = ""
    email: str = ""
    technologies: List[str] = field(default_factory=list)
    source: str = ""
    date_collected: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def to_dict(self) -> dict:
        """Converts the dataclass instance to a flat dictionary for Pandas."""
        data = asdict(self)
        # Convert technologies list to a comma-separated string for easier table display and Excel export
        data["technologies"] = ", ".join(self.technologies) if self.technologies else ""
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Company":
        """Creates a Company instance from a dictionary."""
        # Handle technologies field if it's a string
        tech = data.get("technologies", [])
        if isinstance(tech, str):
            tech = [t.strip() for t in tech.split(",") if t.strip()]
        
        return cls(
            name=data.get("name", ""),
            website=data.get("website", ""),
            country=data.get("country", ""),
            city=data.get("city", ""),
            industry=data.get("industry", ""),
            category=data.get("category", ""),
            description=data.get("description", ""),
            founding_year=data.get("founding_year"),
            employee_count=data.get("employee_count"),
            funding_stage=data.get("funding_stage", "Unknown"),
            total_funding=data.get("total_funding", "Unknown"),
            linkedin=data.get("linkedin", ""),
            email=data.get("email", ""),
            technologies=tech,
            source=data.get("source", ""),
            date_collected=data.get("date_collected", datetime.now().strftime("%Y-%m-%d"))
        )
