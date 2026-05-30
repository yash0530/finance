# Edge Personal Markets Terminal (v3)

> A Bloomberg-style, pull-based personal investment terminal combining real-time candlestick charts, technical indicator overlays, multi-agent debate research, saved screeners, and on-demand AI quick takes — built for individual investors who want institutional-grade markets capabilities.

---

## Current Navigation Pages (Edge v3)

The terminal is structured as a streamlined, dark-theme single-page cockpit with 6 core sections:

1. **Terminal**: The central dashboard displaying Movers (gainers/losers), Watchlists, Theme Heatmaps, Catalysts, and dynamic AI Hypotheses.
2. **Stock View**: A single-ticker cock-pit displaying interactive candlestick charts, server-computed indicators (MA20, MA50, Bollinger, VWAP, RSI, MACD), fundamentals, insider/institutional flow, filings, and theme context.
3. **Console**: A robust slash-command interface (`/thesis`, `/dossier`, `/why`, `/theme`, `/compare`) that drives live streaming agentic reasoning and parallel comparative research.
4. **Library**: A versioned knowledge archive of previous Deep Research reports, Living Memos, and trade decisions.
5. **Screener**: A rule-based scanner executing boolean filters and multi-variable logic over cached technical and fundamental metrics, gracefully handling partial data.
6. **Settings**: A unified panel managing LLM providers (Google Gemini, Anthropic Claude, Ollama), Smart Cost Routing, data-tier badges, and theme pack configurations.

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    REACT FRONTEND (Vite)                        │
│  Dark terminal aesthetic · Glassmorphism · SSE Streaming         │
│                                                                 │
│   Terminal  │  Stock View  │  Console  │  Library  │ Screener   │
└──────────────────────────┬──────────────────────────────────────┘
                           │  REST API + SSE  (port 5173 → 5001)
┌──────────────────────────▼──────────────────────────────────────┐
│                    FLASK BACKEND  (app.py)                      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  v3 CONSOLE ORCHESTRATOR  (console_orchestrator.py)     │   │
│  │  Parses /thesis, /dossier, /why, /theme, /compare commands│   │
│  └─────────────────────────────────────────────────────────┘   │
│  │  v3 AGENTIC DEBATE ENGINE  (agent_loop.py)              │   │
│  │  Planner ──► Tool calls (parallel) ──► Re-plan          │   │
│  │  Bull ──► Bear ──► Judge ──► Self-Critique              │   │
│  └─────────────────────────────────────────────────────────┘   │
│  │  DATA LAYER                                             │   │
│  │  SQLite (WAL mode) at ~/.portfolio_intelligence/        │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                  EXTERNAL DATA INTEGRATIONS                     │
│  yfinance (candlesticks, fundamentals, 13F holdings)            │
│  Finnhub (market news)  ·  SEC EDGAR (10-K, 10-Q, Form 4 flow)  │
│  Financial Modeling Prep (FMP) (transcripts, optional)          │
│  Unusual Whales (options block flow, optional)                  │
│  Polygon.io (intraday ticks, optional)                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Command Bar Suite (Console)

The command line supports powerful on-demand analysis via slash commands:

* **`/thesis <T>`**: Runs a standard agentic debate cycle (~$0.60, 4 rounds). Returns bull/bear cases and a Judge trade recommendation.
* **`/dossier <T>`**: Launches a deeper research run (~$2.00) including SEC EDGAR transcript extraction and extensive peer analytics.
* **`/why <T>`**: Generates a quick 3-sentence on-demand read (~$0.05) using current indicators, cached 4 hours.
* **`/theme <slug>`**: Aggregates constituent indicators and generates a cohesive theme-level investment argument and risk summary.
* **`/compare <A> <B>...`**: Spawns parallel quick deep research runs for up to 5 tickers, generating a comparative score ranking and winner verdict.

---

## Tool Registry (17 Tools)

The Planner agent dynamically loads and invokes specialized data tools:

1. `fundamentals`: Key metrics, market cap, margin structures.
2. `financial_trends`: Standard multi-quarter growth rates.
3. `technicals`: Price volatility, crosses, RSI, and MACD.
4. `dcf_valuation`: Discounted cash flow intrinsic calculations.
5. `sentiment`: Composite market news and rating sentiments.
6. `edgar_filings`: SEC Form 10-K/10-Q extraction.
7. `qoe_forensics`: Quality-of-Earnings accounting forensics.
8. `macro_context`: Core interest rate and indices spreads.
9. `insider_form4`: SEC insider trading flow.
10. `institutional_13f`: Form 13F major holder positions.
11. `options_flow`: Unusual block flows and puts/calls chains.
12. `transcripts`: Earnings call transcript snippets (FMP).
13. `catalyst_lookup`: Calendar catalysts and macro dates.
14. `peer_compare`: Sector average cohorts evaluations.
15. `alt_data`: Google Trends tracking (optional).
16. `memo_read`: Living Memo sections retrieval.
17. `calibration_lookup`: Past recommendation entries lookup.

---

## Getting Started

### 1. Installation

```bash
# Clone the repository
git clone <repo-url>
cd finance

# Install Python requirements
cd analysis
pip3 install -r requirements.txt

# Install React dependencies
cd web
npm install
```

### 2. Configuration (`.env`)

Configure your keys in `analysis/.env`:

```env
# Anthropic API Key (Claude)
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini API Key
GOOGLE_API_KEY=AIza...

# Local Ollama URL
OLLAMA_BASE_URL=http://localhost:11434

# Optional Paid Integrations
FINNHUB_API_KEY=...
FMP_API_KEY=...
UNUSUAL_WHALES_API_KEY=...
POLYGON_API_KEY=...
```

### 3. Launching

Run the unified start script to spin up the Flask backend on `:5001` and Vite development server on `:5173`:

```bash
cd analysis
bash start.sh
```

---

## Testing

Ensure the application is robust using the full test suites:

* **Backend Unit & Integration Tests**:
  ```bash
  cd analysis
  python3 -m pytest tests/
  ```
* **Frontend E2E Browser Tests (Playwright)**:
  ```bash
  cd analysis/web
  npx playwright test
  ```
