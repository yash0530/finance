#!/usr/bin/env python3
"""
edgar_service.py — SEC EDGAR filing fetcher and LLM-powered summarizer.

Uses the free SEC EDGAR full-text search and submissions API.
No API key required — only a User-Agent string identifying yourself
(SEC requirement per https://www.sec.gov/developer).

Fetches the most recent 10-K or 10-Q, extracts key sections:
  - Item 1:  Business Description
  - Item 1A: Risk Factors
  - Item 7:  Management Discussion & Analysis (MD&A)

Then summarizes each section with the LLM.
Results are cached in SQLite (24h TTL).
"""

import re
import time
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# SEC EDGAR requires a descriptive User-Agent or requests get throttled/blocked
_EDGAR_USER_AGENT = os.environ.get(
    "EDGAR_USER_AGENT",
    "PortfolioIntelligenceTool research@portfolio.local"
)
_HEADERS = {
    "User-Agent": _EDGAR_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov",
}
_HEADERS_FULL = {
    "User-Agent": _EDGAR_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
}

# Rate limiting — SEC asks for max 10 req/sec
_LAST_REQUEST_TIME = 0.0
_MIN_REQUEST_INTERVAL = 0.15  # 150ms between requests


def _rate_limited_get(url: str, headers: dict = None, timeout: int = 20) -> requests.Response:
    """GET with SEC rate limiting."""
    global _LAST_REQUEST_TIME
    elapsed = time.time() - _LAST_REQUEST_TIME
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    resp = requests.get(url, headers=headers or _HEADERS_FULL, timeout=timeout)
    _LAST_REQUEST_TIME = time.time()
    return resp


# ============================================================================
# CIK Lookup
# ============================================================================

def get_cik(ticker: str) -> Optional[str]:
    """Resolve a ticker symbol to its SEC CIK number.

    Uses the EDGAR company search API.
    Returns zero-padded 10-digit CIK string, or None if not found.
    """
    ticker = ticker.upper().strip()
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2020-01-01&forms=10-K"

    # Try the tickers.json lookup first — it's faster and more reliable
    try:
        resp = _rate_limited_get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=_HEADERS_FULL
        )
        resp.raise_for_status()
        tickers_data = resp.json()
        # Values: {0: {cik_str, ticker, title}, ...}
        for entry in tickers_data.values():
            if entry.get("ticker", "").upper() == ticker:
                cik = str(entry["cik_str"]).zfill(10)
                logger.debug(f"CIK for {ticker}: {cik}")
                return cik
    except Exception as e:
        logger.warning(f"CIK lookup via tickers.json failed: {e}")

    return None


# ============================================================================
# Filing Discovery
# ============================================================================

def get_latest_filing_url(cik: str, form_type: str = "10-K") -> Optional[Dict]:
    """Find the most recent filing of a given form type for a CIK.

    Returns dict with keys: accession_number, filing_date, document_url
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        resp = _rate_limited_get(url, headers=_HEADERS)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch submissions for CIK {cik}: {e}")
        return None

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])

    for i, form in enumerate(forms):
        if form == form_type:
            accession = accessions[i].replace("-", "")
            filing_date = dates[i]
            # Primary document URL
            doc_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{int(cik)}/{accession}/{accessions[i]}-index.htm"
            )
            return {
                "accession_number": accessions[i],
                "filing_date": filing_date,
                "index_url": doc_url,
                "cik": cik,
                "form_type": form_type,
            }

    return None


def list_recent_filings(ticker: str, limit: int = 15) -> List[Dict]:
    """Return recent SEC filings (form, date, index URL) for a ticker.

    Free metadata only — no document download or LLM summarization. Used by the
    Stock View filings timeline. Returns [] on any failure.
    """
    cik = get_cik(ticker)
    if not cik:
        return []
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        resp = _rate_limited_get(url, headers=_HEADERS)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"list_recent_filings: submissions fetch failed for {ticker}: {e}")
        return []

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", []) or []
    accessions = recent.get("accessionNumber", []) or []
    dates = recent.get("filingDate", []) or []
    docs = recent.get("primaryDocument", []) or []

    out: List[Dict] = []
    n = min(len(forms), len(accessions), len(dates))
    for i in range(n):
        accession_clean = accessions[i].replace("-", "")
        primary = docs[i] if i < len(docs) else ""
        doc_url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_clean}/{primary}"
            if primary else
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_clean}/"
        )
        out.append({
            "form": forms[i],
            "filing_date": dates[i],
            "url": doc_url,
            "accession": accessions[i],
        })
        if len(out) >= limit:
            break
    return out


def _get_primary_document_url(filing_info: Dict) -> Optional[str]:
    """From a filing index, find the primary HTM/HTML document URL."""
    accession_clean = filing_info["accession_number"].replace("-", "")
    cik_int = int(filing_info["cik"])
    index_json_url = (
        f"https://data.sec.gov/Archives/edgar/data/"
        f"{cik_int}/{accession_clean}/{filing_info['accession_number']}-index.json"
    )
    try:
        resp = _rate_limited_get(index_json_url, headers=_HEADERS_FULL)
        resp.raise_for_status()
        index_data = resp.json()
        for doc in index_data.get("documents", []):
            name = doc.get("name", "")
            doc_type = doc.get("type", "")
            if doc_type in (filing_info["form_type"], "10-K", "10-Q") and (
                name.endswith(".htm") or name.endswith(".html")
            ):
                return (
                    f"https://www.sec.gov/Archives/edgar/data/"
                    f"{cik_int}/{accession_clean}/{name}"
                )
    except Exception as e:
        logger.warning(f"Could not find primary document via data.sec.gov: {e}. Trying fallback to directory listing.")
        
    # Fallback: Scrape the raw directory index from www.sec.gov
    fallback_json_url = (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{cik_int}/{accession_clean}/index.json"
    )
    try:
        resp = _rate_limited_get(fallback_json_url, headers=_HEADERS_FULL)
        resp.raise_for_status()
        dir_data = resp.json()
        items = dir_data.get("directory", {}).get("item", [])
        
        # Filter to only .htm or .html files that don't look like exhibits (ex*) or graphics (R*)
        candidates = [i for i in items if (i["name"].endswith(".htm") or i["name"].endswith(".html")) 
                      and not i["name"].lower().startswith("r")
                      and not "index" in i["name"].lower()]
        
        if candidates:
            # The primary document (10-K/10-Q) is almost always the largest HTML file
            candidates.sort(key=lambda x: int(x.get("size", 0) if x.get("size") else 0), reverse=True)
            largest_doc = candidates[0]["name"]
            return (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{cik_int}/{accession_clean}/{largest_doc}"
            )
    except Exception as e:
        logger.warning(f"Fallback directory listing failed: {e}")

    logger.error(f"Could not resolve primary document URL for {filing_info.get('cik')}")
    return None


# ============================================================================
# Section Extraction
# ============================================================================

# Pattern tuples: (section_key, start_patterns, end_patterns)
_SECTION_PATTERNS = {
    "business": (
        [
            r"item\s+1[.\s]+business",
            r"item\s*1\s*[\.\-:]\s*business",
        ],
        [
            r"item\s+1a",
            r"item\s+2",
        ],
    ),
    "risk_factors": (
        [
            r"item\s+1a[.\s]+risk\s+factors",
            r"item\s*1a\s*[\.\-:]\s*risk",
        ],
        [
            r"item\s+1b",
            r"item\s+2",
        ],
    ),
    "mda": (
        [
            r"item\s+7[.\s]+management.{0,30}discussion",
            r"item\s*7\s*[\.\-:]",
        ],
        [
            r"item\s+7a",
            r"item\s+8",
        ],
    ),
}


def _strip_html(html: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    # Remove script and style blocks entirely
    html = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove all remaining tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_sections(raw_text: str) -> Dict[str, str]:
    """Extract key sections from plain-text filing content.

    Returns dict with keys: business, risk_factors, mda
    Each value is the extracted plain text (may be empty string if not found).
    """
    text_lower = raw_text.lower()
    sections = {}

    for section_key, (start_patterns, end_patterns) in _SECTION_PATTERNS.items():
        start_pos = -1

        # Find section start
        for pat in start_patterns:
            match = re.search(pat, text_lower)
            if match:
                start_pos = match.start()
                break

        if start_pos == -1:
            sections[section_key] = ""
            continue

        # Find section end
        end_pos = len(raw_text)
        for pat in end_patterns:
            match = re.search(pat, text_lower[start_pos + 50:])
            if match:
                candidate = start_pos + 50 + match.start()
                if candidate < end_pos:
                    end_pos = candidate

        # Extract and trim to a reasonable length
        section_text = raw_text[start_pos:end_pos].strip()
        # Remove the section header line itself
        section_text = re.sub(r"^.*?\n", "", section_text, count=1)
        # Cap at 12,000 chars to avoid LLM context overflow
        sections[section_key] = section_text[:12_000].strip()

    return sections


# ============================================================================
# Main Public API
# ============================================================================

def fetch_filing_sections(ticker: str, form_type: str = "10-K") -> Dict[str, str]:
    """Fetch and extract sections from the latest 10-K or 10-Q for a ticker.

    Returns:
        Dict with keys: business, risk_factors, mda
        Values are extracted plain text (empty string if section not found).
        Returns empty dict on any unrecoverable error.
    """
    logger.info(f"Fetching {form_type} for {ticker}")

    cik = get_cik(ticker)
    if not cik:
        logger.warning(f"No CIK found for ticker {ticker}")
        return {}

    filing_info = get_latest_filing_url(cik, form_type)
    if not filing_info:
        # Try 10-Q if 10-K not found (e.g., recent IPO)
        if form_type == "10-K":
            logger.info(f"No 10-K found for {ticker}, trying 10-Q")
            filing_info = get_latest_filing_url(cik, "10-Q")
        if not filing_info:
            logger.warning(f"No {form_type} filing found for {ticker}")
            return {}

    doc_url = _get_primary_document_url(filing_info)
    if not doc_url:
        logger.warning(f"Could not resolve primary document URL for {ticker}")
        return {}

    logger.info(f"Fetching document: {doc_url}")
    try:
        resp = _rate_limited_get(doc_url, headers=_HEADERS_FULL, timeout=30)
        resp.raise_for_status()
        html_content = resp.text
    except Exception as e:
        logger.error(f"Failed to fetch filing document for {ticker}: {e}")
        return {}

    plain_text = _strip_html(html_content)
    sections = extract_sections(plain_text)

    # Add metadata
    sections["_filing_date"] = filing_info.get("filing_date", "")
    sections["_form_type"] = filing_info.get("form_type", form_type)
    sections["_ticker"] = ticker.upper()

    return sections


def summarize_filing(ticker: str, form_type: str = "10-K") -> Dict[str, str]:
    """Fetch SEC filing and summarize each key section with the LLM.

    Returns:
        Dict with keys: business, risks, mda, filing_date, form_type
        Each summary is 4-5 bullet points of the most material information.
    """
    from llm_service import summarize_edgar_section

    sections = fetch_filing_sections(ticker, form_type)
    if not sections:
        return {
            "business": "",
            "risks": "",
            "mda": "",
            "error": f"Could not fetch {form_type} filing for {ticker}",
            "available": False
        }

    summaries = {
        "available": True,
        "filing_date": sections.get("_filing_date", ""),
        "form_type": sections.get("_form_type", form_type),
    }

    section_map = {
        "business": ("business", "Business"),
        "risk_factors": ("risks", "Risk Factors"),
        "mda": ("mda", "MD&A"),
    }

    for section_key, (output_key, display_name) in section_map.items():
        raw = sections.get(section_key, "")
        if raw:
            try:
                summary = summarize_edgar_section(raw, section_key, ticker)
                summaries[output_key] = summary
            except Exception as e:
                logger.warning(f"LLM summarization failed for {ticker}/{section_key}: {e}")
                summaries[output_key] = f"[Summary unavailable: {str(e)[:100]}]"
        else:
            summaries[output_key] = ""

    return summaries
