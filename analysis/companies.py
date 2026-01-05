#!/usr/bin/env python3
"""
S&P 500 Company Analysis Script (Robust yfinance Edition)

Extracts all S&P 500 companies, groups them by sector, and displays
comprehensive financial metrics sorted by forward P/E ratio.

Features:
- Rate limiting to avoid Yahoo throttling
- Exponential backoff retry logic
- Local caching to reduce API calls
- Parallel fetching with configurable workers

Data Sources:
- S&P 500 list: Wikipedia (FREE)
- Financial data: yfinance (FREE, no API key needed)

Usage:
    python companies.py
    python companies.py --no-cache    # Force fresh data fetch
"""

import pandas as pd
import requests
import yfinance as yf
from typing import Dict, List, Optional
import sys
import time
import json
import os
import random
from io import StringIO
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


# Configuration
CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_EXPIRY_HOURS = 12  # Cache data for 12 hours
MAX_WORKERS = 5  # Reduced from 10 to be gentler on Yahoo
REQUEST_DELAY = 0.2  # Delay between requests in seconds
MAX_RETRIES = 3  # Number of retry attempts
BACKOFF_FACTOR = 2  # Exponential backoff multiplier


def get_sp500_companies() -> List[Dict]:
    """
    Fetches the list of S&P 500 companies from Wikipedia (FREE).
    """
    print("📊 Fetching S&P 500 company list from Wikipedia...")
    
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        tables = pd.read_html(StringIO(response.text))
        df = tables[0]
        
        companies = []
        for _, row in df.iterrows():
            companies.append({
                'symbol': str(row['Symbol']).replace('.', '-'),
                'name': row['Security'],
                'sector': row['GICS Sector'],
                'industry': row['GICS Sub-Industry']
            })
        
        print(f"✅ Found {len(companies)} S&P 500 companies\n")
        return companies
        
    except Exception as e:
        print(f"❌ Error fetching S&P 500 list: {e}")
        sys.exit(1)


def load_cache() -> Optional[Dict]:
    """Load cached data if it exists and is not expired."""
    cache_file = CACHE_DIR / "sp500_data.json"
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cache = json.load(f)
        
        # Check expiry
        cached_time = datetime.fromisoformat(cache.get('timestamp', '2000-01-01'))
        if datetime.now() - cached_time > timedelta(hours=CACHE_EXPIRY_HOURS):
            print("⚠️  Cache expired, fetching fresh data...\n")
            return None
        
        print(f"✅ Loaded {len(cache.get('data', []))} companies from cache")
        print(f"   Cache age: {(datetime.now() - cached_time).total_seconds() / 3600:.1f} hours\n")
        return cache
        
    except Exception as e:
        print(f"⚠️  Cache read error: {e}")
        return None


def save_cache(data: List[Dict]) -> None:
    """Save data to cache."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / "sp500_data.json"
    
    try:
        cache = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        with open(cache_file, 'w') as f:
            json.dump(cache, f)
        print(f"💾 Cached {len(data)} companies for future runs\n")
    except Exception as e:
        print(f"⚠️  Cache write error: {e}")


def get_ticker_data_with_retry(symbol: str, delay: float = REQUEST_DELAY) -> Dict:
    """
    Fetch financial data for a single ticker with retry logic.
    Implements exponential backoff for robustness.
    """
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            # Add jitter to avoid thundering herd
            jitter = random.uniform(0, delay)
            time.sleep(delay + jitter)
            
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Check if we got valid data
            if not info or info.get('regularMarketPrice') is None and info.get('currentPrice') is None:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(BACKOFF_FACTOR ** attempt)
                    continue
            
            def safe_get(key, default=None):
                return info.get(key, default)
            
            def format_currency(value):
                if value is None:
                    return 'N/A'
                try:
                    value = float(value)
                    if abs(value) >= 1e12:
                        return f"${value/1e12:.2f}T"
                    elif abs(value) >= 1e9:
                        return f"${value/1e9:.2f}B"
                    elif abs(value) >= 1e6:
                        return f"${value/1e6:.2f}M"
                    else:
                        return f"${value:,.0f}"
                except:
                    return 'N/A'
            
            def format_percent(value):
                if value is None:
                    return 'N/A'
                try:
                    return f"{float(value) * 100:.2f}%"
                except:
                    return 'N/A'
            
            price = safe_get('currentPrice') or safe_get('regularMarketPrice')
            market_cap = safe_get('marketCap')
            forward_pe = safe_get('forwardPE')
            trailing_pe = safe_get('trailingPE')
            
            # Calculate P/E ratio (trailing / forward)
            # > 1 means earnings expected to grow, < 1 means expected decline
            pe_ratio = None
            if forward_pe and trailing_pe and forward_pe > 0:
                pe_ratio = trailing_pe / forward_pe
            
            def format_ratio(value):
                if value is None:
                    return 'N/A'
                try:
                    return f"{float(value):.2f}x"
                except:
                    return 'N/A'
            
            return {
                'symbol': symbol,
                'success': True,
                'data': {
                    'current_price': price,
                    'current_price_fmt': f"${price:.2f}" if price else 'N/A',
                    'market_cap': market_cap,
                    'market_cap_fmt': format_currency(market_cap),
                    'forward_pe': forward_pe,
                    'trailing_pe': trailing_pe,
                    'pe_ratio': pe_ratio,
                    'pe_ratio_fmt': format_ratio(pe_ratio),
                    'peg_ratio': safe_get('pegRatio'),
                    'price_to_sales': safe_get('priceToSalesTrailing12Months'),
                    'price_to_book': safe_get('priceToBook'),
                    'ev_to_revenue': safe_get('enterpriseToRevenue'),
                    'ev_to_ebitda': safe_get('enterpriseToEbitda'),
                    'total_revenue': safe_get('totalRevenue'),
                    'total_revenue_fmt': format_currency(safe_get('totalRevenue')),
                    'net_income': safe_get('netIncomeToCommon'),
                    'net_income_fmt': format_currency(safe_get('netIncomeToCommon')),
                    'profit_margin': safe_get('profitMargins'),
                    'profit_margin_fmt': format_percent(safe_get('profitMargins')),
                    'operating_margin': safe_get('operatingMargins'),
                    'operating_margin_fmt': format_percent(safe_get('operatingMargins')),
                    'gross_margin': safe_get('grossMargins'),
                    'dividend_yield': safe_get('dividendYield'),
                    'dividend_yield_fmt': format_percent(safe_get('dividendYield')),
                    'beta': safe_get('beta'),
                    'eps': safe_get('trailingEps'),
                    'revenue_growth': safe_get('revenueGrowth'),
                    'revenue_growth_fmt': format_percent(safe_get('revenueGrowth')),
                }
            }
            
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES - 1:
                wait_time = BACKOFF_FACTOR ** attempt
                time.sleep(wait_time)
    
    return {'symbol': symbol, 'success': False, 'error': last_error or 'Unknown error'}


def fetch_all_data(companies: List[Dict], max_workers: int = MAX_WORKERS) -> List[Dict]:
    """
    Fetch data for all companies using rate-limited parallel requests.
    """
    symbols = [c['symbol'] for c in companies]
    company_info = {c['symbol']: c for c in companies}
    
    results = []
    failed = 0
    retried = 0
    
    print(f"📈 Fetching financial data for {len(symbols)} companies...")
    print(f"   Workers: {max_workers} | Delay: {REQUEST_DELAY}s | Retries: {MAX_RETRIES}")
    print(f"   Estimated time: {len(symbols) * REQUEST_DELAY / max_workers:.0f}-{len(symbols) * REQUEST_DELAY * 2 / max_workers:.0f} seconds\n")
    
    start_time = time.time()
    completed = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(get_ticker_data_with_retry, sym): sym 
            for sym in symbols
        }
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            completed += 1
            
            try:
                result = future.result()
                if result['success']:
                    # Merge yfinance data with Wikipedia data
                    info = company_info[symbol]
                    data = result['data']
                    data['ticker'] = symbol
                    data['company_name'] = info.get('name', symbol)
                    data['sector'] = info.get('sector', 'Unknown')
                    data['industry'] = info.get('industry', 'Unknown')
                    results.append(data)
                else:
                    failed += 1
            except Exception:
                failed += 1
            
            # Progress update
            if completed % 50 == 0 or completed == len(symbols):
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                eta = (len(symbols) - completed) / rate if rate > 0 else 0
                print(f"   Progress: {completed}/{len(symbols)} ({completed*100//len(symbols)}%) | "
                      f"Success: {len(results)} | Failed: {failed} | ETA: {eta:.0f}s")
    
    elapsed = time.time() - start_time
    print(f"\n✅ Completed in {elapsed:.1f}s | Success: {len(results)} | Failed: {failed}\n")
    
    return results


def display_by_sector(data: List[Dict]) -> None:
    """Groups companies by sector and displays sorted by forward P/E."""
    if not data:
        print("❌ No data to display")
        return
    
    df = pd.DataFrame(data)
    sectors = df.groupby('sector')
    sector_names = sorted(df['sector'].unique())
    
    print("=" * 120)
    print("📊 S&P 500 COMPANIES BY SECTOR - SORTED BY FORWARD P/E")
    print("=" * 120)
    
    for sector in sector_names:
        sector_df = sectors.get_group(sector).copy()
        
        # Sort by forward P/E
        sector_df['forward_pe_sort'] = pd.to_numeric(sector_df['forward_pe'], errors='coerce').fillna(float('inf'))
        sector_df = sector_df.sort_values('forward_pe_sort')
        
        company_count = len(sector_df)
        avg_pe = pd.to_numeric(sector_df['forward_pe'], errors='coerce').mean()
        total_market_cap = pd.to_numeric(sector_df['market_cap'], errors='coerce').sum()
        
        avg_pe_str = f"{avg_pe:.2f}" if pd.notna(avg_pe) else 'N/A'
        market_cap_str = f"${total_market_cap/1e12:.2f}T" if pd.notna(total_market_cap) else 'N/A'
        
        print(f"\n{'─' * 120}")
        print(f"🏢 {sector.upper()}")
        print(f"   Companies: {company_count} | Avg Forward P/E: {avg_pe_str} | Total Market Cap: {market_cap_str}")
        print(f"{'─' * 120}")
        
        print(f"{'Ticker':<8} {'Company':<30} {'Price':>10} {'Mkt Cap':>12} "
              f"{'Fwd P/E':>10} {'Trail P/E':>10} {'Revenue':>14} "
              f"{'Profit Mgn':>12}")
        print("-" * 120)
        
        for _, row in sector_df.iterrows():
            company = str(row['company_name'])[:28] if row['company_name'] else 'N/A'
            fwd_pe = f"{float(row['forward_pe']):.2f}" if pd.notna(row['forward_pe']) and row['forward_pe'] else 'N/A'
            trail_pe = f"{float(row['trailing_pe']):.2f}" if pd.notna(row['trailing_pe']) and row['trailing_pe'] else 'N/A'
            
            print(f"{row['ticker']:<8} {company:<30} "
                  f"{row['current_price_fmt']:>10} "
                  f"{row['market_cap_fmt'] or 'N/A':>12} "
                  f"{fwd_pe:>10} "
                  f"{trail_pe:>10} "
                  f"{row['total_revenue_fmt'] or 'N/A':>14} "
                  f"{row['profit_margin_fmt'] or 'N/A':>12}")
    
    # Summary
    print("\n" + "=" * 120)
    print("📈 SUMMARY STATISTICS")
    print("=" * 120)
    
    for sector in sector_names:
        sector_df = sectors.get_group(sector)
        pe_values = pd.to_numeric(sector_df['forward_pe'], errors='coerce')
        avg_fwd_pe = pe_values.mean()
        median_fwd_pe = pe_values.median()
        min_fwd_pe = pe_values.min()
        max_fwd_pe = pe_values.max()
        
        print(f"{sector:<35} | ", end="")
        print(f"Avg Fwd P/E: {avg_fwd_pe:>7.2f} | " if pd.notna(avg_fwd_pe) else "Avg Fwd P/E:     N/A | ", end="")
        print(f"Median: {median_fwd_pe:>7.2f} | " if pd.notna(median_fwd_pe) else "Median:     N/A | ", end="")
        print(f"Min: {min_fwd_pe:>7.2f} | " if pd.notna(min_fwd_pe) else "Min:     N/A | ", end="")
        print(f"Max: {max_fwd_pe:>7.2f}" if pd.notna(max_fwd_pe) else "Max:     N/A")
    
    print("=" * 120)


def export_to_csv(data: List[Dict], filename: str = "sp500_analysis.csv") -> None:
    """Exports the analysis data to a CSV file."""
    if not data:
        print("❌ No data to export")
        return
    
    df = pd.DataFrame(data)
    
    export_columns = [
        'ticker', 'company_name', 'sector', 'industry',
        'current_price', 'market_cap', 
        'forward_pe', 'trailing_pe', 'pe_ratio', 'peg_ratio',
        'price_to_sales', 'price_to_book', 'ev_to_revenue', 'ev_to_ebitda',
        'total_revenue', 'net_income',
        'profit_margin', 'operating_margin', 'gross_margin',
        'revenue_growth', 'dividend_yield', 'beta', 'eps'
    ]
    
    export_columns = [col for col in export_columns if col in df.columns]
    df[export_columns].to_csv(filename, index=False)
    print(f"\n📁 Data exported to: {filename}")


def main():
    """Main entry point for the script."""
    print("\n" + "=" * 60)
    print("   S&P 500 COMPANY ANALYSIS - ROBUST EDITION")
    print("   Data source: Wikipedia + Yahoo Finance (yfinance)")
    print("   ⚡ Rate-limited, cached, and retry-enabled")
    print("=" * 60 + "\n")
    
    try:
        # Check for --no-cache flag
        use_cache = '--no-cache' not in sys.argv
        
        # Try loading from cache first
        cache = None
        if use_cache:
            cache = load_cache()
        
        if cache and cache.get('data'):
            company_data = cache['data']
            print(f"📦 Using cached data for {len(company_data)} companies\n")
        else:
            # Step 1: Get S&P 500 list from Wikipedia
            sp500_companies = get_sp500_companies()
            
            # Step 2: Fetch data for all companies with rate limiting
            company_data = fetch_all_data(sp500_companies)
            
            # Step 3: Cache the results
            if company_data:
                save_cache(company_data)
        
        # Step 4: Display results
        display_by_sector(company_data)
        
        # Step 5: Export to CSV
        export_to_csv(company_data)
        
        print("\n✅ Analysis complete!")
        print("📊 Data is cached for 12 hours. Use --no-cache for fresh data.")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
