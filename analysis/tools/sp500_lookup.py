"""
tools.sp500_lookup — extracts relative metrics from S&P 500 scanner metadata.

Reads S&P 500 data from .cache/sp500_data.json and computes:
- Sector momentum percentile (year_change rank within sector)
- Forward multiple comparisons (ticker forward_pe vs sector & S&P 500 average/median)
- Beta rankings (ticker beta rank within sector & S&P 500)
- Spotlight tags (Growth Stocks, Hot Stocks, Value Plays, Momentum Leaders, Quality Gems, Dividend Champions, Low Volatility, Mega Caps, Turnaround Plays, High Beta Movers)
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

from tools import Source, Tool, ToolResult, register


_CACHE_PATH = Path(__file__).parent.parent / ".cache" / "sp500_data.json"


def _load_sp500_rows() -> List[Dict[str, Any]]:
    """S&P 500 snapshot rows from the scanner cache. Empty list if unavailable."""
    if not _CACHE_PATH.exists():
        return []
    try:
        with open(_CACHE_PATH, "r") as f:
            return json.load(f).get("data", []) or []
    except Exception:
        return []


def sp500_constituents() -> List[str]:
    """All S&P 500 tickers from the snapshot cache."""
    return sorted({(r.get("ticker") or "").upper() for r in _load_sp500_rows() if r.get("ticker")})


def sp500_by_sector() -> Dict[str, List[str]]:
    """GICS sector → constituent tickers."""
    out: Dict[str, List[str]] = {}
    for r in _load_sp500_rows():
        t = (r.get("ticker") or "").upper()
        if t:
            out.setdefault(r.get("sector") or "Unknown", []).append(t)
    return {sec: sorted(ts) for sec, ts in out.items()}


def sp500_snapshot() -> Dict[str, Dict[str, Any]]:
    """ticker → snapshot row (fundamentals + day/year change) from the cache."""
    return {(r.get("ticker") or "").upper(): r for r in _load_sp500_rows() if r.get("ticker")}


class SP500LookupTool(Tool):
    name = "sp500_lookup"
    description = (
        "Extracts relative S&P 500 metrics for a US ticker: sector momentum percentile, "
        "forward P/E comparisons against sector and index averages/medians, beta rankings, "
        "and spotlight category tags (e.g. Value Play, Growth Stock)."
    )
    cache_ttl_seconds = 0  # Metadata file is static/cached daily, no inner tool caching needed
    requires_llm = False

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Ticker symbol (e.g. AMD)"},
            },
            "required": ["ticker"],
        }

    def estimate_cost(self, **args) -> float:
        return 0.0

    def _execute(self, ticker: str, **kwargs) -> ToolResult:
        ticker = ticker.upper().strip()
        
        # Locate the cache file
        cache_path = Path(__file__).parent.parent / ".cache" / "sp500_data.json"
        if not cache_path.exists():
            return ToolResult(
                tool_name=self.name,
                data={},
                error=f"S&P 500 cache file not found at {cache_path}",
                confidence="low"
            )
            
        try:
            with open(cache_path, "r") as f:
                payload = json.load(f)
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                data={},
                error=f"Failed to read S&P 500 cache: {e}",
                confidence="low"
            )
            
        companies_data = payload.get("data", [])
        if not companies_data:
            return ToolResult(
                tool_name=self.name,
                data={},
                error="S&P 500 data cache is empty",
                confidence="low"
            )
            
        # Find target company
        target = None
        for item in companies_data:
            if item.get("ticker", "").upper() == ticker:
                target = item
                break
                
        if not target:
            return ToolResult(
                tool_name=self.name,
                data={},
                error=f"Ticker '{ticker}' not found in S&P 500 scanner metadata",
                confidence="low"
            )
            
        sector = target.get("sector", "Unknown")
        
        # Helper to convert to float safely
        def safe_float(val):
            if val is None or val == "N/A":
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        # Extract numeric columns for all companies to compute percentiles & averages
        all_companies = []
        sector_companies = []
        
        for item in companies_data:
            c_tick = item.get("ticker", "")
            c_sector = item.get("sector", "")
            
            c_data = {
                "ticker": c_tick,
                "sector": c_sector,
                "forward_pe": safe_float(item.get("forward_pe")),
                "trailing_pe": safe_float(item.get("trailing_pe")),
                "pe_ratio": safe_float(item.get("pe_ratio")),
                "year_change": safe_float(item.get("year_change")),
                "beta": safe_float(item.get("beta")),
                "revenue_growth": safe_float(item.get("revenue_growth")),
                "profit_margin": safe_float(item.get("profit_margin")),
                "market_cap": safe_float(item.get("market_cap")),
                "dividend_yield": safe_float(item.get("dividend_yield")),
            }
            all_companies.append(c_data)
            if c_sector and c_sector.lower() == sector.lower():
                sector_companies.append(c_data)

        # Computations
        target_fwd_pe = safe_float(target.get("forward_pe"))
        target_year_change = safe_float(target.get("year_change"))
        target_beta = safe_float(target.get("beta"))
        target_pe_ratio = safe_float(target.get("pe_ratio"))
        target_profit_margin = safe_float(target.get("profit_margin"))
        target_revenue_growth = safe_float(target.get("revenue_growth"))
        target_dividend_yield = safe_float(target.get("dividend_yield"))
        target_market_cap = safe_float(target.get("market_cap"))

        # Sector Momentum Percentile (year_change rank within sector)
        sector_momentum_percentile = None
        if target_year_change is not None:
            valid_sector_mom = [c["year_change"] for c in sector_companies if c["year_change"] is not None]
            if valid_sector_mom:
                less_or_equal = sum(1 for v in valid_sector_mom if v <= target_year_change)
                sector_momentum_percentile = round((less_or_equal / len(valid_sector_mom)) * 100, 2)

        # Forward Multiple Comparisons
        def get_stats(company_list, field):
            vals = [c[field] for c in company_list if c[field] is not None and c[field] > 0]
            if not vals:
                return None, None
            vals.sort()
            avg_val = sum(vals) / len(vals)
            med_val = vals[len(vals) // 2]
            return round(avg_val, 2), round(med_val, 2)

        sector_fwd_pe_avg, sector_fwd_pe_med = get_stats(sector_companies, "forward_pe")
        sp500_fwd_pe_avg, sp500_fwd_pe_med = get_stats(all_companies, "forward_pe")

        # Beta Rankings
        sector_beta_percentile = None
        if target_beta is not None:
            valid_sector_beta = [c["beta"] for c in sector_companies if c["beta"] is not None]
            if valid_sector_beta:
                less_or_equal = sum(1 for v in valid_sector_beta if v <= target_beta)
                sector_beta_percentile = round((less_or_equal / len(valid_sector_beta)) * 100, 2)

        sp500_beta_percentile = None
        if target_beta is not None:
            valid_sp500_beta = [c["beta"] for c in all_companies if c["beta"] is not None]
            if valid_sp500_beta:
                less_or_equal = sum(1 for v in valid_sp500_beta if v <= target_beta)
                sp500_beta_percentile = round((less_or_equal / len(valid_sp500_beta)) * 100, 2)

        # Spotlight Tags evaluation
        spotlight_tags = []
        if target_revenue_growth is not None and target_revenue_growth > 0.15 and target_year_change is not None and target_year_change > 0:
            spotlight_tags.append("Growth Stocks")
        if target_year_change is not None and target_year_change > 0.20:
            spotlight_tags.append("Hot Stocks")
        if target_fwd_pe is not None and 0 < target_fwd_pe < 15 and target_pe_ratio is not None and target_pe_ratio > 1:
            spotlight_tags.append("Value Plays")
        if target_pe_ratio is not None and target_pe_ratio > 1.2:
            spotlight_tags.append("Momentum Leaders")
        if target_profit_margin is not None and target_profit_margin > 0.15 and target_revenue_growth is not None and target_revenue_growth > 0.05:
            spotlight_tags.append("Quality Gems")
        if target_dividend_yield is not None and target_dividend_yield > 0.03:
            spotlight_tags.append("Dividend Champions")
        if target_beta is not None and 0 < target_beta < 0.8:
            spotlight_tags.append("Low Volatility")
        if target_market_cap is not None and target_market_cap > 200e9:
            spotlight_tags.append("Mega Caps")
        if target_year_change is not None and target_year_change < -0.10 and target_fwd_pe is not None and target_fwd_pe > 0:
            spotlight_tags.append("Turnaround Plays")
        if target_beta is not None and target_beta > 1.5:
            spotlight_tags.append("High Beta Movers")

        data_dict = {
            "ticker": ticker,
            "company_name": target.get("company_name"),
            "sector": sector,
            "industry": target.get("industry"),
            "metrics": {
                "forward_pe": target_fwd_pe,
                "trailing_pe": safe_float(target.get("trailing_pe")),
                "pe_ratio": target_pe_ratio,
                "year_change": target_year_change,
                "beta": target_beta,
                "market_cap": target_market_cap,
            },
            "sector_momentum_percentile": sector_momentum_percentile,
            "forward_multiple_comparisons": {
                "ticker_forward_pe": target_fwd_pe,
                "sector_average": sector_fwd_pe_avg,
                "sector_median": sector_fwd_pe_med,
                "sp500_average": sp500_fwd_pe_avg,
                "sp500_median": sp500_fwd_pe_med,
            },
            "beta_rankings": {
                "ticker_beta": target_beta,
                "sector_percentile": sector_beta_percentile,
                "sp500_percentile": sp500_beta_percentile,
            },
            "spotlight_tags": spotlight_tags
        }

        # Build Sources for citations
        now = datetime.now().isoformat()
        url = "file://.cache/sp500_data.json"
        sources = [
            Source(
                tool=self.name,
                field="sector_momentum_percentile",
                fetched_at=now,
                url=url,
                note=f"Computed momentum percentile relative to sector: {sector}"
            ),
            Source(
                tool=self.name,
                field="forward_multiple_comparisons",
                fetched_at=now,
                url=url,
                note="Computed multiple comparison across sector and index"
            ),
            Source(
                tool=self.name,
                field="beta_rankings",
                fetched_at=now,
                url=url,
                note="Computed beta ranking percentile"
            )
        ]
        if spotlight_tags:
            sources.append(Source(
                tool=self.name,
                field="spotlight_tags",
                fetched_at=now,
                url=url,
                note=f"Assigned spotlight tags: {', '.join(spotlight_tags)}"
            ))

        return ToolResult(
            tool_name=self.name,
            data=data_dict,
            sources=sources,
            confidence="high"
        )


register(SP500LookupTool())
