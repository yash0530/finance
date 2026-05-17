"""
Tests for sentiment_service.score_news_with_llm and tools.sentiment.SentimentTool.

Covers the C2 change: LLM vs keyword fallback is honestly reflected in the
returned data (method field), the tool's confidence rating, and the tool's
reported cost_usd.
"""
from __future__ import annotations

import pytest

import sentiment_service
from sentiment_service import score_news_with_llm
from tools.sentiment import SentimentTool


# ============================================================================
# score_news_with_llm
# ============================================================================

def test_score_news_uses_llm_when_available(monkeypatch):
    captured = {}

    def fake_score(headlines, ticker):
        captured["headlines"] = headlines
        captured["ticker"] = ticker
        return {"score": 7.5, "label": "bullish", "reasoning": "strong beats"}

    monkeypatch.setattr("llm_service.score_sentiment", fake_score)

    articles = [{"headline": "NVDA beats earnings"}, {"headline": "Buyback announced"}]
    out = score_news_with_llm(articles, "NVDA")

    assert out["method"] == "llm"
    assert out["score"] == 7.5
    assert out["n_headlines"] == 2
    assert captured["ticker"] == "NVDA"


def test_score_news_caps_headlines(monkeypatch):
    captured = {}

    def fake_score(headlines, ticker):
        captured["count"] = len(headlines)
        return {"score": 5.0, "label": "neutral", "reasoning": "mixed"}

    monkeypatch.setattr("llm_service.score_sentiment", fake_score)

    articles = [{"headline": f"news {i}"} for i in range(50)]
    out = score_news_with_llm(articles, "NVDA", max_headlines=10)

    assert captured["count"] == 10
    assert out["n_headlines"] == 10


def test_score_news_falls_back_to_keyword_on_llm_exception(monkeypatch):
    def boom(headlines, ticker):
        raise RuntimeError("LLM down")

    monkeypatch.setattr("llm_service.score_sentiment", boom)

    articles = [{"headline": "Stock soars on strong beat"}]
    out = score_news_with_llm(articles, "NVDA")

    assert out["method"] == "keyword"
    assert "score" in out
    assert out["n_headlines"] == 1


def test_score_news_falls_back_when_llm_returns_error(monkeypatch):
    monkeypatch.setattr("llm_service.score_sentiment", lambda h, t: {"error": "rate limited"})

    articles = [{"headline": "Some headline"}]
    out = score_news_with_llm(articles, "NVDA")

    assert out["method"] == "keyword"


def test_score_news_empty_returns_none_method():
    out = score_news_with_llm([], "NVDA")
    assert out["method"] == "none"
    assert out["score"] == 5.0
    assert out["n_headlines"] == 0


# ============================================================================
# SentimentTool — confidence + cost mapping
# ============================================================================

def _stub_composite(method="llm", sources_used=("news", "analyst"), n_headlines=5):
    """Helper to monkeypatch get_composite_sentiment with a chosen method."""
    return {
        "composite_score": 7.0,
        "label": "bullish",
        "news_score": 7.5,
        "news_method": method,
        "news_headlines_scored": n_headlines,
        "news_reasoning": "test",
        "analyst_score": 6.5,
        "reddit_score": 5.0,
        "analyst_rating": "Buy",
        "analyst_target": 100,
        "analyst_count": 12,
        "reddit_mentions": 0,
        "reddit_available": False,
        "top_headlines": ["h1", "h2"],
        "sources_used": list(sources_used),
    }


def test_tool_high_confidence_when_llm_and_multi_source(monkeypatch):
    monkeypatch.setattr(
        sentiment_service, "get_composite_sentiment",
        lambda t: _stub_composite(method="llm", sources_used=("news", "analyst")),
    )

    result = SentimentTool()._execute(ticker="NVDA")
    assert result.confidence == "high"
    assert result.cost_usd > 0  # LLM was used → charge


def test_tool_medium_confidence_when_keyword_fallback(monkeypatch):
    monkeypatch.setattr(
        sentiment_service, "get_composite_sentiment",
        lambda t: _stub_composite(method="keyword", sources_used=("news", "analyst")),
    )

    result = SentimentTool()._execute(ticker="NVDA")
    # Two sources but no LLM scoring → medium, not high
    assert result.confidence == "medium"
    assert result.cost_usd == 0.0  # No LLM = no charge


def test_tool_medium_confidence_when_llm_but_one_source(monkeypatch):
    monkeypatch.setattr(
        sentiment_service, "get_composite_sentiment",
        lambda t: _stub_composite(method="llm", sources_used=("news",)),
    )

    result = SentimentTool()._execute(ticker="NVDA")
    assert result.confidence == "medium"
    assert result.cost_usd > 0


def test_tool_low_confidence_when_no_sources(monkeypatch):
    monkeypatch.setattr(
        sentiment_service, "get_composite_sentiment",
        lambda t: _stub_composite(method="none", sources_used=()),
    )

    result = SentimentTool()._execute(ticker="NVDA")
    assert result.confidence == "low"
    assert result.cost_usd == 0.0


def test_tool_source_note_reflects_method(monkeypatch):
    monkeypatch.setattr(
        sentiment_service, "get_composite_sentiment",
        lambda t: _stub_composite(method="keyword", sources_used=("news",)),
    )

    result = SentimentTool()._execute(ticker="NVDA")
    news_sources = [s for s in result.sources if s.field == "news_score"]
    assert len(news_sources) == 1
    assert "keyword-scored fallback" in news_sources[0].note


def test_tool_handles_exception_gracefully(monkeypatch):
    def boom(t):
        raise RuntimeError("service down")

    monkeypatch.setattr(sentiment_service, "get_composite_sentiment", boom)

    result = SentimentTool()._execute(ticker="NVDA")
    assert result.confidence == "low"
    assert result.error
