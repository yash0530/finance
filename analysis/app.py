#!/usr/bin/env python3
"""
S&P 500 Analysis Playground - Flask Backend API

REST API for the S&P 500 company analysis web application.
Serves data from companies.py to the React frontend.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

# Import from companies.py
from companies import (
    load_cache, 
    save_cache, 
    get_sp500_companies, 
    fetch_all_data,
    CACHE_DIR
)


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types."""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if pd.isna(obj):
            return None
        return super().default(obj)


def convert_numpy_types(obj):
    """Recursively convert numpy types to Python native types."""
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj) if not isinstance(obj, (list, dict, str)) else False:
        return None
    return obj


app = Flask(__name__)
app.json.encoder = NumpyEncoder
CORS(app)  # Enable CORS for React frontend

# Cache file path
CACHE_FILE = CACHE_DIR / "sp500_data.json"


def get_cached_data() -> List[Dict]:
    """Load data from cache or return empty list.
    
    Note: This bypasses the cache expiry check from load_cache() 
    so the API can serve stale data rather than returning nothing.
    """
    cache_file = CACHE_DIR / "sp500_data.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
            if cache.get('data'):
                return cache['data']
        except Exception:
            pass
    return []


def get_cache_timestamp() -> Optional[str]:
    """Get the timestamp of when the cache was last updated."""
    cache_file = CACHE_DIR / "sp500_data.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
            return cache.get('timestamp')
        except Exception:
            pass
    return None


def ensure_data() -> List[Dict]:
    """Ensure we have data, fetching if necessary."""
    data = get_cached_data()
    if not data:
        # Fetch fresh data
        companies = get_sp500_companies()
        data = fetch_all_data(companies)
        if data:
            save_cache(data)
    return data


# ============================================================================
# Per-Ticker Caching for History and Financials
# ============================================================================
# These caches are separate from the main S&P 500 cache and store data per ticker.
# This prevents excessive API calls when users view company detail pages.

HISTORY_CACHE_HOURS = 4    # Stock prices update during market hours
FINANCIALS_CACHE_HOURS = 24  # Quarterly data doesn't change often


def get_ticker_cache(ticker: str, cache_type: str, max_age_hours: int) -> Optional[Dict]:
    """Load cached data for a specific ticker if not expired.
    
    Args:
        ticker: Stock ticker symbol
        cache_type: 'history' or 'financials'
        max_age_hours: Maximum age in hours before cache is considered stale
    """
    cache_file = CACHE_DIR / f"{ticker.upper()}_{cache_type}.json"
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cache = json.load(f)
        
        from datetime import datetime, timedelta
        cached_time = datetime.fromisoformat(cache.get('timestamp', '2000-01-01'))
        if datetime.now() - cached_time > timedelta(hours=max_age_hours):
            return None  # Cache expired
        
        return cache.get('data')
    except Exception:
        return None


def save_ticker_cache(ticker: str, cache_type: str, data: Dict) -> None:
    """Save data to ticker-specific cache file."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"{ticker.upper()}_{cache_type}.json"
    
    try:
        from datetime import datetime
        cache = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        with open(cache_file, 'w') as f:
            json.dump(cache, f)
    except Exception:
        pass  # Silently fail on cache write errors


@app.route('/api/companies', methods=['GET'])
def get_companies():
    """Get all S&P 500 companies."""
    data = get_cached_data()
    if not data:
        return jsonify({'error': 'No data available. Use /api/refresh to fetch data.'}), 404
    
    # Optional query parameters for sorting
    sort_by = request.args.get('sort_by', 'forward_pe')
    order = request.args.get('order', 'asc')
    
    df = pd.DataFrame(data)
    
    if sort_by in df.columns:
        df[f'{sort_by}_sort'] = pd.to_numeric(df[sort_by], errors='coerce')
        ascending = order.lower() == 'asc'
        df = df.sort_values(f'{sort_by}_sort', ascending=ascending, na_position='last')
        df = df.drop(columns=[f'{sort_by}_sort'])
    
    return jsonify(convert_numpy_types({
        'count': len(df),
        'data': df.to_dict(orient='records')
    }))


@app.route('/api/sectors', methods=['GET'])
def get_sectors():
    """Get list of unique sectors with counts and statistics."""
    data = get_cached_data()
    if not data:
        return jsonify({'error': 'No data available'}), 404
    
    df = pd.DataFrame(data)
    sectors = []
    
    for sector in sorted(df['sector'].unique()):
        sector_df = df[df['sector'] == sector]
        pe_values = pd.to_numeric(sector_df['forward_pe'], errors='coerce')
        market_cap = pd.to_numeric(sector_df['market_cap'], errors='coerce')
        
        sectors.append({
            'name': sector,
            'count': int(len(sector_df)),
            'avg_forward_pe': float(round(pe_values.mean(), 2)) if pe_values.notna().any() else None,
            'median_forward_pe': float(round(pe_values.median(), 2)) if pe_values.notna().any() else None,
            'total_market_cap': float(market_cap.sum()) if market_cap.notna().any() else 0,
            'total_market_cap_fmt': f"${float(market_cap.sum())/1e12:.2f}T" if market_cap.notna().any() else 'N/A'
        })
    
    return jsonify(convert_numpy_types({
        'count': len(sectors),
        'data': sectors
    }))


@app.route('/api/companies/<path:sector>', methods=['GET'])
def get_companies_by_sector(sector: str):
    """Get companies filtered by sector."""
    data = get_cached_data()
    if not data:
        return jsonify({'error': 'No data available'}), 404
    
    df = pd.DataFrame(data)
    sector_df = df[df['sector'].str.lower() == sector.lower()]
    
    if sector_df.empty:
        return jsonify({'error': f'Sector "{sector}" not found'}), 404
    
    # Sort by forward P/E
    sector_df['forward_pe_sort'] = pd.to_numeric(sector_df['forward_pe'], errors='coerce')
    sector_df = sector_df.sort_values('forward_pe_sort', na_position='last')
    sector_df = sector_df.drop(columns=['forward_pe_sort'])
    
    return jsonify(convert_numpy_types({
        'sector': sector,
        'count': len(sector_df),
        'data': sector_df.to_dict(orient='records')
    }))


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get summary statistics for the entire S&P 500."""
    data = get_cached_data()
    if not data:
        return jsonify({'error': 'No data available'}), 404
    
    df = pd.DataFrame(data)
    
    # Calculate summary stats
    pe_values = pd.to_numeric(df['forward_pe'], errors='coerce')
    market_cap = pd.to_numeric(df['market_cap'], errors='coerce')
    trailing_pe = pd.to_numeric(df['trailing_pe'], errors='coerce')
    profit_margin = pd.to_numeric(df['profit_margin'], errors='coerce')
    revenue_growth = pd.to_numeric(df['revenue_growth'], errors='coerce')
    
    # Top companies by market cap
    top_by_market_cap = df.nlargest(10, 'market_cap')[
        ['ticker', 'company_name', 'sector', 'market_cap_fmt', 'forward_pe', 'current_price_fmt']
    ].to_dict(orient='records')
    
    # Lowest P/E companies (with valid P/E)
    valid_pe_df = df[pd.to_numeric(df['forward_pe'], errors='coerce') > 0].copy()
    valid_pe_df['forward_pe_num'] = pd.to_numeric(valid_pe_df['forward_pe'], errors='coerce')
    lowest_pe = valid_pe_df.nsmallest(10, 'forward_pe_num')[
        ['ticker', 'company_name', 'sector', 'forward_pe', 'trailing_pe', 'current_price_fmt']
    ].to_dict(orient='records')
    
    # Highest revenue growth
    valid_growth_df = df[pd.to_numeric(df['revenue_growth'], errors='coerce').notna()].copy()
    valid_growth_df['growth_num'] = pd.to_numeric(valid_growth_df['revenue_growth'], errors='coerce')
    highest_growth = valid_growth_df.nlargest(10, 'growth_num')[
        ['ticker', 'company_name', 'sector', 'revenue_growth_fmt', 'current_price_fmt']
    ].to_dict(orient='records')
    
    return jsonify(convert_numpy_types({
        'total_companies': int(len(df)),
        'total_market_cap': float(market_cap.sum()),
        'total_market_cap_fmt': f"${float(market_cap.sum())/1e12:.2f}T",
        'avg_forward_pe': float(round(pe_values.mean(), 2)) if pe_values.notna().any() else None,
        'median_forward_pe': float(round(pe_values.median(), 2)) if pe_values.notna().any() else None,
        'avg_trailing_pe': float(round(trailing_pe.mean(), 2)) if trailing_pe.notna().any() else None,
        'avg_profit_margin': float(round(profit_margin.mean() * 100, 2)) if profit_margin.notna().any() else None,
        'avg_revenue_growth': float(round(revenue_growth.mean() * 100, 2)) if revenue_growth.notna().any() else None,
        'sector_count': int(df['sector'].nunique()),
        'top_by_market_cap': top_by_market_cap,
        'lowest_forward_pe': lowest_pe,
        'highest_growth': highest_growth
    }))


@app.route('/api/company/<ticker>', methods=['GET'])
def get_company_by_ticker(ticker: str):
    """Get a single company by ticker symbol."""
    data = get_cached_data()
    if not data:
        return jsonify({'error': 'No data available'}), 404
    
    df = pd.DataFrame(data)
    company_df = df[df['ticker'].str.upper() == ticker.upper()]
    
    if company_df.empty:
        return jsonify({'error': f'Company with ticker "{ticker}" not found'}), 404
    
    company = company_df.iloc[0].to_dict()
    return jsonify(convert_numpy_types(company))


@app.route('/api/search', methods=['GET'])
def search_companies():
    """Search companies by ticker or name."""
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    data = get_cached_data()
    if not data:
        return jsonify({'error': 'No data available'}), 404
    
    df = pd.DataFrame(data)
    
    # Search in ticker and company_name
    mask = (
        df['ticker'].str.lower().str.contains(query, na=False) |
        df['company_name'].str.lower().str.contains(query, na=False)
    )
    
    results = df[mask].head(20).to_dict(orient='records')
    
    return jsonify(convert_numpy_types({
        'query': query,
        'count': len(results),
        'data': results
    }))


@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Trigger a fresh data fetch."""
    try:
        companies = get_sp500_companies()
        data = fetch_all_data(companies)
        if data:
            save_cache(data)
            return jsonify({
                'success': True,
                'message': f'Successfully fetched data for {len(data)} companies'
            })
        return jsonify({'success': False, 'error': 'No data fetched'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/company/<ticker>/history', methods=['GET'])
def get_stock_history(ticker: str):
    """Get historical stock price data for a company.
    
    Always fetches 5 years of data (maximum). Frontend filters by period.
    This is more efficient than fetching different periods separately.
    
    Query params:
        refresh: 'true' to force fresh data fetch (bypass cache)
    
    Returns daily close prices for charting.
    Uses per-ticker caching (4-hour cache).
    """
    import yfinance as yf
    
    force_refresh = request.args.get('refresh', '').lower() == 'true'
    cache_key = 'history_5y'  # Single cache for all history
    
    # Check cache first (unless force refresh)
    if not force_refresh:
        cached = get_ticker_cache(ticker, cache_key, HISTORY_CACHE_HOURS)
        if cached:
            return jsonify(cached)
    
    # Fetch 5 years of data from yfinance
    try:
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period='5y')
        
        if hist.empty:
            return jsonify({'error': f'No history data for {ticker}'}), 404
        
        # Get 52-week high/low from info
        info = stock.info
        week_52_high = info.get('fiftyTwoWeekHigh')
        week_52_low = info.get('fiftyTwoWeekLow')
        
        # Format data for frontend charting
        history_data = []
        for date, row in hist.iterrows():
            history_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'close': round(row['Close'], 2),
                'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0
            })
        
        result = convert_numpy_types({
            'ticker': ticker.upper(),
            'period': '5y',
            'count': len(history_data),
            'week_52_high': round(week_52_high, 2) if week_52_high else None,
            'week_52_low': round(week_52_low, 2) if week_52_low else None,
            'data': history_data
        })
        
        # Save to cache
        save_ticker_cache(ticker, cache_key, result)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/company/<ticker>/financials', methods=['GET'])
def get_company_financials(ticker: str):
    """Get quarterly and annual financial data for a company.
    
    Returns revenue, net income, and EPS breakdown by quarter and year.
    Uses per-ticker caching (24-hour cache).
    
    Query params:
        refresh: 'true' to force fresh data fetch (bypass cache)
    """
    force_refresh = request.args.get('refresh', '').lower() == 'true'
    
    # Check cache first (unless force refresh)
    if not force_refresh:
        cached = get_ticker_cache(ticker, 'financials', FINANCIALS_CACHE_HOURS)
        if cached:
            return jsonify(cached)
    
    # Cache miss - fetch from yfinance
    import yfinance as yf
    
    try:
        stock = yf.Ticker(ticker.upper())
        
        result = {
            'ticker': ticker.upper(),
            'quarterly_revenue': [],
            'quarterly_earnings': [],
            'annual_revenue': [],
            'annual_earnings': []
        }
        
        # Get quarterly financials
        try:
            q_financials = stock.quarterly_financials
            if q_financials is not None and not q_financials.empty:
                for col in q_financials.columns[:8]:  # Last 8 quarters
                    period_label = col.strftime('%b %Y')
                    revenue = q_financials.loc['Total Revenue', col] if 'Total Revenue' in q_financials.index else None
                    net_income = q_financials.loc['Net Income', col] if 'Net Income' in q_financials.index else None
                    
                    if revenue is not None and pd.notna(revenue):
                        result['quarterly_revenue'].append({
                            'period': period_label,
                            'date': col.strftime('%Y-%m-%d'),
                            'value': float(revenue),
                            'formatted': f"${revenue/1e9:.2f}B" if abs(revenue) >= 1e9 else f"${revenue/1e6:.2f}M"
                        })
                    
                    if net_income is not None and pd.notna(net_income):
                        result['quarterly_earnings'].append({
                            'period': period_label,
                            'date': col.strftime('%Y-%m-%d'),
                            'value': float(net_income),
                            'formatted': f"${net_income/1e9:.2f}B" if abs(net_income) >= 1e9 else f"${net_income/1e6:.2f}M"
                        })
        except Exception:
            pass  # Some companies may not have quarterly data
        
        # Get annual financials
        try:
            a_financials = stock.financials
            if a_financials is not None and not a_financials.empty:
                for col in a_financials.columns[:5]:  # Last 5 years
                    period_label = f"FY {col.year}"
                    revenue = a_financials.loc['Total Revenue', col] if 'Total Revenue' in a_financials.index else None
                    net_income = a_financials.loc['Net Income', col] if 'Net Income' in a_financials.index else None
                    
                    if revenue is not None and pd.notna(revenue):
                        result['annual_revenue'].append({
                            'period': period_label,
                            'date': col.strftime('%Y-%m-%d'),
                            'value': float(revenue),
                            'formatted': f"${revenue/1e9:.2f}B" if abs(revenue) >= 1e9 else f"${revenue/1e6:.2f}M"
                        })
                    
                    if net_income is not None and pd.notna(net_income):
                        result['annual_earnings'].append({
                            'period': period_label,
                            'date': col.strftime('%Y-%m-%d'),
                            'value': float(net_income),
                            'formatted': f"${net_income/1e9:.2f}B" if abs(net_income) >= 1e9 else f"${net_income/1e6:.2f}M"
                        })
        except Exception:
            pass  # Some companies may not have annual data
        
        # Reverse to chronological order
        result['quarterly_revenue'].reverse()
        result['quarterly_earnings'].reverse()
        result['annual_revenue'].reverse()
        result['annual_earnings'].reverse()
        
        result = convert_numpy_types(result)
        
        # Save to cache
        save_ticker_cache(ticker, 'financials', result)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Head and Shoulders Pattern Detection
# ============================================================================

PATTERN_CACHE_HOURS = 4  # Pattern detection cache (same as history)


def detect_head_and_shoulders(prices: list, dates: list, window: int = 20) -> dict:
    """
    Detect Head and Shoulders pattern in price data.
    
    The pattern consists of:
    - Left Shoulder: A peak followed by a decline
    - Head: A higher peak followed by a decline
    - Right Shoulder: A lower peak similar to the left shoulder
    - Neckline: Support level connecting the troughs
    
    Args:
        prices: List of closing prices (chronological order)
        dates: List of dates corresponding to prices
        window: Rolling window size for local maxima/minima detection
    
    Returns:
        dict with pattern details or None if no pattern found
    """
    if len(prices) < window * 5:  # Need enough data for pattern
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    # Find local maxima (peaks) using rolling window
    local_maxima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
    
    if len(local_maxima) < 3:
        return None
    
    # Find local minima (troughs) using rolling window
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
    
    if len(local_minima) < 2:
        return None
    
    # Look for Head and Shoulders pattern in recent data
    # Search in the last portion of the price history
    search_start = max(0, n - 120)  # Last ~6 months of daily data
    
    best_pattern = None
    best_confidence = 0
    
    # Try to find patterns using the last few peaks
    recent_maxima = [m for m in local_maxima if m[0] >= search_start]
    
    for i in range(len(recent_maxima) - 2):
        left_idx, left_price = recent_maxima[i]
        head_idx, head_price = recent_maxima[i + 1]
        right_idx, right_price = recent_maxima[i + 2]
        
        # Pattern requirements:
        # 1. Head must be higher than both shoulders
        if head_price <= left_price or head_price <= right_price:
            continue
        
        # 2. Shoulders should be roughly equal (within 15%)
        shoulder_diff = abs(left_price - right_price) / max(left_price, right_price)
        if shoulder_diff > 0.15:
            continue
        
        # 3. Find the troughs between peaks (for neckline)
        left_trough_candidates = [m for m in local_minima if left_idx < m[0] < head_idx]
        right_trough_candidates = [m for m in local_minima if head_idx < m[0] < right_idx]
        
        if not left_trough_candidates or not right_trough_candidates:
            continue
        
        left_trough = min(left_trough_candidates, key=lambda x: x[1])
        right_trough = min(right_trough_candidates, key=lambda x: x[1])
        
        # Calculate neckline (average of troughs)
        neckline = (left_trough[1] + right_trough[1]) / 2
        
        # 4. Head should be significantly higher than neckline (at least 5%)
        head_height = (head_price - neckline) / neckline
        if head_height < 0.05:
            continue
        
        # Calculate pattern confidence score (0-100)
        # Based on: symmetry, proportions, and recency
        shoulder_symmetry = 1 - shoulder_diff  # Higher is better
        height_score = min(head_height * 5, 1)  # Normalize to 0-1
        recency = (right_idx - search_start) / (n - search_start)  # Recent patterns score higher
        
        confidence = int((shoulder_symmetry * 0.3 + height_score * 0.4 + recency * 0.3) * 100)
        
        if confidence > best_confidence:
            best_confidence = confidence
            
            # Calculate target price (neckline - pattern height)
            pattern_height = head_price - neckline
            target_price = neckline - pattern_height
            
            # Calculate current price position relative to pattern
            current_price = prices[-1]
            price_vs_neckline = (current_price - neckline) / neckline
            
            best_pattern = {
                'detected': True,
                'confidence': confidence,
                'left_shoulder': {
                    'date': dates[left_idx],
                    'price': round(left_price, 2)
                },
                'head': {
                    'date': dates[head_idx],
                    'price': round(head_price, 2)
                },
                'right_shoulder': {
                    'date': dates[right_idx],
                    'price': round(right_price, 2)
                },
                'neckline': round(neckline, 2),
                'target_price': round(target_price, 2),
                'current_price': round(current_price, 2),
                'price_vs_neckline_pct': round(price_vs_neckline * 100, 2),
                'pattern_height_pct': round(head_height * 100, 2)
            }
    
    return best_pattern


def scan_stock_for_pattern(ticker: str) -> dict:
    """Scan a single stock for Head and Shoulders pattern using cached history."""
    import yfinance as yf
    
    # Try to get from history cache first
    cached = get_ticker_cache(ticker, 'history_5y', HISTORY_CACHE_HOURS)
    
    if cached and cached.get('data'):
        history_data = cached['data']
    else:
        # Fetch fresh data
        try:
            stock = yf.Ticker(ticker.upper())
            hist = stock.history(period='1y')  # Use 1 year for pattern detection
            
            if hist.empty:
                return None
            
            history_data = [
                {'date': date.strftime('%Y-%m-%d'), 'close': round(row['Close'], 2)}
                for date, row in hist.iterrows()
            ]
        except Exception:
            return None
    
    if not history_data or len(history_data) < 60:
        return None
    
    prices = [d['close'] for d in history_data]
    dates = [d['date'] for d in history_data]
    
    pattern = detect_head_and_shoulders(prices, dates)
    
    if pattern:
        return {
            'ticker': ticker,
            **pattern
        }
    
    return None


@app.route('/api/patterns/head-shoulders', methods=['GET'])
def get_head_shoulders_patterns():
    """Scan all S&P 500 stocks for Head and Shoulders patterns.
    
    Returns list of stocks with detected patterns, sorted by confidence.
    Uses cached history data when available.
    """
    # Check pattern scan cache
    cached = get_ticker_cache('_all_', 'head_shoulders_scan', PATTERN_CACHE_HOURS)
    if cached:
        return jsonify(cached)
    
    data = get_cached_data()
    if not data:
        return jsonify({'error': 'No data available'}), 404
    
    df = pd.DataFrame(data)
    tickers = df['ticker'].tolist()
    
    # Scan all stocks for patterns (using cached history)
    patterns = []
    for ticker in tickers:
        result = scan_stock_for_pattern(ticker)
        if result:
            # Add company info
            company_info = df[df['ticker'] == ticker].iloc[0]
            result['company_name'] = company_info.get('company_name', '')
            result['sector'] = company_info.get('sector', '')
            result['current_price_fmt'] = company_info.get('current_price_fmt', '')
            patterns.append(result)
    
    # Sort by confidence (highest first)
    patterns.sort(key=lambda x: x.get('confidence', 0), reverse=True)
    
    result = convert_numpy_types({
        'title': '📊 Head & Shoulders Patterns',
        'description': 'Stocks showing potential Head and Shoulders reversal patterns',
        'count': len(patterns),
        'patterns': patterns
    })
    
    # Cache the results
    save_ticker_cache('_all_', 'head_shoulders_scan', result)
    
    return jsonify(result)


@app.route('/api/patterns/head-shoulders/<ticker>', methods=['GET'])
def get_head_shoulders_for_ticker(ticker: str):
    """Get Head and Shoulders pattern analysis for a specific stock.
    
    Returns detailed pattern data including chart annotation points.
    """
    data = get_cached_data()
    if not data:
        return jsonify({'error': 'No data available'}), 404
    
    df = pd.DataFrame(data)
    company_df = df[df['ticker'].str.upper() == ticker.upper()]
    
    if company_df.empty:
        return jsonify({'error': f'Company with ticker "{ticker}" not found'}), 404
    
    company_info = company_df.iloc[0]
    
    result = scan_stock_for_pattern(ticker.upper())
    
    if result:
        result['company_name'] = company_info.get('company_name', '')
        result['sector'] = company_info.get('sector', '')
        result['current_price_fmt'] = company_info.get('current_price_fmt', '')
        return jsonify(convert_numpy_types(result))
    else:
        return jsonify({
            'ticker': ticker.upper(),
            'company_name': company_info.get('company_name', ''),
            'sector': company_info.get('sector', ''),
            'detected': False,
            'message': 'No Head and Shoulders pattern detected in recent price history'
        })


# ============================================================================
# Additional Pattern Detection Functions
# ============================================================================

def detect_inverse_head_shoulders(prices: list, dates: list, window: int = 20) -> dict:
    """
    Detect Inverse Head and Shoulders pattern (bullish reversal).
    
    The pattern consists of:
    - Left Shoulder: A trough followed by a rise
    - Head: A lower trough followed by a rise
    - Right Shoulder: A higher trough similar to the left shoulder
    - Neckline: Resistance level connecting the peaks
    """
    if len(prices) < window * 5:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    # Find local minima (troughs) using rolling window
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
    
    if len(local_minima) < 3:
        return None
    
    # Find local maxima (peaks) for neckline
    local_maxima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
    
    if len(local_maxima) < 2:
        return None
    
    search_start = max(0, n - 120)
    best_pattern = None
    best_confidence = 0
    
    recent_minima = [m for m in local_minima if m[0] >= search_start]
    
    for i in range(len(recent_minima) - 2):
        left_idx, left_price = recent_minima[i]
        head_idx, head_price = recent_minima[i + 1]
        right_idx, right_price = recent_minima[i + 2]
        
        # Pattern requirements:
        # 1. Head must be lower than both shoulders
        if head_price >= left_price or head_price >= right_price:
            continue
        
        # 2. Shoulders should be roughly equal (within 15%)
        shoulder_diff = abs(left_price - right_price) / max(left_price, right_price)
        if shoulder_diff > 0.15:
            continue
        
        # 3. Find peaks between troughs (for neckline)
        left_peak_candidates = [m for m in local_maxima if left_idx < m[0] < head_idx]
        right_peak_candidates = [m for m in local_maxima if head_idx < m[0] < right_idx]
        
        if not left_peak_candidates or not right_peak_candidates:
            continue
        
        left_peak = max(left_peak_candidates, key=lambda x: x[1])
        right_peak = max(right_peak_candidates, key=lambda x: x[1])
        
        neckline = (left_peak[1] + right_peak[1]) / 2
        
        # 4. Head should be significantly lower than neckline (at least 5%)
        head_depth = (neckline - head_price) / neckline
        if head_depth < 0.05:
            continue
        
        shoulder_symmetry = 1 - shoulder_diff
        depth_score = min(head_depth * 5, 1)
        recency = (right_idx - search_start) / (n - search_start)
        
        confidence = int((shoulder_symmetry * 0.3 + depth_score * 0.4 + recency * 0.3) * 100)
        
        if confidence > best_confidence:
            best_confidence = confidence
            
            pattern_height = neckline - head_price
            target_price = neckline + pattern_height
            
            current_price = prices[-1]
            price_vs_neckline = (current_price - neckline) / neckline
            
            best_pattern = {
                'detected': True,
                'pattern_type': 'inverse_head_shoulders',
                'pattern_name': 'Inverse Head & Shoulders',
                'signal': 'bullish',
                'confidence': confidence,
                'left_shoulder': {'date': dates[left_idx], 'price': round(left_price, 2)},
                'head': {'date': dates[head_idx], 'price': round(head_price, 2)},
                'right_shoulder': {'date': dates[right_idx], 'price': round(right_price, 2)},
                'neckline': round(neckline, 2),
                'target_price': round(target_price, 2),
                'current_price': round(current_price, 2),
                'price_vs_neckline_pct': round(price_vs_neckline * 100, 2),
                'pattern_height_pct': round(head_depth * 100, 2)
            }
    
    return best_pattern


def detect_double_top(prices: list, dates: list, window: int = 15) -> dict:
    """
    Detect Double Top pattern (bearish reversal).
    
    Two similar peaks with a trough between them.
    """
    if len(prices) < window * 4:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    local_maxima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
    
    if len(local_maxima) < 2:
        return None
    
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
    
    search_start = max(0, n - 100)
    best_pattern = None
    best_confidence = 0
    
    recent_maxima = [m for m in local_maxima if m[0] >= search_start]
    
    for i in range(len(recent_maxima) - 1):
        first_idx, first_price = recent_maxima[i]
        second_idx, second_price = recent_maxima[i + 1]
        
        # Peaks should be roughly equal (within 3%)
        peak_diff = abs(first_price - second_price) / max(first_price, second_price)
        if peak_diff > 0.03:
            continue
        
        # Need sufficient distance between peaks
        if second_idx - first_idx < window * 2:
            continue
        
        # Find trough between peaks
        trough_candidates = [m for m in local_minima if first_idx < m[0] < second_idx]
        if not trough_candidates:
            continue
        
        trough = min(trough_candidates, key=lambda x: x[1])
        neckline = trough[1]
        
        # Pattern height should be significant (at least 5%)
        pattern_height = (first_price - neckline) / neckline
        if pattern_height < 0.05:
            continue
        
        peak_symmetry = 1 - peak_diff
        height_score = min(pattern_height * 5, 1)
        recency = (second_idx - search_start) / (n - search_start)
        
        confidence = int((peak_symmetry * 0.4 + height_score * 0.3 + recency * 0.3) * 100)
        
        if confidence > best_confidence:
            best_confidence = confidence
            
            target_price = neckline - (first_price - neckline)
            current_price = prices[-1]
            
            best_pattern = {
                'detected': True,
                'pattern_type': 'double_top',
                'pattern_name': 'Double Top',
                'signal': 'bearish',
                'confidence': confidence,
                'first_peak': {'date': dates[first_idx], 'price': round(first_price, 2)},
                'second_peak': {'date': dates[second_idx], 'price': round(second_price, 2)},
                'trough': {'date': dates[trough[0]], 'price': round(trough[1], 2)},
                'neckline': round(neckline, 2),
                'target_price': round(target_price, 2),
                'current_price': round(current_price, 2),
                'pattern_height_pct': round(pattern_height * 100, 2)
            }
    
    return best_pattern


def detect_double_bottom(prices: list, dates: list, window: int = 15) -> dict:
    """
    Detect Double Bottom pattern (bullish reversal).
    
    Two similar troughs with a peak between them.
    """
    if len(prices) < window * 4:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
    
    if len(local_minima) < 2:
        return None
    
    local_maxima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
    
    search_start = max(0, n - 100)
    best_pattern = None
    best_confidence = 0
    
    recent_minima = [m for m in local_minima if m[0] >= search_start]
    
    for i in range(len(recent_minima) - 1):
        first_idx, first_price = recent_minima[i]
        second_idx, second_price = recent_minima[i + 1]
        
        # Troughs should be roughly equal (within 3%)
        trough_diff = abs(first_price - second_price) / max(first_price, second_price)
        if trough_diff > 0.03:
            continue
        
        if second_idx - first_idx < window * 2:
            continue
        
        # Find peak between troughs
        peak_candidates = [m for m in local_maxima if first_idx < m[0] < second_idx]
        if not peak_candidates:
            continue
        
        peak = max(peak_candidates, key=lambda x: x[1])
        neckline = peak[1]
        
        pattern_height = (neckline - first_price) / first_price
        if pattern_height < 0.05:
            continue
        
        trough_symmetry = 1 - trough_diff
        height_score = min(pattern_height * 5, 1)
        recency = (second_idx - search_start) / (n - search_start)
        
        confidence = int((trough_symmetry * 0.4 + height_score * 0.3 + recency * 0.3) * 100)
        
        if confidence > best_confidence:
            best_confidence = confidence
            
            target_price = neckline + (neckline - first_price)
            current_price = prices[-1]
            
            best_pattern = {
                'detected': True,
                'pattern_type': 'double_bottom',
                'pattern_name': 'Double Bottom',
                'signal': 'bullish',
                'confidence': confidence,
                'first_trough': {'date': dates[first_idx], 'price': round(first_price, 2)},
                'second_trough': {'date': dates[second_idx], 'price': round(second_price, 2)},
                'peak': {'date': dates[peak[0]], 'price': round(peak[1], 2)},
                'neckline': round(neckline, 2),
                'target_price': round(target_price, 2),
                'current_price': round(current_price, 2),
                'pattern_height_pct': round(pattern_height * 100, 2)
            }
    
    return best_pattern


def detect_triple_top(prices: list, dates: list, window: int = 12) -> dict:
    """
    Detect Triple Top pattern (bearish reversal).
    
    Three similar peaks with two troughs between them.
    """
    if len(prices) < window * 6:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    local_maxima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
    
    if len(local_maxima) < 3:
        return None
    
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
    
    search_start = max(0, n - 150)
    best_pattern = None
    best_confidence = 0
    
    recent_maxima = [m for m in local_maxima if m[0] >= search_start]
    
    for i in range(len(recent_maxima) - 2):
        first_idx, first_price = recent_maxima[i]
        second_idx, second_price = recent_maxima[i + 1]
        third_idx, third_price = recent_maxima[i + 2]
        
        # All three peaks should be roughly equal (within 5%)
        avg_peak = (first_price + second_price + third_price) / 3
        max_diff = max(abs(first_price - avg_peak), abs(second_price - avg_peak), abs(third_price - avg_peak)) / avg_peak
        if max_diff > 0.05:
            continue
        
        # Find troughs between peaks
        trough1_candidates = [m for m in local_minima if first_idx < m[0] < second_idx]
        trough2_candidates = [m for m in local_minima if second_idx < m[0] < third_idx]
        
        if not trough1_candidates or not trough2_candidates:
            continue
        
        trough1 = min(trough1_candidates, key=lambda x: x[1])
        trough2 = min(trough2_candidates, key=lambda x: x[1])
        
        neckline = min(trough1[1], trough2[1])
        pattern_height = (avg_peak - neckline) / neckline
        
        if pattern_height < 0.05:
            continue
        
        peak_uniformity = 1 - max_diff
        height_score = min(pattern_height * 5, 1)
        recency = (third_idx - search_start) / (n - search_start)
        
        confidence = int((peak_uniformity * 0.4 + height_score * 0.3 + recency * 0.3) * 100)
        
        if confidence > best_confidence:
            best_confidence = confidence
            
            target_price = neckline - (avg_peak - neckline)
            current_price = prices[-1]
            
            best_pattern = {
                'detected': True,
                'pattern_type': 'triple_top',
                'pattern_name': 'Triple Top',
                'signal': 'bearish',
                'confidence': confidence,
                'first_peak': {'date': dates[first_idx], 'price': round(first_price, 2)},
                'second_peak': {'date': dates[second_idx], 'price': round(second_price, 2)},
                'third_peak': {'date': dates[third_idx], 'price': round(third_price, 2)},
                'neckline': round(neckline, 2),
                'target_price': round(target_price, 2),
                'current_price': round(current_price, 2),
                'pattern_height_pct': round(pattern_height * 100, 2)
            }
    
    return best_pattern


def detect_triple_bottom(prices: list, dates: list, window: int = 12) -> dict:
    """
    Detect Triple Bottom pattern (bullish reversal).
    
    Three similar troughs with two peaks between them.
    """
    if len(prices) < window * 6:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
    
    if len(local_minima) < 3:
        return None
    
    local_maxima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
    
    search_start = max(0, n - 150)
    best_pattern = None
    best_confidence = 0
    
    recent_minima = [m for m in local_minima if m[0] >= search_start]
    
    for i in range(len(recent_minima) - 2):
        first_idx, first_price = recent_minima[i]
        second_idx, second_price = recent_minima[i + 1]
        third_idx, third_price = recent_minima[i + 2]
        
        avg_trough = (first_price + second_price + third_price) / 3
        max_diff = max(abs(first_price - avg_trough), abs(second_price - avg_trough), abs(third_price - avg_trough)) / avg_trough
        if max_diff > 0.05:
            continue
        
        peak1_candidates = [m for m in local_maxima if first_idx < m[0] < second_idx]
        peak2_candidates = [m for m in local_maxima if second_idx < m[0] < third_idx]
        
        if not peak1_candidates or not peak2_candidates:
            continue
        
        peak1 = max(peak1_candidates, key=lambda x: x[1])
        peak2 = max(peak2_candidates, key=lambda x: x[1])
        
        neckline = max(peak1[1], peak2[1])
        pattern_height = (neckline - avg_trough) / avg_trough
        
        if pattern_height < 0.05:
            continue
        
        trough_uniformity = 1 - max_diff
        height_score = min(pattern_height * 5, 1)
        recency = (third_idx - search_start) / (n - search_start)
        
        confidence = int((trough_uniformity * 0.4 + height_score * 0.3 + recency * 0.3) * 100)
        
        if confidence > best_confidence:
            best_confidence = confidence
            
            target_price = neckline + (neckline - avg_trough)
            current_price = prices[-1]
            
            best_pattern = {
                'detected': True,
                'pattern_type': 'triple_bottom',
                'pattern_name': 'Triple Bottom',
                'signal': 'bullish',
                'confidence': confidence,
                'first_trough': {'date': dates[first_idx], 'price': round(first_price, 2)},
                'second_trough': {'date': dates[second_idx], 'price': round(second_price, 2)},
                'third_trough': {'date': dates[third_idx], 'price': round(third_price, 2)},
                'neckline': round(neckline, 2),
                'target_price': round(target_price, 2),
                'current_price': round(current_price, 2),
                'pattern_height_pct': round(pattern_height * 100, 2)
            }
    
    return best_pattern


def detect_ascending_triangle(prices: list, dates: list, window: int = 10) -> dict:
    """
    Detect Ascending Triangle pattern (bullish continuation).
    
    Flat resistance line with rising support trendline.
    """
    if len(prices) < 60:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    local_maxima = []
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
    
    if len(local_maxima) < 2 or len(local_minima) < 2:
        return None
    
    search_start = max(0, n - 80)
    recent_maxima = [m for m in local_maxima if m[0] >= search_start]
    recent_minima = [m for m in local_minima if m[0] >= search_start]
    
    if len(recent_maxima) < 2 or len(recent_minima) < 2:
        return None
    
    # Check for flat resistance (peaks within 2% of each other)
    peak_prices = [m[1] for m in recent_maxima]
    resistance = np.mean(peak_prices)
    resistance_flatness = max(abs(p - resistance) / resistance for p in peak_prices)
    
    if resistance_flatness > 0.02:
        return None
    
    # Check for rising support (higher lows)
    trough_prices = [m[1] for m in recent_minima]
    if len(trough_prices) < 2:
        return None
    
    # Calculate slope of support line
    trough_indices = [m[0] for m in recent_minima]
    slope = (trough_prices[-1] - trough_prices[0]) / (trough_indices[-1] - trough_indices[0] + 1)
    
    if slope <= 0:  # Support must be rising
        return None
    
    # Pattern height
    current_support = trough_prices[-1]
    pattern_height = (resistance - current_support) / current_support
    
    if pattern_height < 0.03:
        return None
    
    flatness_score = 1 - resistance_flatness * 20
    height_score = min(pattern_height * 10, 1)
    convergence = min(slope * 1000, 1)
    
    confidence = int((flatness_score * 0.4 + height_score * 0.3 + convergence * 0.3) * 100)
    confidence = max(0, min(100, confidence))
    
    if confidence < 30:
        return None
    
    target_price = resistance + (resistance - current_support)
    current_price = prices[-1]
    
    return {
        'detected': True,
        'pattern_type': 'ascending_triangle',
        'pattern_name': 'Ascending Triangle',
        'signal': 'bullish',
        'confidence': confidence,
        'resistance': round(resistance, 2),
        'support_start': round(trough_prices[0], 2),
        'support_current': round(current_support, 2),
        'target_price': round(target_price, 2),
        'current_price': round(current_price, 2),
        'pattern_height_pct': round(pattern_height * 100, 2)
    }


def detect_descending_triangle(prices: list, dates: list, window: int = 10) -> dict:
    """
    Detect Descending Triangle pattern (bearish continuation).
    
    Flat support line with falling resistance trendline.
    """
    if len(prices) < 60:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    local_maxima = []
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
    
    if len(local_maxima) < 2 or len(local_minima) < 2:
        return None
    
    search_start = max(0, n - 80)
    recent_maxima = [m for m in local_maxima if m[0] >= search_start]
    recent_minima = [m for m in local_minima if m[0] >= search_start]
    
    if len(recent_maxima) < 2 or len(recent_minima) < 2:
        return None
    
    # Check for flat support (troughs within 2% of each other)
    trough_prices = [m[1] for m in recent_minima]
    support = np.mean(trough_prices)
    support_flatness = max(abs(p - support) / support for p in trough_prices)
    
    if support_flatness > 0.02:
        return None
    
    # Check for falling resistance (lower highs)
    peak_prices = [m[1] for m in recent_maxima]
    peak_indices = [m[0] for m in recent_maxima]
    slope = (peak_prices[-1] - peak_prices[0]) / (peak_indices[-1] - peak_indices[0] + 1)
    
    if slope >= 0:  # Resistance must be falling
        return None
    
    current_resistance = peak_prices[-1]
    pattern_height = (current_resistance - support) / support
    
    if pattern_height < 0.03:
        return None
    
    flatness_score = 1 - support_flatness * 20
    height_score = min(pattern_height * 10, 1)
    convergence = min(abs(slope) * 1000, 1)
    
    confidence = int((flatness_score * 0.4 + height_score * 0.3 + convergence * 0.3) * 100)
    confidence = max(0, min(100, confidence))
    
    if confidence < 30:
        return None
    
    target_price = support - (current_resistance - support)
    current_price = prices[-1]
    
    return {
        'detected': True,
        'pattern_type': 'descending_triangle',
        'pattern_name': 'Descending Triangle',
        'signal': 'bearish',
        'confidence': confidence,
        'support': round(support, 2),
        'resistance_start': round(peak_prices[0], 2),
        'resistance_current': round(current_resistance, 2),
        'target_price': round(target_price, 2),
        'current_price': round(current_price, 2),
        'pattern_height_pct': round(pattern_height * 100, 2)
    }


def detect_cup_and_handle(prices: list, dates: list, window: int = 10) -> dict:
    """
    Detect Cup and Handle pattern (bullish continuation).
    
    U-shaped bottom (cup) followed by small consolidation (handle).
    """
    if len(prices) < 80:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    # Look for cup in the last 60-100 days
    cup_start = max(0, n - 100)
    cup_data = prices[cup_start:]
    cup_n = len(cup_data)
    
    if cup_n < 40:
        return None
    
    # Find the lowest point (bottom of cup)
    cup_bottom_idx = np.argmin(cup_data)
    if cup_bottom_idx < 10 or cup_bottom_idx > cup_n - 15:
        return None
    
    # Check for U-shape: prices should rise on both sides of bottom
    left_half = cup_data[:cup_bottom_idx]
    right_half = cup_data[cup_bottom_idx:]
    
    if len(left_half) < 5 or len(right_half) < 10:
        return None
    
    # Left lip and right lip should be near the same level
    left_lip = max(left_half[:5])
    right_lip = max(right_half[-15:-5]) if len(right_half) >= 15 else max(right_half[-5:])
    
    lip_diff = abs(left_lip - right_lip) / max(left_lip, right_lip)
    if lip_diff > 0.10:  # Lips within 10%
        return None
    
    cup_bottom = cup_data[cup_bottom_idx]
    cup_depth = (left_lip - cup_bottom) / left_lip
    
    if cup_depth < 0.10 or cup_depth > 0.50:  # Cup should be 10-50% deep
        return None
    
    # Check for handle (small pullback in last 10-20 days)
    handle_data = cup_data[-15:]
    handle_low = min(handle_data)
    handle_high = max(handle_data[:5])
    
    handle_depth = (right_lip - handle_low) / right_lip
    if handle_depth > cup_depth * 0.5:  # Handle shouldn't be too deep
        return None
    
    lip_uniformity = 1 - lip_diff
    depth_score = min(cup_depth * 3, 1)
    shape_score = 0.7 if handle_depth < cup_depth * 0.3 else 0.4
    
    confidence = int((lip_uniformity * 0.3 + depth_score * 0.4 + shape_score * 0.3) * 100)
    
    if confidence < 35:
        return None
    
    resistance = max(left_lip, right_lip)
    target_price = resistance + (resistance - cup_bottom)
    current_price = prices[-1]
    
    return {
        'detected': True,
        'pattern_type': 'cup_and_handle',
        'pattern_name': 'Cup and Handle',
        'signal': 'bullish',
        'confidence': confidence,
        'cup_bottom': round(cup_bottom, 2),
        'cup_bottom_date': dates[cup_start + cup_bottom_idx],
        'left_lip': round(left_lip, 2),
        'right_lip': round(right_lip, 2),
        'resistance': round(resistance, 2),
        'target_price': round(target_price, 2),
        'current_price': round(current_price, 2),
        'cup_depth_pct': round(cup_depth * 100, 2)
    }


def detect_bullish_flag(prices: list, dates: list, window: int = 5) -> dict:
    """
    Detect Bullish Flag pattern (bullish continuation).
    
    Strong upward move (pole) followed by consolidation channel (flag).
    """
    if len(prices) < 40:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    # Look for a strong upward move in the past 30-50 days
    pole_end = n - 15
    pole_start = max(0, pole_end - 30)
    
    pole_data = prices[pole_start:pole_end]
    if len(pole_data) < 15:
        return None
    
    # Find the start and end of the pole
    pole_low_idx = np.argmin(pole_data[:10])
    pole_high_idx = np.argmax(pole_data[-10:]) + len(pole_data) - 10
    
    pole_low = pole_data[pole_low_idx]
    pole_high = pole_data[pole_high_idx]
    
    # Pole should show significant gain (at least 10%)
    pole_gain = (pole_high - pole_low) / pole_low
    if pole_gain < 0.10:
        return None
    
    # Check flag (consolidation in last 10-20 days)
    flag_data = prices[pole_end:]
    if len(flag_data) < 8:
        return None
    
    flag_high = max(flag_data)
    flag_low = min(flag_data)
    flag_range = (flag_high - flag_low) / flag_high
    
    # Flag should be tight consolidation (less than 8%)
    if flag_range > 0.08:
        return None
    
    # Flag should be near the pole high (not too much pullback)
    flag_pullback = (pole_high - min(flag_data)) / pole_high
    if flag_pullback > 0.10:
        return None
    
    pole_strength = min(pole_gain * 5, 1)
    consolidation = 1 - (flag_range * 10)
    position_score = 1 - (flag_pullback * 10)
    
    confidence = int((pole_strength * 0.4 + consolidation * 0.3 + position_score * 0.3) * 100)
    confidence = max(0, min(100, confidence))
    
    if confidence < 35:
        return None
    
    target_price = pole_high + (pole_high - pole_low)  # Measured move
    current_price = prices[-1]
    
    return {
        'detected': True,
        'pattern_type': 'bullish_flag',
        'pattern_name': 'Bullish Flag',
        'signal': 'bullish',
        'confidence': confidence,
        'pole_low': round(pole_low, 2),
        'pole_high': round(pole_high, 2),
        'flag_high': round(flag_high, 2),
        'flag_low': round(flag_low, 2),
        'target_price': round(target_price, 2),
        'current_price': round(current_price, 2),
        'pole_gain_pct': round(pole_gain * 100, 2)
    }


def detect_falling_wedge(prices: list, dates: list, window: int = 8) -> dict:
    """
    Detect Falling Wedge pattern (bullish reversal).
    
    Both support and resistance lines slope downward, but converge.
    """
    if len(prices) < 50:
        return None
    
    prices = np.array(prices)
    n = len(prices)
    
    local_maxima = []
    local_minima = []
    for i in range(window, n - window):
        if prices[i] == max(prices[i - window:i + window + 1]):
            local_maxima.append((i, prices[i]))
        if prices[i] == min(prices[i - window:i + window + 1]):
            local_minima.append((i, prices[i]))
    
    if len(local_maxima) < 2 or len(local_minima) < 2:
        return None
    
    search_start = max(0, n - 70)
    recent_maxima = [m for m in local_maxima if m[0] >= search_start]
    recent_minima = [m for m in local_minima if m[0] >= search_start]
    
    if len(recent_maxima) < 2 or len(recent_minima) < 2:
        return None
    
    # Calculate slopes of resistance and support
    peak_indices = np.array([m[0] for m in recent_maxima])
    peak_prices = np.array([m[1] for m in recent_maxima])
    trough_indices = np.array([m[0] for m in recent_minima])
    trough_prices = np.array([m[1] for m in recent_minima])
    
    resistance_slope = (peak_prices[-1] - peak_prices[0]) / (peak_indices[-1] - peak_indices[0] + 1)
    support_slope = (trough_prices[-1] - trough_prices[0]) / (trough_indices[-1] - trough_indices[0] + 1)
    
    # Both slopes must be negative (falling)
    if resistance_slope >= 0 or support_slope >= 0:
        return None
    
    # Lines must be converging (support slope less steep than resistance)
    if abs(support_slope) >= abs(resistance_slope):
        return None
    
    # Current spread vs initial spread
    initial_spread = peak_prices[0] - trough_prices[0]
    current_spread = peak_prices[-1] - trough_prices[-1]
    
    if current_spread >= initial_spread:  # Must be narrowing
        return None
    
    convergence = (initial_spread - current_spread) / initial_spread
    if convergence < 0.20:  # At least 20% narrower
        return None
    
    convergence_score = min(convergence * 2, 1)
    slope_score = min(abs(resistance_slope) * 100, 1)
    
    confidence = int((convergence_score * 0.5 + slope_score * 0.5) * 100)
    confidence = max(0, min(100, confidence))
    
    if confidence < 30:
        return None
    
    breakout_level = peak_prices[-1]
    target_price = breakout_level + initial_spread
    current_price = prices[-1]
    
    return {
        'detected': True,
        'pattern_type': 'falling_wedge',
        'pattern_name': 'Falling Wedge',
        'signal': 'bullish',
        'confidence': confidence,
        'resistance_start': round(peak_prices[0], 2),
        'resistance_current': round(peak_prices[-1], 2),
        'support_start': round(trough_prices[0], 2),
        'support_current': round(trough_prices[-1], 2),
        'breakout_level': round(breakout_level, 2),
        'target_price': round(target_price, 2),
        'current_price': round(current_price, 2),
        'convergence_pct': round(convergence * 100, 2)
    }


# ============================================================================
# Pattern Scanning Functions
# ============================================================================

# All available pattern detectors
PATTERN_DETECTORS = {
    'head_shoulders': ('Head & Shoulders', 'bearish', detect_head_and_shoulders),
    'inverse_head_shoulders': ('Inverse Head & Shoulders', 'bullish', detect_inverse_head_shoulders),
    'double_top': ('Double Top', 'bearish', detect_double_top),
    'double_bottom': ('Double Bottom', 'bullish', detect_double_bottom),
    'triple_top': ('Triple Top', 'bearish', detect_triple_top),
    'triple_bottom': ('Triple Bottom', 'bullish', detect_triple_bottom),
    'ascending_triangle': ('Ascending Triangle', 'bullish', detect_ascending_triangle),
    'descending_triangle': ('Descending Triangle', 'bearish', detect_descending_triangle),
    'cup_and_handle': ('Cup and Handle', 'bullish', detect_cup_and_handle),
    'bullish_flag': ('Bullish Flag', 'bullish', detect_bullish_flag),
    'falling_wedge': ('Falling Wedge', 'bullish', detect_falling_wedge),
}


def scan_stock_for_all_patterns(ticker: str) -> list:
    """Scan a single stock for all pattern types."""
    import yfinance as yf
    
    # Try to get from history cache first
    cached = get_ticker_cache(ticker, 'history_5y', HISTORY_CACHE_HOURS)
    
    if cached and cached.get('data'):
        history_data = cached['data']
    else:
        try:
            stock = yf.Ticker(ticker.upper())
            hist = stock.history(period='1y')
            
            if hist.empty:
                return []
            
            history_data = [
                {'date': date.strftime('%Y-%m-%d'), 'close': round(row['Close'], 2)}
                for date, row in hist.iterrows()
            ]
        except Exception:
            return []
    
    if not history_data or len(history_data) < 60:
        return []
    
    prices = [d['close'] for d in history_data]
    dates = [d['date'] for d in history_data]
    
    detected_patterns = []
    
    for pattern_key, (name, signal, detector) in PATTERN_DETECTORS.items():
        try:
            pattern = detector(prices, dates)
            if pattern:
                pattern['ticker'] = ticker
                pattern['pattern_type'] = pattern_key
                pattern['pattern_name'] = name
                pattern['signal'] = signal
                detected_patterns.append(pattern)
        except Exception:
            continue
    
    return detected_patterns


@app.route('/api/patterns/all', methods=['GET'])
def get_all_patterns():
    """Scan all S&P 500 stocks for all pattern types.
    
    Returns consolidated list of all detected patterns, grouped by type.
    """
    # Check cache
    cached = get_ticker_cache('_all_', 'all_patterns_scan', PATTERN_CACHE_HOURS)
    if cached:
        return jsonify(cached)
    
    data = get_cached_data()
    if not data:
        return jsonify({'error': 'No data available'}), 404
    
    df = pd.DataFrame(data)
    tickers = df['ticker'].tolist()
    
    # Organize patterns by type
    patterns_by_type = {key: [] for key in PATTERN_DETECTORS.keys()}
    
    for ticker in tickers:
        patterns = scan_stock_for_all_patterns(ticker)
        for pattern in patterns:
            # Add company info
            company_info = df[df['ticker'] == ticker].iloc[0]
            pattern['company_name'] = company_info.get('company_name', '')
            pattern['sector'] = company_info.get('sector', '')
            pattern['current_price_fmt'] = company_info.get('current_price_fmt', '')
            
            pattern_type = pattern.get('pattern_type', '')
            if pattern_type in patterns_by_type:
                patterns_by_type[pattern_type].append(pattern)
    
    # Sort each pattern type by confidence
    for pattern_type in patterns_by_type:
        patterns_by_type[pattern_type].sort(key=lambda x: x.get('confidence', 0), reverse=True)
    
    # Build response with pattern metadata
    result = {
        'title': '📊 Technical Patterns Dashboard',
        'description': 'All detected chart patterns across S&P 500 stocks',
        'pattern_types': {}
    }
    
    for pattern_key, (name, signal, _) in PATTERN_DETECTORS.items():
        patterns = patterns_by_type.get(pattern_key, [])
        result['pattern_types'][pattern_key] = {
            'name': name,
            'signal': signal,
            'count': len(patterns),
            'patterns': patterns
        }
    
    # Summary stats
    total_bullish = sum(1 for k, v in result['pattern_types'].items() if v['signal'] == 'bullish' for _ in v['patterns'])
    total_bearish = sum(1 for k, v in result['pattern_types'].items() if v['signal'] == 'bearish' for _ in v['patterns'])
    
    result['summary'] = {
        'total_patterns': total_bullish + total_bearish,
        'bullish_patterns': total_bullish,
        'bearish_patterns': total_bearish
    }
    
    result = convert_numpy_types(result)
    
    # Cache the results
    save_ticker_cache('_all_', 'all_patterns_scan', result)
    
    return jsonify(result)


@app.route('/api/patterns/<pattern_type>', methods=['GET'])
def get_patterns_by_type(pattern_type: str):
    """Get all stocks with a specific pattern type.
    
    Valid pattern types: head_shoulders, inverse_head_shoulders, double_top,
    double_bottom, triple_top, triple_bottom, ascending_triangle,
    descending_triangle, cup_and_handle, bullish_flag, falling_wedge
    """
    # Normalize pattern type
    pattern_key = pattern_type.replace('-', '_')
    
    if pattern_key not in PATTERN_DETECTORS:
        return jsonify({
            'error': f'Unknown pattern type: {pattern_type}',
            'valid_types': list(PATTERN_DETECTORS.keys())
        }), 404
    
    name, signal, detector = PATTERN_DETECTORS[pattern_key]
    
    # Check cache
    cache_key = f'{pattern_key}_scan'
    cached = get_ticker_cache('_all_', cache_key, PATTERN_CACHE_HOURS)
    if cached:
        return jsonify(cached)
    
    data = get_cached_data()
    if not data:
        return jsonify({'error': 'No data available'}), 404
    
    df = pd.DataFrame(data)
    tickers = df['ticker'].tolist()
    
    patterns = []
    for ticker in tickers:
        # Get history data
        cached_hist = get_ticker_cache(ticker, 'history_5y', HISTORY_CACHE_HOURS)
        
        if cached_hist and cached_hist.get('data'):
            history_data = cached_hist['data']
        else:
            try:
                import yfinance as yf
                stock = yf.Ticker(ticker.upper())
                hist = stock.history(period='1y')
                
                if hist.empty:
                    continue
                
                history_data = [
                    {'date': date.strftime('%Y-%m-%d'), 'close': round(row['Close'], 2)}
                    for date, row in hist.iterrows()
                ]
            except Exception:
                continue
        
        if not history_data or len(history_data) < 60:
            continue
        
        prices = [d['close'] for d in history_data]
        dates = [d['date'] for d in history_data]
        
        try:
            pattern = detector(prices, dates)
            if pattern:
                company_info = df[df['ticker'] == ticker].iloc[0]
                pattern['ticker'] = ticker
                pattern['company_name'] = company_info.get('company_name', '')
                pattern['sector'] = company_info.get('sector', '')
                pattern['current_price_fmt'] = company_info.get('current_price_fmt', '')
                patterns.append(pattern)
        except Exception:
            continue
    
    # Sort by confidence
    patterns.sort(key=lambda x: x.get('confidence', 0), reverse=True)
    
    result = convert_numpy_types({
        'pattern_type': pattern_key,
        'pattern_name': name,
        'signal': signal,
        'count': len(patterns),
        'patterns': patterns
    })
    
    # Cache results
    save_ticker_cache('_all_', cache_key, result)
    
    return jsonify(result)


@app.route('/api/patterns/<pattern_type>/<ticker>', methods=['GET'])
def get_pattern_for_ticker(pattern_type: str, ticker: str):
    """Get specific pattern analysis for a single stock."""
    pattern_key = pattern_type.replace('-', '_')
    
    if pattern_key not in PATTERN_DETECTORS:
        return jsonify({
            'error': f'Unknown pattern type: {pattern_type}',
            'valid_types': list(PATTERN_DETECTORS.keys())
        }), 404
    
    data = get_cached_data()
    if not data:
        return jsonify({'error': 'No data available'}), 404
    
    df = pd.DataFrame(data)
    company_df = df[df['ticker'].str.upper() == ticker.upper()]
    
    if company_df.empty:
        return jsonify({'error': f'Company with ticker "{ticker}" not found'}), 404
    
    company_info = company_df.iloc[0]
    name, signal, detector = PATTERN_DETECTORS[pattern_key]
    
    # Get history data
    cached = get_ticker_cache(ticker, 'history_5y', HISTORY_CACHE_HOURS)
    
    if cached and cached.get('data'):
        history_data = cached['data']
    else:
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker.upper())
            hist = stock.history(period='1y')
            
            if hist.empty:
                return jsonify({
                    'ticker': ticker.upper(),
                    'detected': False,
                    'message': 'No history data available'
                })
            
            history_data = [
                {'date': date.strftime('%Y-%m-%d'), 'close': round(row['Close'], 2)}
                for date, row in hist.iterrows()
            ]
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    if not history_data or len(history_data) < 60:
        return jsonify({
            'ticker': ticker.upper(),
            'detected': False,
            'message': 'Insufficient history data for pattern detection'
        })
    
    prices = [d['close'] for d in history_data]
    dates = [d['date'] for d in history_data]
    
    try:
        pattern = detector(prices, dates)
        
        if pattern:
            pattern['ticker'] = ticker.upper()
            pattern['company_name'] = company_info.get('company_name', '')
            pattern['sector'] = company_info.get('sector', '')
            pattern['current_price_fmt'] = company_info.get('current_price_fmt', '')
            return jsonify(convert_numpy_types(pattern))
        else:
            return jsonify({
                'ticker': ticker.upper(),
                'company_name': company_info.get('company_name', ''),
                'sector': company_info.get('sector', ''),
                'pattern_type': pattern_key,
                'pattern_name': name,
                'detected': False,
                'message': f'No {name} pattern detected in recent price history'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500





@app.route('/api/spotlight', methods=['GET'])
def get_spotlight_companies():
    """Get spotlight companies based on fundamental analysis heuristics.
    
    Returns 10 categories of potential buy candidates:
    - Growth Stocks: High revenue growth + positive momentum
    - Hot Stocks: Strong 52-week performance
    - Value Plays: Low P/E with earnings growth expected (sorted by fwd P/E asc)
    - Momentum Leaders: High PE ratio (earnings acceleration)
    - Quality Gems: High margins + solid growth
    - Dividend Champions: High dividend yield (>3%)
    - Low Volatility: Low beta stocks (<0.8)
    - Mega Caps: Largest companies by market cap (>$200B)
    - Turnaround Plays: Down stocks with positive forward P/E
    - High Beta Movers: High volatility stocks (beta >1.5)
    """
    data = get_cached_data()
    if not data:
        return jsonify({'error': 'No data available'}), 404
    
    df = pd.DataFrame(data)
    
    # Convert numeric columns
    numeric_cols = ['forward_pe', 'trailing_pe', 'pe_ratio', 'revenue_growth', 
                    'year_change', 'profit_margin', 'market_cap', 'dividend_yield', 'beta']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    spotlight = {}
    
    # 1. Growth Stocks: revenue_growth > 15% AND year_change > 0
    growth_df = df[
        (df['revenue_growth'] > 0.15) & 
        (df['year_change'] > 0)
    ].copy()
    growth_df = growth_df.sort_values('revenue_growth', ascending=False).head(5)
    spotlight['growth_stocks'] = {
        'title': '🚀 Growth Stocks',
        'description': 'High revenue growth (>15%) with positive 52-week momentum',
        'companies': growth_df[['ticker', 'company_name', 'sector', 'revenue_growth', 
                                'year_change', 'forward_pe', 'current_price_fmt']].to_dict(orient='records')
    }
    
    # 2. Hot Stocks: Top by year_change (>20%)
    hot_df = df[df['year_change'] > 0.20].copy()
    hot_df = hot_df.sort_values('year_change', ascending=False).head(5)
    spotlight['hot_stocks'] = {
        'title': '🔥 Hot Stocks',
        'description': 'Strongest 52-week performance (>20% gains)',
        'companies': hot_df[['ticker', 'company_name', 'sector', 'year_change', 
                             'forward_pe', 'current_price_fmt']].to_dict(orient='records')
    }
    
    # 3. Value Plays: forward_pe < 15 AND pe_ratio > 1 (sorted by forward_pe ASC)
    value_df = df[
        (df['forward_pe'] > 0) &
        (df['forward_pe'] < 15) & 
        (df['pe_ratio'] > 1)
    ].copy()
    value_df = value_df.sort_values('forward_pe', ascending=True).head(5)
    spotlight['value_plays'] = {
        'title': '💰 Value Plays',
        'description': 'Low forward P/E (<15) with expected earnings growth',
        'companies': value_df[['ticker', 'company_name', 'sector', 'forward_pe', 
                               'trailing_pe', 'pe_ratio', 'current_price_fmt']].to_dict(orient='records')
    }
    
    # 4. Momentum Leaders: pe_ratio > 1.2 (strong earnings acceleration)
    momentum_df = df[df['pe_ratio'] > 1.2].copy()
    momentum_df = momentum_df.sort_values('pe_ratio', ascending=False).head(5)
    spotlight['momentum_leaders'] = {
        'title': '📈 Momentum Leaders',
        'description': 'P/E ratio >1.2x indicating earnings acceleration',
        'companies': momentum_df[['ticker', 'company_name', 'sector', 'pe_ratio', 
                                  'forward_pe', 'trailing_pe', 'current_price_fmt']].to_dict(orient='records')
    }
    
    # 5. Quality Gems: profit_margin > 15% AND revenue_growth > 5%
    quality_df = df[
        (df['profit_margin'] > 0.15) & 
        (df['revenue_growth'] > 0.05)
    ].copy()
    quality_df = quality_df.sort_values('profit_margin', ascending=False).head(5)
    spotlight['quality_gems'] = {
        'title': '🏆 Quality Gems',
        'description': 'High profit margins (>15%) with solid revenue growth (>5%)',
        'companies': quality_df[['ticker', 'company_name', 'sector', 'profit_margin', 
                                 'revenue_growth', 'forward_pe', 'current_price_fmt']].to_dict(orient='records')
    }
    
    # 6. Dividend Champions: dividend_yield > 3%
    dividend_df = df[df['dividend_yield'] > 0.03].copy()
    dividend_df = dividend_df.sort_values('dividend_yield', ascending=False).head(5)
    spotlight['dividend_champions'] = {
        'title': '💵 Dividend Champions',
        'description': 'High dividend yield (>3%) for income investors',
        'companies': dividend_df[['ticker', 'company_name', 'sector', 'dividend_yield', 
                                  'forward_pe', 'current_price_fmt']].to_dict(orient='records')
    }
    
    # 7. Low Volatility: beta < 0.8
    low_vol_df = df[(df['beta'] > 0) & (df['beta'] < 0.8)].copy()
    low_vol_df = low_vol_df.sort_values('beta', ascending=True).head(5)
    spotlight['low_volatility'] = {
        'title': '📉 Low Volatility',
        'description': 'Stable stocks with beta <0.8 for conservative investors',
        'companies': low_vol_df[['ticker', 'company_name', 'sector', 'beta', 
                                 'forward_pe', 'current_price_fmt']].to_dict(orient='records')
    }
    
    # 8. Mega Caps: market_cap > $200B
    mega_df = df[df['market_cap'] > 200e9].copy()
    mega_df = mega_df.sort_values('market_cap', ascending=False).head(5)
    spotlight['mega_caps'] = {
        'title': '🏛️ Mega Caps',
        'description': 'Largest companies with market cap >$200B',
        'companies': mega_df[['ticker', 'company_name', 'sector', 'market_cap', 
                              'market_cap_fmt', 'forward_pe', 'current_price_fmt']].to_dict(orient='records')
    }
    
    # 9. Turnaround Plays: year_change < -10% AND forward_pe > 0
    turnaround_df = df[
        (df['year_change'] < -0.10) & 
        (df['forward_pe'] > 0)
    ].copy()
    turnaround_df = turnaround_df.sort_values('year_change', ascending=True).head(5)
    spotlight['turnaround_plays'] = {
        'title': '🔄 Turnaround Plays',
        'description': 'Down >10% YTD but still profitable (contrarian picks)',
        'companies': turnaround_df[['ticker', 'company_name', 'sector', 'year_change', 
                                    'forward_pe', 'current_price_fmt']].to_dict(orient='records')
    }
    
    # 10. High Beta Movers: beta > 1.5
    high_beta_df = df[df['beta'] > 1.5].copy()
    high_beta_df = high_beta_df.sort_values('beta', ascending=False).head(5)
    spotlight['high_beta_movers'] = {
        'title': '⚡ High Beta Movers',
        'description': 'High volatility stocks (beta >1.5) for aggressive traders',
        'companies': high_beta_df[['ticker', 'company_name', 'sector', 'beta', 
                                   'forward_pe', 'current_price_fmt']].to_dict(orient='records')
    }
    
    return jsonify(convert_numpy_types(spotlight))


@app.route('/api/spotlight/<category>', methods=['GET'])
def get_spotlight_category(category: str):
    """Get all companies matching a spotlight category's criteria.
    
    Returns full list of qualifying companies (not just top 5).
    Value Plays are sorted by forward P/E ascending (low to high).
    """
    data = get_cached_data()
    if not data:
        return jsonify({'error': 'No data available'}), 404
    
    df = pd.DataFrame(data)
    
    # Convert numeric columns
    numeric_cols = ['forward_pe', 'trailing_pe', 'pe_ratio', 'revenue_growth', 
                    'year_change', 'profit_margin', 'market_cap', 'dividend_yield', 'beta']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Define category configurations
    categories = {
        'growth_stocks': {
            'title': '🚀 Growth Stocks',
            'description': 'High revenue growth (>15%) with positive 52-week momentum',
            'filter': lambda d: d[(d['revenue_growth'] > 0.15) & (d['year_change'] > 0)],
            'sort_by': 'revenue_growth',
            'ascending': False,
            'columns': ['ticker', 'company_name', 'sector', 'revenue_growth', 'year_change', 'forward_pe', 'current_price_fmt']
        },
        'hot_stocks': {
            'title': '🔥 Hot Stocks',
            'description': 'Strongest 52-week performance (>20% gains)',
            'filter': lambda d: d[d['year_change'] > 0.20],
            'sort_by': 'year_change',
            'ascending': False,
            'columns': ['ticker', 'company_name', 'sector', 'year_change', 'forward_pe', 'current_price_fmt']
        },
        'value_plays': {
            'title': '💰 Value Plays',
            'description': 'Low forward P/E (<15) with expected earnings growth',
            'filter': lambda d: d[(d['forward_pe'] > 0) & (d['forward_pe'] < 15) & (d['pe_ratio'] > 1)],
            'sort_by': 'forward_pe',
            'ascending': True,  # Low to high for value plays
            'columns': ['ticker', 'company_name', 'sector', 'forward_pe', 'trailing_pe', 'pe_ratio', 'current_price_fmt']
        },
        'momentum_leaders': {
            'title': '📈 Momentum Leaders',
            'description': 'P/E ratio >1.2x indicating earnings acceleration',
            'filter': lambda d: d[d['pe_ratio'] > 1.2],
            'sort_by': 'pe_ratio',
            'ascending': False,
            'columns': ['ticker', 'company_name', 'sector', 'pe_ratio', 'forward_pe', 'trailing_pe', 'current_price_fmt']
        },
        'quality_gems': {
            'title': '🏆 Quality Gems',
            'description': 'High profit margins (>15%) with solid revenue growth (>5%)',
            'filter': lambda d: d[(d['profit_margin'] > 0.15) & (d['revenue_growth'] > 0.05)],
            'sort_by': 'profit_margin',
            'ascending': False,
            'columns': ['ticker', 'company_name', 'sector', 'profit_margin', 'revenue_growth', 'forward_pe', 'current_price_fmt']
        },
        'dividend_champions': {
            'title': '💵 Dividend Champions',
            'description': 'High dividend yield (>3%) for income investors',
            'filter': lambda d: d[d['dividend_yield'] > 0.03],
            'sort_by': 'dividend_yield',
            'ascending': False,
            'columns': ['ticker', 'company_name', 'sector', 'dividend_yield', 'forward_pe', 'current_price_fmt']
        },
        'low_volatility': {
            'title': '📉 Low Volatility',
            'description': 'Stable stocks with beta <0.8 for conservative investors',
            'filter': lambda d: d[(d['beta'] > 0) & (d['beta'] < 0.8)],
            'sort_by': 'beta',
            'ascending': True,
            'columns': ['ticker', 'company_name', 'sector', 'beta', 'forward_pe', 'current_price_fmt']
        },
        'mega_caps': {
            'title': '🏛️ Mega Caps',
            'description': 'Largest companies with market cap >$200B',
            'filter': lambda d: d[d['market_cap'] > 200e9],
            'sort_by': 'market_cap',
            'ascending': False,
            'columns': ['ticker', 'company_name', 'sector', 'market_cap', 'market_cap_fmt', 'forward_pe', 'current_price_fmt']
        },
        'turnaround_plays': {
            'title': '🔄 Turnaround Plays',
            'description': 'Down >10% YTD but still profitable (contrarian picks)',
            'filter': lambda d: d[(d['year_change'] < -0.10) & (d['forward_pe'] > 0)],
            'sort_by': 'year_change',
            'ascending': True,
            'columns': ['ticker', 'company_name', 'sector', 'year_change', 'forward_pe', 'current_price_fmt']
        },
        'high_beta_movers': {
            'title': '⚡ High Beta Movers',
            'description': 'High volatility stocks (beta >1.5) for aggressive traders',
            'filter': lambda d: d[d['beta'] > 1.5],
            'sort_by': 'beta',
            'ascending': False,
            'columns': ['ticker', 'company_name', 'sector', 'beta', 'forward_pe', 'current_price_fmt']
        }
    }
    
    if category not in categories:
        return jsonify({'error': f'Unknown category: {category}'}), 404
    
    config = categories[category]
    filtered_df = config['filter'](df).copy()
    filtered_df = filtered_df.sort_values(config['sort_by'], ascending=config['ascending'])
    
    return jsonify(convert_numpy_types({
        'category': category,
        'title': config['title'],
        'description': config['description'],
        'count': len(filtered_df),
        'companies': filtered_df[config['columns']].to_dict(orient='records')
    }))


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    data = get_cached_data()
    timestamp = get_cache_timestamp()
    return jsonify({
        'status': 'healthy',
        'data_available': len(data) > 0,
        'company_count': len(data),
        'last_updated': timestamp
    })


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("   S&P 500 Analysis Playground - API Server")
    print("   Running on http://localhost:5001")
    print("=" * 60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5001)
