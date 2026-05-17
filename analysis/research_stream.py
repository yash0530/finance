#!/usr/bin/env python3
"""
research_stream.py — Server-Sent Events (SSE) streaming research pipeline.

Yields research progress in real-time so the frontend can render each stage
as it completes (Perplexity-style progressive disclosure).

Event types:
  stage_start     — A research stage has begun
  stage_complete  — A stage finished with data
  stage_error     — A stage failed (non-fatal; pipeline continues)
  report_complete — The full report is assembled and saved

Usage:
    from research_stream import stream_deep_research
    # In Flask route:
    return Response(stream_deep_research(ticker, ...), mimetype='text/event-stream')
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Generator, Optional

logger = logging.getLogger(__name__)


def _sse_event(event_type: str, data: dict) -> str:
    """Format a single SSE event string."""
    payload = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {payload}\n\n"


def stream_deep_research(
    ticker: str,
    portfolio_context: Optional[Dict] = None,
    include_edgar: bool = True,
    force_refresh: bool = False,
) -> Generator[str, None, None]:
    """Run the deep research pipeline, yielding SSE events as each stage completes.

    Args:
        ticker: Stock symbol
        portfolio_context: Optional portfolio weight/cost context
        include_edgar: Whether to include SEC filing analysis
        force_refresh: Skip cache and regenerate

    Yields:
        SSE-formatted strings (event + data)
    """
    from research_engine import (
        fetch_fundamentals,
        fetch_financial_trends,
        fetch_technicals,
        compute_intrinsic_value,
        get_peer_valuation,
        compute_position_sizing,
        _build_context_bundle,
    )
    from db import (
        get_research_cache,
        save_research_cache,
        save_research_report as save_report_v2,
        get_llm_settings,
    )

    ticker = ticker.upper().strip()
    report_id = str(uuid.uuid4())
    llm_conversations = []  # Track every LLM call

    # Stage definitions (order matters)
    stages = [
        "fundamentals", "financial_trends", "valuation", "technicals",
        "risk_management", "sentiment", "edgar", "thesis"
    ]

    # Emit pipeline start
    yield _sse_event("pipeline_start", {
        "report_id": report_id,
        "ticker": ticker,
        "stages": stages,
        "started_at": datetime.now().isoformat(),
    })

    report = {
        "report_id": report_id,
        "ticker": ticker,
        "generated_at": datetime.now().isoformat(),
        "status": "streaming",
        "version": 2,
    }

    # ── Stage 1: Fundamentals ──────────────────────────────
    yield _sse_event("stage_start", {
        "stage": "fundamentals",
        "message": "Fetching fundamental data from Yahoo Finance...",
    })
    try:
        fundamentals = fetch_fundamentals(ticker)
        report["fundamentals"] = fundamentals
        report["company_name"] = fundamentals.get("company_name", ticker)
        report["sector"] = fundamentals.get("sector", "Unknown")
        report["is_etf"] = fundamentals.get("is_etf", False)

        yield _sse_event("stage_complete", {
            "stage": "fundamentals",
            "data": fundamentals,
        })
    except Exception as e:
        logger.error(f"[{ticker}] Fundamentals failed: {e}")
        report["fundamentals"] = {"error": str(e)}
        yield _sse_event("stage_error", {
            "stage": "fundamentals",
            "error": str(e),
        })

    # ── Stage 2: Financial Trends ──────────────────────────
    yield _sse_event("stage_start", {
        "stage": "financial_trends",
        "message": "Analyzing quarterly financial trajectories (8-12 quarters)...",
    })
    try:
        trends = fetch_financial_trends(ticker)
        report["financial_trends"] = trends

        yield _sse_event("stage_complete", {
            "stage": "financial_trends",
            "data": trends,
        })
    except Exception as e:
        logger.error(f"[{ticker}] Financial trends failed: {e}")
        report["financial_trends"] = {"error": str(e), "quarters": [], "signals": {}}
        yield _sse_event("stage_error", {
            "stage": "financial_trends",
            "error": str(e),
        })

    # ── Stage 3: Valuation (DCF & Peers) ───────────────────
    yield _sse_event("stage_start", {
        "stage": "valuation",
        "message": "Computing DCF intrinsic value and peer comparisons...",
    })
    try:
        intrinsic_value = compute_intrinsic_value(ticker, report.get("fundamentals", {}), report.get("financial_trends", {}))
        peer_valuation = get_peer_valuation(ticker, report.get("sector", "Unknown"))
        
        valuation_data = {
            "intrinsic_value": intrinsic_value,
            "peer_valuation": peer_valuation,
        }
        report["valuation"] = valuation_data

        yield _sse_event("stage_complete", {
            "stage": "valuation",
            "data": valuation_data,
        })
    except Exception as e:
        logger.error(f"[{ticker}] Valuation failed: {e}")
        report["valuation"] = {"error": str(e)}
        yield _sse_event("stage_error", {
            "stage": "valuation",
            "error": str(e),
        })

    # ── Stage 4: Technicals ────────────────────────────────
    yield _sse_event("stage_start", {
        "stage": "technicals",
        "message": "Computing technical indicators (RSI, MACD, patterns)...",
    })
    try:
        technicals = fetch_technicals(ticker)
        report["technicals"] = technicals

        yield _sse_event("stage_complete", {
            "stage": "technicals",
            "data": technicals,
        })
    except Exception as e:
        logger.error(f"[{ticker}] Technicals failed: {e}")
        report["technicals"] = {"error": str(e)}
        yield _sse_event("stage_error", {
            "stage": "technicals",
            "error": str(e),
        })

    # ── Stage 5: Risk Management & Sizing ──────────────────
    yield _sse_event("stage_start", {
        "stage": "risk_management",
        "message": "Calculating Kelly Criterion position sizing and stop-loss...",
    })
    try:
        portfolio_val = 10000.0  # Default 10K for demo purposes
        if portfolio_context and portfolio_context.get("total_value"):
            portfolio_val = portfolio_context["total_value"]
            
        risk_management = compute_position_sizing(
            ticker=ticker,
            fundamentals=report.get("fundamentals", {}),
            technicals=report.get("technicals", {}),
            valuation=report.get("valuation", {}).get("intrinsic_value", {}),
            portfolio_value=portfolio_val
        )
        report["risk_management"] = risk_management

        yield _sse_event("stage_complete", {
            "stage": "risk_management",
            "data": risk_management,
        })
    except Exception as e:
        logger.error(f"[{ticker}] Risk management failed: {e}")
        report["risk_management"] = {"error": str(e)}
        yield _sse_event("stage_error", {
            "stage": "risk_management",
            "error": str(e),
        })

    # ── Stage 6: Sentiment ─────────────────────────────────
    yield _sse_event("stage_start", {
        "stage": "sentiment",
        "message": "Gathering news, analyst ratings, and social sentiment...",
    })
    try:
        from sentiment_service import get_composite_sentiment
        sentiment = get_composite_sentiment(ticker)
        report["sentiment"] = sentiment

        yield _sse_event("stage_complete", {
            "stage": "sentiment",
            "data": sentiment,
        })
    except Exception as e:
        logger.warning(f"[{ticker}] Sentiment failed: {e}")
        sentiment = {"composite_score": 5.0, "label": "neutral", "error": str(e)}
        report["sentiment"] = sentiment
        yield _sse_event("stage_error", {
            "stage": "sentiment",
            "error": str(e),
        })

    # ── Stage 7: SEC EDGAR ─────────────────────────────────
    edgar_summary = {}
    if include_edgar and not report.get("is_etf", False):
        yield _sse_event("stage_start", {
            "stage": "edgar",
            "message": "Fetching and summarizing SEC filing (10-K/10-Q)...",
        })
        try:
            from edgar_service import summarize_filing
            edgar_summary = summarize_filing(ticker)
            report["edgar_summary"] = edgar_summary

            yield _sse_event("stage_complete", {
                "stage": "edgar",
                "data": edgar_summary,
            })
        except Exception as e:
            logger.warning(f"[{ticker}] EDGAR failed: {e}")
            edgar_summary = {"available": False, "error": str(e)}
            report["edgar_summary"] = edgar_summary
            yield _sse_event("stage_error", {
                "stage": "edgar",
                "error": str(e),
            })
    else:
        report["edgar_summary"] = {}
        yield _sse_event("stage_complete", {
            "stage": "edgar",
            "data": {"skipped": True, "reason": "ETF or excluded"},
        })

    # ── Portfolio context ──────────────────────────────────
    if portfolio_context:
        report["portfolio_context"] = portfolio_context

    # ── Stage 8: LLM Thesis ───────────────────────────────
    yield _sse_event("stage_start", {
        "stage": "thesis",
        "message": "Initializing 3-pass adversarial AI analysis...",
    })
    try:
        from llm_service import generate_thesis

        # Build the context bundle with financial trends included
        context_bundle = _build_context_bundle(report)
        # Inject financial trends into the context
        trends_data = report.get("financial_trends", {})
        signals = trends_data.get("signals", {})
        if signals:
            context_bundle["financial_trends"] = {
                "revenue_acceleration": signals.get("revenue_acceleration", "unknown"),
                "gross_margin_direction": signals.get("gross_margin_trend", {}).get("direction", "unknown"),
                "net_margin_direction": signals.get("net_margin_trend", {}).get("direction", "unknown"),
                "fcf_direction": signals.get("fcf_trend", {}).get("direction", "unknown"),
                "earnings_quality": signals.get("earnings_quality_verdict", "unknown"),
                "roe_direction": signals.get("roe_trend", {}).get("direction", "unknown"),
                "revenue_growth_rates": signals.get("revenue_growth_rates", []),
            }
            
        valuation_data = report.get("valuation", {})
        if valuation_data and not valuation_data.get("error"):
            context_bundle["valuation"] = valuation_data
            
        risk_data = report.get("risk_management", {})
        if risk_data and not risk_data.get("error"):
            context_bundle["risk_management"] = risk_data

        # Callback for the 3-pass loop
        def _on_thesis_progress(sub_stage: str, message: str):
            # We yield a custom event 'thesis_progress' so the frontend can show the pass
            import copy
            event_data = {
                "stage": "thesis",
                "sub_stage": sub_stage,
                "message": message
            }
            # Note: We can't directly yield from within the callback because it's called
            # from synchronous code, so we append to a list and yield them. Wait, if we pass
            # a callback to synchronous code, we can't yield from it directly if this is a
            # generator function unless we manage a queue or use some async magic.
            # Actually, since Flask SSE uses a generator, if the callback tries to yield,
            # it won't work. But we can just use a mutable list to collect events, but then
            # they'd only be yielded after `generate_thesis` returns. 
            pass  # We'll fix this properly

        # Since we can't yield from a synchronous callback inside a generator easily,
        # we'll run the 3 passes explicitly here in the generator to get real-time streaming!
        from llm_service import _get_provider_and_model, _format_context_bundle
        
        provider, model = _get_provider_and_model("thesis")
        context_str = _format_context_bundle(context_bundle)
        
        # Pass 1
        yield _sse_event("stage_start", {"stage": "thesis", "message": "Pass 1/3: Drafting Bull Case (Optimistic)..."})
        bull_prompt = f"Analyze this stock and draft a highly optimistic BULL CASE.\nFocus on the best possible outcomes for growth, margins, and market share.\nIgnore risks for now.\n\nCONTEXT:\n{context_str}\n\nReturn ONLY plain text paragraphs (no json, no markdown headers)."
        bull_thesis = provider.complete("You are an optimistic hedge fund manager.", bull_prompt, model)
        llm_conversations.append({"stage": "thesis", "type": "bull_pass", "response": bull_thesis})
        
        # Pass 2
        yield _sse_event("stage_start", {"stage": "thesis", "message": "Pass 2/3: Drafting Devil's Advocate (Attacking the Bull Case)..."})
        bear_prompt = f"You are a skeptical short-seller. Read this Bull Case and destroy it.\nHighlight valuation risks, macro headwinds, competition, and flaws in the bullish logic.\n\nBULL CASE:\n{bull_thesis}\n\nCONTEXT:\n{context_str}\n\nReturn ONLY plain text paragraphs (no json, no markdown headers)."
        bear_thesis = provider.complete("You are a ruthless short-seller looking for flaws.", bear_prompt, model)
        llm_conversations.append({"stage": "thesis", "type": "bear_pass", "response": bear_thesis})
        
        # Pass 3
        yield _sse_event("stage_start", {"stage": "thesis", "message": "Pass 3/3: Synthesizing final balanced thesis..."})
        synth_prompt = f"You are a senior portfolio manager. Review the Bull Case and the Bear Case.\nWeigh both arguments against the raw data context, and provide a final verdict.\n\nBULL CASE:\n{bull_thesis}\n\nBEAR CASE:\n{bear_thesis}\n\nRAW CONTEXT:\n{context_str}\n\nRespond ONLY with a JSON object matching this exact schema:\n{{\n  \"summary\": \"<one sentence final verdict>\",\n  \"bull_case\": [\"<reason 1>\", \"<reason 2>\", \"<reason 3>\"],\n  \"bear_case\": [\"<risk 1>\", \"<risk 2>\", \"<risk 3>\"],\n  \"key_catalysts\": [\"<upcoming event or catalyst>\"],\n  \"recommendation\": \"<BUY | HOLD | TRIM | AVOID>\",\n  \"conviction\": \"<HIGH | MEDIUM | LOW>\",\n  \"target_price_range\": {{\"low\": 0, \"high\": 0, \"timeframe\": \"12 months\"}},\n  \"action_items\": [\"<specific actionable step>\"]\n}}"
        thesis = provider.complete_json("You are an objective, data-driven portfolio manager.", synth_prompt, model)
        
        thesis["_raw_bull_pass"] = bull_thesis
        thesis["_raw_bear_pass"] = bear_thesis
        
        report["thesis"] = thesis

        # Log the LLM conversation
        llm_conversations.append({
            "stage": "thesis",
            "type": "thesis_generation",
            "context_bundle_summary": {
                "ticker": ticker,
                "fundamentals_included": bool(report.get("fundamentals")),
                "trends_included": bool(signals),
                "sentiment_included": bool(report.get("sentiment")),
                "edgar_included": bool(edgar_summary.get("available")),
            },
            "response": thesis,
            "timestamp": datetime.now().isoformat(),
        })

        yield _sse_event("stage_complete", {
            "stage": "thesis",
            "data": thesis,
        })
    except Exception as e:
        logger.warning(f"[{ticker}] LLM thesis failed: {e}")
        thesis = {
            "error": str(e),
            "summary": "AI thesis generation failed — check LLM settings.",
            "recommendation": "HOLD",
            "conviction": "LOW",
            "bull_case": [],
            "bear_case": [],
            "action_items": ["Configure LLM provider in Settings to enable AI analysis"],
        }
        report["thesis"] = thesis
        yield _sse_event("stage_error", {
            "stage": "thesis",
            "error": str(e),
        })

    # ── Finalize and save ──────────────────────────────────
    report["status"] = "complete"

    # Save to legacy cache (24h TTL)
    try:
        provider_name = get_llm_settings().get("provider", "unknown")
        save_research_cache(ticker, report, provider_name)
    except Exception:
        pass

    # Save to v2 research_reports table (permanent, with LLM logs)
    try:
        settings = get_llm_settings()
        save_report_v2(
            report_id=report_id,
            ticker=ticker,
            report=report,
            llm_conversations=llm_conversations,
            llm_provider=settings.get("provider", ""),
            llm_model=settings.get("model_deep", ""),
        )
    except Exception as e:
        logger.warning(f"Failed to save v2 research report: {e}")

    yield _sse_event("report_complete", {
        "report_id": report_id,
        "ticker": ticker,
        "status": "complete",
        "total_stages": len(stages),
        "total_llm_calls": len(llm_conversations),
        "generated_at": report["generated_at"],
    })
