#!/usr/bin/env python3
"""
db.py — SQLite database layer for the Next-Gen Portfolio Intelligence Tool.

Tables:
  - portfolio_holdings  : Robinhood/manual holdings
  - watchlist           : User-tracked tickers
  - alerts              : Price/change alerts
  - research_cache      : Cached AI research reports
  - llm_settings        : LLM provider configuration
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

_ANALYSIS_DIR = Path(__file__).resolve().parent

# Determine a writable home for the database.
# We try locations in preference order and pick the first that works.
# macOS sometimes sandboxes Desktop/Documents for CLI processes,
# so we fall back gracefully to the system temp directory.
def _find_db_dir() -> Path:
    candidates = [
        Path.home() / ".portfolio_intelligence",
        Path.home() / "Library" / "Application Support" / "PortfolioIntelligence",
        # System temp — always writable, stable across restarts per user session
        Path(__import__("tempfile").gettempdir()) / "portfolio_intelligence",
    ]
    import sqlite3 as _sq
    for p in candidates:
        try:
            p.mkdir(parents=True, exist_ok=True)
            test = p / ".write_test"
            conn = _sq.connect(str(p / "_test.db"))
            conn.execute("CREATE TABLE IF NOT EXISTS _t (x int)")
            conn.close()
            (p / "_test.db").unlink(missing_ok=True)
            return p
        except (PermissionError, OSError, _sq.OperationalError):
            continue
    raise RuntimeError("Could not find a writable directory for the database.")

_DB_DIR = _find_db_dir()
DB_PATH = _DB_DIR / "finance.db"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent read performance
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist. Safe to call on every startup."""
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS portfolio_holdings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker      TEXT NOT NULL,
                shares      REAL NOT NULL,
                avg_cost    REAL,
                source      TEXT DEFAULT 'manual',  -- 'robinhood' | 'manual'
                synced_at   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS watchlist (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker    TEXT NOT NULL UNIQUE,
                added_at  TEXT NOT NULL,
                notes     TEXT
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker      TEXT NOT NULL,
                condition   TEXT NOT NULL,   -- 'above' | 'below' | 'change_pct_up' | 'change_pct_down'
                threshold   REAL NOT NULL,
                is_active   INTEGER DEFAULT 1,
                is_triggered INTEGER DEFAULT 0,
                triggered_at TEXT,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS research_cache (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker        TEXT NOT NULL UNIQUE,
                report_json   TEXT NOT NULL,
                llm_provider  TEXT,
                generated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS llm_settings (
                id          INTEGER PRIMARY KEY CHECK (id = 1),  -- singleton row
                provider    TEXT DEFAULT 'ollama',   -- 'claude' | 'gemini' | 'ollama'
                model_fast  TEXT DEFAULT 'llama3.2', -- cheap/fast model name
                model_deep  TEXT DEFAULT 'llama3.2', -- best/slowest model name
                api_key     TEXT DEFAULT '',
                base_url    TEXT DEFAULT 'http://localhost:11434', -- for Ollama
                updated_at  TEXT NOT NULL
            );

            -- Insert default LLM settings if not present
            INSERT OR IGNORE INTO llm_settings (id, updated_at)
            VALUES (1, datetime('now'));

            CREATE TABLE IF NOT EXISTS research_reports (
                id              TEXT PRIMARY KEY,      -- UUID
                ticker          TEXT NOT NULL,
                report_json     TEXT NOT NULL,          -- Full report including all LLM conversations
                llm_conversations TEXT,                 -- JSON array of all LLM prompts/responses
                llm_provider    TEXT,
                llm_model       TEXT,
                total_llm_calls INTEGER DEFAULT 0,
                generated_at    TEXT NOT NULL,
                version         INTEGER DEFAULT 2       -- Schema version
            );

            CREATE INDEX IF NOT EXISTS idx_research_reports_ticker
                ON research_reports(ticker);
            CREATE INDEX IF NOT EXISTS idx_research_reports_generated
                ON research_reports(generated_at);
        """)
        conn.commit()
    finally:
        conn.close()


# ============================================================================
# Portfolio Holdings
# ============================================================================

def upsert_holdings(holdings: List[Dict]) -> None:
    """Replace all holdings with a fresh sync result.

    Args:
        holdings: List of dicts with keys: ticker, shares, avg_cost, source
    """
    conn = get_connection()
    try:
        conn.execute("DELETE FROM portfolio_holdings")
        now = datetime.now().isoformat()
        conn.executemany(
            "INSERT INTO portfolio_holdings (ticker, shares, avg_cost, source, synced_at) "
            "VALUES (:ticker, :shares, :avg_cost, :source, :synced_at)",
            [{**h, "synced_at": now} for h in holdings]
        )
        conn.commit()
    finally:
        conn.close()


def get_holdings() -> List[Dict]:
    """Return all portfolio holdings as a list of dicts."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT ticker, shares, avg_cost, source, synced_at FROM portfolio_holdings ORDER BY ticker"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def clear_holdings() -> None:
    """Remove all holdings (e.g., on disconnect)."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM portfolio_holdings")
        conn.commit()
    finally:
        conn.close()


# ============================================================================
# Watchlist
# ============================================================================

def add_to_watchlist(ticker: str, notes: str = "") -> Dict:
    """Add a ticker to the watchlist. Returns the row."""
    conn = get_connection()
    try:
        ticker = ticker.upper().strip()
        now = datetime.now().isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (ticker, added_at, notes) VALUES (?, ?, ?)",
            (ticker, now, notes)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM watchlist WHERE ticker = ?", (ticker,)).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def remove_from_watchlist(ticker: str) -> bool:
    """Remove a ticker from the watchlist. Returns True if removed."""
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_watchlist() -> List[Dict]:
    """Return all watchlist entries."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM watchlist ORDER BY added_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def is_on_watchlist(ticker: str) -> bool:
    conn = get_connection()
    try:
        row = conn.execute("SELECT 1 FROM watchlist WHERE ticker = ?", (ticker.upper(),)).fetchone()
        return row is not None
    finally:
        conn.close()


# ============================================================================
# Alerts
# ============================================================================

def create_alert(ticker: str, condition: str, threshold: float) -> Dict:
    """Create a new price alert.

    Args:
        ticker: Stock ticker (e.g. 'NVDA')
        condition: 'above' | 'below' | 'change_pct_up' | 'change_pct_down'
        threshold: Price level or % change (e.g. 150.0 or 5.0 for 5%)
    """
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        cursor = conn.execute(
            "INSERT INTO alerts (ticker, condition, threshold, created_at) VALUES (?, ?, ?, ?)",
            (ticker.upper(), condition, threshold, now)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM alerts WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def get_alerts(active_only: bool = True) -> List[Dict]:
    """Return alerts. Optionally filter to only non-triggered ones."""
    conn = get_connection()
    try:
        if active_only:
            rows = conn.execute(
                "SELECT * FROM alerts WHERE is_active = 1 AND is_triggered = 0 ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM alerts ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def mark_alert_triggered(alert_id: int) -> None:
    """Mark an alert as triggered."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE alerts SET is_triggered = 1, triggered_at = ? WHERE id = ?",
            (datetime.now().isoformat(), alert_id)
        )
        conn.commit()
    finally:
        conn.close()


def delete_alert(alert_id: int) -> bool:
    """Delete an alert by ID."""
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ============================================================================
# Research Cache
# ============================================================================

def get_research_cache(ticker: str, max_age_hours: int = 24) -> Optional[Dict]:
    """Return cached research report if not expired."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT report_json, generated_at FROM research_cache WHERE ticker = ?",
            (ticker.upper(),)
        ).fetchone()
        if not row:
            return None
        from datetime import timedelta
        generated = datetime.fromisoformat(row["generated_at"])
        if datetime.now() - generated > timedelta(hours=max_age_hours):
            return None  # Expired
        return json.loads(row["report_json"])
    finally:
        conn.close()


def save_research_cache(ticker: str, report: Dict, llm_provider: str = "") -> None:
    """Upsert a research report into the cache."""
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO research_cache (ticker, report_json, llm_provider, generated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(ticker) DO UPDATE SET
                 report_json = excluded.report_json,
                 llm_provider = excluded.llm_provider,
                 generated_at = excluded.generated_at""",
            (ticker.upper(), json.dumps(report), llm_provider, now)
        )
        conn.commit()
    finally:
        conn.close()


def clear_research_cache(ticker: Optional[str] = None) -> None:
    """Clear cache for a specific ticker, or all if ticker is None."""
    conn = get_connection()
    try:
        if ticker:
            conn.execute("DELETE FROM research_cache WHERE ticker = ?", (ticker.upper(),))
        else:
            conn.execute("DELETE FROM research_cache")
        conn.commit()
    finally:
        conn.close()


# ============================================================================
# LLM Settings
# ============================================================================

def get_llm_settings() -> Dict:
    """Return the singleton LLM settings row."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM llm_settings WHERE id = 1").fetchone()
        if row:
            d = dict(row)
            d.pop("api_key", None)  # Never return the raw key over API
            return d
        return {}
    finally:
        conn.close()


def get_llm_api_key() -> str:
    """Return the raw API key (only used internally by llm_service)."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT api_key FROM llm_settings WHERE id = 1").fetchone()
        return row["api_key"] if row else ""
    finally:
        conn.close()


def save_llm_settings(
    provider: str,
    model_fast: str,
    model_deep: str,
    api_key: str = "",
    base_url: str = "http://localhost:11434"
) -> Dict:
    """Update LLM provider settings."""
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        
        # If api_key is empty, keep the existing one
        if not api_key:
            row = conn.execute("SELECT api_key FROM llm_settings WHERE id = 1").fetchone()
            if row:
                api_key = row["api_key"]
                
        conn.execute(
            """UPDATE llm_settings SET
                 provider = ?, model_fast = ?, model_deep = ?,
                 api_key = ?, base_url = ?, updated_at = ?
               WHERE id = 1""",
            (provider, model_fast, model_deep, api_key, base_url, now)
        )
        conn.commit()
        return get_llm_settings()
    finally:
        conn.close()


# ============================================================================
# Research Reports (v2 — full conversation storage)
# ============================================================================

def save_research_report(
    report_id: str,
    ticker: str,
    report: Dict,
    llm_conversations: List[Dict],
    llm_provider: str = "",
    llm_model: str = "",
) -> None:
    """Save a full research report with all LLM conversation logs."""
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO research_reports
                (id, ticker, report_json, llm_conversations, llm_provider,
                 llm_model, total_llm_calls, generated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 report_json = excluded.report_json,
                 llm_conversations = excluded.llm_conversations,
                 total_llm_calls = excluded.total_llm_calls,
                 generated_at = excluded.generated_at""",
            (
                report_id,
                ticker.upper(),
                json.dumps(report, default=str),
                json.dumps(llm_conversations, default=str),
                llm_provider,
                llm_model,
                len(llm_conversations),
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_research_report(report_id: str) -> Optional[Dict]:
    """Retrieve a single research report by ID."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM research_reports WHERE id = ?", (report_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["report"] = json.loads(d.pop("report_json"))
        d["llm_conversations"] = json.loads(d["llm_conversations"] or "[]")
        return d
    finally:
        conn.close()


def get_research_reports_for_ticker(
    ticker: str, limit: int = 10
) -> List[Dict]:
    """Return recent research reports for a ticker (newest first)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, ticker, llm_provider, llm_model, total_llm_calls, "
            "generated_at, version FROM research_reports "
            "WHERE ticker = ? ORDER BY generated_at DESC LIMIT ?",
            (ticker.upper(), limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_research_reports(limit: int = 50) -> List[Dict]:
    """Return the most recent research reports across all tickers."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, ticker, llm_provider, llm_model, total_llm_calls, "
            "generated_at, version FROM research_reports "
            "ORDER BY generated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# Initialize on import
init_db()
