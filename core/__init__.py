"""
core/__init__.py

Exposes the main pipeline orchestration function so the Streamlit app
has a single import to run the full discovery → audit → analyze → export pipeline.
"""

import logging
import time
from typing import Callable, Optional

import pandas as pd

from core.scraper import search_businesses
from core.website_checker import check_website
from core.analyzer import analyze_business
from core.data_pipeline import build_dataframe, clean_dataframe, save_to_csv

logger = logging.getLogger(__name__)


def run_pipeline(
    query: str,
    location: str,
    max_results: int = 20,
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> pd.DataFrame:
    """
    Full pipeline orchestrator: Discovery → Audit → AI Analysis → Clean.

    Args:
        query:             Industry category string (e.g., "Hotels")
        location:          City or region (e.g., "Indore")
        max_results:       Maximum number of leads to process
        progress_callback: Optional fn(message: str, pct: float) for UI updates

    Returns:
        Clean pandas DataFrame with all SHEET_COLUMNS populated.
    """

    def _update(msg: str, pct: float = 0.0):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg, pct)

    # ── Stage 1: Discovery ──────────────────────────────────────────────────
    _update(f"🔍 Discovering '{query}' businesses in {location}...", 0.05)

    raw_businesses = search_businesses(
        query=query,
        location=location,
        max_results=max_results,
        progress_callback=lambda msg: _update(msg, 0.1),
    )

    if not raw_businesses:
        _update("⚠️ No businesses found. Try a different query or location.", 1.0)
        return pd.DataFrame()

    _update(f"✅ Found {len(raw_businesses)} businesses — starting audit in parallel...", 0.25)

    # ── Stage 2: Website Audit (Parallel) ───────────────────────────────────
    from concurrent.futures import ThreadPoolExecutor, as_completed

    total = len(raw_businesses)

    def _audit_single(index: int, biz: dict) -> str:
        try:
            status = check_website(biz.get("website_url"))
            biz["website_status"] = status.status
            biz["website_details"] = status.details
            # Back-fill website URL from redirect if we discovered it
            if status.url and not biz.get("website_url"):
                biz["website_url"] = status.url
        except Exception as exc:
            logger.warning(f"Website check failed for {biz.get('business_name')}: {exc}")
            biz["website_status"] = "No Website"
            biz["website_details"] = "Audit error"
        return f"🌐 [{index+1}/{total}] Audited: {biz.get('business_name', 'Unknown')}"

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_audit_single, i, biz) for i, biz in enumerate(raw_businesses)]
        for i, fut in enumerate(as_completed(futures)):
            pct = 0.2 + (0.3 * (i / total))
            msg = fut.result()
            _update(msg, pct)

    _update("✅ Website audit complete — running AI analysis in parallel...", 0.60)

    # ── Stage 3: AI Analysis (Parallel) ─────────────────────────────────────
    def _analyze_single(index: int, biz: dict) -> str:
        try:
            analysis = analyze_business(biz)
            biz["potential_category"] = analysis.get("potential_category", "Medium")
            biz["reasoning"]          = analysis.get("reasoning", "")
        except Exception as exc:
            logger.warning(f"Analysis failed for {biz.get('business_name')}: {exc}")
            biz["potential_category"] = "Medium"
            biz["reasoning"]          = "Analysis unavailable"
        return f"🤖 [{index+1}/{total}] Analyzed: {biz.get('business_name', 'Unknown')}"

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_analyze_single, i, biz) for i, biz in enumerate(raw_businesses)]
        for i, fut in enumerate(as_completed(futures)):
            pct = 0.5 + (0.3 * (i / total))
            msg = fut.result()
            _update(msg, pct)

    _update("✅ AI analysis complete — cleaning data...", 0.92)

    # ── Stage 4: Clean & Structure ──────────────────────────────────────────
    df = build_dataframe(raw_businesses)
    df = clean_dataframe(df)
    save_to_csv(df)

    _update(
        f"🎉 Pipeline complete! {len(df)} leads ready "
        f"({(df['Potential Category']=='High').sum()} High priority)",
        1.0,
    )

    return df
