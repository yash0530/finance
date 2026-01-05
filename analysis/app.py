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
    """Load data from cache or return empty list."""
    cache = load_cache()
    if cache and cache.get('data'):
        return cache['data']
    return []


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


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    data = get_cached_data()
    return jsonify({
        'status': 'healthy',
        'data_available': len(data) > 0,
        'company_count': len(data)
    })


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("   S&P 500 Analysis Playground - API Server")
    print("   Running on http://localhost:5001")
    print("=" * 60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5001)
