#!/usr/bin/env python3
"""
db.py — SQLite database layer for the Next-Gen Portfolio Intelligence Tool.

Tables:
  - portfolio_holdings  : Robinhood/manual holdings
  - watchlist           : User-tracked tickers
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

            -- ============================================================
            -- Deep Research tables (additive — legacy tables unchanged)
            -- ============================================================

            -- Per-ticker evolving knowledge document
            CREATE TABLE IF NOT EXISTS living_memo (
                ticker          TEXT PRIMARY KEY,
                current_version INTEGER NOT NULL DEFAULT 1,
                content_md      TEXT NOT NULL,
                content_json    TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS living_memo_versions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker           TEXT NOT NULL,
                version          INTEGER NOT NULL,
                content_md       TEXT NOT NULL,
                content_json     TEXT NOT NULL,
                delta_summary    TEXT,
                source_report_id TEXT,
                user_edited      INTEGER DEFAULT 0,
                created_at       TEXT NOT NULL,
                UNIQUE(ticker, version)
            );
            CREATE INDEX IF NOT EXISTS idx_memo_versions_ticker
                ON living_memo_versions(ticker);

            CREATE TABLE IF NOT EXISTS living_memo_staged (
                ticker           TEXT PRIMARY KEY,
                content_json     TEXT NOT NULL,
                delta_summary    TEXT,
                source_report_id TEXT,
                staged_at        TEXT NOT NULL
            );

            -- Audit log: every tool call in a research session
            CREATE TABLE IF NOT EXISTS tool_call_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id       TEXT NOT NULL,
                tool_name       TEXT NOT NULL,
                args_json       TEXT,
                result_summary  TEXT,
                sources_json    TEXT,
                confidence      TEXT,
                cost_usd        REAL DEFAULT 0,
                latency_ms      INTEGER DEFAULT 0,
                cached          INTEGER DEFAULT 0,
                error           TEXT,
                called_at       TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_toollog_report
                ON tool_call_log(report_id);

            -- Recommendation calibration
            CREATE TABLE IF NOT EXISTS recommendations (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id                TEXT NOT NULL,
                ticker                   TEXT NOT NULL,
                recommendation           TEXT NOT NULL,
                conviction               TEXT NOT NULL,
                price_at_recommendation  REAL NOT NULL,
                target_low               REAL,
                target_high              REAL,
                stop_loss                REAL,
                thesis_summary           TEXT,
                what_would_change_mind   TEXT,
                created_at               TEXT NOT NULL,
                outcome_1m_return_pct    REAL,
                outcome_3m_return_pct    REAL,
                outcome_6m_return_pct    REAL,
                outcome_1y_return_pct    REAL,
                outcome_thesis_falsified INTEGER,
                outcome_updated_at       TEXT,
                outcome_notes            TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_recs_ticker
                ON recommendations(ticker);
            CREATE INDEX IF NOT EXISTS idx_recs_created
                ON recommendations(created_at);

            CREATE TABLE IF NOT EXISTS catalysts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker      TEXT NOT NULL,
                event_type  TEXT NOT NULL,
                event_date  TEXT NOT NULL,
                description TEXT,
                source      TEXT,
                created_at  TEXT NOT NULL,
                UNIQUE(ticker, event_type, event_date)
            );
            CREATE INDEX IF NOT EXISTS idx_catalysts_date
                ON catalysts(event_date);

            -- Tool-specific caches (separate tables for targeted invalidation)
            CREATE TABLE IF NOT EXISTS transcripts_cache (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker                   TEXT NOT NULL,
                quarter                  TEXT NOT NULL,
                transcript_text          TEXT,
                guidance_extracted_json  TEXT,
                kpi_mentions_json        TEXT,
                source                   TEXT,
                fetched_at               TEXT NOT NULL,
                UNIQUE(ticker, quarter)
            );

            CREATE TABLE IF NOT EXISTS insider_trades_cache (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker            TEXT NOT NULL,
                filing_date       TEXT NOT NULL,
                insider_name      TEXT,
                insider_role      TEXT,
                transaction_type  TEXT,
                shares            REAL,
                price             REAL,
                total_value       REAL,
                raw_filing_url    TEXT,
                fetched_at        TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_insider_ticker_date
                ON insider_trades_cache(ticker, filing_date);

            CREATE TABLE IF NOT EXISTS institutional_holdings_cache (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker                   TEXT NOT NULL,
                quarter                  TEXT NOT NULL,
                holder_name              TEXT NOT NULL,
                shares                   REAL,
                value_usd                REAL,
                pct_of_holder_portfolio  REAL,
                qoq_delta_shares         REAL,
                fetched_at               TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_inst_ticker_quarter
                ON institutional_holdings_cache(ticker, quarter);

            CREATE TABLE IF NOT EXISTS options_metrics_cache (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker          TEXT NOT NULL,
                snapshot_date   TEXT NOT NULL,
                iv_rank         REAL,
                iv_percentile   REAL,
                put_call_ratio  REAL,
                skew            REAL,
                unusual_json    TEXT,
                fetched_at      TEXT NOT NULL,
                UNIQUE(ticker, snapshot_date)
            );

            -- Generic per-tool cache (for tools that don't need a bespoke table)
            CREATE TABLE IF NOT EXISTS tool_result_cache (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name   TEXT NOT NULL,
                cache_key   TEXT NOT NULL,
                result_json TEXT NOT NULL,
                fetched_at  TEXT NOT NULL,
                UNIQUE(tool_name, cache_key)
            );
            CREATE INDEX IF NOT EXISTS idx_toolcache_lookup
                ON tool_result_cache(tool_name, cache_key);

            -- Sector classification cache (avoids re-classifying every research)
            CREATE TABLE IF NOT EXISTS sector_classification_cache (
                ticker       TEXT PRIMARY KEY,
                sector_key   TEXT NOT NULL,
                gics_industry TEXT,
                method       TEXT,
                classified_at TEXT NOT NULL,
                manual_override INTEGER DEFAULT 0
            );

            -- Daily monitoring digest entries
            CREATE TABLE IF NOT EXISTS monitoring_digest (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker      TEXT NOT NULL,
                digest_date TEXT NOT NULL,
                items_json  TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                UNIQUE(ticker, digest_date)
            );

            -- Per-ticker monitoring opt-in
            CREATE TABLE IF NOT EXISTS monitoring_enabled (
                ticker      TEXT PRIMARY KEY,
                enabled_at  TEXT NOT NULL
            );
        """)
        conn.commit()

        # ── Additive migrations (safe for existing DBs) ──────────────
        # SQLite has no IF NOT EXISTS on ADD COLUMN, so we check manually.
        def _column_exists(table, column):
            cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return any(c["name"] == column for c in cols)

        for col, ddl in [
            ("total_cost_usd", "REAL DEFAULT 0"),
            ("wall_clock_sec", "REAL DEFAULT 0"),
        ]:
            if not _column_exists("research_reports", col):
                conn.execute(
                    f"ALTER TABLE research_reports ADD COLUMN {col} {ddl}"
                )
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


def clear_robinhood_holdings() -> None:
    """Remove only Robinhood holdings (e.g., on session expiration)."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM portfolio_holdings WHERE source = 'robinhood'")
        conn.commit()
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
# Research Reports (full conversation storage)
# ============================================================================

def save_research_report(
    report_id: str,
    ticker: str,
    report: Dict,
    llm_conversations: List[Dict],
    llm_provider: str = "",
    llm_model: str = "",
    total_cost_usd: float = 0.0,
    wall_clock_sec: float = 0.0,
) -> None:
    """Save a full research report with all LLM conversation logs."""
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO research_reports
                (id, ticker, report_json, llm_conversations, llm_provider,
                 llm_model, total_llm_calls, generated_at, total_cost_usd, wall_clock_sec)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 report_json = excluded.report_json,
                 llm_conversations = excluded.llm_conversations,
                 total_llm_calls = excluded.total_llm_calls,
                 generated_at = excluded.generated_at,
                 total_cost_usd = excluded.total_cost_usd,
                 wall_clock_sec = excluded.wall_clock_sec""",
            (
                report_id,
                ticker.upper(),
                json.dumps(report, default=str),
                json.dumps(llm_conversations, default=str),
                llm_provider,
                llm_model,
                len(llm_conversations),
                now,
                total_cost_usd,
                wall_clock_sec,
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
            """SELECT rr.id, rr.ticker, rr.llm_provider, rr.llm_model,
                      rr.total_llm_calls, rr.generated_at, rr.version,
                      rr.total_cost_usd, rr.wall_clock_sec,
                      json_extract(rr.report_json, '$.verdict.recommendation') AS recommendation,
                      json_extract(rr.report_json, '$.verdict.conviction') AS conviction,
                      json_extract(rr.report_json, '$.verdict.target_price_range.low') AS target_low,
                      json_extract(rr.report_json, '$.verdict.target_price_range.high') AS target_high,
                      (SELECT COUNT(*) FROM tool_call_log WHERE report_id = rr.id) AS tool_call_count
               FROM research_reports rr
               WHERE rr.ticker = ?
               ORDER BY rr.generated_at DESC LIMIT ?""",
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
            """SELECT rr.id, rr.ticker, rr.llm_provider, rr.llm_model,
                      rr.total_llm_calls, rr.generated_at, rr.version,
                      rr.total_cost_usd, rr.wall_clock_sec,
                      json_extract(rr.report_json, '$.verdict.recommendation') AS recommendation,
                      json_extract(rr.report_json, '$.verdict.conviction') AS conviction,
                      json_extract(rr.report_json, '$.verdict.target_price_range.low') AS target_low,
                      json_extract(rr.report_json, '$.verdict.target_price_range.high') AS target_high,
                      (SELECT COUNT(*) FROM tool_call_log WHERE report_id = rr.id) AS tool_call_count
               FROM research_reports rr
               ORDER BY rr.generated_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_research_report(report_id: str) -> bool:
    """Delete a research report and its associated logs, recommendations, and references."""
    conn = get_connection()
    try:
        exists = conn.execute("SELECT 1 FROM research_reports WHERE id = ?", (report_id,)).fetchone()
        if not exists:
            return False
        conn.execute("DELETE FROM research_reports WHERE id = ?", (report_id,))
        conn.execute("DELETE FROM tool_call_log WHERE report_id = ?", (report_id,))
        conn.execute("DELETE FROM recommendations WHERE report_id = ?", (report_id,))
        conn.execute("UPDATE living_memo_versions SET source_report_id = NULL WHERE source_report_id = ?", (report_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def delete_research_reports(report_ids: list) -> int:
    """Delete multiple research reports and their associated logs, recommendations, and references. Returns count of deleted reports."""
    if not report_ids:
        return 0
    conn = get_connection()
    try:
        placeholders = ",".join("?" for _ in report_ids)
        count = conn.execute(f"SELECT COUNT(*) FROM research_reports WHERE id IN ({placeholders})", tuple(report_ids)).fetchone()[0]
        if count == 0:
            return 0
        conn.execute(f"DELETE FROM research_reports WHERE id IN ({placeholders})", tuple(report_ids))
        conn.execute(f"DELETE FROM tool_call_log WHERE report_id IN ({placeholders})", tuple(report_ids))
        conn.execute(f"DELETE FROM recommendations WHERE report_id IN ({placeholders})", tuple(report_ids))
        conn.execute(f"UPDATE living_memo_versions SET source_report_id = NULL WHERE source_report_id IN ({placeholders})", tuple(report_ids))
        conn.commit()
        return count
    finally:
        conn.close()


# ============================================================================
# Living Memo
# ============================================================================

def get_living_memo(ticker: str) -> Optional[Dict]:
    """Return the current Living Memo for a ticker, or None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM living_memo WHERE ticker = ?", (ticker.upper(),)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["content_json"] = json.loads(d["content_json"])
        return d
    finally:
        conn.close()


def save_living_memo(
    ticker: str,
    content_md: str,
    content_json: Dict,
    delta_summary: Optional[str] = None,
    source_report_id: Optional[str] = None,
    user_edited: bool = False,
) -> int:
    """Upsert the current memo + append a new version. Returns the new version number."""
    conn = get_connection()
    try:
        ticker = ticker.upper()
        now = datetime.now().isoformat()
        json_str = json.dumps(content_json, default=str)

        # Determine next version
        row = conn.execute(
            "SELECT current_version FROM living_memo WHERE ticker = ?", (ticker,)
        ).fetchone()
        next_version = (row["current_version"] + 1) if row else 1

        conn.execute(
            """INSERT INTO living_memo (ticker, current_version, content_md, content_json, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(ticker) DO UPDATE SET
                 current_version = excluded.current_version,
                 content_md = excluded.content_md,
                 content_json = excluded.content_json,
                 updated_at = excluded.updated_at""",
            (ticker, next_version, content_md, json_str, now),
        )
        conn.execute(
            """INSERT INTO living_memo_versions
               (ticker, version, content_md, content_json, delta_summary,
                source_report_id, user_edited, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ticker, next_version, content_md, json_str, delta_summary,
             source_report_id, 1 if user_edited else 0, now),
        )
        conn.commit()
        return next_version
    finally:
        conn.close()


def get_memo_versions(ticker: str, limit: int = 20) -> List[Dict]:
    """Return version history for a ticker (newest first)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id, ticker, version, delta_summary, source_report_id,
                      user_edited, created_at
               FROM living_memo_versions
               WHERE ticker = ?
               ORDER BY version DESC LIMIT ?""",
            (ticker.upper(), limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_memo_version(ticker: str, version: int) -> Optional[Dict]:
    """Return a specific historical memo version."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM living_memo_versions WHERE ticker = ? AND version = ?",
            (ticker.upper(), version),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["content_json"] = json.loads(d["content_json"])
        return d
    finally:
        conn.close()


# ============================================================================
# Living Memo Staging
# ============================================================================

def save_staged_memo(
    ticker: str,
    content_json: Dict,
    delta_summary: Optional[str] = None,
    source_report_id: Optional[str] = None,
) -> None:
    """Save or overwrite a staged memo in living_memo_staged."""
    conn = get_connection()
    try:
        ticker = ticker.upper()
        now = datetime.now().isoformat()
        json_str = json.dumps(content_json, default=str)
        conn.execute(
            """INSERT INTO living_memo_staged (ticker, content_json, delta_summary, source_report_id, staged_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(ticker) DO UPDATE SET
                 content_json = excluded.content_json,
                 delta_summary = excluded.delta_summary,
                 source_report_id = excluded.source_report_id,
                 staged_at = excluded.staged_at""",
            (ticker, json_str, delta_summary, source_report_id, now)
        )
        conn.commit()
    finally:
        conn.close()


def get_staged_memo(ticker: str) -> Optional[Dict]:
    """Retrieve the staged memo for a ticker, returning a dict with parsed content_json, or None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM living_memo_staged WHERE ticker = ?", (ticker.upper(),)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["content_json"] = json.loads(d["content_json"])
        return d
    finally:
        conn.close()


def delete_staged_memo(ticker: str) -> None:
    """Delete the staged memo for a ticker if it exists."""
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM living_memo_staged WHERE ticker = ?", (ticker.upper(),)
        )
        conn.commit()
    finally:
        conn.close()


# ============================================================================
# Tool call audit log
# ============================================================================

def log_tool_call(
    report_id: str,
    tool_name: str,
    args: Optional[Dict] = None,
    result_summary: str = "",
    sources: Optional[List[Dict]] = None,
    confidence: str = "medium",
    cost_usd: float = 0.0,
    latency_ms: int = 0,
    cached: bool = False,
    error: Optional[str] = None,
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO tool_call_log
               (report_id, tool_name, args_json, result_summary, sources_json,
                confidence, cost_usd, latency_ms, cached, error, called_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report_id, tool_name,
                json.dumps(args or {}, default=str),
                (result_summary or "")[:2000],
                json.dumps(sources or [], default=str),
                confidence, cost_usd, latency_ms,
                1 if cached else 0, error,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_tool_call_log(report_id: str) -> List[Dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM tool_call_log WHERE report_id = ? ORDER BY id",
            (report_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["args"] = json.loads(d.pop("args_json") or "{}")
            except Exception:
                d["args"] = {}
            try:
                d["sources"] = json.loads(d.pop("sources_json") or "[]")
            except Exception:
                d["sources"] = []
            out.append(d)
        return out
    finally:
        conn.close()


# ============================================================================
# Recommendation calibration
# ============================================================================

def save_recommendation(
    report_id: str,
    ticker: str,
    recommendation: str,
    conviction: str,
    price_at_recommendation: float,
    target_low: Optional[float] = None,
    target_high: Optional[float] = None,
    stop_loss: Optional[float] = None,
    thesis_summary: str = "",
    what_would_change_mind: str = "",
) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO recommendations
               (report_id, ticker, recommendation, conviction, price_at_recommendation,
                target_low, target_high, stop_loss, thesis_summary, what_would_change_mind,
                created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report_id, ticker.upper(), recommendation, conviction,
                price_at_recommendation, target_low, target_high, stop_loss,
                thesis_summary, what_would_change_mind,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_recommendations(ticker: Optional[str] = None, limit: int = 100) -> List[Dict]:
    conn = get_connection()
    try:
        if ticker:
            rows = conn.execute(
                "SELECT * FROM recommendations WHERE ticker = ? ORDER BY created_at DESC LIMIT ?",
                (ticker.upper(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM recommendations ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_recommendation_outcome(
    rec_id: int,
    outcome_1m: Optional[float] = None,
    outcome_3m: Optional[float] = None,
    outcome_6m: Optional[float] = None,
    outcome_1y: Optional[float] = None,
    thesis_falsified: Optional[bool] = None,
    notes: str = "",
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE recommendations SET
                 outcome_1m_return_pct = COALESCE(?, outcome_1m_return_pct),
                 outcome_3m_return_pct = COALESCE(?, outcome_3m_return_pct),
                 outcome_6m_return_pct = COALESCE(?, outcome_6m_return_pct),
                 outcome_1y_return_pct = COALESCE(?, outcome_1y_return_pct),
                 outcome_thesis_falsified = COALESCE(?, outcome_thesis_falsified),
                 outcome_updated_at = ?,
                 outcome_notes = COALESCE(NULLIF(?, ''), outcome_notes)
               WHERE id = ?""",
            (
                outcome_1m, outcome_3m, outcome_6m, outcome_1y,
                None if thesis_falsified is None else (1 if thesis_falsified else 0),
                datetime.now().isoformat(),
                notes, rec_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ============================================================================
# Catalysts
# ============================================================================

def upsert_catalyst(
    ticker: str, event_type: str, event_date: str,
    description: str = "", source: str = "",
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO catalysts
               (ticker, event_type, event_date, description, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (ticker.upper(), event_type, event_date, description, source,
             datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_catalysts(
    tickers: Optional[List[str]] = None, days_ahead: int = 90,
) -> List[Dict]:
    conn = get_connection()
    try:
        from datetime import timedelta
        now_iso = datetime.now().date().isoformat()
        end_iso = (datetime.now().date() + timedelta(days=days_ahead)).isoformat()
        if tickers:
            placeholders = ",".join("?" for _ in tickers)
            rows = conn.execute(
                f"""SELECT * FROM catalysts
                    WHERE event_date >= ? AND event_date <= ?
                      AND ticker IN ({placeholders})
                    ORDER BY event_date ASC""",
                (now_iso, end_iso, *[t.upper() for t in tickers]),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM catalysts
                   WHERE event_date >= ? AND event_date <= ?
                   ORDER BY event_date ASC""",
                (now_iso, end_iso),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ============================================================================
# Generic tool-result cache
# ============================================================================

def get_tool_cache(tool_name: str, cache_key: str, max_age_seconds: int) -> Optional[Dict]:
    """Return cached tool result if not expired."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT result_json, fetched_at FROM tool_result_cache WHERE tool_name = ? AND cache_key = ?",
            (tool_name, cache_key),
        ).fetchone()
        if not row:
            return None
        from datetime import timedelta
        fetched = datetime.fromisoformat(row["fetched_at"])
        if datetime.now() - fetched > timedelta(seconds=max_age_seconds):
            return None
        return json.loads(row["result_json"])
    finally:
        conn.close()


def save_tool_cache(tool_name: str, cache_key: str, result: Dict) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO tool_result_cache (tool_name, cache_key, result_json, fetched_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(tool_name, cache_key) DO UPDATE SET
                 result_json = excluded.result_json,
                 fetched_at = excluded.fetched_at""",
            (tool_name, cache_key, json.dumps(result, default=str),
             datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


# ============================================================================
# Sector classification cache
# ============================================================================

def get_sector_classification(ticker: str) -> Optional[Dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM sector_classification_cache WHERE ticker = ?",
            (ticker.upper(),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_sector_classification(
    ticker: str, sector_key: str, gics_industry: str = "",
    method: str = "auto", manual_override: bool = False,
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO sector_classification_cache
               (ticker, sector_key, gics_industry, method, classified_at, manual_override)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (ticker.upper(), sector_key, gics_industry, method,
             datetime.now().isoformat(), 1 if manual_override else 0),
        )
        conn.commit()
    finally:
        conn.close()


# ============================================================================
# Monitoring
# ============================================================================

def enable_monitoring(ticker: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO monitoring_enabled (ticker, enabled_at) VALUES (?, ?)""",
            (ticker.upper(), datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def disable_monitoring(ticker: str) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM monitoring_enabled WHERE ticker = ?", (ticker.upper(),))
        conn.commit()
    finally:
        conn.close()


def get_monitored_tickers() -> List[str]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT ticker FROM monitoring_enabled").fetchall()
        return [r["ticker"] for r in rows]
    finally:
        conn.close()


def save_monitoring_digest(ticker: str, digest_date: str, items: List[Dict]) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO monitoring_digest
               (ticker, digest_date, items_json, created_at)
               VALUES (?, ?, ?, ?)""",
            (ticker.upper(), digest_date, json.dumps(items, default=str),
             datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_digests(days: int = 7) -> List[Dict]:
    conn = get_connection()
    try:
        from datetime import timedelta
        cutoff = (datetime.now().date() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            "SELECT * FROM monitoring_digest WHERE digest_date >= ? ORDER BY digest_date DESC",
            (cutoff,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["items"] = json.loads(d.pop("items_json") or "[]")
            except Exception:
                d["items"] = []
            out.append(d)
        return out
    finally:
        conn.close()


# Initialize on import
init_db()
