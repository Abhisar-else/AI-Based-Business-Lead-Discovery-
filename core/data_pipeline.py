"""
data_pipeline.py — Data Processing & Cleaning Module

Handles:
  - Deduplication by business name + location
  - Phone / email normalization
  - Column standardization to match SHEET_COLUMNS schema
  - Local CSV caching
  - Filtering by potential category
"""

import re
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from core.config import SHEET_COLUMNS, LEADS_CACHE_PATH

logger = logging.getLogger(__name__)


# ─── Main Processing Functions ────────────────────────────────────────────────

def build_dataframe(raw_leads: list[dict]) -> pd.DataFrame:
    """
    Convert a list of raw business dicts (from scraper + analyzer) into
    a clean, schema-conformant DataFrame.
    """
    if not raw_leads:
        return pd.DataFrame(columns=SHEET_COLUMNS)

    df = pd.DataFrame(raw_leads)

    # Rename internal keys → display columns
    rename_map = {
        "business_name":       "Business Name",
        "industry_category":   "Industry Category",
        "business_description":"Business Description",
        "location":            "Location",
        "google_maps_link":    "Google Maps Link",
        "website_url":         "Website URL",
        "website_status":      "Website Status",
        "phone_number":        "Phone Number",
        "email_address":       "Email Address",
        "owner_founder":       "Owner / Founder",
        "linkedin_profile":    "LinkedIn Profile",
        "potential_category":  "Potential Category",
        "reasoning":           "Reasoning",
         "ai_summary":          "AI Summary",        
        "collected_at":        "Collected At",
    }
    df = df.rename(columns=rename_map)

    # Add any missing columns with empty defaults
    for col in SHEET_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # Reorder to canonical schema
    df = df[SHEET_COLUMNS]

    return df


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply data quality transforms:
      1. Strip leading/trailing whitespace from all string fields
      2. Normalize phone numbers
      3. Lowercase and trim emails
      4. Deduplicate on Business Name + Location
      5. Fill NA with empty string
    """
    if df.empty:
        return df

    df = df.copy()

    # 1. Strip whitespace from all object columns
    str_cols = df.select_dtypes(include="object").columns
    df[str_cols] = df[str_cols].apply(
        lambda col: col.str.strip() if col.dtype == "object" else col
    )

    # 2. Normalize phone numbers
    if "Phone Number" in df.columns:
        df["Phone Number"] = df["Phone Number"].apply(_normalize_phone)
    # 3. Lowercase emails
    if "Email Address" in df.columns:
        df["Email Address"] = df["Email Address"].str.lower().str.strip()

    # 4. Deduplicate: keep first occurrence of name+location combo
    before = len(df)
    df = df.drop_duplicates(
        subset=["Business Name", "Location"],
        keep="first"
    ).reset_index(drop=True)
    dupes_removed = before - len(df)
    if dupes_removed > 0:
        logger.info(f"Removed {dupes_removed} duplicate entries")

    # 5. Drop rows with no business name
    df = df[df["Business Name"].notna() & (df["Business Name"] != "")]

    # 6. Replace NaN with empty string for Sheets compatibility
    df = df.fillna("")

    # 7. Add timestamps if missing
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if "Collected At" in df.columns:
        df["Collected At"] = df["Collected At"].replace("", now)

    return df.reset_index(drop=True)


def filter_by_potential(
    df: pd.DataFrame,
    include: tuple[str , ...] = ("High", "Medium", "Low")
) -> pd.DataFrame:
    """Filter leads by Potential Category."""
    if df.empty or "Potential Category" not in df.columns:
        return df
    return df[df["Potential Category"].isin(include)].reset_index(drop=True)


def filter_by_website_status(
    df: pd.DataFrame,
    statuses: list[str] = ("No Website", "Poor Website", "Good Website", "Check Failed")
) -> pd.DataFrame:
    """Filter leads by Website Status."""
    if df.empty or "Website Status" not in df.columns:
        return df
    return df[df["Website Status"].isin(statuses)].reset_index(drop=True)


# ─── Summary Stats ────────────────────────────────────────────────────────────

def get_summary_stats(df: pd.DataFrame) -> dict:
    """
    Compute dashboard KPI stats from a processed DataFrame.
    Returns a dict suitable for Streamlit metric cards.
    """
    if df.empty:
        return {
            "total": 0,
            "high": 0, "medium": 0, "low": 0,
            "no_website": 0, "poor_website": 0, "good_website": 0,
            "with_email": 0, "with_phone": 0,
        }

    def _count(col: str, val: str) -> int:
        if col not in df.columns:
            return 0
        return int((df[col] == val).sum())

    return {
        "total":        len(df),
        "high":         _count("Potential Category", "High"),
        "medium":       _count("Potential Category", "Medium"),
        "low":          _count("Potential Category", "Low"),
        "no_website":   _count("Website Status", "No Website"),
        "poor_website": _count("Website Status", "Poor Website"),
        "good_website": _count("Website Status", "Good Website"),
        "with_email":   int(df["Email Address"].ne("").sum()) if "Email Address" in df.columns else 0,
        "with_phone":   int(df["Phone Number"].ne("").sum()) if "Phone Number" in df.columns else 0,
    }


# ─── Local CSV Cache ──────────────────────────────────────────────────────────

def save_to_csv(df: pd.DataFrame, path: Path = LEADS_CACHE_PATH) -> Path:
    """Save DataFrame to local CSV cache. Returns the path."""
    path.parent.mkdir(exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    logger.info(f"Saved {len(df)} leads to {path}")
    return path


def load_from_csv(path: Path = LEADS_CACHE_PATH) -> pd.DataFrame:
    """Load previously cached leads. Returns empty DataFrame if file not found."""
    if not path.exists():
        return pd.DataFrame(columns=SHEET_COLUMNS)
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
        logger.info(f"Loaded {len(df)} cached leads from {path}")
        return df
    except Exception as exc:
        logger.error(f"Failed to load CSV cache: {exc}")
        return pd.DataFrame(columns=SHEET_COLUMNS)


def export_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """
    Convert DataFrame to CSV bytes for Streamlit download button.
    """
    return df.to_csv(index=False, encoding="utf-8").encode("utf-8")


# ─── Utility Functions ────────────────────────────────────────────────────────

def _normalize_phone(raw: str) -> str:
    """
    Normalize phone numbers to a consistent format.
    Handles Indian (10-digit) and international numbers.
    """
    if not raw or not isinstance(raw, str):
        return ""

    digits = re.sub(r"\D", "", raw)

    # Indian mobile: 10 digits starting with 6-9
    if len(digits) == 10 and digits[0] in "6789":
        return f"+91 {digits[:5]} {digits[5:]}"

    # Indian with country code: 12 digits starting with 91
    if len(digits) == 12 and digits[:2] == "91":
        d = digits[2:]
        return f"+91 {d[:5]} {d[5:]}"
# Indian with leading 0: 11 digits starting with 0
    if len(digits) == 11 and digits[0] == "0":
        d = digits[1:]
        if d[0] in "6789":
           return f"+91 {d[:5]} {d[5:]}"

    # US format
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    # International with country code
    if len(digits) == 11 and digits[0] == "1":
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

    # Return as-is if unrecognized
    return raw.strip()
