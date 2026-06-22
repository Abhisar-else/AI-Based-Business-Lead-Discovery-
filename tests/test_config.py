"""
test_config.py - Unit tests for configuration helpers.
"""
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import config


def test_sheets_config_status_reports_missing_credentials(tmp_path):
    missing_path = tmp_path / "missing.json"

    with patch.object(config, "SPREADSHEET_ID", "sheet123"), \
         patch.object(config, "GOOGLE_CREDENTIALS_PATH", str(missing_path)), \
         patch.object(config, "GOOGLE_SERVICE_ACCOUNT_JSON", ""), \
         patch.object(config, "SHEET_NAME", "Business Leads"):

        status = config.get_sheets_config_status()

    assert status["has_spreadsheet_id"] is True
    assert status["has_credentials"] is False
    assert status["credentials_path"] == str(missing_path)
    assert status["credential_source"] == ""


def test_sheets_config_status_accepts_env_json():
    with patch.object(config, "SPREADSHEET_ID", "sheet123"), \
         patch.object(config, "GOOGLE_CREDENTIALS_PATH", "credentials/google_credentials.json"), \
         patch.object(config, "GOOGLE_SERVICE_ACCOUNT_JSON", '{"type":"service_account"}'), \
         patch.object(config, "SHEET_NAME", "Business Leads"):

        status = config.get_sheets_config_status()

    assert status["has_spreadsheet_id"] is True
    assert status["has_credentials"] is True
    assert status["credential_source"] == "GOOGLE_SERVICE_ACCOUNT_JSON"
