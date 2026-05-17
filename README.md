# Portfolio Intelligence Tool

> An AI-powered investment research platform combining real portfolio tracking, institutional-grade analysis, and multi-provider LLM synthesis — built for individual investors who want Bloomberg Terminal capabilities without the $24,000/year price tag.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Running the App](#running-the-app)
- [User Flows](#user-flows)
  - [Portfolio Management](#1-portfolio-management)
  - [Deep Research](#2-deep-research)
  - [Portfolio Rebalancing](#3-portfolio-rebalancing)
  - [Watchlist](#4-watchlist)
  - [Price Alerts](#5-price-alerts)
  - [S&P 500 Market Scanner](#6-sp500-market-scanner)
  - [LLM Settings](#7-llm-settings)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [LLM Configuration](#llm-configuration)
- [CLI Usage](#cli-usage)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)

---

## Overview

This tool started as a passive S&P 500 viewer and evolved into a full portfolio intelligence platform. It connects to your real brokerage (Robinhood), runs deep multi-layer AI research on any US stock or ETF, and delivers concrete, actionable portfolio decisions — not just data dumps.

**Three things it does that most tools don't:**

1. **3-pass adversarial AI thesis** — Bull case → Bear case → Balanced synthesis, so you see both sides before acting.
2. **Real-time SSE streaming** — Research stages appear as they complete, Perplexity-style, so you're never staring at a spinner.
3. **Institutional data for free** — SEC EDGAR 10-K/10-Q filings, Finnhub analyst ratings, Reddit sentiment, and 11 technical chart patterns, all stitched together by an LLM.

---

## Features

| Feature | Description |
|---------|-------------|
| **Portfolio Sync** | Connect Robinhood via OAuth + OTP, or import a CSV. Live P&L, cost basis, and allocation weights. |
| **Deep Research** | 8-stage pipeline: fundamentals → financial trends → DCF valuation → technicals → risk sizing → sentiment → SEC filings → AI thesis. |
| **Streaming Research** | Server-Sent Events (SSE) deliver each stage in real time as it completes. |
| **Research History** | Every report is saved permanently with full LLM conversation logs for audit and replay. |
| **Portfolio Rebalancing** | Compare current allocation against Conservative / Moderate / Aggressive risk profiles. Get specific TRIM / ADD / REVIEW actions. |
| **Watchlist** | Save tickers with notes. One-click to launch deep research from any watchlist entry. |
| **Price Alerts** | Set price-above, price-below, or % change thresholds. Background daemon polls every 60 seconds. |
| **S&P 500 Scanner** | Browse all 500 companies, filter by sector and metrics, detect 11 chart patterns with confidence scores. |
| **Multi-Provider LLM** | Plug in Google Gemini, Anthropic Claude, or a local Ollama model. Cost-optimized routing uses cheap models for quick tasks and expensive models for deep analysis. |
| **Sentiment Scoring** | Composite 0–10 score from news (Finnhub), analyst ratings, Reddit WSB/r/investing, and yfinance fallback. |
| **SEC EDGAR Integration** | Pulls 10-K and 10-Q filings directly from the SEC API. Extracts Business, Risk Factors, and MD&A sections, then summarizes each with the LLM. |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    REACT FRONTEND (Vite)                        │
│  Dark terminal aesthetic · Recharts · SSE streaming             │
│                                                                 │
│  Portfolio │ Deep Research │ Watchlist │ Rebalance │ Alerts     │
│  S&P 500 Market │ Research History │ LLM Settings               │
└──────────────────────────┬──────────────────────────────────────┘
                           │  REST API + SSE  (port 5173 → 5001)
┌──────────────────────────▼──────────────────────────────────────┐
│                    FLASK BACKEND  (app.py)                      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  AI ANALYSIS ENGINE                     │   │
│  │                                                         │   │
│  │  Fundamentals    Technicals      Sentiment              │   │
│  │  (yfinance)      (11 patterns)   (News + Reddit)        │   │
│  │       │               │               │                 │   │
│  │       └───────────────┴───────────────┘                 │   │
│  │                       │                                 │   │
│  │           ┌───────────▼──────────┐                      │   │
│  │           │   LLM Synthesizer    │                      │   │
│  │           │  Gemini / Claude /   │                      │   │
│  │           │  Ollama (local)      │                      │   │
│  │           └──────────────────────┘                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  DATA LAYER                                             │   │
│  │  SQLite (finance.db)  ·  JSON Cache (.cache/)           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  BACKGROUND DAEMON  (alert_worker.py)                   │   │
│  │  Price polling every 60s · Trigger recording            │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                  EXTERNAL DATA SOURCES                          │
│                                                                 │
│  Robinhood (robin_stocks)    yfinance (prices + fundamentals)   │
│  Finnhub (news + ratings)    SEC EDGAR (10-K / 10-Q)            │
│  Reddit praw (WSB sentiment) Wikipedia (S&P 500 list)           │
│  Google Gemini / Anthropic Claude / Ollama (LLM)                │
└─────────────────────────────────────────────────────────────────┘
```

### Backend Modules

| Module | Responsibility |
|--------|---------------|
| `app.py` | Flask REST API — all routes, CORS, request handling |
| `db.py` | SQLite abstraction — schema init, CRUD for all tables |
| `portfolio_service.py` | Robinhood OAuth, CSV import, live P&L enrichment |
| `research_engine.py` | Fundamentals, technicals, DCF valuation, position sizing |
| `research_stream.py` | SSE streaming pipeline — yields events as each stage completes |
| `llm_service.py` | Multi-provider LLM abstraction (Claude / Gemini / Ollama) |
| `rebalancing_engine.py` | Risk profile comparison, TRIM/ADD/REVIEW action generation |
| `sentiment_service.py` | Composite sentiment scoring (news + analyst + Reddit) |
| `edgar_service.py` | SEC EDGAR filing fetcher and LLM summarizer |
| `alert_worker.py` | Background daemon — price polling and alert triggering |
| `companies.py` | S&P 500 data fetcher (CLI + cache layer) |

### Deep Research Pipeline (8 Stages)

```
Ticker Input
    │
    ├─ 1. Fundamentals      P/E, revenue, margins, EPS, balance sheet (yfinance)
    ├─ 2. Financial Trends  8–12 quarters of revenue/margin/FCF trajectory
    ├─ 3. Valuation         DCF intrinsic value + peer comparison
    ├─ 4. Technicals        RSI, MACD, Bollinger Bands, 11 chart patterns
    ├─ 5. Risk Management   Kelly Criterion position sizing, stop-loss levels
    ├─ 6. Sentiment         News (40%) + Analyst ratings (35%) + Reddit (15%) + fallback (10%)
    ├─ 7. SEC EDGAR         10-K/10-Q → Business / Risk Factors / MD&A → LLM summary
    └─ 8. AI Thesis         3-pass adversarial: Bull → Bear → Balanced synthesis
                            Output: BUY/HOLD/TRIM/AVOID · conviction · target price range
```

Each stage streams to the frontend via SSE as it completes. The full report is saved permanently with LLM conversation logs.

---

## Tech Stack

### Backend
- **Python 3.8+**
- **Flask 3.0** + Flask-CORS
- **SQLite** with WAL mode (auto-migrating schema)
- **pandas** + **numpy** (data manipulation)
- **yfinance** (stock prices, fundamentals, history)
- **robin_stocks** (Robinhood unofficial API)
- **praw** (Reddit API client)
- **requests** (HTTP client for EDGAR, Finnhub)

### LLM Providers
- **Google Gemini** — `gemini-2.0-flash` (fast), `gemini-2.5-pro` (deep)
- **Anthropic Claude** — `claude-3-5-haiku` (fast), `claude-opus-4` (deep)
- **Ollama** (local) — `llama3.2`, `mistral`, any locally pulled model

### Frontend
- **React 19** + **Vite 7**
- **Recharts 3** (charts and visualizations)
- **Vanilla CSS** (dark terminal theme, glassmorphism cards)
- **EventSource API** (SSE streaming)

### External APIs (all free tier)
- **Finnhub** — news sentiment, analyst ratings (60 req/min free)
- **SEC EDGAR** — 10-K/10-Q filings (no key required)
- **Reddit API** — WSB + r/investing sentiment (free tier)
- **Wikipedia** — S&P 500 company list (free)

---

## Getting Started

### Prerequisites

- **Python 3.8+** — `python3 --version`
- **Node.js 18+** — `node --version`
- **pip3** — `pip3 --version`
- At least one LLM API key (Gemini, Claude) **or** a local [Ollama](https://ollama.ai) installation

### Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd analysis

# 2. Install Python dependencies
pip3 install -r requirements.txt

# 3. Install frontend dependencies
cd web
npm install
cd ..
```

### Environment Variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and configure:

```env
# ── LLM Provider (choose ONE) ──────────────────────────────────

# Anthropic Claude — https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini — https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=AIza...

# Ollama (local, no key needed) — https://ollama.ai
OLLAMA_BASE_URL=http://localhost:11434

# ── News & Sentiment ───────────────────────────────────────────

# Finnhub — free tier, 60 req/min — https://finnhub.io
FINNHUB_API_KEY=...

# Reddit API — https://www.reddit.com/prefs/apps (type: "script")
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=PortfolioIntelligence/1.0

# ── SEC EDGAR (no key needed, just your contact info) ──────────
EDGAR_USER_AGENT=YourName your@email.com
```

**Minimum required:** one LLM key (or Ollama running locally). Everything else is optional — the app degrades gracefully when keys are missing.

### Running the App

**Option A — One command (recommended):**

```bash
cd analysis
bash start.sh
```

This starts both services and prints their URLs. Press `Ctrl+C` to stop both.

**Option B — Manual (two terminals):**

```bash
# Terminal 1 — Flask API
cd analysis
python3 app.py

# Terminal 2 — React frontend
cd analysis/web
npm run dev
```

**Access:**
- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend API: [http://localhost:5001/api](http://localhost:5001/api)

---

## User Flows

### 1. Portfolio Management

**Connect Robinhood:**
1. Navigate to the **Portfolio** page.
2. Enter your Robinhood email, password, and the OTP from your authenticator app.
3. Click **Connect** — the session is cached for 24 hours (no password stored).
4. Click **Sync** to pull your latest holdings.

**Manual CSV Import:**
1. On the Portfolio page, click **Import CSV**.
2. Upload a file with the format:
   ```
   ticker,shares,avg_cost
   AAPL,10,145.50
   NVDA,5,480.00
   ```
3. Holdings are enriched with live prices and P&L automatically.

**What you see:**
- Total portfolio value, total P&L, cost basis
- Per-holding: current price, unrealized P&L, portfolio weight %
- Sector allocation breakdown

---

### 2. Deep Research

1. Navigate to **Deep Research**.
2. Enter any US ticker (stock or ETF) in the search bar.
3. Click **Research** — the 8-stage pipeline starts streaming immediately.
4. Watch each stage appear in real time:
   - Fundamentals, financial trends, valuation, technicals, risk sizing, sentiment, SEC filing, AI thesis
5. The final thesis shows: **BUY / HOLD / TRIM / AVOID**, conviction level, target price range, bull case, bear case, key catalysts, and action items.
6. Reports are saved to **Research History** automatically.

**Tip:** Add `?refresh=true` to bypass the 24-hour cache and force a fresh analysis.

**Compare mode:** Enter multiple tickers (comma-separated) to get a side-by-side LLM comparison.

---

### 3. Portfolio Rebalancing

1. Navigate to **Rebalance**.
2. Select your risk profile: **Conservative**, **Moderate**, or **Aggressive**.

| Profile | Max Single Position | Max Sector | Min Positions |
|---------|--------------------|-----------:|:-------------:|
| Conservative | 10% | 25% | 15 |
| Moderate | 15% | 35% | 10 |
| Aggressive | 25% | 50% | 5 |

3. The engine compares your current allocation against the profile limits.
4. You receive a prioritized action list:
   - **TRIM** — position is overweight, reduce it
   - **ADD** — position or sector is underweight
   - **REVIEW** — position needs attention (concentration risk, etc.)

---

### 4. Watchlist

1. Navigate to **Watchlist**.
2. Search for a ticker and click **Add** — optionally add a note.
3. Your watchlist shows all saved tickers with their current prices.
4. Click the **🔬 Research** icon on any entry to instantly launch Deep Research for that ticker.
5. Remove tickers with the **✕** button.

---

### 5. Price Alerts

1. Navigate to **Alerts**.
2. Click **New Alert** and configure:
   - **Ticker** — any US stock or ETF
   - **Condition** — Price Above / Price Below / % Change Up / % Change Down
   - **Threshold** — the target value
3. The background daemon (`alert_worker.py`) polls prices every 60 seconds.
4. When triggered, the alert is marked in the database and highlighted in the UI.
5. Delete alerts with the **✕** button.

---

### 6. S&P 500 Market Scanner

1. Navigate to **Market**.
2. Browse all 500 companies sorted by Forward P/E (default) or any metric.
3. Filter by sector using the sidebar.
4. Click any company to see detailed metrics, price history, and financial trends.
5. Use the **Patterns** tab to scan for technical chart patterns:
   - Head & Shoulders, Inverse H&S
   - Double Top / Double Bottom
   - Triple Top / Triple Bottom
   - Ascending / Descending Triangle
   - Cup & Handle, Bullish Flag, Falling Wedge
6. The **Spotlight** section surfaces curated categories: Growth, Value, Momentum, Quality, Dividend.

**Force refresh:** Click **Refresh Data** to bypass the 12-hour cache and fetch fresh data from yfinance.

---

### 7. LLM Settings

1. Navigate to **Settings**.
2. Select your LLM provider: **Gemini**, **Claude**, or **Ollama**.
3. Enter your API key (or Ollama base URL for local models).
4. Configure fast model (used for sentiment/summaries) and deep model (used for thesis/analysis).
5. Click **Test Connection** to verify the setup before running research.

**Cost routing logic:**
- Fast tasks (sentiment scoring, quick summaries) → `model_fast`
- Deep tasks (investment thesis, EDGAR analysis, portfolio rebalancing) → `model_deep`

---

## API Reference

All endpoints are prefixed with `/api` and served on port `5001`.

### Portfolio

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/portfolio/connect` | Robinhood OAuth + OTP authentication |
| `POST` | `/api/portfolio/disconnect` | Logout and clear session |
| `POST` | `/api/portfolio/sync` | Fetch latest holdings from Robinhood |
| `POST` | `/api/portfolio/import` | Import holdings from CSV |
| `GET` | `/api/portfolio/holdings` | Current holdings with live P&L |
| `GET` | `/api/portfolio/summary` | Portfolio-level stats (total value, P&L, etc.) |
| `GET` | `/api/portfolio/status` | Connection status and holdings count |

### Research

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/research/<ticker>` | Full deep research report (cached 24h) |
| `GET` | `/api/research/<ticker>/stream` | SSE stream — stages delivered in real time |
| `GET` | `/api/research/reports` | All saved research reports (paginated) |
| `GET` | `/api/research/reports/<ticker>` | Research history for a specific ticker |
| `GET` | `/api/research/report/<report_id>` | Single report with full LLM conversation logs |
| `POST` | `/api/research/compare` | Compare multiple tickers side-by-side |

Add `?refresh=true` to the research endpoint to bypass the cache.

### Rebalancing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/rebalance?profile=moderate` | Rebalancing analysis for a risk profile |

### Watchlist

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/watchlist` | All watched tickers |
| `POST` | `/api/watchlist` | Add a ticker (body: `{ ticker, notes }`) |
| `DELETE` | `/api/watchlist/<ticker>` | Remove a ticker |

### Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/alerts` | All alerts (active and triggered) |
| `POST` | `/api/alerts` | Create alert (body: `{ ticker, condition, threshold }`) |
| `DELETE` | `/api/alerts/<id>` | Delete an alert |

Conditions: `above` · `below` · `change_pct_up` · `change_pct_down`

### LLM Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/settings/llm` | Current LLM configuration |
| `POST` | `/api/settings/llm` | Update provider, models, and API key |
| `POST` | `/api/settings/llm/test` | Test LLM connection |

### S&P 500 (Legacy)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/companies` | All S&P 500 companies (sortable via `?sort_by=&order=`) |
| `GET` | `/api/sectors` | Sector list with aggregate stats |
| `GET` | `/api/companies/<sector>` | Companies filtered by sector |
| `GET` | `/api/company/<ticker>` | Single company detail |
| `GET` | `/api/company/<ticker>/history` | 5-year price history (cached 4h) |
| `GET` | `/api/company/<ticker>/financials` | Quarterly/annual financials (cached 24h) |
| `GET` | `/api/patterns/head-shoulders` | Head & Shoulders scan across all S&P 500 |
| `GET` | `/api/patterns/<pattern>/<ticker>` | Pattern analysis for a specific ticker |
| `GET` | `/api/stats` | Summary statistics |
| `GET` | `/api/search?q=<query>` | Search by ticker or company name |
| `POST` | `/api/refresh` | Force fresh data fetch (bypasses cache) |
| `GET` | `/api/spotlight` | Curated spotlight categories |
| `GET` | `/api/health` | Health check |

---

## Database Schema

The SQLite database is stored at `~/.portfolio_intelligence/finance.db` (falls back to `~/Library/Application Support/PortfolioIntelligence/` or the system temp directory if the primary location is not writable).

```sql
-- Portfolio holdings (Robinhood or manual)
portfolio_holdings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT NOT NULL,
    shares      REAL NOT NULL,
    avg_cost    REAL,
    source      TEXT DEFAULT 'manual',   -- 'robinhood' | 'manual'
    synced_at   TEXT NOT NULL
)

-- User watchlist
watchlist (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker    TEXT NOT NULL UNIQUE,
    added_at  TEXT NOT NULL,
    notes     TEXT
)

-- Price and change alerts
alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker       TEXT NOT NULL,
    condition    TEXT NOT NULL,           -- 'above' | 'below' | 'change_pct_up' | 'change_pct_down'
    threshold    REAL NOT NULL,
    is_active    INTEGER DEFAULT 1,
    is_triggered INTEGER DEFAULT 0,
    triggered_at TEXT,
    created_at   TEXT NOT NULL
)

-- Research reports (v2 — permanent, with LLM logs)
research_reports (
    id                TEXT PRIMARY KEY,   -- UUID
    ticker            TEXT NOT NULL,
    report_json       TEXT NOT NULL,      -- Full JSON report
    llm_conversations TEXT,              -- JSON array of every LLM call
    llm_provider      TEXT,
    llm_model         TEXT,
    total_llm_calls   INTEGER DEFAULT 0,
    generated_at      TEXT NOT NULL,
    version           INTEGER DEFAULT 2
)

-- LLM provider configuration (singleton row, id=1)
llm_settings (
    id         INTEGER PRIMARY KEY DEFAULT 1,
    provider   TEXT NOT NULL DEFAULT 'ollama',
    model_fast TEXT NOT NULL DEFAULT 'llama3.2',
    model_deep TEXT NOT NULL DEFAULT 'llama3.2',
    api_key    TEXT DEFAULT '',
    base_url   TEXT DEFAULT 'http://localhost:11434',
    updated_at TEXT NOT NULL
)
```

---

## LLM Configuration

The tool supports three providers. You can switch between them at any time from the **Settings** page without restarting the server.

### Google Gemini (recommended for quality/cost balance)

1. Get a free API key at [aistudio.google.com](https://aistudio.google.com/app/apikey)
2. Set `GOOGLE_API_KEY` in `.env` or enter it in Settings
3. Suggested models:
   - Fast: `gemini-2.0-flash`
   - Deep: `gemini-2.5-pro`

### Anthropic Claude (best quality)

1. Get an API key at [console.anthropic.com](https://console.anthropic.com/)
2. Set `ANTHROPIC_API_KEY` in `.env` or enter it in Settings
3. Suggested models:
   - Fast: `claude-3-5-haiku-20241022`
   - Deep: `claude-opus-4-5`

### Ollama (local, no cost)

1. Install Ollama: [ollama.ai](https://ollama.ai)
2. Pull a model: `ollama pull llama3.2`
3. Ensure Ollama is running: `ollama serve`
4. Set `OLLAMA_BASE_URL=http://localhost:11434` in `.env`
5. Suggested models:
   - Fast: `llama3.2` (3B, fast)
   - Deep: `mistral` or `llama3.1:8b` (better reasoning)

**Cost routing:** The tool automatically routes cheap/fast tasks (sentiment scoring, quick summaries) to `model_fast` and expensive deep tasks (investment thesis, EDGAR analysis, rebalancing recommendations) to `model_deep`. This keeps costs low while maintaining quality where it matters.

---

## CLI Usage

The `companies.py` script can be run standalone for S&P 500 data fetching and CSV export, without starting the web server.

```bash
cd analysis

# Standard run (uses 12-hour cache if available)
python3 companies.py

# Force fresh data fetch from yfinance
python3 companies.py --no-cache
```

**Output files:**
- `sp500_analysis.csv` — Full metrics export for all 500 companies
- `.cache/sp500_data.json` — Internal cache (12-hour expiry)

**Configuration constants** (edit in `companies.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_EXPIRY_HOURS` | `12` | Hours before cache expires |
| `MAX_WORKERS` | `5` | Parallel request threads |
| `REQUEST_DELAY` | `0.2s` | Delay between API calls |
| `MAX_RETRIES` | `3` | Retry attempts on failure |
| `BACKOFF_FACTOR` | `2` | Exponential backoff multiplier |

---

## Project Structure

```
analysis/
├── app.py                  # Flask REST API — all routes
├── db.py                   # SQLite abstraction layer
├── portfolio_service.py    # Robinhood + CSV portfolio ingestion
├── research_engine.py      # Fundamentals, technicals, DCF, position sizing
├── research_stream.py      # SSE streaming research pipeline
├── llm_service.py          # Multi-provider LLM abstraction
├── rebalancing_engine.py   # Risk profile comparison + action generation
├── sentiment_service.py    # Composite sentiment scoring
├── edgar_service.py        # SEC EDGAR filing fetcher + summarizer
├── alert_worker.py         # Background price polling daemon
├── companies.py            # S&P 500 data fetcher (CLI)
├── requirements.txt        # Python dependencies
├── start.sh                # One-command launcher (Flask + Vite)
├── .env.example            # Environment variable template
├── .cache/                 # JSON cache (auto-created)
│   ├── sp500_data.json
│   └── latest_prices.json
├── docs/
│   ├── spec.md             # Original S&P 500 tool spec
│   └── next_gen_tool.md    # Next-gen portfolio tool spec
└── web/                    # React frontend
    ├── src/
    │   ├── App.jsx          # Root component + routing
    │   ├── components/      # Reusable UI components
    │   │   ├── Dashboard.jsx
    │   │   ├── CompanyTable.jsx
    │   │   ├── CompanyDetail.jsx
    │   │   ├── ResearchStream.jsx
    │   │   ├── MetricsPanel.jsx
    │   │   ├── SectorChart.jsx
    │   │   ├── AllocationChart.jsx
    │   │   ├── FinancialTrendsChart.jsx
    │   │   ├── TechnicalPatternsDashboard.jsx
    │   │   ├── HeadShouldersDashboard.jsx
    │   │   ├── SpotlightDashboard.jsx
    │   │   ├── PatternVisualization.jsx
    │   │   ├── ValuationCard.jsx
    │   │   ├── RiskCard.jsx
    │   │   ├── SearchBar.jsx
    │   │   └── Sidebar.jsx
    │   ├── pages/           # Top-level page components
    │   │   ├── PortfolioPage.jsx
    │   │   ├── DeepResearchPage.jsx
    │   │   ├── ResearchPage.jsx
    │   │   ├── ResearchHistoryPage.jsx
    │   │   ├── WatchlistPage.jsx
    │   │   ├── RebalancePage.jsx
    │   │   ├── AlertsPage.jsx
    │   │   ├── MarketPage.jsx
    │   │   └── LLMSettingsPage.jsx
    │   └── utils/
    │       └── api.js       # Unified API client
    ├── package.json
    └── vite.config.js
```

---

## Roadmap

These are planned for future phases:

- **Push Notifications** — Email/SMS alerts via Twilio or SendGrid when price thresholds are hit
- **Options Flow** — Unusual options activity detection and tracking
- **Portfolio Backtesting** — Test rebalancing strategies against historical data
- **Macro Indicators** — Fed rate, CPI, yield curve integration into thesis generation
- **Voice Interface** — Whisper STT + LLM for hands-free research queries
- **Trade Execution** — Direct broker API integration for one-click rebalancing
- **Custom LLM Fine-tuning** — Train on your own historical trades and notes

---

## Notes

- The Robinhood integration uses the unofficial `robin_stocks` library. Robinhood does not provide an official public API, so this may break if Robinhood changes their authentication flow.
- SEC EDGAR requests require a descriptive `User-Agent` header per [SEC developer guidelines](https://www.sec.gov/developer). Set `EDGAR_USER_AGENT` in your `.env` to your name and email.
- yfinance is an unofficial Yahoo Finance client. Data is generally reliable but not guaranteed for production trading decisions.
- All LLM-generated content (investment theses, recommendations) is for informational purposes only and does not constitute financial advice.
