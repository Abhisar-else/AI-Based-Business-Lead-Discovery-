"""
config.py — Centralized configuration for the Business Lead Discovery System.

All settings are loaded from environment variables (via .env file).
Never hard-code secrets here!
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env")

# ─── AI Provider ──────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# Gemini model to use (Flash = fast + cheap, great for classification tasks)
GEMINI_MODEL: str = "gemini-1.5-flash"

# ─── Data Collection ──────────────────────────────────────────────────────────
# Serper.dev API key for Google Maps structured data
# Sign up at https://serper.dev
SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")

# ─── Google Sheets ────────────────────────────────────────────────────────────
SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "")
SHEET_NAME: str = os.getenv("SHEET_NAME", "Business Leads")
GOOGLE_CREDENTIALS_PATH: str = os.getenv(
    "GOOGLE_CREDENTIALS_PATH",
    str(_project_root / "credentials" / "google_credentials.json")
)

# ─── Business Categories ──────────────────────────────────────────────────────
TARGET_CATEGORIES: list[str] = [
    "Manufacturing",
    "Real Estate",
    "Hotels and Resorts",
    "Educational Institutes",
    "Healthcare",
    "Retail",
    "Restaurants and Cafes",
    "Professional Services",
]

# ─── Scraping Settings ────────────────────────────────────────────────────────
# Maximum number of leads to collect per search query
MAX_RESULTS: int = 20

# Seconds to wait between HTTP requests (be respectful to servers!)
RATE_LIMIT_DELAY: float = 2.0

# HTTP request timeout in seconds
WEBSITE_TIMEOUT: int = 8

# Maximum number of retries for failed requests
MAX_RETRIES: int = 3

# ─── Website Audit Thresholds ────────────────────────────────────────────────
# Page response time (seconds) above which site is classified "Poor Website"
SLOW_SITE_THRESHOLD: float = 5.0

# ─── Data Paths ───────────────────────────────────────────────────────────────
DATA_DIR: Path = _project_root / "data"
LEADS_CACHE_PATH: Path = DATA_DIR / "leads_cache.csv"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# ─── Output Schema ────────────────────────────────────────────────────────────
# Column order for Google Sheets and CSV export
SHEET_COLUMNS: list[str] = [
    "Business Name",
    "Industry Category",
    "Business Description",
    "Location",
    "Google Maps Link",
    "Website URL",
    "Website Status",
    "Phone Number",
    "Email Address",
    "Owner / Founder",
    "LinkedIn Profile",
    "Potential Category",
    "Reasoning",
    "Collected At",
]

# ─── Validation Helpers ───────────────────────────────────────────────────────
def has_gemini_key() -> bool:
    return bool(GEMINI_API_KEY and GEMINI_API_KEY != "your-gemini-api-key-here")

def has_openai_key() -> bool:
    return bool(OPENAI_API_KEY and OPENAI_API_KEY != "your-openai-api-key-here")

def has_serper_key() -> bool:
    return bool(SERPER_API_KEY and SERPER_API_KEY != "your-serper-api-key-here")

def has_sheets_config() -> bool:
    return bool(
        SPREADSHEET_ID
        and SPREADSHEET_ID != "your-google-spreadsheet-id-here"
        and Path(GOOGLE_CREDENTIALS_PATH).exists()
    )
