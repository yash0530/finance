from __future__ import annotations

import json
import sys
from types import SimpleNamespace


class _Ticker:
    data = {
        "AAPL": {
            "longName": "Apple Inc.",
            "sector": "Information Technology",
            "industry": "Consumer Electronics",
            "marketCap": 3000000000000,
            "forwardPE": 25.0,
            "trailingPE": 30.0,
            "pegRatio": 2.1,
            "priceToSalesTrailing12Months": 8.0,
            "priceToBook": 40.0,
            "enterpriseToRevenue": 8.2,
            "enterpriseToEbitda": 22.0,
            "totalRevenue": 400000000000,
            "netIncomeToCommon": 100000000000,
            "profitMargins": 0.25,
            "operatingMargins": 0.30,
            "grossMargins": 0.45,
            "dividendYield": 0.005,
            "beta": 1.1,
            "trailingEps": 8.0,
            "revenueGrowth": 0.08,
            "averageVolume": 100,
            "52WeekChange": 0.12,
            "fiftyTwoWeekHigh": 250.0,
            "fiftyTwoWeekLow": 150.0,
            "fiftyDayAverage": 210.0,
            "twoHundredDayAverage": 195.0,
            "currentPrice": 225.0,
        },
        "MSFT": {
            "longName": "Microsoft Corporation",
            "sector": "Information Technology",
            "industry": "Software - Infrastructure",
            "marketCap": 2800000000000,
            "forwardPE": 28.0,
            "trailingPE": 35.0,
            "profitMargins": 0.35,
            "revenueGrowth": 0.12,
            "averageVolume": 300,
            "52WeekChange": 0.20,
            "fiftyTwoWeekHigh": 500.0,
            "currentPrice": 450.0,
        },
    }
    fast = {
        "AAPL": {"last_price": 230.0, "previous_close": 220.0, "last_volume": 123, "market_cap": 3100000000000},
        "MSFT": {"last_price": 455.0, "previous_close": 450.0, "last_volume": 456, "market_cap": 2850000000000},
    }

    def __init__(self, ticker):
        self.ticker = ticker.upper()

    @property
    def info(self):
        return self.data[self.ticker]

    @property
    def fast_info(self):
        return self.fast[self.ticker]


def test_sp500_refresh_writes_snapshot_and_lookup_reads_it(tmp_path, monkeypatch):
    cache_path = tmp_path / "sp500_data.json"
    cache_path.write_text(json.dumps({
        "timestamp": "2026-01-01T00:00:00",
        "data": [{"ticker": "AAPL"}, {"ticker": "MSFT"}],
    }))

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=_Ticker))

    import tools.sp500_lookup as lookup
    import tools.sp500_refresh as refresh

    monkeypatch.setattr(refresh, "_CACHE_PATH", cache_path)
    monkeypatch.setattr(lookup, "_CACHE_PATH", cache_path)
    monkeypatch.setattr(refresh, "_fetch_constituent_rows", lambda: [
        {"ticker": "AAPL", "company_name": "Apple Inc.", "sector": "Information Technology", "industry": "Consumer Electronics"},
        {"ticker": "MSFT", "company_name": "Microsoft Corporation", "sector": "Information Technology", "industry": "Software - Infrastructure"},
    ])

    result = refresh.SP500RefreshTool().execute(max_workers=1)

    assert result.error is None
    assert result.data["row_count"] == 2
    assert result.data["failed_count"] == 0

    payload = json.loads(cache_path.read_text())
    assert set(payload.keys()) == {"timestamp", "data"}
    assert {row["ticker"] for row in payload["data"]} == {"AAPL", "MSFT"}
    row = next(r for r in payload["data"] if r["ticker"] == "AAPL")
    assert row["company_name"] == "Apple Inc."
    assert row["sector"] == "Information Technology"
    assert row["market_cap"] == 3100000000000
    assert row["current_price"] == 230.0
    assert row["day_change_percent"] == 4.55
    assert row["volume"] == 123
    assert row["average_volume"] == 100
    assert row["volume_ratio"] == 1.23
    assert row["pct_from_high"] == -0.08

    assert lookup.sp500_constituents() == ["AAPL", "MSFT"]
    assert lookup.sp500_snapshot()["AAPL"]["forward_pe"] == 25.0


def test_sp500_refresh_can_use_explicit_tickers(tmp_path, monkeypatch):
    cache_path = tmp_path / "sp500_data.json"
    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=_Ticker))

    import tools.sp500_refresh as refresh

    monkeypatch.setattr(refresh, "_CACHE_PATH", cache_path)
    result = refresh.SP500RefreshTool().execute(tickers=["AAPL"], max_workers=1)

    assert result.error is None
    assert result.data["requested_count"] == 1
    assert refresh.snapshot_status(cache_path)["row_count"] == 1


def test_seed_tickers_prefers_live_constituents_over_partial_cache(tmp_path, monkeypatch):
    cache_path = tmp_path / "sp500_data.json"
    cache_path.write_text(json.dumps({
        "timestamp": "2026-01-01T00:00:00",
        "data": [{"ticker": "AAPL"}],
    }))

    import tools.sp500_refresh as refresh

    monkeypatch.setattr(refresh, "_fetch_constituent_rows", lambda: [
        {"ticker": "AAPL", "company_name": "Apple Inc.", "sector": "Information Technology", "industry": "Consumer Electronics"},
        {"ticker": "MU", "company_name": "Micron Technology", "sector": "Information Technology", "industry": "Semiconductors"},
    ])

    assert refresh.seed_tickers(cache_path) == ["AAPL", "MU"]


def test_rebuild_keeps_constituent_row_when_yfinance_info_fails(tmp_path, monkeypatch):
    cache_path = tmp_path / "sp500_data.json"
    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=_Ticker))

    import tools.sp500_refresh as refresh

    monkeypatch.setattr(refresh, "_CACHE_PATH", cache_path)
    monkeypatch.setattr(refresh, "_fetch_constituent_rows", lambda: [
        {"ticker": "MU", "company_name": "Micron Technology", "sector": "Information Technology", "industry": "Semiconductors"},
    ])

    result = refresh.SP500RefreshTool().execute(max_workers=1)

    assert result.error is None
    assert result.data["requested_count"] == 1
    assert result.data["row_count"] == 1
    assert result.data["failed_count"] == 1

    payload = json.loads(cache_path.read_text())
    assert payload["data"][0]["ticker"] == "MU"
    assert payload["data"][0]["company_name"] == "Micron Technology"
    assert payload["data"][0]["sector"] == "Information Technology"


def test_rebuild_preserves_cached_metrics_when_yfinance_rate_limited(tmp_path, monkeypatch):
    cache_path = tmp_path / "sp500_data.json"
    cache_path.write_text(json.dumps({
        "timestamp": "2026-01-01T00:00:00",
        "data": [{
            "ticker": "MU",
            "company_name": "Micron Technology",
            "sector": "Information Technology",
            "industry": "Semiconductors",
            "forward_pe": 12.5,
        }],
    }))
    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=_Ticker))

    import tools.sp500_refresh as refresh

    monkeypatch.setattr(refresh, "_CACHE_PATH", cache_path)
    monkeypatch.setattr(refresh, "_fetch_constituent_rows", lambda: [
        {"ticker": "MU", "company_name": "Micron Technology", "sector": "Information Technology", "industry": "Semiconductors"},
    ])

    result = refresh.SP500RefreshTool().execute(max_workers=1)

    assert result.error is None
    assert result.data["failed_count"] == 1
    payload = json.loads(cache_path.read_text())
    assert payload["data"][0]["forward_pe"] == 12.5


def test_rebuild_preserves_cached_metrics_when_yfinance_info_is_sparse(tmp_path, monkeypatch):
    cache_path = tmp_path / "sp500_data.json"
    cache_path.write_text(json.dumps({
        "timestamp": "2026-01-01T00:00:00",
        "data": [{
            "ticker": "CFG",
            "company_name": "Citizens Financial Group, Inc.",
            "sector": "Financials",
            "industry": "Regional Banks",
            "current_price": 44.0,
            "market_cap": 20000000000,
            "forward_pe": 11.2,
            "trailing_pe": 12.1,
            "profit_margin": 0.18,
            "revenue_growth": 0.04,
            "year_change": 0.22,
            "fifty_two_week_high": 50.0,
            "fifty_two_week_low": 30.0,
            "beta": 1.3,
            "eps": 3.6,
        }],
    }))

    class SparseTicker:
        def __init__(self, ticker):
            self.ticker = ticker

        @property
        def info(self):
            return {}

        @property
        def fast_info(self):
            return {
                "last_price": 45.0,
                "previous_close": 44.0,
                "last_volume": 1000,
                "market_cap": 21000000000,
            }

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=SparseTicker))

    import tools.sp500_refresh as refresh

    monkeypatch.setattr(refresh, "_CACHE_PATH", cache_path)
    monkeypatch.setattr(refresh, "_fetch_constituent_rows", lambda: [
        {"ticker": "CFG", "company_name": "Citizens Financial Group, Inc.", "sector": "Financials", "industry": "Regional Banks"},
    ])

    result = refresh.SP500RefreshTool().execute(max_workers=1)

    assert result.error is None
    assert result.data["row_count"] == 1
    assert result.data["failed_count"] == 1
    assert result.data["preserved_count"] == 1
    payload = json.loads(cache_path.read_text())
    row = payload["data"][0]
    assert row["current_price"] == 45.0
    assert row["market_cap"] == 21000000000
    assert row["forward_pe"] == 11.2
    assert row["trailing_pe"] == 12.1
    assert row["profit_margin_fmt"] == "18.00%"
    assert row["revenue_growth_fmt"] == "4.00%"
    assert row["pct_from_high"] == -0.1


def test_broad_refresh_caps_full_info_requests(tmp_path, monkeypatch):
    cache_path = tmp_path / "sp500_data.json"

    class CountingTicker:
        info_calls = []

        def __init__(self, ticker):
            self.ticker = ticker

        @property
        def info(self):
            CountingTicker.info_calls.append(self.ticker)
            return {
                "longName": self.ticker,
                "forwardPE": 10.0,
                "trailingPE": 12.0,
                "profitMargins": 0.1,
                "revenueGrowth": 0.05,
                "52WeekChange": 0.2,
                "fiftyTwoWeekHigh": 20.0,
                "fiftyTwoWeekLow": 10.0,
                "beta": 1.0,
                "trailingEps": 2.0,
            }

        @property
        def fast_info(self):
            return {
                "last_price": 15.0,
                "previous_close": 14.0,
                "last_volume": 1000,
                "market_cap": 1000000000,
            }

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=CountingTicker))

    import tools.sp500_refresh as refresh

    monkeypatch.setattr(refresh, "_CACHE_PATH", cache_path)
    monkeypatch.setattr(refresh, "_fetch_constituent_rows", lambda: [
        {"ticker": "AAA", "company_name": "AAA", "sector": "Industrials", "industry": ""},
        {"ticker": "BBB", "company_name": "BBB", "sector": "Industrials", "industry": ""},
        {"ticker": "CCC", "company_name": "CCC", "sector": "Industrials", "industry": ""},
    ])

    result = refresh.SP500RefreshTool().execute(max_workers=1, max_info_requests=2)

    assert result.error is None
    assert result.data["info_requested_count"] == 2
    assert result.data["info_deferred_count"] == 1
    assert CountingTicker.info_calls == ["AAA", "BBB"]
    payload = json.loads(cache_path.read_text())
    by_ticker = {row["ticker"]: row for row in payload["data"]}
    assert by_ticker["AAA"]["forward_pe"] == 10.0
    assert by_ticker["BBB"]["forward_pe"] == 10.0
    assert by_ticker["CCC"]["forward_pe"] is None
    assert by_ticker["CCC"]["market_cap"] == 1000000000
