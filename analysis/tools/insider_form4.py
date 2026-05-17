"""
tools.insider_form4 — SEC EDGAR Form 4 insider trade aggregator.

Pulls the last 90 days of Form 4 filings for a ticker, extracts per-transaction
detail (filer, role, type, shares, price, value), aggregates buy/sell flow and
flags clustered buying (>=3 distinct insiders buying within any 30d window) and
CEO-level activity. Persists each transaction to insider_trades_cache.

Free SEC EDGAR JSON APIs. Requires User-Agent on every request and respects a
small (>10 req/sec safe) sleep between requests.
"""

from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

from tools import Source, Tool, ToolResult, register
from db import get_connection, get_tool_cache, save_tool_cache

logger = logging.getLogger(__name__)

# SEC requires an identifying User-Agent on every request.
SEC_USER_AGENT = "PortfolioIntelligence research@example.com"
SEC_HEADERS = {"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"}
REQUEST_DELAY_SEC = 0.15  # SEC tolerates up to ~10 req/sec; we use ~6.

CIK_LOOKUP_URL = "https://www.sec.gov/files/company_tickers.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sec_get(url: str, timeout: int = 15) -> Optional[requests.Response]:
    """Polite SEC GET; returns Response or None on failure."""
    try:
        time.sleep(REQUEST_DELAY_SEC)
        resp = requests.get(url, headers=SEC_HEADERS, timeout=timeout)
        if resp.status_code >= 400:
            logger.warning(f"SEC GET {url} -> {resp.status_code}")
            return None
        return resp
    except Exception as e:
        logger.warning(f"SEC GET {url} raised {type(e).__name__}: {e}")
        return None


def _resolve_cik(ticker: str) -> Optional[str]:
    """Map a ticker symbol to its zero-padded 10-digit CIK string."""
    resp = _sec_get(CIK_LOOKUP_URL)
    if resp is None:
        return None
    try:
        payload = resp.json()
    except Exception:
        return None
    ticker_u = ticker.upper().strip()
    # File is a dict of integer-keyed entries with cik_str / ticker / title.
    for _, entry in payload.items():
        if not isinstance(entry, dict):
            continue
        if str(entry.get("ticker", "")).upper() == ticker_u:
            cik_int = int(entry["cik_str"])
            return f"{cik_int:010d}"
    return None


def _fetch_submissions(cik: str) -> Optional[Dict[str, Any]]:
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    resp = _sec_get(url)
    if resp is None:
        return None
    try:
        return resp.json()
    except Exception:
        return None


def _list_recent_form4_filings(submissions: Dict[str, Any], lookback_days: int) -> List[Dict[str, Any]]:
    """Return Form-4 filings from the recent-filings index within lookback_days."""
    out: List[Dict[str, Any]] = []
    recent = (submissions.get("filings", {}) or {}).get("recent", {}) or {}
    forms = recent.get("form", []) or []
    accession_nums = recent.get("accessionNumber", []) or []
    filing_dates = recent.get("filingDate", []) or []
    primary_docs = recent.get("primaryDocument", []) or []

    cutoff = (datetime.now() - timedelta(days=lookback_days)).date()
    n = min(len(forms), len(accession_nums), len(filing_dates), len(primary_docs))
    for i in range(n):
        if str(forms[i]).strip() != "4":
            continue
        try:
            fdate = datetime.fromisoformat(filing_dates[i]).date()
        except Exception:
            continue
        if fdate < cutoff:
            continue
        out.append({
            "accession": accession_nums[i],
            "filing_date": filing_dates[i],
            "primary_document": primary_docs[i],
        })
    return out


def _accession_to_url(cik: str, accession: str, primary_doc: str) -> str:
    cleaned = accession.replace("-", "")
    # CIK in folder path is non-padded.
    cik_int = int(cik)
    return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{cleaned}/{primary_doc}"


def _txt(node: Optional[ET.Element]) -> str:
    return (node.text or "").strip() if node is not None and node.text else ""


def _parse_form4_xml(xml_text: str) -> Dict[str, Any]:
    """Pull insider name/role and per-transaction detail from a Form 4 XML doc."""
    parsed: Dict[str, Any] = {
        "insider_name": "",
        "insider_role": "",
        "is_director": False,
        "is_officer": False,
        "is_ten_percent_owner": False,
        "officer_title": "",
        "transactions": [],
    }
    try:
        root = ET.fromstring(xml_text)
    except Exception as e:
        logger.debug(f"Form4 XML parse failed: {e}")
        return parsed

    # Reporting owner
    owner = root.find(".//reportingOwner")
    if owner is not None:
        name = _txt(owner.find(".//reportingOwnerId/rptOwnerName"))
        parsed["insider_name"] = name
        rel = owner.find(".//reportingOwnerRelationship")
        if rel is not None:
            is_director = _txt(rel.find("isDirector")) in ("1", "true", "True")
            is_officer = _txt(rel.find("isOfficer")) in ("1", "true", "True")
            is_ten = _txt(rel.find("isTenPercentOwner")) in ("1", "true", "True")
            officer_title = _txt(rel.find("officerTitle"))
            parsed["is_director"] = is_director
            parsed["is_officer"] = is_officer
            parsed["is_ten_percent_owner"] = is_ten
            parsed["officer_title"] = officer_title
            role_parts: List[str] = []
            if is_officer:
                role_parts.append(officer_title or "Officer")
            if is_director:
                role_parts.append("Director")
            if is_ten:
                role_parts.append("10%Owner")
            parsed["insider_role"] = " / ".join(role_parts) if role_parts else "Insider"

    # Non-derivative transactions (most insider buys/sells)
    for txn in root.findall(".//nonDerivativeTable/nonDerivativeTransaction"):
        t = _extract_transaction(txn)
        if t:
            parsed["transactions"].append(t)
    # Derivative transactions (options, etc.) — include but note via 'derivative'
    for txn in root.findall(".//derivativeTable/derivativeTransaction"):
        t = _extract_transaction(txn, derivative=True)
        if t:
            parsed["transactions"].append(t)

    return parsed


def _extract_transaction(node: ET.Element, derivative: bool = False) -> Optional[Dict[str, Any]]:
    try:
        date_n = node.find("transactionDate/value")
        code_n = node.find("transactionCoding/transactionCode")
        shares_n = node.find("transactionAmounts/transactionShares/value")
        price_n = node.find("transactionAmounts/transactionPricePerShare/value")
        ad_n = node.find("transactionAmounts/transactionAcquiredDisposedCode/value")
        if date_n is None and code_n is None:
            return None
        try:
            shares = float(_txt(shares_n) or 0)
        except Exception:
            shares = 0.0
        try:
            price = float(_txt(price_n) or 0)
        except Exception:
            price = 0.0
        return {
            "date": _txt(date_n),
            "code": _txt(code_n),  # P, S, A, M, F, etc.
            "shares": shares,
            "price": price,
            "value": shares * price,
            "acquired_disposed": _txt(ad_n),  # A or D
            "derivative": derivative,
        }
    except Exception:
        return None


def _persist_transactions(ticker: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        conn.executemany(
            """INSERT INTO insider_trades_cache
               (ticker, filing_date, insider_name, insider_role,
                transaction_type, shares, price, total_value,
                raw_filing_url, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    ticker,
                    r.get("filing_date") or r.get("date") or "",
                    r.get("insider_name") or "",
                    r.get("insider_role") or "",
                    r.get("code") or "",
                    float(r.get("shares") or 0),
                    float(r.get("price") or 0),
                    float(r.get("value") or 0),
                    r.get("filing_url") or "",
                    now,
                )
                for r in rows
            ],
        )
        conn.commit()
    finally:
        conn.close()


def _aggregate(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate the list of insider transactions into the tool's output."""
    buys = [t for t in transactions if t.get("acquired_disposed") == "A" and t.get("code") in ("P", "A")]
    # Strict buy = open-market purchase code "P"
    open_buys = [t for t in transactions if t.get("code") == "P"]
    sells = [t for t in transactions if t.get("code") == "S"]

    total_buy_value = sum(float(t.get("value") or 0) for t in open_buys)
    total_sell_value = sum(float(t.get("value") or 0) for t in sells)

    bs_ratio: Optional[float] = None
    if total_sell_value > 0:
        bs_ratio = round(total_buy_value / total_sell_value, 4)
    elif total_buy_value > 0:
        bs_ratio = None  # infinite — sells == 0

    # Clustered buying detection: any 30d window with >=3 distinct insiders buying
    clustered = False
    if open_buys:
        dated = []
        for t in open_buys:
            try:
                d = datetime.fromisoformat(t["date"]).date()
                dated.append((d, t.get("insider_name") or ""))
            except Exception:
                continue
        dated.sort(key=lambda x: x[0])
        for i, (d_i, _) in enumerate(dated):
            window_end = d_i + timedelta(days=30)
            window_names: set = set()
            for d_j, name_j in dated[i:]:
                if d_j > window_end:
                    break
                if name_j:
                    window_names.add(name_j)
            if len(window_names) >= 3:
                clustered = True
                break

    # CEO activity (officer title contains CEO/Chief Executive)
    ceo_activity: Optional[Dict[str, Any]] = None
    ceo_txns = [
        t for t in transactions
        if "CEO" in (t.get("officer_title") or "").upper()
        or "CHIEF EXECUTIVE" in (t.get("officer_title") or "").upper()
    ]
    if ceo_txns:
        ceo_buys = [t for t in ceo_txns if t.get("code") == "P"]
        ceo_sells = [t for t in ceo_txns if t.get("code") == "S"]
        if sum(float(t.get("value") or 0) for t in ceo_buys) >= sum(float(t.get("value") or 0) for t in ceo_sells):
            shares = sum(float(t.get("shares") or 0) for t in ceo_buys)
            val = sum(float(t.get("value") or 0) for t in ceo_buys)
            ceo_activity = {"type": "buy" if shares > 0 else "none", "shares": int(shares), "value": float(val)}
        else:
            shares = sum(float(t.get("shares") or 0) for t in ceo_sells)
            val = sum(float(t.get("value") or 0) for t in ceo_sells)
            ceo_activity = {"type": "sell", "shares": int(shares), "value": float(val)}

    # Top 10 by absolute value
    by_value = sorted(transactions, key=lambda t: abs(float(t.get("value") or 0)), reverse=True)[:10]
    recent = [
        {
            "date": t.get("date"),
            "insider": t.get("insider_name"),
            "role": t.get("insider_role"),
            "code": t.get("code"),
            "shares": int(float(t.get("shares") or 0)),
            "price": round(float(t.get("price") or 0), 4),
            "value": round(float(t.get("value") or 0), 2),
        }
        for t in by_value
    ]

    return {
        "total_buys": len(open_buys),
        "total_buy_value_usd": round(total_buy_value, 2),
        "total_sells": len(sells),
        "total_sell_value_usd": round(total_sell_value, 2),
        "buy_sell_ratio": bs_ratio,
        "clustered_buying": clustered,
        "ceo_activity": ceo_activity,
        "recent_trades": recent,
    }


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

class InsiderForm4Tool(Tool):
    name = "insider_form4"
    description = (
        "SEC EDGAR Form 4 insider-trade aggregator. Pulls last 90 days of "
        "Form 4 filings, aggregates buys/sells by value, flags clustered "
        "insider buying and CEO activity. Persists per-transaction rows to "
        "insider_trades_cache. Cached 24h."
    )
    cache_ttl_seconds = 24 * 3600
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Ticker symbol (e.g. NVDA)"},
                "lookback_days": {"type": "integer", "default": 90},
            },
            "required": ["ticker"],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0  # SEC EDGAR is free

    def _execute(self, ticker: str, lookback_days: int = 90, **kwargs) -> ToolResult:
        ticker = ticker.upper().strip()
        now_iso = datetime.now().isoformat()

        cached = get_tool_cache(self.name, ticker, self.cache_ttl_seconds)
        if cached:
            return ToolResult(
                tool_name=self.name,
                data=cached,
                sources=_build_sources(ticker, cached.get("_cik", ""), cached=True),
                confidence="high",
                cached=True,
            )

        cik = _resolve_cik(ticker)
        if not cik:
            return ToolResult(
                tool_name=self.name, data={},
                error=f"Could not resolve CIK for {ticker}",
                confidence="low",
            )

        submissions = _fetch_submissions(cik)
        if submissions is None:
            return ToolResult(
                tool_name=self.name, data={},
                error="SEC submissions index unavailable (rate-limited or network error)",
                confidence="low",
            )

        filings = _list_recent_form4_filings(submissions, lookback_days)

        all_transactions: List[Dict[str, Any]] = []
        for f in filings:
            url = _accession_to_url(cik, f["accession"], f["primary_document"])
            resp = _sec_get(url)
            if resp is None:
                continue
            parsed = _parse_form4_xml(resp.text)
            for t in parsed.get("transactions", []):
                merged = {
                    **t,
                    "insider_name": parsed["insider_name"],
                    "insider_role": parsed["insider_role"],
                    "officer_title": parsed["officer_title"],
                    "filing_date": f["filing_date"],
                    "filing_url": url,
                }
                all_transactions.append(merged)

        # Persist transactions (best-effort)
        try:
            _persist_transactions(ticker, all_transactions)
        except Exception as e:
            logger.warning(f"Failed to persist insider transactions: {e}")

        aggregated = _aggregate(all_transactions)
        data = {
            "ticker": ticker,
            "lookback_days": lookback_days,
            "_cik": cik,
            **aggregated,
            "fetched_at": now_iso,
        }

        save_tool_cache(self.name, ticker, data)

        confidence = "high" if all_transactions else "medium"
        return ToolResult(
            tool_name=self.name,
            data=data,
            sources=_build_sources(ticker, cik, cached=False),
            confidence=confidence,
        )


def _build_sources(ticker: str, cik: str, cached: bool) -> List[Source]:
    now = datetime.now().isoformat()
    suffix = " (cached)" if cached else ""
    url = (
        f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4"
        if cik else None
    )
    sources: List[Source] = []
    for field_name in (
        "total_buys", "total_sells", "buy_sell_ratio",
        "clustered_buying", "ceo_activity",
    ):
        sources.append(Source(
            tool="insider_form4",
            field=field_name,
            fetched_at=now,
            url=url,
            note=f"SEC EDGAR Form 4 aggregate{suffix}",
        ))
    return sources


register(InsiderForm4Tool())
