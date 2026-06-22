"""
test_scraper.py — Unit tests for the data collection module.
"""
import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.scraper import (
    search_businesses,
    extract_contact_info,
    _clean_phone,
    _safe_get,
)


class TestCleanPhone:
    """Test phone number cleaning utility."""

    def test_indian_mobile(self):
        assert _clean_phone("9876543210") != ""

    def test_with_country_code(self):
        assert _clean_phone("+91-98765-43210") != ""

    def test_empty_input(self):
        assert _clean_phone("") == ""
        assert _clean_phone(None) == ""

    def test_too_short(self):
        assert _clean_phone("123") == ""

    def test_strips_junk(self):
        result = _clean_phone("  (555) 123-4567  ")
        assert result.strip() != ""


class TestExtractContactInfo:
    """Test contact extraction from websites."""

    def test_empty_url(self):
        info = extract_contact_info("")
        assert info["email_address"] == ""
        assert info["phone_number"] == ""
        assert info["linkedin_profile"] == ""

    def test_none_url(self):
        info = extract_contact_info(None)
        assert info["email_address"] == ""

    @patch("core.scraper._safe_get")
    def test_extracts_email_from_html(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = """
        <html><body>
            Contact us at info@testcompany.com
            <a href="https://linkedin.com/company/testco">LinkedIn</a>
            Call: +91 98765 43210
        </body></html>
        """
        mock_get.return_value = mock_resp

        info = extract_contact_info("https://testcompany.com")
        assert info["email_address"] == "info@testcompany.com"
        assert "linkedin.com" in info["linkedin_profile"]

    @patch("core.scraper._safe_get")
    def test_filters_example_emails(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = '<html><body>user@example.com test@test.com</body></html>'
        mock_get.return_value = mock_resp

        info = extract_contact_info("https://example.com")
        # Both should be filtered as false positives
        assert "example.com" not in info["email_address"]


class TestSearchBusinesses:
    """Test the main search orchestration function."""

    @patch("core.scraper._search_via_serper")
    @patch("core.scraper._search_via_justdial")
    @patch("core.scraper._search_via_sulekha")
    @patch("core.scraper.has_serper_key", return_value=False)
    def test_returns_list(self, mock_key, mock_sulekha, mock_jd, mock_serp):
        """Should return a list even if all sources return empty."""
        mock_jd.return_value = []
        mock_sulekha.return_value = []

        results = search_businesses("Hotels", "Indore", max_results=5)
        assert isinstance(results, list)

    @patch("core.scraper._search_via_serper")
    @patch("core.scraper.has_serper_key", return_value=True)
    def test_serper_results_passed_through(self, mock_key, mock_serp):
        """Serper.dev results should appear in the output."""
        mock_serp.return_value = [
            {
                "business_name": "Test Hotel",
                "industry_category": "Hotels",
                "business_description": "",
                "location": "Indore",
                "google_maps_link": "",
                "website_url": "",
                "phone_number": "",
                "email_address": "",
                "owner_founder": "",
                "linkedin_profile": "",
                "source": "serper_google_maps",
                "collected_at": "2024-01-01",
            }
        ]

        results = search_businesses("Hotels", "Indore", max_results=1)
        assert len(results) >= 1
        assert results[0]["business_name"] == "Test Hotel"

    def test_respects_max_results(self):
        """Output should never exceed max_results."""
        with patch("core.scraper.has_serper_key", return_value=False), \
             patch("core.scraper._search_via_justdial", return_value=[
                 {"business_name": f"Biz {i}", "website_url": ""} for i in range(10)
             ]), \
             patch("core.scraper._search_via_sulekha", return_value=[]):

            results = search_businesses("Test", "City", max_results=3)
            assert len(results) <= 3
