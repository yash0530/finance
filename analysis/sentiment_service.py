#!/usr/bin/env python3
"""
sentiment_service.py — Smart-weighted composite sentiment scoring.

Signal sources and default weights:
  - Professional news via Finnhub (40%)
  - Analyst ratings via Finnhub (35%)
  - Reddit WSB + r/investing via praw (15%)
  - yfinance .news fallback (10%, used when Finnhub quota is hit)

The composite score is 0–10:
  0–3   = Bearish
  3–6   = Neutral
  6–10  = Bullish

Each source is individually cached to avoid redundant API calls.
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# Cache durations
_NEWS_CACHE_MINUTES = 60       # News refreshes hourly
_REDDIT_CACHE_MINUTES = 60     # Reddit data refreshes hourly
_ANALYST_CACHE_HOURS = 24      # Analyst ratings are stable

# In-memory cache (keyed by ticker + source)
_cache: Dict[str, Dict] = {}


def _cache_get(key: str, max_age_seconds: int) -> Optional[Dict]:
    entry = _cache.get(key)
    if not entry:
        return None
    age = time.time() - entry["ts"]
    if age > max_age_seconds:
        return None
    return entry["data"]


def _cache_set(key: str, data: Dict) -> None:
    _cache[key] = {"ts": time.time(), "data": data}


# ============================================================================
# Finnhub — News & Analyst Ratings
# ============================================================================

_FINNHUB_BASE = "https://finnhub.io/api/v1"


def _finnhub_get(endpoint: str, params: dict) -> Optional[dict]:
    """Make a Finnhub API call. Returns None on error or missing key."""
    api_key = os.environ.get("FINNHUB_API_KEY", "").strip()
    if not api_key:
        logger.debug("No FINNHUB_API_KEY set — skipping Finnhub call")
        return None
    try:
        params["token"] = api_key
        resp = requests.get(
            f"{_FINNHUB_BASE}/{endpoint}",
            params=params,
            timeout=10
        )
        if resp.status_code == 429:
            logger.warning("Finnhub rate limit hit")
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"Finnhub {endpoint} failed: {e}")
        return None


def get_finnhub_news(ticker: str, days_back: int = 7) -> List[Dict]:
    """Fetch recent company news from Finnhub.

    Returns list of articles: {headline, summary, url, datetime, source}
    """
    cache_key = f"finnhub_news:{ticker}"
    cached = _cache_get(cache_key, _NEWS_CACHE_MINUTES * 60)
    if cached is not None:
        return cached

    now = datetime.now()
    from_date = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
    to_date = now.strftime("%Y-%m-%d")

    data = _finnhub_get("company-news", {
        "symbol": ticker.upper(),
        "from": from_date,
        "to": to_date
    })

    if not data or not isinstance(data, list):
        _cache_set(cache_key, [])
        return []

    articles = []
    for item in data[:20]:  # Cap at 20 most recent
        articles.append({
            "headline": item.get("headline", ""),
            "summary": item.get("summary", "")[:300],
            "url": item.get("url", ""),
            "source": item.get("source", ""),
            "published_at": datetime.fromtimestamp(
                item.get("datetime", 0)
            ).strftime("%Y-%m-%d") if item.get("datetime") else "",
        })

    _cache_set(cache_key, articles)
    return articles


def get_analyst_ratings(ticker: str) -> Dict:
    """Fetch analyst consensus rating from Finnhub.

    Returns dict: {rating, buy, hold, sell, strong_buy, strong_sell,
                   price_target, target_high, target_low, analyst_count}
    """
    cache_key = f"finnhub_analyst:{ticker}"
    cached = _cache_get(cache_key, _ANALYST_CACHE_HOURS * 3600)
    if cached is not None:
        return cached

    # Recommendation trends
    rec_data = _finnhub_get("stock/recommendation", {"symbol": ticker.upper()})
    # Price target
    pt_data = _finnhub_get("stock/price-target", {"symbol": ticker.upper()})

    result = {
        "rating": "N/A",
        "buy": 0, "hold": 0, "sell": 0,
        "strong_buy": 0, "strong_sell": 0,
        "analyst_count": 0,
        "price_target": None,
        "target_high": None,
        "target_low": None,
    }

    if rec_data and isinstance(rec_data, list) and rec_data:
        latest = rec_data[0]  # Most recent period
        sb = latest.get("strongBuy", 0)
        b = latest.get("buy", 0)
        h = latest.get("hold", 0)
        s = latest.get("sell", 0)
        ss = latest.get("strongSell", 0)
        total = sb + b + h + s + ss

        result.update({
            "strong_buy": sb, "buy": b, "hold": h,
            "sell": s, "strong_sell": ss,
            "analyst_count": total,
        })

        # Derive consensus label
        if total > 0:
            bullish_pct = (sb + b) / total
            bearish_pct = (ss + s) / total
            if bullish_pct >= 0.6:
                result["rating"] = "Strong Buy" if bullish_pct >= 0.75 else "Buy"
            elif bearish_pct >= 0.5:
                result["rating"] = "Sell"
            else:
                result["rating"] = "Hold"

    if pt_data and isinstance(pt_data, dict):
        result.update({
            "price_target": pt_data.get("targetMean"),
            "target_high": pt_data.get("targetHigh"),
            "target_low": pt_data.get("targetLow"),
        })

    _cache_set(cache_key, result)
    return result


# ============================================================================
# yfinance News Fallback
# ============================================================================

def get_yfinance_news(ticker: str) -> List[Dict]:
    """Fetch news from yfinance as a fallback when Finnhub is unavailable."""
    cache_key = f"yf_news:{ticker}"
    cached = _cache_get(cache_key, _NEWS_CACHE_MINUTES * 60)
    if cached is not None:
        return cached

    try:
        import yfinance as yf
        stock = yf.Ticker(ticker.upper())
        raw_news = stock.news or []
        articles = []
        for item in raw_news[:15]:
            articles.append({
                "headline": item.get("title", ""),
                "summary": item.get("description", item.get("summary", ""))[:300],
                "url": item.get("link", ""),
                "source": item.get("publisher", ""),
                "published_at": datetime.fromtimestamp(
                    item.get("providerPublishTime", 0)
                ).strftime("%Y-%m-%d") if item.get("providerPublishTime") else "",
            })
        _cache_set(cache_key, articles)
        return articles
    except Exception as e:
        logger.warning(f"yfinance news failed for {ticker}: {e}")
        _cache_set(cache_key, [])
        return []


# ============================================================================
# Reddit Sentiment
# ============================================================================

_REDDIT_SUBS = ["wallstreetbets", "investing", "stocks", "options"]
_REDDIT_CACHE: Dict[str, Dict] = {}


def get_reddit_sentiment(ticker: str, days_back: int = 3) -> Dict:
    """Fetch and score Reddit mentions for a ticker.

    Searches r/wallstreetbets and r/investing for posts mentioning the ticker.
    Returns: {score, mentions, top_posts, label}
    """
    cache_key = f"reddit:{ticker}"
    cached = _cache_get(cache_key, _REDDIT_CACHE_MINUTES * 60)
    if cached is not None:
        return cached

    client_id = os.environ.get("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "").strip()
    user_agent = os.environ.get("REDDIT_USER_AGENT", "PortfolioIntelligence/1.0")

    if not client_id or not client_secret:
        logger.debug("Reddit credentials not set — skipping Reddit sentiment")
        result = {"score": 5.0, "mentions": 0, "label": "neutral", "top_posts": [], "available": False}
        _cache_set(cache_key, result)
        return result

    try:
        import praw
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            ratelimit_sleep=True,
        )

        posts = []
        cutoff = datetime.now() - timedelta(days=days_back)

        for sub_name in _REDDIT_SUBS:
            try:
                subreddit = reddit.subreddit(sub_name)
                # Search for exact ticker (e.g. "$NVDA" or "NVDA")
                query = f'"{ticker}" OR "${ticker}"'
                for post in subreddit.search(query, sort="new", time_filter="week", limit=25):
                    post_time = datetime.fromtimestamp(post.created_utc)
                    if post_time >= cutoff:
                        posts.append({
                            "title": post.title,
                            "score": post.score,
                            "upvote_ratio": post.upvote_ratio,
                            "num_comments": post.num_comments,
                            "subreddit": sub_name,
                        })
            except Exception:
                continue

        if not posts:
            result = {"score": 5.0, "mentions": 0, "label": "neutral", "top_posts": [], "available": True}
            _cache_set(cache_key, result)
            return result

        # Score by upvote ratio and engagement
        total_score = 0.0
        total_weight = 0.0
        for p in posts:
            # Weight by engagement (upvotes + comments), clamp to reasonable range
            weight = min(p["score"] + p["num_comments"], 1000) + 1
            # Map upvote_ratio (0-1) to sentiment scale (0-10)
            sentiment = p["upvote_ratio"] * 10
            total_score += sentiment * weight
            total_weight += weight

        avg_score = round(total_score / total_weight, 2) if total_weight > 0 else 5.0
        label = "bullish" if avg_score >= 6.5 else ("bearish" if avg_score <= 3.5 else "neutral")

        top_posts = sorted(posts, key=lambda x: x["score"], reverse=True)[:5]

        result = {
            "score": avg_score,
            "mentions": len(posts),
            "label": label,
            "top_posts": [{"title": p["title"], "score": p["score"], "sub": p["subreddit"]} for p in top_posts],
            "available": True,
        }
        _cache_set(cache_key, result)
        return result

    except ImportError:
        logger.warning("praw not installed — Reddit sentiment unavailable")
        result = {"score": 5.0, "mentions": 0, "label": "neutral", "top_posts": [], "available": False}
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        logger.warning(f"Reddit sentiment failed for {ticker}: {e}")
        result = {"score": 5.0, "mentions": 0, "label": "neutral", "top_posts": [], "available": False}
        _cache_set(cache_key, result)
        return result


# ============================================================================
# LLM News Sentiment Scoring
# ============================================================================

def score_news_with_llm(articles: List[Dict], ticker: str) -> Dict:
    """Score a set of news articles using the LLM sentiment scorer.

    Falls back to keyword heuristic if LLM unavailable.
    """
    if not articles:
        return {"score": 5.0, "label": "neutral", "reasoning": "No news available"}

    headlines = [a["headline"] for a in articles if a.get("headline")]

    try:
        from llm_service import score_sentiment
        result = score_sentiment(headlines, ticker)
        if "error" not in result:
            return result
    except Exception as e:
        logger.warning(f"LLM sentiment scoring failed: {e}")

    # Fallback: keyword heuristic
    return _keyword_sentiment(headlines)


def _keyword_sentiment(headlines: List[str]) -> Dict:
    """Simple keyword-based sentiment fallback (no LLM required)."""
    bull_words = [
        "surge", "rally", "beat", "record", "strong", "upgrade", "buy",
        "growth", "profit", "bullish", "outperform", "raise", "soar", "gain"
    ]
    bear_words = [
        "fall", "drop", "miss", "weak", "downgrade", "sell", "loss",
        "cut", "decline", "bearish", "underperform", "crash", "plunge", "risk"
    ]

    bull_count = 0
    bear_count = 0
    for h in headlines:
        h_lower = h.lower()
        bull_count += sum(1 for w in bull_words if w in h_lower)
        bear_count += sum(1 for w in bear_words if w in h_lower)

    total = bull_count + bear_count
    if total == 0:
        return {"score": 5.0, "label": "neutral", "reasoning": "Insufficient signal in headlines"}

    score = round(5.0 + (bull_count - bear_count) / max(total, 1) * 5, 2)
    score = max(0.0, min(10.0, score))
    label = "bullish" if score >= 6.5 else ("bearish" if score <= 3.5 else "neutral")
    return {
        "score": score,
        "label": label,
        "reasoning": f"Keyword analysis: {bull_count} bullish signals, {bear_count} bearish signals"
    }


# ============================================================================
# Composite Score
# ============================================================================

# Default weights (must sum to 1.0)
_WEIGHTS = {
    "news": 0.40,       # Finnhub news with LLM scoring
    "analyst": 0.35,    # Finnhub analyst consensus
    "reddit": 0.15,     # Reddit WSB + r/investing
    "yf_news": 0.10,    # yfinance news fallback
}


def _analyst_to_score(rating: str, analyst_count: int) -> float:
    """Convert analyst consensus rating to 0–10 scale."""
    if analyst_count == 0:
        return 5.0  # Neutral if no coverage
    mapping = {
        "Strong Buy": 9.0,
        "Buy": 7.5,
        "Hold": 5.0,
        "Sell": 2.5,
        "Strong Sell": 1.0,
        "N/A": 5.0,
    }
    return mapping.get(rating, 5.0)


def get_composite_sentiment(ticker: str) -> Dict:
    """Compute the smart-weighted composite sentiment score.

    Weights are adjusted dynamically: if a source is unavailable,
    its weight is redistributed proportionally to available sources.

    Returns:
        {
            composite_score: float (0-10),
            label: str ('bullish'|'neutral'|'bearish'),
            news_score: float,
            analyst_score: float,
            reddit_score: float,
            analyst_rating: str,
            analyst_target: float|None,
            reddit_mentions: int,
            top_headlines: List[str],
            sources_used: List[str],
        }
    """
    ticker = ticker.upper()
    cache_key = f"composite:{ticker}"
    cached = _cache_get(cache_key, _NEWS_CACHE_MINUTES * 60)
    if cached is not None:
        return cached

    scores = {}
    weights_used = {}

    # 1. Finnhub news
    finnhub_articles = get_finnhub_news(ticker)
    if finnhub_articles:
        news_sentiment = score_news_with_llm(finnhub_articles, ticker)
        scores["news"] = news_sentiment.get("score", 5.0)
        weights_used["news"] = _WEIGHTS["news"]
    else:
        # Fall back to yfinance news
        yf_articles = get_yfinance_news(ticker)
        if yf_articles:
            news_sentiment = score_news_with_llm(yf_articles, ticker)
            # Absorb both news and yf_news weights
            scores["news"] = news_sentiment.get("score", 5.0)
            weights_used["news"] = _WEIGHTS["news"] + _WEIGHTS["yf_news"]
            finnhub_articles = yf_articles  # Use for headline display
        else:
            news_sentiment = {"score": 5.0}

    # 2. Analyst ratings
    analyst = get_analyst_ratings(ticker)
    analyst_score = _analyst_to_score(analyst.get("rating", "N/A"), analyst.get("analyst_count", 0))
    scores["analyst"] = analyst_score
    weights_used["analyst"] = _WEIGHTS["analyst"]

    # 3. Reddit
    reddit = get_reddit_sentiment(ticker)
    if reddit.get("available") and reddit.get("mentions", 0) > 0:
        scores["reddit"] = reddit["score"]
        weights_used["reddit"] = _WEIGHTS["reddit"]

    # Normalize weights to sum to 1.0
    total_weight = sum(weights_used.values())
    if total_weight == 0:
        composite = 5.0
    else:
        composite = sum(
            scores.get(k, 5.0) * (w / total_weight)
            for k, w in weights_used.items()
        )
        composite = round(composite, 2)

    label = "bullish" if composite >= 6.5 else ("bearish" if composite <= 3.5 else "neutral")

    # Top headlines for display
    top_headlines = [
        a["headline"] for a in (finnhub_articles or [])[:5] if a.get("headline")
    ]

    result = {
        "composite_score": composite,
        "label": label,
        "news_score": round(scores.get("news", 5.0), 2),
        "analyst_score": round(analyst_score, 2),
        "reddit_score": round(scores.get("reddit", 5.0), 2),
        "analyst_rating": analyst.get("rating", "N/A"),
        "analyst_target": analyst.get("price_target"),
        "analyst_count": analyst.get("analyst_count", 0),
        "reddit_mentions": reddit.get("mentions", 0),
        "reddit_available": reddit.get("available", False),
        "top_headlines": top_headlines,
        "sources_used": list(weights_used.keys()),
    }

    _cache_set(cache_key, result)
    return result
