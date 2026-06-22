"""
test_sheets_client.py - Unit tests for Google Sheets export behavior.
"""
from unittest.mock import MagicMock, patch

import pandas as pd

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import sheets_client


def test_sheet_rows_uses_configured_column_order():
    df = pd.DataFrame(
        [
            {
                "Business Name": "Acme Clinic",
                "Potential Category": "High",
                "Extra Column": "ignored",
            }
        ]
    )

    rows = sheets_client._sheet_rows(df)

    assert len(rows) == 1
    assert rows[0][0] == "Acme Clinic"
    assert rows[0][11] == "High"
    assert len(rows[0]) == len(sheets_client.SHEET_COLUMNS)


@patch("core.sheets_client.has_sheets_config", return_value=False)
def test_append_dataframe_requires_configuration(mock_config):
    df = pd.DataFrame([{"Business Name": "Acme"}])

    success, message = sheets_client.append_dataframe(df)

    assert success is False
    assert "Google Sheets not configured" in message


@patch("core.sheets_client.has_sheets_config", return_value=True)
def test_append_dataframe_rejects_empty_dataframe(mock_config):
    success, message = sheets_client.append_dataframe(pd.DataFrame())

    assert success is False
    assert "empty" in message.lower()


@patch("core.sheets_client._ensure_header")
@patch("core.sheets_client._get_worksheet")
@patch("core.sheets_client.has_sheets_config", return_value=True)
def test_append_dataframe_writes_rows(mock_config, mock_get_worksheet, mock_header):
    worksheet = MagicMock()
    mock_get_worksheet.return_value = worksheet
    df = pd.DataFrame(
        [
            {"Business Name": "Acme", "Potential Category": "High"},
            {"Business Name": "Beta", "Potential Category": "Medium"},
        ]
    )

    success, message = sheets_client.append_dataframe(df)

    assert success is True
    assert "2 leads" in message
    mock_header.assert_called_once_with(worksheet)
    worksheet.append_rows.assert_called_once()
    rows = worksheet.append_rows.call_args.args[0]
    assert rows[0][0] == "Acme"
    assert rows[1][0] == "Beta"


@patch("core.sheets_client._get_worksheet")
@patch("core.sheets_client.has_sheets_config", return_value=True)
def test_overwrite_sheet_clears_and_rewrites(mock_config, mock_get_worksheet):
    worksheet = MagicMock()
    mock_get_worksheet.return_value = worksheet
    df = pd.DataFrame([{"Business Name": "Acme", "Potential Category": "High"}])

    success, message = sheets_client.overwrite_sheet(df)

    assert success is True
    assert "1 leads" in message
    worksheet.clear.assert_called_once()
    worksheet.update.assert_called_once()
    values = worksheet.update.call_args.args[1]
    assert values[0] == sheets_client.SHEET_COLUMNS
    assert values[1][0] == "Acme"


def test_get_sheet_url_uses_spreadsheet_id():
    with patch.object(sheets_client, "SPREADSHEET_ID", "abc123"):
        assert sheets_client.get_sheet_url() == "https://docs.google.com/spreadsheets/d/abc123/edit"
