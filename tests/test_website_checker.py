"""
test_website_checker.py — Unit tests for the website auditing module.
"""
import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.website_checker import (
    check_website,
    _is_mobile_friendly,
    _has_contact_info,
    _classify,
    WebsiteStatus,
)
from bs4 import BeautifulSoup


class TestCheckWebsite:
    """Test the main check_website function."""

    def test_no_url(self):
        result = check_website(None)
        assert result.status == "No Website"

    def test_empty_url(self):
        result = check_website("")
        assert result.status == "No Website"

    def test_whitespace_url(self):
        result = check_website("   ")
        assert result.status == "No Website"

    @patch("core.website_checker._check_with_requests")
    def test_unreachable_site(self, mock_check):
        mock_check.return_value = WebsiteStatus(
            url="https://dead-site.com",
            is_reachable=False,
            issues=["Connection refused"],
        )
        # Also patch Selenium so it doesn't actually launch
        with patch("core.website_checker._check_with_selenium") as mock_sel:
            mock_sel.return_value = WebsiteStatus(
                url="https://dead-site.com",
                is_reachable=False,
            )
            result = check_website("https://dead-site.com")
            assert result.status == "No Website"

    @patch("core.website_checker._check_with_requests")
    def test_good_website(self, mock_check):
        mock_check.return_value = WebsiteStatus(
            url="https://good-site.com",
            is_reachable=True,
            has_ssl=True,
            is_mobile_friendly=True,
            load_time=1.2,
            has_contact_info=True,
        )
        result = check_website("https://good-site.com")
        assert result.status == "Good Website"

    @patch("core.website_checker._check_with_requests")
    def test_poor_website_no_ssl_no_mobile(self, mock_check):
        mock_check.return_value = WebsiteStatus(
            url="http://old-site.com",
            is_reachable=True,
            has_ssl=False,
            is_mobile_friendly=False,
            load_time=2.0,
            has_contact_info=True,
        )
        result = check_website("http://old-site.com")
        assert result.status == "Poor Website"


class TestMobileFriendly:
    """Test viewport/responsive detection."""

    def test_has_viewport(self):
        html = '<html><head><meta name="viewport" content="width=device-width"></head></html>'
        soup = BeautifulSoup(html, "lxml")
        assert _is_mobile_friendly(soup) is True

    def test_no_viewport(self):
        html = "<html><head><title>Old Site</title></head><body></body></html>"
        soup = BeautifulSoup(html, "lxml")
        assert _is_mobile_friendly(soup) is False

    def test_bootstrap_detected(self):
        html = '<html><head><link rel="stylesheet" href="https://cdn.bootstrap.min.css"></head></html>'
        soup = BeautifulSoup(html, "lxml")
        assert _is_mobile_friendly(soup) is True

    def test_media_query_in_style(self):
        html = "<html><head><style>@media (max-width: 768px) { .foo {} }</style></head></html>"
        soup = BeautifulSoup(html, "lxml")
        assert _is_mobile_friendly(soup) is True


class TestHasContactInfo:
    """Test contact info detection."""

    def test_has_email(self):
        html = "<html><body>Email: info@company.com</body></html>"
        soup = BeautifulSoup(html, "lxml")
        assert _has_contact_info(soup) is True

    def test_has_phone(self):
        html = "<html><body>Call us: 9876543210</body></html>"
        soup = BeautifulSoup(html, "lxml")
        assert _has_contact_info(soup) is True

    def test_has_tel_link(self):
        html = '<html><body><a href="tel:+919876543210">Call</a></body></html>'
        soup = BeautifulSoup(html, "lxml")
        assert _has_contact_info(soup) is True

    def test_no_contact(self):
        html = "<html><body>Welcome to our site</body></html>"
        soup = BeautifulSoup(html, "lxml")
        assert _has_contact_info(soup) is False


class TestClassify:
    """Test the _classify decision logic."""

    def test_unreachable_is_no_website(self):
        s = WebsiteStatus(url="x", is_reachable=False)
        assert _classify(s) == "No Website"

    def test_all_good(self):
        s = WebsiteStatus(
            url="x", is_reachable=True,
            has_ssl=True, is_mobile_friendly=True,
            load_time=1.0, has_contact_info=True,
        )
        assert _classify(s) == "Good Website"

    def test_no_ssl_no_mobile_is_poor(self):
        s = WebsiteStatus(
            url="x", is_reachable=True,
            has_ssl=False, is_mobile_friendly=False,
            load_time=1.0, has_contact_info=True,
        )
        assert _classify(s) == "Poor Website"

    def test_slow_no_contact_is_poor(self):
        s = WebsiteStatus(
            url="x", is_reachable=True,
            has_ssl=True, is_mobile_friendly=True,
            load_time=8.0, has_contact_info=False,
        )
        assert _classify(s) == "Poor Website"
