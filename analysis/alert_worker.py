#!/usr/bin/env python3
"""
alert_worker.py — Background thread for price polling and alert triggering.

Runs periodically to check active alerts from the database against
real-time prices via yfinance. Triggers notifications if conditions are met.
"""

import time
import logging
import threading
from datetime import datetime, timedelta
import yfinance as yf

import db
import portfolio_service

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SEC = 60  # Poll every 1 minute
_RUNNING = False
_THREAD = None

def _fetch_current_prices(tickers: list[str]) -> dict:
    """Fetch current price and previous close for a list of tickers."""
    prices = {}
    if not tickers:
        return prices
    try:
        data = yf.download(
            tickers=" ".join(tickers),
            period="2d",
            interval="1d",
            progress=False,
            group_by="ticker",
            threads=True
        )
        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    current_price = float(data["Close"].iloc[-1])
                    previous_close = float(data["Close"].iloc[-2]) if len(data) > 1 else current_price
                else:
                    current_price = float(data["Close"][ticker].iloc[-1])
                    previous_close = float(data["Close"][ticker].iloc[-2]) if len(data["Close"][ticker]) > 1 else current_price
                prices[ticker] = {
                    "current_price": round(current_price, 2),
                    "previous_close": round(previous_close, 2)
                }
            except Exception:
                prices[ticker] = {"current_price": None, "previous_close": None}
    except Exception as e:
        logger.error(f"Failed to fetch prices for alerts: {e}")
    return prices

def _check_alerts() -> None:
    """Check all active alerts against current prices."""
    try:
        alerts = db.get_alerts(active_only=True)
        if not alerts:
            return

        # Group by ticker to minimize yfinance calls
        tickers = list(set(a["ticker"] for a in alerts))
        
        prices = _fetch_current_prices(tickers)
        
        for alert in alerts:
            ticker = alert["ticker"]
            if ticker not in prices:
                continue
                
            price_data = prices[ticker]
            current_price = price_data.get("current_price")
            prev_close = price_data.get("previous_close")
            
            if current_price is None:
                continue
                
            condition = alert["condition"]
            threshold = alert["threshold"]
            triggered = False
            
            if condition == "above" and current_price > threshold:
                triggered = True
            elif condition == "below" and current_price < threshold:
                triggered = True
            elif condition in ("change_pct_up", "change_pct_down") and prev_close:
                pct_change = ((current_price - prev_close) / prev_close) * 100
                if condition == "change_pct_up" and pct_change >= threshold:
                    triggered = True
                elif condition == "change_pct_down" and pct_change <= -threshold:
                    triggered = True
                    
            if triggered:
                logger.info(f"� Alert triggered for {ticker}: {condition} {threshold} (Current: {current_price})")
                db.mark_alert_triggered(alert["id"])
                
    except Exception as e:
        logger.error(f"Error checking alerts: {e}")

def _worker_loop() -> None:
    """Main worker loop."""
    logger.info("Alert worker started.")
    while _RUNNING:
        _check_alerts()
        
        # Sleep for _POLL_INTERVAL_SEC, checking _RUNNING periodically
        for _ in range(_POLL_INTERVAL_SEC):
            if not _RUNNING:
                break
            time.sleep(1)
            
    logger.info("Alert worker stopped.")

def start_background_worker() -> None:
    """Start the background alert worker thread."""
    global _RUNNING, _THREAD
    if _RUNNING:
        return
        
    _RUNNING = True
    _THREAD = threading.Thread(target=_worker_loop, daemon=True)
    _THREAD.start()

def stop_background_worker() -> None:
    """Stop the background alert worker thread."""
    global _RUNNING, _THREAD
    _RUNNING = False
    if _THREAD:
        _THREAD.join(timeout=5)
