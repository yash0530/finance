"""
Tests for tools.news_tape — merged, de-duplicated, newest-first headlines.

sentiment_service fetchers are monkeypatched so no network is hit.
"""
from __future__ import annotations

import pytest

import db
import sentiment_service
from tools import ToolResult


@pytest.fixture(autouse=True)
def _wipe_cache():
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM tool_result_cache")
        conn.commit()
    finally:
        conn.close()
    yield


def _article(headline, published_at, url=""):
    return {
        "headline": headline,
        "summary": "summary",
        "url": url or f"https://example.com/{headline.replace(' ', '-')}",
        "source": "TestWire",
        "published_at": published_at,
    }


def test_news_tape_merges_and_sorts(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "fake")

    def fake_finnhub(ticker, days_back=7):
        return [
            _article(f"{ticker} older", "2026-05-01"),
            _article(f"{ticker} newer", "2026-05-20"),
        ]

    monkeypatch.setattr(sentiment_service, "get_finnhub_news", fake_finnhub)

    from tools.news_tape import NewsTapeTool
    result = NewsTapeTool().execute(tickers=["NVDA", "AMD"], limit=50)

    assert isinstance(result, ToolResult)
    assert result.is_ok()
    items = result.data["items"]
    assert len(items) == 4
    # newest first
    assert items[0]["published_at"] >= items[-1]["published_at"]
    assert result.data["count"] == 4


def test_news_tape_dedupes(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "fake")
    dupe = _article("Shared headline", "2026-05-10", url="https://x.com/a")

    monkeypatch.setattr(sentiment_service, "get_finnhub_news", lambda t, days_back=7: [dupe])

    from tools.news_tape import NewsTapeTool
    result = NewsTapeTool().execute(tickers=["NVDA", "AMD"], limit=50)
    assert result.is_ok()
    assert result.data["count"] == 1


def test_news_tape_falls_back_to_yfinance_without_key(monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    called = {"yf": False}

    def fake_yf_news(ticker):
        called["yf"] = True
        return [_article(f"{ticker} yf news", "2026-05-15")]

    monkeypatch.setattr(sentiment_service, "get_yfinance_news", fake_yf_news)

    from tools.news_tape import NewsTapeTool
    result = NewsTapeTool().execute(ticker="NVDA", limit=10)
    assert result.is_ok()
    assert called["yf"] is True
    assert result.data["count"] == 1


def test_news_tape_requires_ticker():
    from tools.news_tape import NewsTapeTool
    result = NewsTapeTool().execute(limit=10)
    assert isinstance(result, ToolResult)
    assert result.error is not None
    assert result.data["items"] == []
