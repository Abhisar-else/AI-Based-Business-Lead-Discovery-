"""
scraper.py — Business Discovery & Data Collection Module

Strategy (anti-blocking):
  1. SerpAPI (Google Maps)  — cleanest data, API-based, no scraping
  2. JustDial scraping      — fallback for Indian cities (no API key needed)
  3. Sulekha scraping       — second directory fallback
  4. Contact extraction     — pulls email/phone from business websites
"""

import re
import time
import random
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from core.config import (
    SERPER_API_KEY,
    RATE_LIMIT_DELAY,
    WEBSITE_TIMEOUT,
    MAX_RETRIES,
    has_serper_key,
)
SERPAPI_KEY = SERPER_API_KEY  
has_serpapi_key = has_serper_key
# Alias for backward compatibility

logger = logging.getLogger(__name__)

# ─── User Agent Rotation ─────────────────────────────────────────────────────
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

def _get_headers() -> dict:
    """Return randomized headers to reduce blocking."""
    return {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "DNT": "1",
    }


def _safe_get(
    url: str,
    retries: int = MAX_RETRIES,
    timeout: int = WEBSITE_TIMEOUT,
    **kwargs
) -> Optional[requests.Response]:
    """HTTP GET with retries and rate limiting."""
    for attempt in range(retries):
        try:
            resp = requests.get(
                url,
                headers=_get_headers(),
                timeout=timeout,
                **kwargs
            )
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            logger.warning(f"[Attempt {attempt+1}] GET {url} failed: {exc}")
            if attempt < retries - 1:
                time.sleep(RATE_LIMIT_DELAY * (attempt + 1))
    return None


# ─── Serper.dev Source (Google Maps) ──────────────────────────────────────────

def _search_via_serper(query: str, location: str, max_results: int) -> list[dict]:
    """
    Fetch business listings from Google Maps via Serper.dev.
    Returns structured business dicts.
    """
    results = []
    try:
        url = "https://google.serper.dev/maps"
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "q": f"{query} in {location}",
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for place in data.get("places", []):
            business = {
                "business_name": place.get("title", "").strip(),
                "industry_category": place.get("category", place.get("type", "")).strip(),
                "business_description": place.get("description", "").strip(),
                "location": place.get("address", location).strip(),
                "google_maps_link": place.get("googleMapsUrl", place.get("cid", "")),
                "website_url": place.get("website", ""),
                "phone_number": place.get("phoneNumber", place.get("phone", "")),
                "email_address": "",
                "owner_founder": "",
                "linkedin_profile": "",
                "source": "serper_google_maps",
                "collected_at": datetime.now().isoformat(),
            }
            results.append(business)
            if len(results) >= max_results:
                break

    except Exception as exc:
        logger.error(f"Serper search failed: {exc}")

    return results


# ─── JustDial Scraper (India-focused fallback) ───────────────────────────────

def _search_via_justdial(query: str, location: str, max_results: int) -> list[dict]:
    """
    Scrape JustDial for business listings (India-focused).
    Falls back gracefully if blocked.
    """
    results = []
    city = location.lower().replace(" ", "-")
    category_slug = query.lower().replace(" ", "-")
    url = f"https://www.justdial.com/{city}/{category_slug}/nmo-1"

    resp = _safe_get(url)
    if not resp:
        logger.warning("JustDial scraping returned no response.")
        return results

    soup = BeautifulSoup(resp.text, "lxml")

    # JustDial uses li[data-id] for listing cards
    cards = soup.select("li[data-id]") or soup.select(".resultbox_info")
    logger.info(f"JustDial found {len(cards)} raw cards for '{query} in {location}'")

    for card in cards[:max_results]:
        try:
            name_tag = card.select_one(".resultbox_title_anchor, .fn")
            addr_tag = card.select_one(".mrehover, .adr")
            phone_tag = card.select_one(".contact_info .tel")
            cat_tag   = card.select_one(".resultbox_category, .resultbox_info_title")

            name    = name_tag.get_text(strip=True) if name_tag else ""
            address = addr_tag.get_text(strip=True) if addr_tag else location
            phone   = phone_tag.get_text(strip=True) if phone_tag else ""
            cat     = cat_tag.get_text(strip=True) if cat_tag else query

            if not name:
                continue

            business = {
                "business_name": name,
                "industry_category": cat or query,
                "business_description": "",
                "location": address,
                "google_maps_link": "",
                "website_url": _extract_justdial_website(card),
                "phone_number": _clean_phone(phone),
                "email_address": "",
                "owner_founder": "",
                "linkedin_profile": "",
                "source": "justdial",
                "collected_at": datetime.now().isoformat(),
            }
            results.append(business)
        except Exception as exc:
            logger.debug(f"JustDial card parse error: {exc}")
            continue

        time.sleep(random.uniform(0.5, 1.5))

    return results


def _extract_justdial_website(card: BeautifulSoup) -> str:
    """Extract website URL from a JustDial listing card."""
    link = card.select_one("a[href*='http']:not([href*='justdial'])")
    if link:
        href = link.get("href", "")
        if href.startswith("http") and "justdial.com" not in href:
            return href
    return ""


# ─── Sulekha Scraper (second India fallback) ─────────────────────────────────

def _search_via_sulekha(query: str, location: str, max_results: int) -> list[dict]:
    """Scrape Sulekha for business listings."""
    results = []
    city = location.lower().replace(" ", "-")
    q    = query.lower().replace(" ", "-")
    url = f"https://www.sulekha.com/{city}/{q}-services"
    resp = _safe_get(url)
    if not resp:
        return results

    soup = BeautifulSoup(resp.text, "lxml")
    cards = soup.select(".srp-listing-card, .bizlisting-block")
    logger.info(f"Sulekha found {len(cards)} raw cards")

    for card in cards[:max_results]:
        try:
            name_tag  = card.select_one(".bizname, .business-name")
            addr_tag  = card.select_one(".locality, .address")
            phone_tag = card.select_one(".phone, .contact-number")

            name    = name_tag.get_text(strip=True) if name_tag else ""
            address = addr_tag.get_text(strip=True) if addr_tag else location
            phone   = phone_tag.get_text(strip=True) if phone_tag else ""

            if not name:
                continue

            business = {
                "business_name": name,
                "industry_category": query,
                "business_description": "",
                "location": address,
                "google_maps_link": "",
                "website_url": "",
                "phone_number": _clean_phone(phone),
                "email_address": "",
                "owner_founder": "",
                "linkedin_profile": "",
                "source": "sulekha",
                "collected_at": datetime.now().isoformat(),
            }
            results.append(business)
        except Exception as exc:
            logger.debug(f"Sulekha parse error: {exc}")

    return results
  
# ─── IndiaMart Scraper (B2B India directory) ──────────────────────────────────

def _search_via_indiamart(query: str, location: str, max_results: int) -> list[dict]:
    """Scrape IndiaMart for B2B business listings."""
    results = []
    url = f"https://dir.indiamart.com/search.mp?ss={quote_plus(query)}&cq={quote_plus(location)}"

    resp = _safe_get(url)
    if not resp:
        logger.warning("IndiaMart returned no response")
        return results

    soup = BeautifulSoup(resp.text, "lxml")
    cards = soup.select(".company-name-widget, .compnyName, .bname, .card")
    logger.info(f"IndiaMart found {len(cards)} raw cards")

    for card in cards[:max_results]:
        try:
            name_el = card.select_one("a.company-name, a.bname, h2 a, h3 a")
            if not name_el:
                continue
            name = name_el.get_text(strip=True)
            if not name:
                continue

            website = ""
            site_el = card.select_one("a[href*='http']:not([href*='indiamart'])")
            if site_el:
                website = site_el.get("href", "")

            phone = ""
            phone_el = card.select_one(".contact, .phone, .tel")
            if phone_el:
                phone = _clean_phone(phone_el.get_text(strip=True))

            results.append({
                "business_name": name,
                "industry_category": query,
                "business_description": "",
                "location": location,
                "google_maps_link": "",
                "website_url": website,
                "phone_number": phone,
                "email_address": "",
                "owner_founder": "",
                "linkedin_profile": "",
                "source": "indiamart",
                "collected_at": datetime.now().isoformat(),
            })
        except Exception as exc:
            logger.debug(f"IndiaMart card parse error: {exc}")
            continue

    logger.info(f"IndiaMart returned {len(results)} results")
    return results 

# ─── Contact Extractor ────────────────────────────────────────────────────────

def extract_contact_info(url: str) -> dict:
    """
    Visit a business website and extract publicly available contact details.
    Checks homepage + /contact page.
    Returns: { email, phone, linkedin }
    """
    info = {"email_address": "", "phone_number": "", "linkedin_profile": "","owner_founder": ""}
    if not url:
        return info

    # Normalize URL
    if not url.startswith("http"):
        url = "https://" + url

    pages_to_check = [url]
    # Also try /contact or /about pages
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    for path in ["/contact", "/contact-us", "/about", "/about-us","/team"]:
        pages_to_check.append(base + path)

    emails_found   = set()
    phones_found   = set()
    linkedin_found = ""
    owner = ""

    for page_url in pages_to_check[:3]:  # Limit to 3 pages
        resp = _safe_get(page_url, retries=1, timeout=4)
        if not resp:
            continue

        text = resp.text
        soup = BeautifulSoup(text, "lxml")  # Single parse, used for everything

        # Extract emails using regex
        email_pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
        for e in re.findall(email_pattern, text):
            if not any(skip in e.lower() for skip in ["example", "yourname", "test@", "sentry"]):
                emails_found.add(e.lower())


        # Extract Indian + international phone numbers
        phone_pattern = r"(?:\+91[\-\s]?)?[6-9]\d{9}|(?:\+1[\-\s]?)?\(?\d{3}\)?[\-\s]?\d{3}[\-\s]?\d{4}"
        for p in re.findall(phone_pattern, text):
            cleaned = _clean_phone(p)
            if cleaned:
                phones_found.add(cleaned)
             # Extract LinkedIn
        if not linkedin_found:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "linkedin.com" in href:
                    linkedin_found = href.split("?")[0]
                    break

        # Extract Owner/Founder (NEW: inside the loop, reuses soup)
        if not owner:
            about_text = soup.get_text(" ", strip=True)
            match = re.search(
                r"(?:founder|owner|director|ceo|md|proprietor|managing director)"
                r"[:\s\-]+([A-Z][a-z]+ [A-Z][a-z]+)",
                about_text,
                re.IGNORECASE,
            )
            if match:
                owner = match.group(1)
        time.sleep(RATE_LIMIT_DELAY)

    info["email_address"]  = sorted(emails_found)[0] if emails_found else ""
    info["phone_number"]   = sorted(phones_found)[0] if phones_found else ""
    info["linkedin_profile"] = linkedin_found
    info["owner_founder"] = owner
    return info
    # Owner/Founder — check About/Team pages
    owner = ""
    for page_url in pages_to_check[:3]:
        try:
            resp = _safe_get(page_url)
            if not resp:
                continue
            about_text = BeautifulSoup(resp.text, "lxml").get_text(" ", strip=True)
            match = re.search(
                r"(?:founder|owner|director|ceo|md|proprietor)"
                r"[:\s\-]+([A-Z][a-z]+ [A-Z][a-z]+)",
                about_text,
                re.IGNORECASE,
            )
            if match:
                owner = match.group(1)
                break
        except Exception:
            continue
    info["owner_founder"] = owner
    return info


# ─── Main Public Function ─────────────────────────────────────────────────────

def search_businesses(
    query: str,
    location: str,
    max_results: int = 20,
    progress_callback=None
) -> list[dict]:
    """
    Discover businesses matching query+location from multiple sources.

    Args:
        query:             Industry category (e.g., "Hotels", "Manufacturing")
        location:          City/area (e.g., "Indore", "Mumbai")
        max_results:       Maximum leads to return
        progress_callback: Optional callable(msg: str) for Streamlit progress updates

    Returns:
        List of business dicts ready for the pipeline.
    """
    def _log(msg: str):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    all_results: list[dict] = []

    # --- Source 1: Serper.dev (best quality) ---
    if has_serper_key():
        _log("🔍 Searching Google Maps via Serper.dev...")
        results = _search_via_serper(query, location, max_results)
        _log(f"   ✓ Serper returned {len(results)} results")
        all_results.extend(results)
    else:
        _log("⚠️  No Serper.dev API key — skipping Google Maps source")

    # --- Source 2: JustDial (India fallback) ---
    remaining = max_results - len(all_results)
    if remaining > 0:
        _log("🔍 Searching JustDial...")
        time.sleep(RATE_LIMIT_DELAY)
        results = _search_via_justdial(query, location, remaining)
        _log(f"   ✓ JustDial returned {len(results)} results")
        all_results.extend(results)

    # --- Source 3: Sulekha (extra fallback) ---
    remaining = max_results - len(all_results)
    if remaining > 0:
        _log("🔍 Searching Sulekha...")
        time.sleep(RATE_LIMIT_DELAY)
        results = _search_via_sulekha(query, location, remaining)
        _log(f"   ✓ Sulekha returned {len(results)} results")
        all_results.extend(results)

    # --- Source 4: IndiaMart (B2B India directory) ---
    remaining = max_results - len(all_results)
    if remaining > 0:
        _log("🔍 Searching IndiaMart...")
        time.sleep(RATE_LIMIT_DELAY)
        results = _search_via_indiamart(query, location, remaining)
        _log(f"   ✓ IndiaMart returned {len(results)} results")
        all_results.extend(results)

    # --- Enrich with contact info from websites in parallel ---
    _log(f"📬 Extracting contact info for {len(all_results)} businesses in parallel...")
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _enrich_single(index, biz):
        if biz.get("website_url") and not biz.get("email_address"):
            try:
                contact = extract_contact_info(biz["website_url"])
                biz.update({
                    k: v for k, v in contact.items()
                    if not biz.get(k) and v
                })
                return f"   [{index+1}/{len(all_results)}] Enriched: {biz['business_name']}"
            except Exception as exc:
                logger.debug(f"Contact extraction failed for {biz.get('business_name')}: {exc}")
        return biz

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_enrich_single, i, biz) for i, biz in enumerate(all_results)]
        for fut in as_completed(futures):
            msg = fut.result()
            if msg:
                _log(msg)

    _log(f"✅ Discovery complete: {len(all_results)} businesses found")
    return all_results[:max_results]


# ─── Utility Functions ────────────────────────────────────────────────────────

def _clean_phone(raw: str) -> str:
    """Normalize a phone number string."""
    if not raw:
        return ""
    # Keep only digits, +, -, spaces, parens
    cleaned = re.sub(r"[^\d+\-() ]", "", raw).strip()
    return cleaned if len(cleaned) >= 7 else ""
