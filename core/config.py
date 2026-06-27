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
GOOGLE_SERVICE_ACCOUNT_JSON: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

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
WEBSITE_TIMEOUT: int = 4

# Maximum number of retries for failed requests
MAX_RETRIES: int = 3

# ─── Website Audit Thresholds ────────────────────────────────────────────────
# Page response time (seconds) above which site is classified "Poor Website"
SLOW_SITE_THRESHOLD: float = 5.0

# Sentinel value used when a website audit raises an exception (distinct from
# "No Website" which means the business genuinely has no URL or the URL is dead).
WEBSITE_STATUS_CHECK_FAILED: str = "Check Failed"

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
    "AI Summary",
    "Collected At",
]

# ─── Validation Helpers ───────────────────────────────────────────────────────

def has_gemini_key() -> bool:
    try:
        import streamlit as st
        key = st.secrets.get("GEMINI_API_KEY", GEMINI_API_KEY)
    except Exception:
        key = GEMINI_API_KEY
    return bool(key and key != "your-gemini-api-key-here")

def has_openai_key() -> bool:
    return bool(OPENAI_API_KEY and OPENAI_API_KEY != "your-openai-api-key-here")

def has_serper_key() -> bool:
    try:
        import streamlit as st
        key = st.secrets.get("SERPER_API_KEY", SERPER_API_KEY)
    except Exception:
        key = SERPER_API_KEY
    return bool(key and key != "your-serper-api-key-here")

# ─── Aliases for scraper.py compatibility ─────────────────────────────────────
# has_serpapi_key kept for backward compatibility with scraper.py import
def has_serpapi_key() -> bool:
    return has_serper_key()

def has_sheets_config() -> bool:
    has_spreadsheet = bool(
        SPREADSHEET_ID
        and SPREADSHEET_ID != "your-google-spreadsheet-id-here"
        and SPREADSHEET_ID != "your-google-spreadsheet-id"
    )
    if not has_spreadsheet:
        try:
            import streamlit as st
            has_spreadsheet = bool(st.secrets.get("SPREADSHEET_ID"))
        except Exception:
            pass
    if not has_spreadsheet:
        return False
    # Check Streamlit secrets (cloud)
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            return True
    except Exception:
        pass
    # Check local env or file
    return bool(
        GOOGLE_SERVICE_ACCOUNT_JSON
        or Path(GOOGLE_CREDENTIALS_PATH).exists()
    )

def get_sheets_config_status() -> dict[str, object]:
    """Return Google Sheets setup status without exposing secret values."""
    creds_path = Path(GOOGLE_CREDENTIALS_PATH)
    has_service_account_json = bool(GOOGLE_SERVICE_ACCOUNT_JSON.strip())
    has_credentials_file = creds_path.exists()
    has_spreadsheet = bool(
        SPREADSHEET_ID
        and SPREADSHEET_ID != "your-google-spreadsheet-id-here"
        and SPREADSHEET_ID != "your-google-spreadsheet-id"
    )
    try:
        import streamlit as st
        has_streamlit_secrets = "gcp_service_account" in st.secrets
        if not has_spreadsheet:
            has_spreadsheet = bool(st.secrets.get("SPREADSHEET_ID"))
    except Exception:
        has_streamlit_secrets = False

    if has_streamlit_secrets:
        credential_source = "Streamlit Secrets"
    elif has_service_account_json:
        credential_source = "GOOGLE_SERVICE_ACCOUNT_JSON"
    elif has_credentials_file:
        credential_source = str(creds_path)
    else:
        credential_source = ""

    return {
        "has_spreadsheet_id": has_spreadsheet,
        "has_credentials": has_service_account_json or has_credentials_file or has_streamlit_secrets,
        "credentials_path": str(creds_path),
        "credential_source": credential_source,
        "sheet_name": SHEET_NAME,
    }