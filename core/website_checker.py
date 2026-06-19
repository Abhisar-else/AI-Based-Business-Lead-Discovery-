"""
website_checker.py — Digital Audit Module

Classifies business websites into:
  - "No Website"   → URL missing, 404, connection refused, timeout
  - "Poor Website" → No HTTPS, no viewport meta, slow load, no contact info
  - "Good Website" → Passes all quality checks

Strategy:
  1. requests + BeautifulSoup (fast path for most sites)
  2. Selenium fallback for JS-heavy/gated sites
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Optional

import requests
from bs4 import BeautifulSoup

from core.config import WEBSITE_TIMEOUT, SLOW_SITE_THRESHOLD

logger = logging.getLogger(__name__)

# ─── Result Schema ────────────────────────────────────────────────────────────

@dataclass
class WebsiteStatus:
    status: str           # "No Website" | "Poor Website" | "Good Website"
    url: str = ""
    has_ssl: bool = False
    is_mobile_friendly: bool = False
    load_time: float = 0.0
    has_contact_info: bool = False
    is_reachable: bool = False
    details: str = ""
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "website_status": self.status,
            "website_details": self.details,
        }


# ─── Core Check Logic ─────────────────────────────────────────────────────────

def check_website(url: Optional[str]) -> WebsiteStatus:
    """
    Main entry point. Analyzes a business URL and returns a WebsiteStatus.
    Falls back to Selenium if requests gets a JS-block response (403/JS redirect).
    """
    if not url or not url.strip():
        return WebsiteStatus(
            status="No Website",
            details="No website URL provided in the listing.",
        )

    # Normalize URL
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    result = _check_with_requests(url)

    # Selenium fallback if blocked or JS-rendered
    if not result.is_reachable:
        logger.info(f"Requests failed for {url} — trying Selenium fallback")
        result = _check_with_selenium(url)

    # Final classification
    result.status = _classify(result)
    result.details = _build_detail_string(result)
    return result


def _check_with_requests(url: str) -> WebsiteStatus:
    """Fast HTTP check using requests + BeautifulSoup."""
    result = WebsiteStatus(url=url)

    try:
        start = time.perf_counter()
        resp = requests.get(
            url,
            timeout=WEBSITE_TIMEOUT,
            allow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
                )
            },
        )
        result.load_time = time.perf_counter() - start
        result.is_reachable = resp.status_code < 400
        result.has_ssl = resp.url.startswith("https://")

        if result.is_reachable:
            soup = BeautifulSoup(resp.text, "lxml")
            result.is_mobile_friendly = _is_mobile_friendly(soup)
            result.has_contact_info   = _has_contact_info(soup)

            if resp.status_code in (403, 429):
                # Might be JS-gated — mark unreachable to trigger Selenium
                result.is_reachable = False

    except requests.exceptions.SSLError:
        result.is_reachable = True   # Site exists but has SSL issues
        result.has_ssl = False
        result.issues.append("SSL certificate error")

    except requests.exceptions.ConnectionError:
        result.is_reachable = False
        result.issues.append("Connection refused or DNS failure")

    except requests.exceptions.Timeout:
        result.is_reachable = False
        result.issues.append(f"Timed out after {WEBSITE_TIMEOUT}s")

    except Exception as exc:
        result.is_reachable = False
        result.issues.append(str(exc))
        logger.debug(f"Requests check error for {url}: {exc}")

    return result


def _check_with_selenium(url: str) -> WebsiteStatus:
    """
    Selenium-based fallback for JS-heavy sites.
    Only imported here to avoid overhead when not needed.
    """
    result = WebsiteStatus(url=url)
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280,800")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        driver  = webdriver.Chrome(service=service, options=options)

        try:
            start = time.perf_counter()
            driver.get(url)
            time.sleep(2)   # Wait for JS to render
            result.load_time = time.perf_counter() - start

            page_source = driver.page_source
            current_url = driver.current_url

            result.is_reachable = True
            result.has_ssl = current_url.startswith("https://")

            soup = BeautifulSoup(page_source, "lxml")
            result.is_mobile_friendly = _is_mobile_friendly(soup)
            result.has_contact_info   = _has_contact_info(soup)

        finally:
            driver.quit()

    except ImportError:
        logger.warning("Selenium not installed — skipping fallback check")
        result.issues.append("Selenium unavailable")
    except Exception as exc:
        logger.warning(f"Selenium check failed for {url}: {exc}")
        result.issues.append(f"Selenium error: {exc}")

    return result


# ─── HTML Analysis Helpers ────────────────────────────────────────────────────

def _is_mobile_friendly(soup: BeautifulSoup) -> bool:
    """
    Heuristic mobile-friendliness check.
    Looks for viewport meta tag and responsive indicators.
    """
    # Primary: viewport meta tag
    viewport = soup.find("meta", attrs={"name": lambda v: v and "viewport" in v.lower()})
    if viewport:
        content = viewport.get("content", "")
        if "width=device-width" in content:
            return True

    # Secondary: Bootstrap / Tailwind / responsive framework indicators
    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href", "").lower()
        if any(fw in href for fw in ["bootstrap", "tailwind", "foundation", "bulma"]):
            return True

    # Tertiary: CSS media query in <style> tags
    for style in soup.find_all("style"):
        if "@media" in (style.string or ""):
            return True

    return False


def _has_contact_info(soup: BeautifulSoup) -> bool:
    """
    Check if the page exposes contact information (phone, email, or address).
    """
    import re
    text = soup.get_text(" ", strip=True)

    # Email pattern
    if re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text):
        return True

    # Indian or international phone
    if re.search(r"(?:\+91[\s\-]?)?[6-9]\d{9}", text):
        return True

    # Generic 10-digit patterns
    if re.search(r"\b\d{10}\b", text):
        return True

    # "Contact us" / "Call us" links
    contact_links = soup.find_all("a", href=lambda h: h and "tel:" in h.lower())
    if contact_links:
        return True

    return False


# ─── Classification Logic ─────────────────────────────────────────────────────

def _classify(result: WebsiteStatus) -> str:
    """
    Determine the final status bucket based on audit results.
    """
    if not result.is_reachable:
        return "No Website"

    poor_signals = []

    if not result.has_ssl:
        poor_signals.append("no HTTPS")
    if not result.is_mobile_friendly:
        poor_signals.append("not mobile-friendly")
    if result.load_time > SLOW_SITE_THRESHOLD:
        poor_signals.append(f"slow load ({result.load_time:.1f}s)")
    if not result.has_contact_info:
        poor_signals.append("no contact info")

    result.issues.extend(poor_signals)

    # Poor = 2+ issues (stricter) OR missing both SSL and mobile
    if len(poor_signals) >= 2 or (not result.has_ssl and not result.is_mobile_friendly):
        return "Poor Website"

    # 1 minor issue → still classified as Good (borderline)
    return "Good Website"


def _build_detail_string(result: WebsiteStatus) -> str:
    """Build a human-readable detail string for the Sheets / UI."""
    if result.status == "No Website":
        return "; ".join(result.issues) if result.issues else "No URL found"

    checks = []
    checks.append("✅ HTTPS" if result.has_ssl else "❌ No HTTPS")
    checks.append("✅ Mobile-Friendly" if result.is_mobile_friendly else "❌ Not Mobile-Friendly")
    checks.append(f"⚡ Load: {result.load_time:.1f}s")
    checks.append("✅ Contact Info" if result.has_contact_info else "❌ No Contact Info")

    return " | ".join(checks)
