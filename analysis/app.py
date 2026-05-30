#!/usr/bin/env python3
"""
Edge — Personal Markets Terminal · Flask backend API.

Routes: terminal panels, stock view, chart, console (slash commands), themes,
screener, library, deep-research SSE + memo/report CRUD, settings, docs.
The legacy S&P 500 scanner, portfolio, spotlight, and pattern HTTP routes were
removed in v3 (pull-based terminal); the deep-research brain is unchanged.
"""

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import json
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

# Core service modules
try:
    import db
    import llm_service
    SERVICES_ENABLED = True
except ImportError as _e:
    SERVICES_ENABLED = False
    import logging
    logging.getLogger(__name__).warning(f"Core services unavailable: {_e}")


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

# Build/version stamps used by /api/version so the frontend can detect a stale backend.
import subprocess as _subprocess
import datetime as _dt

def _git_info():
    repo = Path(__file__).resolve().parent.parent
    try:
        sha = _subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'], cwd=repo, stderr=_subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        sha = 'unknown'
    try:
        dirty = bool(_subprocess.check_output(
            ['git', 'status', '--porcelain'], cwd=repo, stderr=_subprocess.DEVNULL,
        ).decode().strip())
    except Exception:
        dirty = False
    return sha, dirty

_GIT_SHA, _GIT_DIRTY = _git_info()
_STARTED_AT = _dt.datetime.utcnow()


def _services_unavailable():
    return jsonify({'error': 'Core services not available. Check server logs.'}), 503























# ============================================================================
# Head and Shoulders Pattern Detection
# ============================================================================











# ============================================================================
# Additional Pattern Detection Functions
# ============================================================================























# ============================================================================
# Pattern Scanning Functions
# ============================================================================

# All available pattern detectors

















@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'services_enabled': SERVICES_ENABLED,
    })


@app.route('/api/version', methods=['GET'])
def version():
    """Backend build/version stamp. Used by the frontend to detect stale processes."""
    now = _dt.datetime.utcnow()
    return jsonify({
        'git_sha': _GIT_SHA,
        'git_dirty': _GIT_DIRTY,
        'started_at': _STARTED_AT.isoformat() + 'Z',
        'uptime_s': int((now - _STARTED_AT).total_seconds()),
        'route_count': len(list(app.url_map.iter_rules())),
    })


# ============================================================================
# Portfolio Routes (Phase 1)
# ============================================================================


















# ============================================================================
# LLM Settings Routes
# ============================================================================

@app.route('/api/settings/llm', methods=['GET'])
def get_llm_settings():
    """Return current LLM provider settings (API key is masked)."""
    if not SERVICES_ENABLED:
        return _services_unavailable()
    settings = db.get_llm_settings()
    return jsonify(settings)


@app.route('/api/settings/llm', methods=['POST'])
def save_llm_settings():
    """Update LLM provider settings.

    Body: {
        "provider": "claude" | "gemini" | "ollama",
        "model_fast": "claude-3-5-haiku-20241022",
        "model_deep": "claude-opus-4-5",
        "api_key": "sk-ant-...",
        "base_url": "http://localhost:11434"  // Ollama only
    }
    """
    if not SERVICES_ENABLED:
        return _services_unavailable()

    body = request.get_json() or {}
    provider = body.get('provider', 'ollama')

    if provider not in ('claude', 'gemini', 'ollama'):
        return jsonify({'error': 'provider must be claude, gemini, or ollama'}), 400

    settings = db.save_llm_settings(
        provider=provider,
        model_fast=body.get('model_fast', 'llama3.2'),
        model_deep=body.get('model_deep', 'llama3.2'),
        api_key=body.get('api_key', ''),
        base_url=body.get('base_url', 'http://localhost:11434')
    )
    return jsonify({'success': True, 'settings': settings})


@app.route('/api/settings/llm/test', methods=['POST'])
def test_llm_connection():
    """Send a quick test prompt to verify LLM connectivity."""
    if not SERVICES_ENABLED:
        return _services_unavailable()
    try:
        result = llm_service.score_sentiment(
            ["Markets rally on strong earnings reports"],
            ticker="TEST"
        )
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 400
        return jsonify({'success': True, 'test_result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400



# ============================================================================
# Research Routes (Phase 2)
# ============================================================================


@app.route('/api/research/reports', methods=['GET'])
def get_all_research_history():
    """Get past research reports across all tickers."""
    if not SERVICES_ENABLED:
        return _services_unavailable()
    limit = request.args.get('limit', 50, type=int)
    reports = db.get_all_research_reports(limit=limit)
    return jsonify({'count': len(reports), 'reports': reports})


@app.route('/api/research/reports/<ticker>', methods=['GET'])
def get_research_history(ticker: str):
    """Get past research reports for a ticker."""
    if not SERVICES_ENABLED:
        return _services_unavailable()
    limit = request.args.get('limit', 10, type=int)
    reports = db.get_research_reports_for_ticker(ticker, limit=limit)
    return jsonify({'ticker': ticker.upper(), 'count': len(reports), 'reports': reports})


@app.route('/api/research/report/<report_id>', methods=['GET'])
def get_research_report_by_id(report_id: str):
    """Get a specific research report by its UUID."""
    if not SERVICES_ENABLED:
        return _services_unavailable()
    report = db.get_research_report(report_id)
    if not report:
        return jsonify({'error': f'Report {report_id} not found'}), 404
    return jsonify(convert_numpy_types(report))


@app.route('/api/research/report/<report_id>', methods=['DELETE'])
def delete_research_report_route(report_id: str):
    """Delete a research report by its UUID."""
    if not SERVICES_ENABLED:
        return _services_unavailable()
    success = db.delete_research_report(report_id)
    if not success:
        return jsonify({'error': f'Report {report_id} not found'}), 404
    return jsonify({'success': True, 'message': f'Report {report_id} deleted successfully'})


@app.route('/api/research/reports/delete-bulk', methods=['POST'])
def delete_research_reports_bulk_route():
    """Delete multiple research reports by their UUIDs."""
    if not SERVICES_ENABLED:
        return _services_unavailable()
    body = request.get_json() or {}
    report_ids = body.get('report_ids', [])
    if not report_ids:
        return jsonify({'error': 'No report_ids provided'}), 400
    count = db.delete_research_reports(report_ids)
    return jsonify({'success': True, 'message': f'{count} reports deleted successfully'})


@app.route('/api/research/report/<report_id>/drift', methods=['GET'])
def get_research_report_drift(report_id: str):
    """Get price drift since a report was generated."""
    if not SERVICES_ENABLED:
        return _services_unavailable()
    report = db.get_research_report(report_id)
    if not report:
        return jsonify({'error': f'Report {report_id} not found'}), 404

    report_data = report.get("report", {})
    ticker = report.get("ticker", "")

    # Get price at report time
    price_at_report = report_data.get("price_at_report") or 0
    if not price_at_report:
        # Fallback: try verdict.trade_plan.entry_zone or recommendations
        verdict = report_data.get("verdict", {})
        entry = (verdict.get("trade_plan") or {}).get("entry_zone", {})
        if entry.get("upper"):
            price_at_report = (entry.get("lower", 0) + entry.get("upper", 0)) / 2

    # Get current price
    current_price = 0
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
    except Exception:
        pass

    # Calculate drift
    pct_change = 0
    if price_at_report and current_price:
        pct_change = round(((current_price - price_at_report) / price_at_report) * 100, 2)

    # Days since report
    days_old = 0
    generated_at = report.get("generated_at", "")
    if generated_at:
        try:
            from datetime import datetime as dt
            gen_date = dt.fromisoformat(generated_at.replace("Z", "+00:00"))
            days_old = (dt.now() - gen_date.replace(tzinfo=None)).days
        except Exception:
            pass

    return jsonify({
        "price_at_report": price_at_report,
        "current_price": current_price,
        "pct_change": pct_change,
        "days_old": days_old,
        "ticker": ticker,
    })




# ============================================================================
# Deep Research routes — agentic loop + Living Memo + calibration
# ============================================================================

@app.route('/api/research/<ticker>/v2/stream', methods=['GET'])
def research_v2_stream(ticker):
    """SSE stream for deep research (agentic loop + multi-agent debate)."""
    try:
        from agent_loop import stream_deep_research
    except ImportError as e:
        return jsonify({'error': f'Agent loop unavailable: {e}'}), 500

    profile = request.args.get('budget', 'deep')
    force = request.args.get('refresh', 'false').lower() == 'true'

    # Portfolio context retired in v3 (portfolio management is out of scope).
    portfolio_context = None

    return Response(
        stream_deep_research(
            ticker=ticker.upper().strip(),
            portfolio_context=portfolio_context,
            budget_profile=profile,
            force_refresh=force,
        ),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@app.route('/api/research/<ticker>/memo', methods=['GET'])
def get_memo(ticker):
    try:
        import living_memo
        memo = living_memo.load(ticker)
        if not memo:
            return jsonify({'exists': False, 'ticker': ticker.upper()}), 404
        return jsonify({'exists': True, **memo})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/research/<ticker>/memo', methods=['PUT'])
def update_memo(ticker):
    try:
        import living_memo
        body = request.get_json() or {}
        content_json = body.get('content_json')
        delta_summary = body.get('delta_summary', 'manual edit')
        if not content_json:
            return jsonify({'error': 'content_json required'}), 400
        version = living_memo.save(
            ticker=ticker,
            content_json=content_json,
            delta_summary=delta_summary,
            user_edited=True,
        )
        return jsonify({'success': True, 'new_version': version})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/research/<ticker>/memo/history', methods=['GET'])
def memo_history(ticker):
    try:
        import living_memo
        limit = int(request.args.get('limit', 20))
        return jsonify({'ticker': ticker.upper(), 'versions': living_memo.history(ticker, limit)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/research/<ticker>/memo/version/<int:version>', methods=['GET'])
def memo_version(ticker, version):
    try:
        import living_memo
        v = living_memo.get_version(ticker, version)
        if not v:
            return jsonify({'error': 'version not found'}), 404
        return jsonify(v)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/research/<ticker>/tool-log/<report_id>', methods=['GET'])
def tool_log(ticker, report_id):
    try:
        from db import get_tool_call_log
        log = get_tool_call_log(report_id)
        return jsonify({'report_id': report_id, 'ticker': ticker.upper(), 'count': len(log), 'log': log})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/sectors/classify/<ticker>', methods=['GET'])
def sector_classify(ticker):
    try:
        import sector_router
        cls = sector_router.classify(ticker)
        return jsonify(cls)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sectors/classify/<ticker>', methods=['POST'])
def sector_classify_manual(ticker):
    """User-driven manual override of sector classification."""
    try:
        import sector_router
        body = request.get_json() or {}
        sector_key = body.get('sector_key')
        gics = body.get('gics_industry', '')
        if not sector_key:
            return jsonify({'error': 'sector_key required'}), 400
        result = sector_router.manual_classify(ticker, sector_key, gics)
        return jsonify(result)
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/catalysts', methods=['GET'])
def catalysts():
    try:
        from db import get_catalysts
        tickers_param = request.args.get('tickers', '')
        tickers = [t.strip().upper() for t in tickers_param.split(',') if t.strip()] or None
        days = int(request.args.get('days_ahead', 90))
        return jsonify({'count': len(get_catalysts(tickers, days)),
                        'catalysts': get_catalysts(tickers, days)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# ============================================================================
# /api/docs — in-app docs surface (D1)
# ============================================================================

# Whitelist: slug → (filename, title, category, order). Filenames are
# resolved against analysis/docs/ and the slug→filename mapping prevents
# path traversal. Only files listed here are served.
_DOCS_MANIFEST = [
    {"slug": "getting-started", "file": "getting_started.md",
     "title": "Getting Started", "category": "Start here", "order": 1},
    {"slug": "how-to-invest", "file": "how_to_invest.md",
     "title": "How to Invest with This Tool", "category": "Start here", "order": 2},
    {"slug": "understanding-outputs", "file": "understanding_outputs.md",
     "title": "Understanding the Outputs", "category": "Daily use", "order": 3},
    {"slug": "troubleshooting", "file": "troubleshooting.md",
     "title": "Troubleshooting", "category": "Daily use", "order": 4},
    {"slug": "architecture", "file": "architecture.md",
     "title": "Architecture Overview", "category": "Reference", "order": 5},
]
_DOCS_BY_SLUG = {d["slug"]: d for d in _DOCS_MANIFEST}


def _docs_dir():
    import os
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")


@app.route('/api/docs', methods=['GET'])
def list_docs():
    """List user-facing guides with metadata. Skips entries whose file is missing."""
    import os
    available = []
    for entry in _DOCS_MANIFEST:
        path = os.path.join(_docs_dir(), entry["file"])
        if os.path.isfile(path):
            available.append({k: entry[k] for k in ("slug", "title", "category", "order")})
    available.sort(key=lambda d: (d["order"], d["title"]))
    return jsonify({"docs": available, "count": len(available)})


@app.route('/api/docs/<slug>', methods=['GET'])
def get_doc(slug):
    """Return the rendered markdown body for a single guide.

    Slug-to-filename lookup is whitelisted in _DOCS_BY_SLUG to prevent path
    traversal. The response includes a minimal table-of-contents extracted
    from H2/H3 headings so the UI can render scroll-spy without a markdown
    parser on the server side.
    """
    import os
    import re

    entry = _DOCS_BY_SLUG.get(slug)
    if not entry:
        return jsonify({"error": f"Unknown doc slug '{slug}'"}), 404

    path = os.path.join(_docs_dir(), entry["file"])
    if not os.path.isfile(path):
        return jsonify({"error": f"Doc file missing for slug '{slug}'"}), 404

    try:
        with open(path, "r", encoding="utf-8") as f:
            body = f.read()
    except Exception as e:
        return jsonify({"error": f"Failed to read doc: {e}"}), 500

    # Cheap TOC: pull H2/H3 from raw markdown (ignore lines inside fenced code).
    toc = []
    in_fence = False
    for line in body.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^(#{2,3})\s+(.+?)\s*$", line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            anchor = re.sub(r"[^a-z0-9\s-]", "", text.lower()).strip().replace(" ", "-")
            toc.append({"level": level, "text": text, "anchor": anchor})

    return jsonify({
        "slug": slug,
        "title": entry["title"],
        "category": entry["category"],
        "order": entry["order"],
        "body": body,
        "toc": toc,
    })


# ============================================================================
# Terminal — daily scan panels (pull-based, no background workers)
# ============================================================================

def _watchlist_tickers() -> List[str]:
    try:
        return [w["ticker"] for w in db.get_watchlist()]
    except Exception:
        return []


def _terminal_universe() -> List[str]:
    """Resolve the default Terminal scan universe: watchlist ∪ movers default."""
    from tools.movers import DEFAULT_UNIVERSE
    seen, universe = set(), []
    for t in _watchlist_tickers() + DEFAULT_UNIVERSE:
        u = t.upper().strip()
        if u and u not in seen:
            seen.add(u)
            universe.append(u)
    return universe


@app.route('/api/terminal/movers', methods=['GET'])
def terminal_movers():
    """Top gainers/losers across the requested universe. TTL handled by the tool."""
    from tools import get_tool
    universe_param = request.args.get('universe', 'themes')
    if universe_param == 'watchlist':
        tickers = _watchlist_tickers()
    else:
        tickers = _terminal_universe()
    top_n = int(request.args.get('top_n', 10))
    result = get_tool('movers').execute(tickers=tickers, top_n=top_n)
    return jsonify(result.to_dict())


@app.route('/api/terminal/news', methods=['GET'])
def terminal_news():
    """Recent news headlines across the universe (or a single theme/ticker set)."""
    from tools import get_tool
    limit = int(request.args.get('limit', 50))
    theme = request.args.get('theme', 'all')
    if theme and theme not in ('all', ''):
        tickers = [theme.upper()]
    else:
        tickers = _terminal_universe()
    result = get_tool('news_tape').execute(tickers=tickers, limit=limit)
    return jsonify(result.to_dict())


@app.route('/api/terminal/watchlist', methods=['GET'])
def terminal_watchlist():
    """Watchlist tickers enriched with day change from the movers tool."""
    from tools.movers import fetch_quotes
    rows = db.get_watchlist()
    tickers = [r["ticker"] for r in rows]
    quotes = fetch_quotes(tickers) if tickers else {}
    items = []
    for r in rows:
        q = quotes.get(r["ticker"], {})
        items.append({
            "ticker": r["ticker"],
            "added_at": r["added_at"],
            "notes": r.get("notes"),
            "price": q.get("price"),
            "change_pct": q.get("change_pct"),
        })
    return jsonify({"items": items, "count": len(items)})


@app.route('/api/terminal/watchlist', methods=['POST'])
def terminal_watchlist_add():
    body = request.get_json(silent=True) or {}
    ticker = (body.get('ticker') or '').upper().strip()
    if not ticker:
        return jsonify({'error': 'ticker required'}), 400
    db.add_watchlist(ticker, body.get('notes', ''))
    return jsonify({'ok': True, 'ticker': ticker})


@app.route('/api/terminal/watchlist/<ticker>', methods=['DELETE'])
def terminal_watchlist_remove(ticker):
    db.remove_watchlist(ticker)
    return jsonify({'ok': True, 'ticker': ticker.upper().strip()})


@app.route('/api/chart/<ticker>', methods=['GET'])
def chart(ticker):
    """OHLCV bars for a ticker over a range/interval, backed by price_history tool."""
    from tools import get_tool
    rng = request.args.get('range', '1y')
    interval = request.args.get('interval', '')
    result = get_tool('price_history').execute(
        ticker=ticker.upper().strip(), range=rng, interval=interval,
    )
    return jsonify(result.to_dict())


@app.route('/api/terminal/theme-heat', methods=['GET'])
def terminal_theme_heat():
    """Per-theme median move + leader/laggard. ?universe=themes|sp500-sectors."""
    from tools import get_tool
    universe = request.args.get('universe', 'themes')
    result = get_tool('theme_heat').execute(universe=universe)
    return jsonify(result.to_dict())


@app.route('/api/terminal/catalysts', methods=['GET'])
def terminal_catalysts():
    """Upcoming catalysts for watchlist + theme constituents within `days`."""
    days = int(request.args.get('days', 7))
    import themes_service
    tickers = themes_service.scan_universe(extra=_watchlist_tickers())
    # Refresh catalysts for the universe so the table isn't stale (cached per-tool).
    from tools import get_tool
    tool = get_tool('catalyst_lookup')
    for t in tickers:
        try:
            tool.execute(ticker=t)
        except Exception:
            continue
    events = db.get_catalysts(tickers=tickers, days_ahead=days)
    return jsonify({"items": events, "count": len(events), "days": days})


@app.route('/api/terminal/flow', methods=['GET'])
def terminal_flow():
    """Options flow snapshot. Degrades to a sparse payload without an UW key."""
    import os
    from tools import get_tool
    ticker = (request.args.get('ticker') or '').upper().strip()
    if not os.environ.get('UNUSUAL_WHALES_API_KEY', '').strip():
        return jsonify({
            "degraded": True,
            "reason": "No UNUSUAL_WHALES_API_KEY — real unusual blocks, dark pool, and gamma are gated.",
            "ticker": ticker or None,
            "free_tier": "yfinance options metrics available per-ticker via Stock View.",
        })
    if not ticker:
        return jsonify({"degraded": False, "items": [], "note": "Provide ?ticker=<T> for a flow snapshot."})
    result = get_tool('options_flow').execute(ticker=ticker)
    payload = result.to_dict()
    payload["degraded"] = False
    return jsonify(payload)


@app.route('/api/terminal/hypothesis', methods=['POST'])
def terminal_hypothesis():
    """Generate (or return cached) a 3-sentence quick take for a ticker.

    Cache TTL 4h. AI on demand only — each uncached call is ~$0.05.
    """
    body = request.get_json(silent=True) or {}
    ticker = (body.get('ticker') or '').upper().strip()
    if not ticker:
        return jsonify({'error': 'ticker required'}), 400

    cached = db.get_hypothesis(ticker, max_age_seconds=4 * 3600)
    if cached and not body.get('refresh'):
        return jsonify({
            "ticker": ticker,
            "why_md": cached["content_md"],
            "evidence_refs": cached.get("evidence_refs", []),
            "cost_usd": cached.get("cost_usd"),
            "cached": True,
            "generated_at": cached["generated_at"],
        })

    try:
        from agent_loop import run_quick_take
    except ImportError as e:
        return jsonify({'error': f'Agent loop unavailable: {e}'}), 500

    take = run_quick_take(ticker)
    db.save_hypothesis(
        ticker=ticker,
        content_md=take.get("why_md", ""),
        cost_usd=take.get("cost_usd", 0.0),
        evidence_refs=take.get("evidence_refs", []),
    )
    from datetime import datetime
    return jsonify({**take, "cached": False, "generated_at": datetime.now().isoformat()})


@app.route('/api/themes', methods=['GET'])
def themes_list():
    import themes_service
    return jsonify({"themes": themes_service.list_themes()})


@app.route('/api/themes', methods=['POST'])
def themes_create():
    body = request.get_json(silent=True) or {}
    slug = (body.get('slug') or '').strip().lower()
    name = (body.get('name') or '').strip()
    if not slug or not name:
        return jsonify({'error': 'slug and name required'}), 400
    db.upsert_theme(slug, name, body.get('description', ''))
    for t in body.get('tickers', []) or []:
        db.add_theme_ticker(slug, t)
    return jsonify({'ok': True, 'slug': slug})


@app.route('/api/themes/<slug>', methods=['DELETE'])
def themes_delete(slug):
    db.delete_theme(slug)
    return jsonify({'ok': True, 'slug': slug})


@app.route('/api/themes/<slug>/tickers', methods=['GET'])
def themes_tickers(slug):
    import themes_service
    detail = themes_service.get_theme_detail(slug)
    if not detail:
        return jsonify({'error': f'Unknown theme {slug}'}), 404
    return jsonify(detail)


@app.route('/api/themes/<slug>/tickers', methods=['POST'])
def themes_add_ticker(slug):
    body = request.get_json(silent=True) or {}
    ticker = (body.get('ticker') or '').upper().strip()
    if not ticker:
        return jsonify({'error': 'ticker required'}), 400
    db.add_theme_ticker(slug, ticker, float(body.get('weight_hint', 1.0)))
    return jsonify({'ok': True, 'slug': slug, 'ticker': ticker})


@app.route('/api/themes/<slug>/tickers/<ticker>', methods=['DELETE'])
def themes_remove_ticker(slug, ticker):
    db.remove_theme_ticker(slug, ticker)
    return jsonify({'ok': True, 'slug': slug, 'ticker': ticker.upper().strip()})


@app.route('/api/themes/by-ticker/<ticker>', methods=['GET'])
def themes_by_ticker(ticker):
    import themes_service
    return jsonify({
        "ticker": ticker.upper().strip(),
        "themes": themes_service.themes_for_ticker(ticker),
    })


# ============================================================================
# Stock View — single-ticker cockpit sections (lazy-fetched in parallel)
# ============================================================================

@app.route('/api/stock/<ticker>/header', methods=['GET'])
def stock_header(ticker):
    """Price/mcap/fundamentals snapshot for the Stock View header."""
    from tools import get_tool
    result = get_tool('fundamentals').execute(ticker=ticker.upper().strip())
    return jsonify(result.to_dict())


@app.route('/api/stock/<ticker>/fundamentals', methods=['GET'])
def stock_fundamentals(ticker):
    """Fundamentals + multi-quarter financial trends for the Stock View."""
    from tools import get_tool
    t = ticker.upper().strip()
    fundamentals = get_tool('fundamentals').execute(ticker=t)
    trends = get_tool('financial_trends').execute(ticker=t)
    return jsonify({
        "fundamentals": fundamentals.to_dict(),
        "trends": trends.to_dict(),
    })


@app.route('/api/stock/<ticker>/technicals', methods=['GET'])
def stock_technicals(ticker):
    """Technical indicators incl. relative_strength_vs_spy for the chart overlays."""
    from tools import get_tool
    result = get_tool('technicals').execute(ticker=ticker.upper().strip())
    return jsonify(result.to_dict())


@app.route('/api/stock/<ticker>/ownership', methods=['GET'])
def stock_ownership(ticker):
    """Institutional holders + insider Form-4 flow for the Ownership strip."""
    from tools import get_tool
    t = ticker.upper().strip()
    inst = get_tool('institutional_13f').execute(ticker=t)
    insider = get_tool('insider_form4').execute(ticker=t)
    return jsonify({
        "institutional": inst.to_dict(),
        "insider": insider.to_dict(),
    })


@app.route('/api/stock/<ticker>/filings', methods=['GET'])
def stock_filings(ticker):
    """Recent SEC filings (free metadata, no LLM) for the Filings/News timeline."""
    import edgar_service
    t = ticker.upper().strip()
    try:
        filings = edgar_service.list_recent_filings(t, limit=15)
    except Exception as e:
        filings = []
        return jsonify({"ticker": t, "filings": [], "error": str(e)})
    return jsonify({"ticker": t, "filings": filings, "count": len(filings)})


# ============================================================================
# Console — slash-command dispatcher (SSE)
# ============================================================================

@app.route('/api/console/run', methods=['POST'])
def console_run():
    """Dispatch a slash command and stream its SSE output."""
    body = request.get_json(silent=True) or {}
    command = (body.get('command') or '').strip()
    if not command:
        return jsonify({'error': 'command required'}), 400
    try:
        import console_orchestrator
    except ImportError as e:
        return jsonify({'error': f'Console orchestrator unavailable: {e}'}), 500

    return Response(
        console_orchestrator.run(command),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@app.route('/api/library/memos', methods=['GET'])
def library_memos():
    """Index of all Living Memos for the Library Memos tab."""
    return jsonify({"memos": db.get_all_living_memos()})


# ============================================================================
# Screener
# ============================================================================

@app.route('/api/screener/run', methods=['POST'])
def screener_run():
    """Evaluate a rules-JSON spec against a universe; return matched tickers."""
    spec = request.get_json(silent=True) or {}
    try:
        import screener_engine
    except ImportError as e:
        return jsonify({'error': f'Screener engine unavailable: {e}'}), 500
    result = screener_engine.run_screen(spec)
    return jsonify(result)


@app.route('/api/screener/fields', methods=['GET'])
def screener_fields():
    import screener_engine
    return jsonify({
        "fields": screener_engine.available_fields(),
        "patterns": screener_engine.pattern_names(),
    })


@app.route('/api/screener/saved', methods=['GET'])
def screener_saved_list():
    return jsonify({"saved": db.get_screener_saved()})


@app.route('/api/screener/saved', methods=['POST'])
def screener_saved_create():
    body = request.get_json(silent=True) or {}
    name = (body.get('name') or '').strip()
    rules = body.get('rules')
    if not name or rules is None:
        return jsonify({'error': 'name and rules required'}), 400
    sid = db.save_screener(name, rules)
    return jsonify({'ok': True, 'id': sid})


@app.route('/api/screener/saved/<int:screener_id>', methods=['DELETE'])
def screener_saved_delete(screener_id):
    db.delete_screener(screener_id)
    return jsonify({'ok': True, 'id': screener_id})


# ============================================================================
# Settings — data-tier badges + dashboard layout
# ============================================================================

@app.route('/api/settings/data-tier', methods=['GET'])
def settings_data_tier():
    """Report which data tiers are live based on env keys (no secrets returned)."""
    import os
    def present(key):
        return bool(os.environ.get(key, '').strip())
    tiers = [
        {"id": "free", "label": "Free (yfinance + Finnhub + SEC)", "active": True,
         "unlocks": "All panels (Flow degraded), Stock View, Console, Screener"},
        {"id": "fmp", "label": "+ FMP", "env": "FMP_API_KEY", "active": present("FMP_API_KEY"),
         "unlocks": "Real transcripts, analyst estimates, fundamentals freshness"},
        {"id": "uw", "label": "+ Unusual Whales", "env": "UNUSUAL_WHALES_API_KEY",
         "active": present("UNUSUAL_WHALES_API_KEY"),
         "unlocks": "Real unusual options blocks, dark pool prints, gamma in Flow"},
        {"id": "polygon", "label": "+ Polygon", "env": "POLYGON_API_KEY", "active": present("POLYGON_API_KEY"),
         "unlocks": "True intraday minute ticks, faster news tape"},
    ]
    optional = {
        "FINNHUB_API_KEY": present("FINNHUB_API_KEY"),
        "ANTHROPIC_API_KEY": present("ANTHROPIC_API_KEY"),
    }
    return jsonify({"tiers": tiers, "optional_keys": optional})


@app.route('/api/dashboard/layout', methods=['GET'])
def dashboard_layout_get():
    layout = db.get_dashboard_layout()
    return jsonify(layout or {"layout": None})


@app.route('/api/dashboard/layout', methods=['POST'])
def dashboard_layout_save():
    body = request.get_json(silent=True) or {}
    if 'layout' not in body:
        return jsonify({'error': 'layout required'}), 400
    db.save_dashboard_layout(body['layout'])
    return jsonify({'ok': True})


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("   Portfolio Intelligence Tool — API Server")
    print("   Running on http://localhost:5001")
    print("=" * 60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)
