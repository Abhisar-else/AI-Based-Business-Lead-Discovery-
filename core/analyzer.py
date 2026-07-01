"""
analyzer.py — AI-Powered Business Intelligence Module

Uses Google Gemini 1.5 Flash (primary) with a structured JSON output prompt
to classify each business lead as High / Medium / Low potential.

Falls back to a deterministic heuristic classifier when no AI key is available,
ensuring the pipeline always produces a result.
"""

import json
import logging
from typing import Optional

from core.config import (
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    GEMINI_MODEL,
    has_gemini_key,
    has_openai_key,
)

logger = logging.getLogger(__name__)

# ─── AI Prompt Template ───────────────────────────────────────────────────────

_SYSTEM_PROMPT = f"""You are a senior business development analyst specializing in 
digital transformation. Your task is to evaluate a business lead and determine 
its potential for digital services (website, SEO, online marketing, e-commerce).

Respond ONLY with a valid JSON object — no markdown, no explanation outside JSON.
Return JSON with exactly these keys:
- potential_category: "High" | "Medium" | "Low"
- reasoning: one sentence why
- summary: one sentence business description like "Growing textile manufacturer in Indore with no digital presence"
"""

_USER_PROMPT_TEMPLATE = """Evaluate this business lead and determine its digital 
transformation potential:

Business Data:
- Name: {business_name}
- Category: {industry_category}
- Location: {location}
- Website Status: {website_status}
- Has Phone: {has_phone}
- Has Email: {has_email}
- Website URL: {website_url}
- Description: {business_description}

Based on this data, classify the lead potential and explain why.

Return ONLY this JSON:
{{
  "potential_category": "High" | "Medium" | "Low",
  "reasoning": "<one clear sentence explaining the classification>",
  "summary": "<one sentence business description>"
}}

Classification guide:
- High: No website OR very poor digital presence with clear improvement opportunity
- Medium: Has basic website but lacks key features (mobile, SEO, contact info)  
- Low: Already has a good digital presence with little obvious gap
"""


# ─── Prompt Builder ───────────────────────────────────────────────────────────

def _build_prompt(business: dict) -> str:
    """Build the analysis prompt for a business dict (shared by all AI backends)."""
    return _USER_PROMPT_TEMPLATE.format(
        business_name        = business.get("business_name", "Unknown"),
        industry_category    = business.get("industry_category", "Unknown"),
        location             = business.get("location", "Unknown"),
        website_status       = business.get("website_status", "Unknown"),
        has_phone            = "Yes" if business.get("phone_number") else "No",
        has_email            = "Yes" if business.get("email_address") else "No",
        website_url          = business.get("website_url", "None"),
        business_description = business.get("business_description", "Not available"),
    )


# ─── Gemini Integration ───────────────────────────────────────────────────────

def _analyze_with_gemini(business: dict) -> Optional[dict]:
    """Call Gemini 1.5 Flash with JSON mode prompt."""
    try:
        import google.generativeai as genai

        from core.config import GEMINI_API_KEY as _key
        try:
            import streamlit as st
            _key = st.secrets.get("GEMINI_API_KEY", _key)
        except Exception:
            pass
        genai.configure(api_key=_key)
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.2,
                "max_output_tokens": 256,
            },
            system_instruction=_SYSTEM_PROMPT,
        )

        response = model.generate_content(_build_prompt(business))
        result = json.loads(response.text)

        # Validate structure
        if result.get("potential_category") in ("High", "Medium", "Low"):
            logger.debug(f"Gemini classified '{business.get('business_name')}' "
                         f"→ {result['potential_category']}")
            return result

    except json.JSONDecodeError as exc:
        logger.warning(f"Gemini returned invalid JSON: {exc}")
    except Exception as exc:
        logger.warning(f"Gemini API error: {exc}")

    return None


# ─── OpenAI Fallback Integration ─────────────────────────────────────────────

def _analyze_with_openai(business: dict) -> Optional[dict]:
    """OpenAI GPT-4o-mini fallback with JSON mode."""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": _build_prompt(business)},
            ],
            temperature=0.2,
            max_tokens=256,
        )

        result = json.loads(response.choices[0].message.content)
        if result.get("potential_category") in ("High", "Medium", "Low"):
            return result

    except Exception as exc:
        logger.warning(f"OpenAI API error: {exc}")

    return None


# ─── Heuristic Fallback (No API Key) ─────────────────────────────────────────

_HEURISTIC_RULES = [
    # (condition_fn, potential, reasoning)
    (
        lambda b: b.get("website_status") == "No Website",
        "High",
        "Business has no online presence — significant digital transformation opportunity."
    ),
    (
        lambda b: (
            b.get("website_status") == "Poor Website"
            and not b.get("email_address")
            and not b.get("phone_number")
        ),
        "High",
        "Poor website with no reachable contact information — major digital gap identified."
    ),
    (
        lambda b: (
            b.get("website_status") == "Poor Website"
            and (b.get("email_address") or b.get("phone_number"))
        ),
        "Medium",
        "Business has basic contact info but website quality needs significant improvement."
    ),
    (
        lambda b: b.get("website_status") == "Good Website" and not b.get("email_address"),
        "Medium",
        "Website appears functional but lacks visible contact information for lead capture."
    ),
    (
        lambda b: b.get("website_status") == "Good Website",
        "Low",
        "Business already maintains a good digital presence with limited improvement gap."
    ),
]

def _analyze_with_heuristics(business: dict) -> dict:
    """
    Rule-based classification used when no AI API is available.
    Returns the same {potential_category, reasoning} dict structure.
    """
    for condition, potential, reasoning in _HEURISTIC_RULES:
        try:
            if condition(business):
                return {"potential_category": potential, "reasoning": reasoning,"ai_summary": reasoning}
        except Exception:
            continue

    # Default
    return {
        "potential_category": "Medium",
        "reasoning": "Insufficient data for precise classification — manual review recommended.",
        "ai_summary": "Heuristic analysis: insufficient data for detailed summary.",  
          }


# ─── Main Public Function ─────────────────────────────────────────────────────

def analyze_business(business: dict) -> dict:
    """
    Classify a business lead's digital transformation potential.

    Tries (in order):
      1. Gemini 1.5 Flash (if key available)
      2. OpenAI GPT-4o-mini (if key available)
      3. Heuristic rules (always available)

    Args:
        business: Dict containing at minimum website_status, business_name,
                  location, phone_number, email_address.

    Returns:
        Dict with keys: potential_category (str), reasoning (str)
    """
    # Try Gemini first (preferred)
    if has_gemini_key():
        result = _analyze_with_gemini(business)
        if result:
            result["analysis_source"] = "gemini"
            result["ai_summary"]= result.get("summary", "")
            return result

    # OpenAI fallback
    if has_openai_key():
        result = _analyze_with_openai(business)
        if result:
            result["analysis_source"] = "openai"
            result["ai_summary"] = result.get("summary", result.get("reasoning", ""))
            return result

    # Deterministic heuristic fallback
    logger.info(f"Using heuristic analysis for '{business.get('business_name')}'")
    result = _analyze_with_heuristics(business)
    result["analysis_source"] = "heuristic"
    result["ai_summary"]= "No AI key available; heuristic classification applied."
    return result


def get_analysis_mode() -> str:
    """Return human-readable description of the active analysis mode."""
    if has_gemini_key():
        return "🤖 Gemini 1.5 Flash (AI)"
    if has_openai_key():
        return "🤖 OpenAI GPT-4o-mini (AI)"
    return "📐 Heuristic Rules (No AI key)"
