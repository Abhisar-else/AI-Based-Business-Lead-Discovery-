"""
test_analyzer.py — Unit tests for the AI analysis module.
"""
import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.analyzer import (
    analyze_business,
    _analyze_with_heuristics,
    get_analysis_mode,
)


# ─── Sample Business Data ────────────────────────────────────────────────────

BIZ_NO_WEBSITE = {
    "business_name": "Sunrise Manufacturing",
    "industry_category": "Manufacturing",
    "location": "Indore",
    "website_status": "No Website",
    "phone_number": "9876543210",
    "email_address": "",
    "website_url": "",
}

BIZ_POOR_NO_CONTACT = {
    "business_name": "Old Hotel",
    "industry_category": "Hotels",
    "location": "Bhopal",
    "website_status": "Poor Website",
    "phone_number": "",
    "email_address": "",
    "website_url": "http://old-hotel.com",
}

BIZ_POOR_WITH_CONTACT = {
    "business_name": "City Clinic",
    "industry_category": "Healthcare",
    "location": "Delhi",
    "website_status": "Poor Website",
    "phone_number": "9988776655",
    "email_address": "info@cityclinic.in",
    "website_url": "http://cityclinic.in",
}

BIZ_GOOD = {
    "business_name": "TechCorp Solutions",
    "industry_category": "Professional Services",
    "location": "Bangalore",
    "website_status": "Good Website",
    "phone_number": "1234567890",
    "email_address": "hello@techcorp.io",
    "website_url": "https://techcorp.io",
}


class TestHeuristicAnalysis:
    """Test the deterministic heuristic classifier."""

    def test_no_website_is_high(self):
        result = _analyze_with_heuristics(BIZ_NO_WEBSITE)
        assert result["potential_category"] == "High"
        assert "no online presence" in result["reasoning"].lower()

    def test_poor_no_contact_is_high(self):
        result = _analyze_with_heuristics(BIZ_POOR_NO_CONTACT)
        assert result["potential_category"] == "High"

    def test_poor_with_contact_is_medium(self):
        result = _analyze_with_heuristics(BIZ_POOR_WITH_CONTACT)
        assert result["potential_category"] == "Medium"

    def test_good_website_is_low(self):
        result = _analyze_with_heuristics(BIZ_GOOD)
        assert result["potential_category"] == "Low"

    def test_always_returns_required_keys(self):
        for biz in [BIZ_NO_WEBSITE, BIZ_POOR_NO_CONTACT, BIZ_POOR_WITH_CONTACT, BIZ_GOOD]:
            result = _analyze_with_heuristics(biz)
            assert "potential_category" in result
            assert "reasoning" in result
            assert result["potential_category"] in ("High", "Medium", "Low")

    def test_empty_business_returns_medium(self):
        result = _analyze_with_heuristics({})
        assert result["potential_category"] == "Medium"


class TestAnalyzeBusiness:
    """Test the main analyze_business function with mocked AI providers."""

    @patch("core.analyzer.has_gemini_key", return_value=False)
    @patch("core.analyzer.has_openai_key", return_value=False)
    def test_falls_back_to_heuristic(self, mock_openai, mock_gemini):
        result = analyze_business(BIZ_NO_WEBSITE)
        assert result["potential_category"] == "High"
        assert result["analysis_source"] == "heuristic"

    @patch("core.analyzer.has_gemini_key", return_value=True)
    @patch("core.analyzer._analyze_with_gemini")
    def test_uses_gemini_when_available(self, mock_gemini_fn, mock_key):
        mock_gemini_fn.return_value = {
            "potential_category": "High",
            "reasoning": "AI says this is high potential",
        }
        result = analyze_business(BIZ_NO_WEBSITE)
        assert result["potential_category"] == "High"
        assert result["analysis_source"] == "gemini"

    @patch("core.analyzer.has_gemini_key", return_value=True)
    @patch("core.analyzer._analyze_with_gemini", return_value=None)
    @patch("core.analyzer.has_openai_key", return_value=False)
    def test_gemini_failure_falls_to_heuristic(self, mock_oai, mock_gem_fn, mock_key):
        result = analyze_business(BIZ_GOOD)
        assert result["analysis_source"] == "heuristic"

    @patch("core.analyzer.has_gemini_key", return_value=False)
    @patch("core.analyzer.has_openai_key", return_value=True)
    @patch("core.analyzer._analyze_with_openai")
    def test_openai_fallback(self, mock_oai_fn, mock_oai_key, mock_gem_key):
        mock_oai_fn.return_value = {
            "potential_category": "Medium",
            "reasoning": "OpenAI analysis",
        }
        result = analyze_business(BIZ_POOR_WITH_CONTACT)
        assert result["analysis_source"] == "openai"


class TestGetAnalysisMode:
    """Test the human-readable analysis mode reporter."""

    @patch("core.analyzer.has_gemini_key", return_value=True)
    def test_gemini_mode(self, mock_key):
        mode = get_analysis_mode()
        assert "Gemini" in mode

    @patch("core.analyzer.has_gemini_key", return_value=False)
    @patch("core.analyzer.has_openai_key", return_value=True)
    def test_openai_mode(self, mock_oai, mock_gem):
        mode = get_analysis_mode()
        assert "OpenAI" in mode

    @patch("core.analyzer.has_gemini_key", return_value=False)
    @patch("core.analyzer.has_openai_key", return_value=False)
    def test_heuristic_mode(self, mock_oai, mock_gem):
        mode = get_analysis_mode()
        assert "Heuristic" in mode
