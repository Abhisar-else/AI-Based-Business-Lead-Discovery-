"""
sheets_client.py — Google Sheets Integration Module

Uses gspread + a GCP Service Account for authenticated writes.
Handles:
  - Auto-creating the header row if the sheet is empty
  - Batch row appending (thread-safe, rate-limit aware)
  - Full sheet overwrite mode (for dashboard refresh)
  - Graceful failure when credentials are missing
"""

import logging
import json
import time
from pathlib import Path
from typing import Optional

import pandas as pd

from core.config import (
    SPREADSHEET_ID,
    SHEET_NAME,
    GOOGLE_CREDENTIALS_PATH,
    GOOGLE_SERVICE_ACCOUNT_JSON,
    SHEET_COLUMNS,
    has_sheets_config,
)

logger = logging.getLogger(__name__)

# Google API rate limit: 60 writes/minute → ~1 write/second safe
_SHEETS_WRITE_DELAY = 1.2


# ─── Connection ───────────────────────────────────────────────────────────────

def _build_credentials(scopes: list[str]):
    """Build Google credentials from env JSON first, then local JSON file."""
    from google.oauth2.service_account import Credentials

    if GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        except json.JSONDecodeError as exc:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON.") from exc
        return Credentials.from_service_account_info(service_account_info, scopes=scopes)

    creds_path = Path(GOOGLE_CREDENTIALS_PATH)
    if not creds_path.exists():
        raise FileNotFoundError(
            f"Google credentials not found at: {creds_path}\n"
            "Add credentials/google_credentials.json or set GOOGLE_SERVICE_ACCOUNT_JSON."
        )

    return Credentials.from_service_account_file(str(creds_path), scopes=scopes)


def _sheet_rows(df: pd.DataFrame) -> list[list[str]]:
    """Return rows in the configured Sheet column order."""
    return df.reindex(columns=SHEET_COLUMNS, fill_value="").fillna("").astype(str).values.tolist()


def _get_worksheet():
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
        ]

        # Try Streamlit secrets first (cloud deployment)
        try:
            import streamlit as st
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        except Exception:
            # Fallback to local file (local development)
            from pathlib import Path
            creds_path = Path(GOOGLE_CREDENTIALS_PATH)
            if not creds_path.exists():
                raise FileNotFoundError(
                    f"Google credentials not found at: {creds_path}"
                )
            creds = Credentials.from_service_account_file(
                str(creds_path), scopes=scopes
            )

        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)

        try:
            worksheet = spreadsheet.worksheet(SHEET_NAME)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=SHEET_NAME,
                rows=1000,
                cols=len(SHEET_COLUMNS) + 2,
            )

        return worksheet

    except ImportError:
        raise ImportError("gspread or google-auth not installed")



def _ensure_header(worksheet) -> None:
    """Write the header row if the sheet is empty."""
    try:
        existing = worksheet.row_values(1)
        if not existing:
            worksheet.append_row(SHEET_COLUMNS, value_input_option="RAW")
            logger.info("Header row written to Google Sheet")
            time.sleep(_SHEETS_WRITE_DELAY)
    except Exception as exc:
        logger.warning(f"Could not check/write header row: {exc}")


# ─── Core Write Operations ────────────────────────────────────────────────────

def append_dataframe(df: pd.DataFrame) -> tuple[bool, str]:
    """
    Append all rows from a DataFrame to the Google Sheet.
    Creates the header row if the sheet is currently empty.

    Returns:
        (success: bool, message: str)
    """
    if not has_sheets_config():
        return False, (
            "Google Sheets not configured. "
            "Add SPREADSHEET_ID and credentials/google_credentials.json "
            "or GOOGLE_SERVICE_ACCOUNT_JSON."
        )

    if df.empty:
        return False, "No data to export — DataFrame is empty."

    try:
        worksheet = _get_worksheet()
        _ensure_header(worksheet)

        rows = _sheet_rows(df)

        # Batch append in chunks of 50 to stay within API limits
        chunk_size = 50
        total_written = 0

        for i in range(0, len(rows), chunk_size):
            chunk = rows[i : i + chunk_size]
            worksheet.append_rows(chunk, value_input_option="USER_ENTERED")
            total_written += len(chunk)
            logger.info(f"Appended {total_written}/{len(rows)} rows to Google Sheets")
            if i + chunk_size < len(rows):
                time.sleep(_SHEETS_WRITE_DELAY)

        msg = (
            f"✅ Successfully exported {total_written} leads to "
            f"Google Sheets → '{SHEET_NAME}'"
        )
        logger.info(msg)
        return True, msg

    except FileNotFoundError as exc:
        return False, str(exc)
    except Exception as exc:
        error_msg = f"Google Sheets export failed: {exc}"
        logger.error(error_msg)
        return False, error_msg


def overwrite_sheet(df: pd.DataFrame) -> tuple[bool, str]:
    """
    Clear the sheet and rewrite all data (full refresh mode).
    Useful for keeping the sheet in sync with the latest pipeline run.
    """
    if not has_sheets_config():
        return False, "Google Sheets not configured."

    try:
        worksheet = _get_worksheet()
        worksheet.clear()
        logger.info("Cleared existing Google Sheet data")
        time.sleep(_SHEETS_WRITE_DELAY)

        all_rows = [SHEET_COLUMNS] + _sheet_rows(df)
        worksheet.update(f"A1", all_rows, value_input_option="RAW")

        msg = f"✅ Sheet refreshed with {len(df)} leads"
        logger.info(msg)
        return True, msg

    except Exception as exc:
        error_msg = f"Sheet overwrite failed: {exc}"
        logger.error(error_msg)
        return False, error_msg


def get_sheet_url() -> str:
    """Return the direct URL to open the Google Sheet in a browser."""
    if not SPREADSHEET_ID or SPREADSHEET_ID == "your-google-spreadsheet-id-here":
        return ""
    return f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit"


def test_connection() -> tuple[bool, str]:
    """
    Test the Google Sheets connection without writing any data.
    Returns (success, message) suitable for Streamlit status display.
    """
    if not has_sheets_config():
        return False, "Missing credentials or Spreadsheet ID in .env"
    try:
        worksheet = _get_worksheet()
        title = worksheet.title
        return True, f"✅ Connected to sheet: '{title}'"
    except Exception as exc:
        return False, f"❌ Connection failed: {exc}"
