#!/usr/bin/env python3
"""
portfolio_service.py — Portfolio ingestion from Robinhood or manual CSV.

Robinhood flow:
  1. Call connect_robinhood(username, password, otp) → returns session info
  2. Session token cached in .cache/rh_session.json (no password stored)
  3. Subsequent calls reuse the cached session automatically

Manual CSV flow:
  CSV format: ticker,shares,avg_cost
  e.g.:  AAPL,10,145.50
         NVDA,5,480.00
"""

import csv
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from db import upsert_holdings, get_holdings as db_get_holdings

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / ".cache"
SESSION_FILE = CACHE_DIR / "rh_session.json"
PRICES_CACHE_FILE = CACHE_DIR / "latest_prices.json"

CACHE_DIR.mkdir(exist_ok=True)

# RAM-only session storage
_RAM_SESSION = {
    "username": None,
    "synced_at": None,
    "login_result": None
}

def _cleanup_disk_tokens() -> None:
    """Permanently delete existing cached Robinhood session tokens on disk."""
    try:
        # 1. Clean up our own cache rh_session.json
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
        
        # 2. Clean up robin_stocks token pickle files
        tokens_dir = Path.home() / ".tokens"
        if tokens_dir.exists():
            for pickle_file in tokens_dir.glob("*.pickle"):
                try:
                    pickle_file.unlink()
                except Exception:
                    pass
            try:
                # If directory is empty, remove it
                if not any(tokens_dir.iterdir()):
                    tokens_dir.rmdir()
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Error cleaning up disk session tokens: {e}")

# Run cleanup immediately on module import
_cleanup_disk_tokens()


# ============================================================================
# Robinhood Integration
# ============================================================================

def connect_robinhood(username: str, password: str, otp: str) -> Dict:
    """Authenticate with Robinhood using credentials + OTP.

    Uses the unofficial robin_stocks library. The session token is cached
    locally so subsequent calls do not require credentials.

    Args:
        username: Robinhood account email
        password: Robinhood account password
        otp: One-time password from authenticator app or SMS

    Returns:
        Dict with success status and message.
    """
    try:
        import robin_stocks.robinhood as rh
    except ImportError:
        return {
            "success": False,
            "error": "robin_stocks not installed. Run: pip install robin_stocks"
        }

    try:
        login_result = rh.login(
            username=username,
            password=password,
            mfa_code=otp,
            store_session=False,  # RAM-only session, no caching to disk
            expiresIn=86400       # 24-hour session
        )

        if login_result and login_result.get("access_token"):
            # Save a lightweight session marker to our own cache
            _save_session_marker(username, login_result)
            return {
                "success": True,
                "message": f"Connected to Robinhood as {username}",
                "username": username
            }
        else:
            return {
                "success": False,
                "error": "Login failed — check credentials or OTP and try again."
            }

    except Exception as e:
        error_msg = str(e)
        if "MFA" in error_msg or "mfa" in error_msg.lower():
            return {"success": False, "error": "Invalid OTP code. Please try again."}
        elif "challenge" in error_msg.lower():
            return {"success": False, "error": "Robinhood device challenge required. Check your email/SMS for a verification link."}
        else:
            return {"success": False, "error": f"Connection failed: {error_msg}"}


def disconnect_robinhood() -> None:
    """Log out from Robinhood and clear the session cache."""
    try:
        import robin_stocks.robinhood as rh
        rh.logout()
    except Exception:
        pass

    _RAM_SESSION["username"] = None
    _RAM_SESSION["synced_at"] = None
    _RAM_SESSION["login_result"] = None

    _cleanup_disk_tokens()


def is_connected() -> bool:
    """Check if we have an active Robinhood session."""
    if _RAM_SESSION["username"] is None or _RAM_SESSION["synced_at"] is None:
        return False
    try:
        synced_at = _RAM_SESSION["synced_at"]
        # Session expires after 24 hours
        from datetime import timedelta
        is_conn = datetime.now() - synced_at < timedelta(hours=24)
        if not is_conn:
            disconnect_robinhood()
            from db import clear_robinhood_holdings
            clear_robinhood_holdings()
        return is_conn
    except Exception:
        return False


def get_robinhood_holdings() -> Tuple[List[Dict], Optional[str]]:
    """Fetch current holdings from Robinhood.

    Returns:
        Tuple of (holdings_list, error_message)
        holdings_list: List of normalized holding dicts
        error_message: None on success, string on failure
    """
    try:
        import robin_stocks.robinhood as rh
    except ImportError:
        return [], "robin_stocks not installed"

    try:
        positions = rh.get_open_stock_positions()
        if not positions:
            return [], None

        holdings = []
        for pos in positions:
            try:
                ticker = _get_ticker_from_instrument(pos.get("instrument", ""))
                if not ticker:
                    continue

                shares = float(pos.get("quantity", 0))
                avg_cost = float(pos.get("average_buy_price", 0))

                if shares <= 0:
                    continue

                holdings.append({
                    "ticker": ticker.upper(),
                    "shares": round(shares, 6),
                    "avg_cost": round(avg_cost, 4),
                    "source": "robinhood"
                })
            except (ValueError, TypeError):
                continue

        return holdings, None

    except Exception as e:
        error = str(e)
        if "Not logged in" in error or "401" in error:
            disconnect_robinhood()
            return [], "Session expired. Please reconnect to Robinhood."
        return [], f"Failed to fetch holdings: {error}"


def sync_robinhood_portfolio() -> Dict:
    """Fetch Robinhood holdings and sync to the local database.

    Returns:
        Dict with success status, count, and any error.
    """
    holdings, error = get_robinhood_holdings()

    if error:
        return {"success": False, "error": error}

    if not holdings:
        return {"success": True, "count": 0, "message": "No open positions found."}

    upsert_holdings(holdings)

    return {
        "success": True,
        "count": len(holdings),
        "message": f"Synced {len(holdings)} positions from Robinhood.",
        "synced_at": datetime.now().isoformat()
    }


# ============================================================================
# Manual CSV Import
# ============================================================================

def import_from_csv(csv_text: str) -> Dict:
    """Parse a CSV string and save holdings to database.

    Expected CSV format (header optional):
        ticker,shares,avg_cost
        AAPL,10,145.50
        NVDA,5,480.00

    Also accepts 2-column format (assumes avg_cost = 0):
        AAPL,10

    Returns:
        Dict with success status, count of imported rows, and any errors.
    """
    reader = csv.reader(io.StringIO(csv_text.strip()))
    holdings = []
    errors = []
    row_num = 0

    for row in reader:
        row_num += 1
        row = [cell.strip() for cell in row if cell.strip()]

        if not row:
            continue

        # Skip header rows
        if row[0].lower() in ("ticker", "symbol", "stock"):
            continue

        try:
            ticker = row[0].upper()
            shares = float(row[1]) if len(row) > 1 else 0.0
            avg_cost = float(row[2]) if len(row) > 2 else 0.0

            if not ticker or shares <= 0:
                errors.append(f"Row {row_num}: invalid ticker or zero shares")
                continue

            holdings.append({
                "ticker": ticker,
                "shares": round(shares, 6),
                "avg_cost": round(avg_cost, 4),
                "source": "manual"
            })
        except (ValueError, IndexError) as e:
            errors.append(f"Row {row_num}: {str(e)}")

    if not holdings:
        return {
            "success": False,
            "error": "No valid holdings found in CSV.",
            "parsing_errors": errors
        }

    upsert_holdings(holdings)

    return {
        "success": True,
        "count": len(holdings),
        "message": f"Imported {len(holdings)} holdings.",
        "parsing_errors": errors,
        "imported_at": datetime.now().isoformat()
    }


# ============================================================================
# Portfolio Enrichment
# ============================================================================

def get_enriched_holdings() -> List[Dict]:
    """Return holdings from DB enriched with live price and P&L data.

    Fetches current prices from yfinance for all held tickers.
    Uses local cache as a fallback to ensure stability.
    """
    import yfinance as yf
    import pandas as pd

    raw_holdings = db_get_holdings()
    if not is_connected():
        raw_holdings = [h for h in raw_holdings if h.get("source") != "robinhood"]
    if not raw_holdings:
        return []

    tickers = [h["ticker"] for h in raw_holdings]

    # Load fallback prices from cache
    fallback_prices = {}
    if PRICES_CACHE_FILE.exists():
        try:
            fallback_prices = json.loads(PRICES_CACHE_FILE.read_text())
        except Exception as e:
            logger.warning(f"Failed to read prices cache: {e}")

    # Batch fetch current prices
    prices = {}
    try:
        data = yf.download(
            tickers=" ".join(tickers),
            period="2d",
            interval="1d",
            progress=False,
            group_by="ticker",
            threads=True
        )

        for ticker in tickers:
            try:
                # Resilient MultiIndex & single index extraction
                if isinstance(data.columns, pd.MultiIndex):
                    if data.columns.names[0] == 'Ticker':
                        price = float(data[ticker]["Close"].iloc[-1])
                    else:
                        price = float(data["Close"][ticker].iloc[-1])
                else:
                    if "Close" in data.columns:
                        price = float(data["Close"].iloc[-1])
                    else:
                        price = float(data[ticker]["Close"].iloc[-1])
                
                if pd.isna(price):
                    prices[ticker] = None
                else:
                    prices[ticker] = round(price, 2)
            except Exception:
                prices[ticker] = None

    except Exception as e:
        logger.warning(f"Failed to fetch batch prices: {e}")

    # Resolve prices using fetched data or fallback cache
    resolved_prices = {}
    updated_cache = fallback_prices.copy()
    cache_dirty = False

    for ticker in tickers:
        price = prices.get(ticker)
        if price is not None and not pd.isna(price):
            resolved_prices[ticker] = price
            updated_cache[ticker] = price
            cache_dirty = True
        else:
            # Fallback to cache if available
            fallback = fallback_prices.get(ticker)
            if fallback is not None:
                resolved_prices[ticker] = fallback
                logger.info(f"Using fallback price for {ticker}: {fallback}")
            else:
                # Fallback to avg_cost to ensure the UI doesn't completely break
                avg_cost = next((h.get("avg_cost") for h in raw_holdings if h["ticker"] == ticker), 0.0)
                if avg_cost and avg_cost > 0:
                    resolved_prices[ticker] = avg_cost
                    logger.info(f"Using avg_cost fallback for {ticker}: {avg_cost}")
                else:
                    resolved_prices[ticker] = None

    # Save updated cache if we got new prices
    if cache_dirty:
        try:
            PRICES_CACHE_FILE.write_text(json.dumps(updated_cache))
        except Exception as e:
            logger.warning(f"Failed to save prices cache: {e}")

    prices = resolved_prices

    # Enrich each holding
    enriched = []
    total_value = 0.0

    for h in raw_holdings:
        ticker = h["ticker"]
        shares = h["shares"]
        avg_cost = h.get("avg_cost") or 0.0
        current_price = prices.get(ticker)

        current_value = round(shares * current_price, 2) if current_price else None
        cost_basis = round(shares * avg_cost, 2) if avg_cost else None
        unrealized_pnl = round(current_value - cost_basis, 2) if (current_value and cost_basis) else None
        unrealized_pnl_pct = round(
            (unrealized_pnl / cost_basis) * 100, 2
        ) if (unrealized_pnl is not None and cost_basis and cost_basis != 0) else None

        if current_value:
            total_value += current_value

        enriched.append({
            **h,
            "current_price": current_price,
            "current_value": current_value,
            "cost_basis": cost_basis,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "weight_pct": None  # Calculated after total_value is known
        })

    # Calculate weights now that we have total_value
    for h in enriched:
        if h["current_value"] and total_value > 0:
            h["weight_pct"] = round((h["current_value"] / total_value) * 100, 2)

    # Sort by current value descending
    enriched.sort(key=lambda x: x.get("current_value") or 0, reverse=True)

    return enriched


def get_portfolio_summary(enriched_holdings: Optional[List[Dict]] = None) -> Dict:
    """Compute portfolio-level summary statistics.

    Args:
        enriched_holdings: Pre-fetched enriched holdings (fetched fresh if None)

    Returns:
        Dict with total_value, total_cost_basis, total_pnl, total_pnl_pct,
        sector_allocation, and top_holdings.
    """
    if enriched_holdings is None:
        enriched_holdings = get_enriched_holdings()

    if not enriched_holdings:
        return {"total_value": 0, "holdings_count": 0}

    total_value = 0
    total_cost = 0
    
    for h in enriched_holdings:
        cost = h.get("cost_basis") or 0
        val = h.get("current_value")
        
        total_cost += cost
        if val is not None:
            total_value += val
        else:
            # Fallback to cost_basis if live price is unavailable
            # to prevent total value from plummeting to $0
            total_value += cost

    total_value = round(total_value, 2)
    total_cost = round(total_cost, 2)
    total_pnl = round(total_value - total_cost, 2)
    total_pnl_pct = round((total_pnl / total_cost) * 100, 2) if total_cost > 0 else 0

    return {
        "total_value": round(total_value, 2),
        "total_value_fmt": f"${total_value:,.2f}",
        "total_cost_basis": round(total_cost, 2),
        "total_pnl": total_pnl,
        "total_pnl_fmt": f"{'+'if total_pnl >= 0 else ''}${total_pnl:,.2f}",
        "total_pnl_pct": total_pnl_pct,
        "holdings_count": len(enriched_holdings),
        "top_holdings": enriched_holdings[:5],
        "synced_at": enriched_holdings[0].get("synced_at") if enriched_holdings else None
    }


# ============================================================================
# Helpers
# ============================================================================

def _save_session_marker(username: str, login_result: Dict) -> None:
    """Save a non-sensitive session marker to RAM."""
    _RAM_SESSION["username"] = username
    _RAM_SESSION["synced_at"] = datetime.now()
    _RAM_SESSION["login_result"] = login_result


def _get_ticker_from_instrument(instrument_url: str) -> Optional[str]:
    """Resolve a Robinhood instrument URL to a ticker symbol."""
    if not instrument_url:
        return None
    try:
        import robin_stocks.robinhood as rh
        instrument_data = rh.get_instrument_by_url(instrument_url)
        return instrument_data.get("symbol")
    except Exception:
        return None


def get_session_info() -> Dict:
    """Return non-sensitive session status info."""
    connected = is_connected()
    return {
        "connected": connected,
        "username": _RAM_SESSION["username"] if connected else "",
        "synced_at": _RAM_SESSION["synced_at"].isoformat() if (connected and _RAM_SESSION["synced_at"]) else None
    }
