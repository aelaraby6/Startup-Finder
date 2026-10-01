import logging
import sys
from typing import List

# Supported Startup Categories
CATEGORIES: List[str] = [
    "Software",
    "AI",
    "SaaS",
    "FinTech",
    "HealthTech",
    "EdTech",
    "Cybersecurity",
    "Cloud",
    "DevTools",
    "E-commerce",
    "Gaming",
    "Robotics",
    "Blockchain",
    "Data",
    "Mobile"
]

# Supported Countries 
COUNTRIES: List[str] = [
    # Middle East & North Africa
    "Saudi Arabia",
    "United Arab Emirates",
    "Egypt",
    "Qatar",
    "Kuwait",
    "Bahrain",
    "Oman",
    "Jordan",
    "Lebanon",
    "Morocco",
    "Tunisia",
    
    # North & South America
    "United States",
    "Canada",
    "Brazil",
    "Mexico",
    "Argentina",
    "Chile",
    "Colombia",
    
    # Asia & Pacific / Oceania
    "Australia",
    "New Zealand",
    "India",
    "Singapore",
    "Japan",
    "South Korea",
    "China",
    "Hong Kong",
    "Taiwan",
    "Indonesia",
    "Malaysia",
    "Vietnam",
    "Philippines",
    "Thailand",
    "Pakistan",
    
    # All European Countries (including Scandinavia / Nordic)
    "Albania",
    "Andorra",
    "Austria",
    "Belarus",
    "Belgium",
    "Bosnia and Herzegovina",
    "Bulgaria",
    "Croatia",
    "Cyprus",
    "Czech Republic",
    "Denmark",
    "Estonia",
    "Finland",
    "France",
    "Germany",
    "Greece",
    "Hungary",
    "Iceland",
    "Ireland",
    "Italy",
    "Kosovo",
    "Latvia",
    "Liechtenstein",
    "Lithuania",
    "Luxembourg",
    "Malta",
    "Moldova",
    "Monaco",
    "Montenegro",
    "Netherlands",
    "North Macedonia",
    "Norway",
    "Poland",
    "Portugal",
    "Romania",
    "Russia",
    "San Marino",
    "Serbia",
    "Slovakia",
    "Slovenia",
    "Spain",
    "Sweden",
    "Switzerland",
    "Ukraine",
    "United Kingdom",
    "Vatican City",
    
    # Africa
    "South Africa",
    "Nigeria",
    "Kenya",
    "Ghana",
    "Rwanda"
]

# Request Configuration
DEFAULT_TIMEOUT: int = 15  # seconds
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Live Logging Capture for Streamlit UI
class StreamlitLogHandler(logging.Handler):
    """
    A thread-safe logging handler that buffers log messages in memory
    so they can be retrieved and displayed live in the Streamlit UI.
    """
    def __init__(self):
        super().__init__()
        self.logs: List[str] = []

    def emit(self, record):
        try:
            msg = self.format(record)
            self.logs.append(msg)
        except Exception:
            self.handleError(record)

    def get_new_logs(self) -> List[str]:
        logs_copy = list(self.logs)
        return logs_copy

    def clear(self):
        self.logs.clear()

# Setup Logger
logger = logging.getLogger("startup_finder")
logger.setLevel(logging.INFO)

# Avoid duplicate handlers
if not logger.handlers:
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Streamlit live handler
    streamlit_handler = StreamlitLogHandler()
    streamlit_formatter = logging.Formatter("[%(levelname)s] %(message)s")
    streamlit_handler.setFormatter(streamlit_formatter)
    logger.addHandler(streamlit_handler)
else:
    # Find existing streamlit handler if config is re-imported
    streamlit_handler = None
    for h in logger.handlers:
        if isinstance(h, StreamlitLogHandler):
            streamlit_handler = h
            break
    if streamlit_handler is None:
        streamlit_handler = StreamlitLogHandler()
        streamlit_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(streamlit_handler)

def get_streamlit_handler() -> StreamlitLogHandler:
    return streamlit_handler
