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
