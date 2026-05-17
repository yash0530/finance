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
# Multi-Quarter Financial Trends
# ============================================================================

def fetch_financial_trends(ticker: str) -> Dict:
    """Pull 3-5 years of quarterly financial data and compute trajectory metrics.

    Analyzes revenue, margins, FCF, EPS, debt, and returns over 8-12 quarters
    to detect acceleration/deceleration, expansion/contraction, and quality.

    Returns:
        Dict with 'quarters' (raw data for charting) and 'signals' (computed insights).
    """
    try:
        stock = yf.Ticker(ticker.upper())
    except Exception as e:
        logger.error(f"yfinance Ticker init failed for {ticker}: {e}")
        return {"error": str(e), "quarters": [], "signals": {}}

    quarters = []

    # --- Pull quarterly financials ---
    try:
        inc = stock.quarterly_financials
        bs = stock.quarterly_balance_sheet
        cf = stock.quarterly_cashflow
    except Exception as e:
        logger.warning(f"Quarterly data fetch failed for {ticker}: {e}")
        return {"error": str(e), "quarters": [], "signals": {}}

    if inc is None or inc.empty:
        return {"error": "No quarterly financials available", "quarters": [], "signals": {}}

    # Columns are dates (most recent first). Transpose so rows = quarters.
    dates = sorted(inc.columns)  # oldest first

    def _safe_val(df, key, date):
        """Safely extract a value from a DataFrame."""
        if df is None or df.empty:
            return None
        for k in ([key] if isinstance(key, str) else key):
            if k in df.index:
                try:
                    v = df.loc[k, date]
                    if pd.notna(v) and v != 0:
                        return float(v)
                except (KeyError, TypeError):
                    continue
        return None

    for dt in dates:
        revenue = _safe_val(inc, ["Total Revenue", "Revenue"], dt)
        cogs = _safe_val(inc, ["Cost Of Revenue", "Cost of Revenue"], dt)
        gross_profit = _safe_val(inc, ["Gross Profit"], dt)
        operating_income = _safe_val(inc, ["Operating Income", "EBIT"], dt)
        net_income = _safe_val(inc, ["Net Income", "Net Income Common Stockholders"], dt)
        ebitda = _safe_val(inc, ["EBITDA", "Normalized EBITDA"], dt)

        # Balance sheet
        total_debt = _safe_val(bs, ["Total Debt", "Long Term Debt"], dt)
        total_equity = _safe_val(bs, ["Total Stockholders Equity", "Stockholders Equity", "Common Stock Equity"], dt)
        total_assets = _safe_val(bs, ["Total Assets"], dt)
        current_assets = _safe_val(bs, ["Current Assets", "Total Current Assets"], dt)
        current_liabilities = _safe_val(bs, ["Current Liabilities", "Total Current Liabilities"], dt)
        cash = _safe_val(bs, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"], dt)

        # Cash flow
        operating_cf = _safe_val(cf, ["Operating Cash Flow", "Total Cash From Operating Activities"], dt)
        capex = _safe_val(cf, ["Capital Expenditure", "Capital Expenditures"], dt)
        fcf = None
        if operating_cf is not None and capex is not None:
            fcf = operating_cf - abs(capex)  # capex is usually negative
        elif operating_cf is not None:
            fcf = operating_cf

        # Compute margins
        gross_margin = None
        if gross_profit and revenue and revenue != 0:
            gross_margin = round(gross_profit / revenue * 100, 2)
        elif revenue and cogs and revenue != 0:
            gross_margin = round((revenue - cogs) / revenue * 100, 2)

        operating_margin = round(operating_income / revenue * 100, 2) if operating_income and revenue else None
        net_margin = round(net_income / revenue * 100, 2) if net_income and revenue else None

        # Debt / equity
        debt_equity = round(total_debt / total_equity, 2) if total_debt and total_equity and total_equity != 0 else None

        # ROE
        roe = round(net_income / total_equity * 100, 2) if net_income and total_equity and total_equity != 0 else None

        # Earnings quality (FCF / Net Income) — >0.8 is good, <0.5 is suspicious
        earnings_quality = round(fcf / net_income, 2) if fcf and net_income and net_income != 0 else None

        quarters.append({
            "date": dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt),
            "quarter_label": f"Q{((dt.month - 1) // 3) + 1} {dt.year}" if hasattr(dt, "month") else str(dt),
            "revenue": revenue,
            "gross_profit": gross_profit,
            "operating_income": operating_income,
            "net_income": net_income,
            "ebitda": ebitda,
            "fcf": fcf,
            "operating_cf": operating_cf,
            "capex": capex,
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "net_margin": net_margin,
            "total_debt": total_debt,
            "total_equity": total_equity,
            "cash": cash,
            "debt_equity": debt_equity,
            "roe": roe,
            "earnings_quality": earnings_quality,
        })

    # --- Compute trajectory signals ---
    signals = _compute_trend_signals(quarters)

    return {
        "quarters": quarters,
        "quarter_count": len(quarters),
        "signals": signals,
    }


def _compute_trend_signals(quarters: List[Dict]) -> Dict:
    """Compute directional trend signals from quarterly data."""
    if len(quarters) < 2:
        return {}

    def _trend(values):
        """Classify trend from a list of numeric values (oldest to newest)."""
        clean = [v for v in values if v is not None]
        if len(clean) < 2:
            return {"direction": "insufficient_data", "values": clean}
        recent_half = clean[len(clean) // 2:]
        older_half = clean[:len(clean) // 2]
        avg_recent = sum(recent_half) / len(recent_half) if recent_half else 0
        avg_older = sum(older_half) / len(older_half) if older_half else 0

        if avg_older == 0:
            pct_change = 0
        else:
            pct_change = round((avg_recent - avg_older) / abs(avg_older) * 100, 1)

        if pct_change > 10:
            direction = "expanding"
        elif pct_change > 2:
            direction = "slightly_expanding"
        elif pct_change < -10:
            direction = "contracting"
        elif pct_change < -2:
            direction = "slightly_contracting"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "change_pct": pct_change,
            "latest": clean[-1] if clean else None,
            "oldest": clean[0] if clean else None,
        }

    def _growth_rates(values):
        """Compute YoY growth rates (need >= 5 quarters for meaningful QoQ→YoY)."""
        clean = [(i, v) for i, v in enumerate(values) if v is not None]
        rates = []
        for j in range(len(clean)):
            idx, val = clean[j]
            # Find value ~4 quarters ago
            for k in range(j):
                prev_idx, prev_val = clean[k]
                if idx - prev_idx >= 3 and idx - prev_idx <= 5 and prev_val != 0:
                    rates.append(round((val - prev_val) / abs(prev_val) * 100, 1))
                    break
        return rates

    revenues = [q["revenue"] for q in quarters]
    growth_rates = _growth_rates(revenues)

    # Revenue growth acceleration/deceleration
    rev_accel = "insufficient_data"
    if len(growth_rates) >= 2:
        recent = growth_rates[-1]
        prev = growth_rates[-2] if len(growth_rates) >= 2 else growth_rates[0]
        if recent > prev + 3:
            rev_accel = "accelerating"
        elif recent < prev - 3:
            rev_accel = "decelerating"
        else:
            rev_accel = "stable"

    # Market cap for FCF yield (from latest quarter's data)
    latest = quarters[-1] if quarters else {}

    signals = {
        "revenue_trend": _trend(revenues),
        "revenue_growth_rates": growth_rates,
        "revenue_acceleration": rev_accel,
        "gross_margin_trend": _trend([q["gross_margin"] for q in quarters]),
        "operating_margin_trend": _trend([q["operating_margin"] for q in quarters]),
        "net_margin_trend": _trend([q["net_margin"] for q in quarters]),
        "fcf_trend": _trend([q["fcf"] for q in quarters]),
        "debt_equity_trend": _trend([q["debt_equity"] for q in quarters]),
        "roe_trend": _trend([q["roe"] for q in quarters]),
        "earnings_quality_latest": latest.get("earnings_quality"),
        "earnings_quality_verdict": (
            "high" if (latest.get("earnings_quality") or 0) > 0.8
            else "moderate" if (latest.get("earnings_quality") or 0) > 0.5
            else "low" if latest.get("earnings_quality") is not None
            else "unknown"
        ),
    }

    return signals


# ============================================================================
# Intrinsic Valuation (DCF) & Peer Comparison
# ============================================================================

def compute_intrinsic_value(ticker: str, fundamentals: Dict, trends: Dict) -> Dict:
    """Compute intrinsic value using a Discounted Cash Flow (DCF) model.

    Uses an automated 3-scenario model (Base, Bull, Bear) based on
    latest FCF, revenue growth trajectories, and standard discount rates.
    """
    if fundamentals.get("is_etf"):
        return {"skipped": True, "reason": "Not applicable for ETFs"}

    # Extract base inputs
    fcf = None
    shares_outstanding = None
    growth_rate = 0.05  # Default 5%

    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info
        shares_outstanding = info.get("sharesOutstanding")

        # Prefer calculating TTM FCF from our trends data (latest 4 quarters)
        fcf = None
        if trends and trends.get("quarters"):
            fcf_vals = [q["fcf"] for q in trends["quarters"][-4:] if q.get("fcf") is not None]
            if len(fcf_vals) == 4:
                fcf = sum(fcf_vals)
        
        # Fallback to Yahoo Finance info
        if not fcf:
            fcf = info.get("freeCashflow")
    except Exception as e:
        logger.warning(f"[{ticker}] Failed to fetch inputs for DCF: {e}")

    if not fcf or not shares_outstanding or fcf <= 0:
        return {"error": "Insufficient or negative FCF data for DCF modeling"}

    # Determine growth rate from trends if possible
    if trends and trends.get("signals") and trends["signals"].get("revenue_growth_rates"):
        rates = trends["signals"]["revenue_growth_rates"]
        if rates:
            avg_recent_growth = sum(rates) / len(rates) / 100
            # Cap growth rate between 2% and 25% for conservative modeling
            growth_rate = max(0.02, min(0.25, avg_recent_growth))

    # Standard DCF parameters
    discount_rate = 0.09  # 9% WACC assumption
    terminal_growth_rate = 0.025  # 2.5% terminal growth
    years = 5

    def _calculate_dcf(fcf_base, g_rate, d_rate, t_rate, shares):
        pv_fcf = 0
        projected_fcf = fcf_base
        for i in range(1, years + 1):
            projected_fcf *= (1 + g_rate)
            pv_fcf += projected_fcf / ((1 + d_rate) ** i)

        # Terminal Value = FCF5 * (1 + g) / (WACC - g)
        terminal_value = (projected_fcf * (1 + t_rate)) / (d_rate - t_rate)
        pv_tv = terminal_value / ((1 + d_rate) ** years)

        intrinsic_value_total = pv_fcf + pv_tv
        return round(intrinsic_value_total / shares, 2)

    current_price = fundamentals.get("current_price", 0)

    try:
        base_value = _calculate_dcf(fcf, growth_rate, discount_rate, terminal_growth_rate, shares_outstanding)
        bull_value = _calculate_dcf(fcf, growth_rate * 1.5, discount_rate - 0.01, terminal_growth_rate, shares_outstanding)
        bear_value = _calculate_dcf(fcf, growth_rate * 0.5, discount_rate + 0.01, terminal_growth_rate, shares_outstanding)

        margin_of_safety = round((base_value - current_price) / base_value * 100, 1) if base_value > 0 else 0

        # Verdict
        if current_price < bear_value:
            verdict = "Deeply Undervalued"
        elif current_price < base_value:
            verdict = "Undervalued"
        elif current_price < bull_value:
            verdict = "Fairly Valued"
        else:
            verdict = "Overvalued"

        return {
            "base_case": base_value,
            "bull_case": bull_value,
            "bear_case": bear_value,
            "current_price": current_price,
            "margin_of_safety_pct": margin_of_safety,
            "implied_growth_rate": round(growth_rate * 100, 1),
            "verdict": verdict,
            "inputs": {
                "fcf_base": fcf,
                "shares": shares_outstanding,
                "discount_rate": discount_rate,
            }
        }
    except Exception as e:
        logger.error(f"[{ticker}] DCF math error: {e}")
        return {"error": str(e)}


def get_peer_valuation(ticker: str, sector: str) -> Dict:
    """Fetch basic peer comparison metrics."""
    # Note: Comprehensive peer lookup requires paid APIs or complex scraping.
    # For this iteration, we mock sector averages based on the sector string.
    # In a real app, you would query your DB or Yahoo Finance sector peers.
    sector_averages = {
        "Technology": {"pe": 32.5, "ps": 6.2, "pb": 7.8},
        "Healthcare": {"pe": 24.1, "ps": 4.1, "pb": 4.5},
        "Financial Services": {"pe": 14.5, "ps": 2.8, "pb": 1.4},
        "Consumer Cyclical": {"pe": 22.3, "ps": 2.1, "pb": 3.9},
        "Industrials": {"pe": 20.8, "ps": 1.9, "pb": 3.4},
        "Energy": {"pe": 12.4, "ps": 1.2, "pb": 1.8},
    }

    avg = sector_averages.get(sector, {"pe": 20.0, "ps": 2.5, "pb": 3.0})
    return {
        "sector": sector,
        "average_pe": avg["pe"],
        "average_ps": avg["ps"],
        "average_pb": avg["pb"]
    }


# ============================================================================
# Position Sizing & Risk Management
# ============================================================================

def compute_position_sizing(ticker: str, fundamentals: Dict, technicals: Dict, valuation: Dict, portfolio_value: float = 10000.0) -> Dict:
    """Compute risk-managed position size using Half-Kelly Criterion and volatility scaling.
    
    Args:
        ticker: Stock symbol
        fundamentals: Output of fetch_fundamentals
        technicals: Output of fetch_technicals
        valuation: Output of compute_intrinsic_value
        portfolio_value: Total portfolio value in dollars (default $10K)
        
    Returns:
        Dict with recommended sizing, stop-loss, and take-profit levels.
    """
    if fundamentals.get("error") or technicals.get("error"):
        return {"error": "Missing required data for position sizing"}

    current_price = fundamentals.get("current_price")
    if not current_price or current_price <= 0:
        return {"error": "Invalid current price"}

    # 1. Determine Win Probability (P) based on technicals and valuation
    win_probability = 0.50  # Base line
    
    # Adjust for valuation margin of safety
    mos = valuation.get("margin_of_safety_pct")
    if mos is not None:
        if mos > 20: win_probability += 0.10
        elif mos > 0: win_probability += 0.05
        elif mos < -20: win_probability -= 0.10
        elif mos < 0: win_probability -= 0.05
        
    # Adjust for technical trend
    if technicals.get("above_200ma"): win_probability += 0.05
    if technicals.get("golden_cross"): win_probability += 0.05
    if technicals.get("rsi") and technicals["rsi"] > 70: win_probability -= 0.05
    if technicals.get("rsi") and technicals["rsi"] < 30: win_probability += 0.05
    
    # Cap probability between 10% and 80%
    win_probability = max(0.10, min(0.80, win_probability))
    loss_probability = 1.0 - win_probability

    # 2. Determine Reward-to-Risk Ratio (W/L)
    # Average volatility from technicals or default 25% annualized
    volatility = technicals.get("annualized_volatility_pct", 25.0) / 100.0
    if volatility <= 0: volatility = 0.25
    
    # Stop-Loss distance is 1.5x to 2x Annualized Volatility scaled to monthly
    # Monthly Volatility = Annualized Volatility / sqrt(12)
    monthly_vol = volatility / 3.46
    stop_loss_pct = max(0.05, min(0.25, monthly_vol * 1.5)) # Between 5% and 25%
    
    # Stop loss price
    stop_loss_price = current_price * (1 - stop_loss_pct)
    
    # Take profit price
    # If undervalued, target base_case or bull_case. Otherwise, use risk-reward ratio.
    take_profit_price = current_price * (1 + (stop_loss_pct * 2.5)) # Default 2.5 Reward/Risk
    
    if valuation.get("base_case") and valuation["base_case"] > current_price:
        take_profit_price = max(take_profit_price, valuation["base_case"])
        
    take_profit_pct = (take_profit_price - current_price) / current_price
    
    reward_risk_ratio = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else 1.0

    # 3. Kelly Criterion formula: f* = W - (1-W)/R
    kelly_pct = win_probability - (loss_probability / reward_risk_ratio)
    
    # 4. Apply Half-Kelly for safety
    half_kelly_pct = kelly_pct / 2.0
    
    # Further scale down for extreme volatility (Vol scaling target = 15%)
    vol_scalar = 0.15 / volatility if volatility > 0 else 1.0
    adjusted_kelly_pct = half_kelly_pct * vol_scalar

    # Boundaries: Never recommend shorting here, and cap at 15% max portfolio weight
    recommended_weight = max(0.0, min(0.15, adjusted_kelly_pct))
    
    # Dollar amount and shares
    position_dollars = portfolio_value * recommended_weight
    shares_to_buy = position_dollars / current_price if current_price > 0 else 0
    
    # Calculate Risk Amount ($)
    risk_dollars = position_dollars * stop_loss_pct

    return {
        "recommended_weight_pct": round(recommended_weight * 100, 1),
        "position_size_usd": round(position_dollars, 2),
        "shares_to_buy": round(shares_to_buy, 2),
        "risk_metrics": {
            "win_probability_est_pct": round(win_probability * 100, 1),
            "reward_risk_ratio": round(reward_risk_ratio, 2),
            "stop_loss_price": round(stop_loss_price, 2),
            "stop_loss_pct": round(stop_loss_pct * 100, 1),
            "take_profit_price": round(take_profit_price, 2),
            "take_profit_pct": round(take_profit_pct * 100, 1),
            "dollars_at_risk": round(risk_dollars, 2),
            "portfolio_value_used": portfolio_value
        }
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
