#!/usr/bin/env python3
"""
research_engine.py — Full deep research pipeline orchestrator.

For any US stock or ETF ticker, this module:
  1. Fetches fundamentals (yfinance)
  2. Computes technical indicators (RSI, MACD, MAs, existing patterns)
  3. Gets composite sentiment (sentiment_service)
  4. Fetches + summarizes SEC filing (edgar_service)
  5. Assembles context bundle → LLM investment thesis (llm_service)
  6. Caches the full report (SQLite, 24h TTL)
  7. Supports comparison of multiple tickers

The output is a standardized ResearchReport dict that the API
and frontend consume directly.
"""

import logging
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Cache TTL for research reports
_REPORT_CACHE_HOURS = 24


# ============================================================================
# Fundamentals
# ============================================================================

def fetch_fundamentals(ticker: str) -> Dict:
    """Fetch fundamental data for a ticker via yfinance.

    Returns a flat dict of the most useful financial metrics.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info or {}
    except Exception as e:
        logger.error(f"yfinance info fetch failed for {ticker}: {e}")
        return {"error": str(e)}

    def _safe(key, default=None):
        val = info.get(key)
        return val if val not in (None, "N/A", "", float("inf"), float("-inf")) else default

    def _fmt_large(val):
        if val is None:
            return "N/A"
        if abs(val) >= 1e12:
            return f"${val / 1e12:.2f}T"
        if abs(val) >= 1e9:
            return f"${val / 1e9:.2f}B"
        if abs(val) >= 1e6:
            return f"${val / 1e6:.2f}M"
        return f"${val:,.0f}"

    def _fmt_pct(val):
        if val is None:
            return "N/A"
        return f"{val * 100:.1f}%"

    revenue = _safe("totalRevenue")
    net_income = _safe("netIncomeToCommon")
    market_cap = _safe("marketCap")
    profit_margin = _safe("profitMargins")
    revenue_growth = _safe("revenueGrowth")
    gross_margin = _safe("grossMargins")
    operating_margin = _safe("operatingMargins")
    forward_pe = _safe("forwardPE")
    trailing_pe = _safe("trailingPE")
    price_to_book = _safe("priceToBook")
    eps = _safe("trailingEps")
    debt_to_equity = _safe("debtToEquity")
    current_ratio = _safe("currentRatio")
    dividend_yield = _safe("dividendYield")
    beta = _safe("beta")
    week_52_high = _safe("fiftyTwoWeekHigh")
    week_52_low = _safe("fiftyTwoWeekLow")
    current_price = _safe("currentPrice") or _safe("regularMarketPrice")
    target_mean_price = _safe("targetMeanPrice")
    recommendation = _safe("recommendationKey", "").replace("_", " ").title()

    # ETF detection
    quote_type = info.get("quoteType", "")
    is_etf = quote_type in ("ETF", "MUTUALFUND")

    return {
        "ticker": ticker.upper(),
        "company_name": info.get("longName", info.get("shortName", ticker.upper())),
        "sector": info.get("sector", "ETF" if is_etf else "Unknown"),
        "industry": info.get("industry", ""),
        "country": info.get("country", "US"),
        "is_etf": is_etf,
        "quote_type": quote_type,
        "description": (info.get("longBusinessSummary", "") or "")[:500],
        # Price
        "current_price": current_price,
        "week_52_high": week_52_high,
        "week_52_low": week_52_low,
        "pct_from_52w_high": round(((current_price or 0) / week_52_high - 1) * 100, 2) if (week_52_high and current_price) else None,
        "pct_from_52w_low": round(((current_price or 0) / week_52_low - 1) * 100, 2) if (week_52_low and current_price) else None,
        # Valuation
        "market_cap": market_cap,
        "market_cap_fmt": _fmt_large(market_cap),
        "forward_pe": round(forward_pe, 2) if forward_pe else None,
        "trailing_pe": round(trailing_pe, 2) if trailing_pe else None,
        "price_to_book": round(price_to_book, 2) if price_to_book else None,
        "eps": eps,
        "beta": round(beta, 2) if beta else None,
        # Income
        "revenue": revenue,
        "revenue_fmt": _fmt_large(revenue),
        "net_income": net_income,
        "net_income_fmt": _fmt_large(net_income),
        "revenue_growth": round(revenue_growth * 100, 2) if revenue_growth else None,
        "revenue_growth_fmt": _fmt_pct(revenue_growth),
        # Margins
        "profit_margin": round((profit_margin or 0) * 100, 2) if profit_margin else None,
        "profit_margin_fmt": _fmt_pct(profit_margin),
        "gross_margin": round((gross_margin or 0) * 100, 2) if gross_margin else None,
        "operating_margin": round((operating_margin or 0) * 100, 2) if operating_margin else None,
        # Balance sheet
        "debt_to_equity": round(debt_to_equity, 2) if debt_to_equity else None,
        "current_ratio": round(current_ratio, 2) if current_ratio else None,
        # Income / Dividends
        "dividend_yield": round((dividend_yield or 0) * 100, 2) if dividend_yield else None,
        # Analyst
        "analyst_target": target_mean_price,
        "analyst_recommendation": recommendation,
    }


# ============================================================================
# Technical Indicators
# ============================================================================

def _compute_rsi(prices: pd.Series, period: int = 14) -> Optional[float]:
    """Compute RSI(14) for the most recent price."""
    if len(prices) < period + 1:
        return None
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 2) if not math.isnan(val) else None


def _compute_macd(prices: pd.Series) -> Dict:
    """Compute MACD (12,26,9) and return signal."""
    if len(prices) < 35:
        return {"macd": None, "signal": None, "histogram": None, "signal_label": "N/A"}
    ema12 = prices.ewm(span=12, adjust=False).mean()
    ema26 = prices.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    macd_val = float(macd_line.iloc[-1])
    sig_val = float(signal_line.iloc[-1])
    hist_val = float(histogram.iloc[-1])
    # Recent crossover detection
    if histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0:
        label = "bullish_crossover"
    elif histogram.iloc[-1] < 0 and histogram.iloc[-2] >= 0:
        label = "bearish_crossover"
    elif macd_val > sig_val:
        label = "bullish"
    else:
        label = "bearish"
    return {
        "macd": round(macd_val, 4),
        "signal": round(sig_val, 4),
        "histogram": round(hist_val, 4),
        "signal_label": label,
    }


def _compute_bollinger(prices: pd.Series, period: int = 20) -> Dict:
    """Compute Bollinger Bands (20, 2σ)."""
    if len(prices) < period:
        return {"upper": None, "middle": None, "lower": None, "position": None}
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = float((sma + 2 * std).iloc[-1])
    middle = float(sma.iloc[-1])
    lower = float((sma - 2 * std).iloc[-1])
    current = float(prices.iloc[-1])
    # % position within band (0 = at lower, 1 = at upper)
    band_width = upper - lower
    position = round((current - lower) / band_width, 3) if band_width > 0 else 0.5
    return {
        "upper": round(upper, 2),
        "middle": round(middle, 2),
        "lower": round(lower, 2),
        "position": position  # >0.8 = overbought, <0.2 = oversold
    }


def fetch_technicals(ticker: str, history_data: Optional[List[Dict]] = None) -> Dict:
    """Compute technical indicators for a ticker.

    Args:
        ticker: Stock symbol
        history_data: Pre-fetched history [{date, close, volume}, ...] (optional)
                      If None, fetches 1y of data from yfinance.

    Returns:
        Dict with RSI, MACD, Bollinger Bands, MAs, detected patterns.
    """
    # Get price history
    if history_data:
        closes = pd.Series([d["close"] for d in history_data])
        dates = [d["date"] for d in history_data]
    else:
        try:
            stock = yf.Ticker(ticker.upper())
            hist = stock.history(period="1y", auto_adjust=True)
            if hist.empty:
                return {"error": "No price history available"}
            closes = hist["Close"]
            dates = [d.strftime("%Y-%m-%d") for d in hist.index]
        except Exception as e:
            logger.error(f"Failed to fetch price history for {ticker}: {e}")
            return {"error": str(e)}

    closes = pd.Series(closes.values if hasattr(closes, "values") else list(closes))

    # Moving averages
    ma_50 = round(float(closes.rolling(50).mean().iloc[-1]), 2) if len(closes) >= 50 else None
    ma_200 = round(float(closes.rolling(200).mean().iloc[-1]), 2) if len(closes) >= 200 else None
    current_price = round(float(closes.iloc[-1]), 2)

    # Golden/Death cross
    golden_cross = None
    if ma_50 and ma_200:
        golden_cross = ma_50 > ma_200

    # Price vs MAs
    above_50ma = current_price > ma_50 if ma_50 else None
    above_200ma = current_price > ma_200 if ma_200 else None

    # Indicators
    rsi = _compute_rsi(closes)
    macd = _compute_macd(closes)
    bollinger = _compute_bollinger(closes)

    # RSI interpretation
    rsi_signal = "overbought" if (rsi and rsi > 70) else ("oversold" if (rsi and rsi < 30) else "neutral")

    # Detect patterns using existing app.py functions (imported dynamically)
    detected_patterns = _detect_all_patterns(
        closes.tolist(),
        dates[-len(closes):]
    )

    # 1-year price performance
    if len(closes) >= 252:
        year_return = round((closes.iloc[-1] / closes.iloc[-252] - 1) * 100, 2)
    elif len(closes) > 1:
        year_return = round((closes.iloc[-1] / closes.iloc[0] - 1) * 100, 2)
    else:
        year_return = None

    # 30-day volatility (annualized)
    if len(closes) >= 30:
        daily_returns = closes.pct_change().dropna()[-30:]
        volatility = round(float(daily_returns.std() * (252 ** 0.5) * 100), 2)
    else:
        volatility = None

    return {
        "current_price": current_price,
        "ma_50": ma_50,
        "ma_200": ma_200,
        "golden_cross": golden_cross,
        "above_50ma": above_50ma,
        "above_200ma": above_200ma,
        "rsi": rsi,
        "rsi_signal": rsi_signal,
        "macd": macd,
        "bollinger": bollinger,
        "year_return_pct": year_return,
        "annualized_volatility_pct": volatility,
        "patterns": detected_patterns,
        "data_points": len(closes),
    }


def _detect_all_patterns(prices: list, dates: list) -> List[Dict]:
    """Run all 11 pattern detectors and return detected patterns."""
    detected = []
    try:
        # Import pattern detection functions from the existing app.py
        # We use a lazy import to avoid circular deps
        import importlib.util
        import sys

        # Try to import detection functions from app module if already loaded
        app_module = sys.modules.get("__main__") or sys.modules.get("app")

        # Pattern detectors to try
        detectors = []
        try:
            from app import (
                detect_head_and_shoulders,
                detect_inverse_head_shoulders,
                detect_double_top,
                detect_double_bottom,
                detect_ascending_triangle,
                detect_descending_triangle,
                detect_cup_and_handle,
                detect_bullish_flag,
                detect_falling_wedge,
            )
            detectors = [
                ("head_shoulders", detect_head_and_shoulders),
                ("inverse_head_shoulders", detect_inverse_head_shoulders),
                ("double_top", detect_double_top),
                ("double_bottom", detect_double_bottom),
                ("ascending_triangle", detect_ascending_triangle),
                ("descending_triangle", detect_descending_triangle),
                ("cup_and_handle", detect_cup_and_handle),
                ("bullish_flag", detect_bullish_flag),
                ("falling_wedge", detect_falling_wedge),
            ]
        except ImportError:
            pass

        for pattern_key, detector_fn in detectors:
            try:
                result = detector_fn(prices, dates)
                if result and result.get("detected"):
                    detected.append({
                        "type": pattern_key,
                        "name": result.get("pattern_name", pattern_key.replace("_", " ").title()),
                        "signal": result.get("signal", "unknown"),
                        "confidence": result.get("confidence", 0),
                        "target_price": result.get("target_price"),
                    })
            except Exception:
                continue

    except Exception as e:
        logger.debug(f"Pattern detection failed: {e}")

    return sorted(detected, key=lambda x: x.get("confidence", 0), reverse=True)


# ============================================================================
# ETF-specific Data
# ============================================================================

def fetch_etf_data(ticker: str, fundamentals: Dict) -> Dict:
    """Fetch ETF-specific data: top holdings, category, expense ratio."""
    if not fundamentals.get("is_etf"):
        return {}

    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info or {}

        # Top holdings via yfinance
        holdings = []
        try:
            fund_holdings = stock.funds_data
            if fund_holdings and hasattr(fund_holdings, "top_holdings"):
                top = fund_holdings.top_holdings
                for _, row in top.iterrows():
                    holdings.append({
                        "ticker": row.get("Symbol", ""),
                        "name": row.get("Name", row.get("Holding Name", "")),
                        "weight": round(float(row.get("% Net Assets", row.get("Weight", 0))), 2)
                    })
        except Exception:
            pass

        return {
            "category": info.get("category", ""),
            "expense_ratio": info.get("annualReportExpenseRatio"),
            "ytd_return": info.get("ytdReturn"),
            "three_year_avg_return": info.get("threeYearAverageReturn"),
            "five_year_avg_return": info.get("fiveYearAverageReturn"),
            "total_assets": info.get("totalAssets"),
            "top_holdings": holdings[:10],
        }
    except Exception as e:
        logger.warning(f"ETF data fetch failed for {ticker}: {e}")
        return {}


# ============================================================================
# Full Research Pipeline
# ============================================================================

def run_full_research(
    ticker: str,
    portfolio_context: Optional[Dict] = None,
    force_refresh: bool = False,
    include_edgar: bool = True,
) -> Dict:
    """Run the complete deep research pipeline for a ticker.

    Stages:
      1. Check cache (24h TTL) unless force_refresh
      2. Fetch fundamentals
      3. Compute technicals
      4. Composite sentiment
      5. SEC EDGAR filing summary
      6. LLM investment thesis
      7. Cache and return

    Args:
        ticker: Stock symbol (e.g. 'NVDA')
        portfolio_context: Optional dict with weight_pct, avg_cost, unrealized_pnl_pct
        force_refresh: Skip cache and regenerate
        include_edgar: Include SEC filing analysis (adds ~10-15s)

    Returns:
        Full research report dict
    """
    from db import get_research_cache, save_research_cache
    from sentiment_service import get_composite_sentiment
    from llm_service import generate_thesis

    ticker = ticker.upper().strip()

    # 1. Cache check
    if not force_refresh:
        cached = get_research_cache(ticker, max_age_hours=_REPORT_CACHE_HOURS)
        if cached:
            logger.info(f"Research cache hit for {ticker}")
            if portfolio_context:
                cached["portfolio_context"] = portfolio_context
            return cached

    logger.info(f"Running full research pipeline for {ticker}")
    report = {
        "ticker": ticker,
        "generated_at": datetime.now().isoformat(),
        "status": "pending",
    }

    # 2. Fundamentals
    logger.info(f"[{ticker}] Fetching fundamentals...")
    fundamentals = fetch_fundamentals(ticker)
    report["fundamentals"] = fundamentals
    report["company_name"] = fundamentals.get("company_name", ticker)
    report["sector"] = fundamentals.get("sector", "Unknown")
    report["is_etf"] = fundamentals.get("is_etf", False)

    # ETF-specific data
    if fundamentals.get("is_etf"):
        report["etf_data"] = fetch_etf_data(ticker, fundamentals)

    # 3. Technicals
    logger.info(f"[{ticker}] Computing technicals...")
    technicals = fetch_technicals(ticker)
    report["technicals"] = technicals

    # 4. Sentiment
    logger.info(f"[{ticker}] Fetching sentiment...")
    try:
        sentiment = get_composite_sentiment(ticker)
    except Exception as e:
        logger.warning(f"Sentiment failed for {ticker}: {e}")
        sentiment = {
            "composite_score": 5.0, "label": "neutral",
            "error": str(e)
        }
    report["sentiment"] = sentiment

    # 5. EDGAR filing
    edgar_summary = {}
    if include_edgar and not fundamentals.get("is_etf"):
        logger.info(f"[{ticker}] Fetching SEC filing...")
        try:
            from edgar_service import summarize_filing
            edgar_summary = summarize_filing(ticker)
        except Exception as e:
            logger.warning(f"EDGAR failed for {ticker}: {e}")
            edgar_summary = {"available": False, "error": str(e)}
    report["edgar_summary"] = edgar_summary

    # 6. Portfolio context (optional)
    if portfolio_context:
        report["portfolio_context"] = portfolio_context

    # 7. LLM thesis
    logger.info(f"[{ticker}] Generating LLM thesis...")
    try:
        context_bundle = _build_context_bundle(report)
        thesis = generate_thesis(context_bundle)
    except Exception as e:
        logger.warning(f"LLM thesis failed for {ticker}: {e}")
        thesis = {
            "error": str(e),
            "summary": "AI thesis generation failed — check LLM settings.",
            "recommendation": "HOLD",
            "conviction": "LOW",
            "bull_case": [],
            "bear_case": [],
            "action_items": ["Configure LLM provider in Settings to enable AI analysis"],
        }
    report["thesis"] = thesis
    report["status"] = "complete"

    # 8. Cache
    try:
        from db import get_llm_settings
        provider = get_llm_settings().get("provider", "unknown")
        save_research_cache(ticker, report, provider)
    except Exception:
        pass

    return report


def _build_context_bundle(report: Dict) -> Dict:
    """Build the context bundle dict expected by llm_service.generate_thesis."""
    fund = report.get("fundamentals", {})
    tech = report.get("technicals", {})
    sent = report.get("sentiment", {})
    edgar = report.get("edgar_summary", {})

    return {
        "ticker": report["ticker"],
        "company_name": report.get("company_name", report["ticker"]),
        "sector": report.get("sector", "Unknown"),
        "fundamentals": {
            "revenue_fmt": fund.get("revenue_fmt", "N/A"),
            "revenue_growth_fmt": (
                f"{fund['revenue_growth']:.1f}%" if fund.get("revenue_growth") else "N/A"
            ),
            "net_income_fmt": fund.get("net_income_fmt", "N/A"),
            "profit_margin_fmt": (
                f"{fund['profit_margin']:.1f}%" if fund.get("profit_margin") else "N/A"
            ),
            "forward_pe": fund.get("forward_pe"),
            "trailing_pe": fund.get("trailing_pe"),
            "eps": fund.get("eps"),
            "sector_pe_avg": None,  # Could be enriched from S&P 500 data
            "debt_equity": fund.get("debt_to_equity"),
            "current_ratio": fund.get("current_ratio"),
            "market_cap_fmt": fund.get("market_cap_fmt", "N/A"),
        },
        "technicals": {
            "current_price": tech.get("current_price"),
            "week_52_high": fund.get("week_52_high"),
            "week_52_low": fund.get("week_52_low"),
            "pct_from_52w_high": fund.get("pct_from_52w_high"),
            "pct_from_52w_low": fund.get("pct_from_52w_low"),
            "rsi": tech.get("rsi"),
            "ma_50": tech.get("ma_50"),
            "ma_200": tech.get("ma_200"),
            "macd_signal": tech.get("macd", {}).get("signal_label", "N/A"),
            "patterns": [p["name"] for p in tech.get("patterns", [])],
            "year_return_pct": tech.get("year_return_pct"),
        },
        "sentiment": {
            "composite_score": sent.get("composite_score", 5.0),
            "news_score": sent.get("news_score"),
            "analyst_rating": sent.get("analyst_rating", "N/A"),
            "analyst_target": sent.get("analyst_target"),
            "reddit_score": sent.get("reddit_score"),
            "reddit_mentions": sent.get("reddit_mentions", 0),
            "top_headlines": sent.get("top_headlines", []),
        },
        "edgar_summary": {
            "business": edgar.get("business", ""),
            "risks": edgar.get("risks", ""),
            "mda": edgar.get("mda", ""),
        },
        "portfolio_context": report.get("portfolio_context"),
    }


# ============================================================================
# Multi-ticker Comparison
# ============================================================================

def compare_tickers(tickers: List[str], portfolio_holdings: Optional[List[Dict]] = None) -> Dict:
    """Run research on multiple tickers and generate a comparative analysis.

    Args:
        tickers: List of ticker symbols (max 4)
        portfolio_holdings: Optional list of holdings from portfolio_service

    Returns:
        Comparison report with per-ticker reports + LLM comparison
    """
    from llm_service import compare_tickers as llm_compare

    tickers = [t.upper() for t in tickers[:4]]  # Cap at 4

    # Build portfolio context map if holdings provided
    context_map = {}
    if portfolio_holdings:
        for h in portfolio_holdings:
            if h["ticker"] in tickers:
                context_map[h["ticker"]] = {
                    "weight_pct": h.get("weight_pct"),
                    "avg_cost": h.get("avg_cost"),
                    "unrealized_pnl_pct": h.get("unrealized_pnl_pct"),
                }

    # Run research for each ticker (no EDGAR to keep it fast)
    reports = []
    for ticker in tickers:
        logger.info(f"Comparing: running research for {ticker}")
        report = run_full_research(
            ticker,
            portfolio_context=context_map.get(ticker),
            include_edgar=False  # Skip EDGAR for comparison speed
        )
        reports.append(report)

    # LLM comparison
    comparison = {}
    try:
        comparison = llm_compare(reports)
    except Exception as e:
        logger.warning(f"LLM comparison failed: {e}")
        comparison = {"error": str(e)}

    return {
        "tickers": tickers,
        "generated_at": datetime.now().isoformat(),
        "reports": reports,
        "comparison": comparison,
    }
