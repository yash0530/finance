# 🌐 Next-Gen AI Portfolio Intelligence Tool

[![Status: Production](https://img.shields.io/badge/Status-Operational%20v1.0-emerald?style=for-the-badge)](https://github.com/yash0530/finance)
[![Backend: Flask & SQLite](https://img.shields.io/badge/Backend-Flask%20%26%20SQLite-blue?style=for-the-badge)](https://flask.palletsprojects.com/)
[![Frontend: React & Recharts](https://img.shields.io/badge/Frontend-React%20%26%20Recharts-cyan?style=for-the-badge)](https://react.dev/)
[![AI Engine: Gemini / Claude / Ollama](https://img.shields.io/badge/AI%20Engine-Gemini%20%2F%20Claude%20%2F%20Ollama-violet?style=for-the-badge)](https://ai.google.dev/)

An institutional-grade **AI Portfolio Intelligence & Research Terminal** built to bridge the gap between passive market tracking and active, data-driven portfolio management. Designed as a unified Bloomberg-style hub, it connects directly to your live portfolio (Robinhood or CSV), runs automated high-fidelity analysis (fundamentals, technical patterns, Reddit/news sentiment, SEC EDGAR filings), and delivers **concrete, actionable investment theses** via custom LLM synthesis.

---

## 🗺️ Architectural Topology & Data Flow

Below is the complete orchestration architecture of the terminal, detailing how frontend pages, service layers, multithreaded workers, and third-party data providers interact in real-time.

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                    CLIENT INTERFACE                     │
                  │   React + Vite (Modern Dark Terminal Grid, Recharts,    │
                  │         SSE Streaming Views, Framer Motion)             │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               │ REST API / SSE (Server-Sent Events)
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │                 FLASK BACKEND GATEWAY                   │
                  │              (Flask Application: app.py)                │
                  └──────┬─────────────────────┬─────────────────────┬──────┘
                         │                     │                     │
      ┌──────────────────▼──┐           ┌──────▼────────────┐  ┌─────▼──────────────┐
      │  PORTFOLIO ROUTER   │           │  RESEARCH ROUTER  │  │ ALERTS & WATCHLIST │
      │  (portfolio_svc)    │           │ (research_engine) │  │      ROUTER        │
      └──────────┬──────────┘           └──────────┬────────┘  └──────────┬─────────┘
                 │                                 │                      │
 ┌───────────────┼─────────────────────────────────┼──────────────────────┼─────────────┐
 │ SERVICES & DAEMONS LAYER                        │                      │             │
 │                                                 │                      │             │
 │  ┌────────────▼──────────────┐        ┌─────────▼───────────┐    ┌─────▼──────────┐  │
 │  │      Portfolio Ingestion  │        │   Deep Research     │    │ Alert Worker   │  │
 │  │     - Robinhood OAuth/MFA │        │   Orchestrator      │    │ Background     │  │
 │  │     - CSV Import Parser   │        │   - Fundamental     │    │ Daemon (60s)   │  │
 │  │     - Resilient Fallbacks │        │   - Technical (11)  │    │                │  │
 │  └────────────┬──────────────┘        │   - SEC EDGAR       │    └─────┬──────────┘  │
 │               │                       │   - Sentiment       │          │             │
 │               │                       └─────────┬───────────┘          │             │
 │               │                                 │                      │             │
 │               │                       ┌─────────▼───────────┐          │             │
 │               │                       │ SSE Streaming       │          │             │
 │               │                       │ Pipeline (Research) │          │             │
 │               │                       └─────────┬───────────┘          │             │
 └───────────────┼─────────────────────────────────┼──────────────────────┼─────────────┘
                 │                                 │                      │
                 ▼                                 ▼                      ▼
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │                           PERSISTENCE & DATA LAYER                              │
  │     - SQLite DB (finance.db - Schema: Portfolio, Watchlist, Settings, Alerts)   │
  │     - Price & Security Fallback Cache (.cache/latest_prices.json)               │
  └──────────────┬─────────────────────────────────┬──────────────────────┬─────────┘
                 │                                 │                      │
                 ▼                                 ▼                      ▼
  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │                            EXTERNAL INTEGRATIONS                                │
  │                                                                                 │
  │   🏦 Robinhood API      📈 yfinance API       📂 SEC EDGAR API    🤖 LLM Gateway  │
  │    (robin_stocks)        (Market Data)         (10-K/10-Q JSON)    (Gemini/Claude)│
  │                                                                                 │
  │   📰 Finnhub API        🤖 Reddit API (PRAW)  🌐 Wikipedia        🏠 Local Ollama │
  │    (Financial News)      (WSB Sentiment)       (S&P 500 List)      (Offline LLM)   │
  └─────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Core Capabilities & Supported Flows

### 1. Unified Portfolio Ingestion & Syncing
- **Robinhood Integration:** Connects securely using credentials + MFA (One-Time Password) using `robin_stocks`. It caches a lightweight session marker locally for 24 hours so you don't have to repeatedly authenticate.
- **Manual CSV Fallback:** Quickly import portfolio allocations using a simple structure: `ticker,shares,avg_cost`.
- **Enrichment & Performance Calculations:** Automatically cross-references holdings with live market prices from `yfinance` to calculate real-time P&L, percentage changes, and portfolio weights.
- **Resilient Fallback Design:** In the event of network drops, Yahoo Finance rate limits, or off-market hours, the service automatically falls back to local price caches, and if unavailable, seamlessly defaults to your asset's `avg_cost`. This preserves visual integrity without displaying broken statistics or artificial portfolio drops.

### 2. Live SSE Streaming Deep Research Pipeline
- **Continuous Stream (SSE):** Utilizes Server-Sent Events to stream deep stock analyses progressively. The terminal guides you through every step in real-time:
  - **Stage 1:** Fundamentals Extraction (yfinance)
  - **Stage 2:** Financial Trajectory (Revenue and Margin trends)
  - **Stage 3:** Technical Patterns (Detects up to 11 indicators)
  - **Stage 4:** Public Sentiment Scoring (Finnhub & Reddit)
  - **Stage 5:** Institutional Disclosures (Direct SEC EDGAR 10-K/10-Q extraction)
  - **Stage 6:** Final AI Thesis Synthesis
- **Institutional-Grade AI Thesis:** Summarizes millions of data points into a concise markdown presentation highlighting:
  - The Bull Case vs. Bear Case.
  - Near-term critical catalysts.
  - Definitive actionable recommendations (`BUY`, `HOLD`, `TRIM`, `AVOID`) with low/medium/high conviction metrics.
  - A structured target price range.

### 3. Comprehensive Technical Pattern Detection
The system houses a dedicated mathematical analyzer to run technical scanners on historical daily charts. It detects:
- **Major Reversal Patterns:** Head and Shoulders (Standard and Inverse), Double Tops, Double Bottoms, Triple Tops, Triple Bottoms.
- **Continuation & Breakout Formations:** Cup and Handle, Bullish Flag, Falling Wedge, Ascending & Descending Triangles.
- **Momentum Indicators:** Overlaid calculations for 50 DMA, 200 DMA, RSI (Relative Strength Index), MACD, and Bollinger Bands.

### 4. Smart Multi-Provider LLM Routing
- Configure your primary LLM options directly via the **LLM Settings** interface.
- Supports **Google Gemini**, **Anthropic Claude**, and **Ollama (local models)**.
- Implements **Smart Cost Routing** schemas:
  - Uses highly optimized, lightweight fast models (e.g., `gemini-3.1-flash-lite`) to parse sentiment chunks and financial records.
  - Leverages deep reasoning engines (e.g., `gemini-2.5-pro` or `claude-3-5-sonnet`) to draft detailed investment theses.

### 5. Portfolio Rebalancing Engine
- Evaluates current holdings concentration against predefined risk models:
  - **Conservative:** 60% equities, strict single-position concentration limits.
  - **Moderate:** 80% equities, balanced indexing.
  - **Aggressive:** 95% equities, high-conviction growth.
- Computes specific share diffs, transaction sizes, and trade weights required to optimize alignment with your target profile.

### 6. Background Alerts & Watchlist Daemon
- **Watchlist Tracker:** Keep custom notes on tickers, monitoring valuation metrics dynamically with one-click triggers to deep-dive into research.
- **Background Daemon Worker:** A persistent, non-blocking background daemon (`alert_worker.py`) constantly checks stock movements in 60-second intervals and records price targets triggered directly into SQLite.

---

## 🛠️ Codebase Structure

```
finance/
├── .gitignore                    # Local cache & credential exclusion rules
├── README.md                     # Terminal documentation (this file)
└── analysis/
    ├── app.py                    # REST Server Gateway & Endpoint Controller
    ├── db.py                     # SQLite interface & automatic schema migrations
    ├── companies.py              # S&P 500 metadata scraper (Wikipedia extraction)
    ├── edgar_service.py          # SEC filings connector & 10-K/10-Q parser
    ├── llm_service.py            # Multi-provider LLM connector & routing engine
    ├── portfolio_service.py      # Normalizes holdings & executes resilient price lookups
    ├── rebalancing_engine.py    # Risk-based model optimization calculator
    ├── research_engine.py        # Gathers fundamental/technical/sentiment context
    ├── research_stream.py        # Generates SSE server packets for deep analysis
    ├── sentiment_service.py      # Crawls Reddit (PRAW) and aggregates Finnhub news
    ├── alert_worker.py           # Background thread executing active price checks
    ├── requirements.txt          # Python environments, ML libraries, & connectors
    ├── start.sh                  # One-click startup script for both backend & frontend
    └── web/                      # React SPA
        ├── src/
        │   ├── App.jsx           # Core layout & component Router
        │   ├── index.css         # Styling system (Glassmorphism theme)
        │   ├── utils/
        │   │   └── api.js        # JavaScript HTTP Client & SSE listener
        │   ├── components/
        │   │   ├── Sidebar.jsx   # Persistence layout navigation
        │   │   ├── RiskCard.jsx  # Rebalance engine visualization
        │   │   └── ...           # Customized UI components
        │   └── pages/
        │       ├── PortfolioPage.jsx     # Live P&L grids & allocation graphs
        │       ├── DeepResearchPage.jsx  # SSE stream outputs & research report tabs
        │       └── ...                   # Application views
```

---

## 🚀 Getting Started

### Prerequisites
1. **Python 3.9+** and `pip` (Package manager).
2. **Node.js 18+** and `npm` (Frontend development toolkit).
3. **LLM Credentials:** A Google AI Studio (Gemini) API Key, Anthropic API Key, or a local running instance of Ollama.
4. **Reddit Developer App credentials** (Optional, for live Subreddit sentiment analysis):
   - Set up a script application at [Reddit App Preferences](https://www.reddit.com/prefs/apps) to obtain a client ID and client secret.

### ⚙️ Environment Configuration

Navigate to the `analysis/` directory and set up your configurations:

```bash
cd analysis
cp .env.example .env
```

Open `.env` and fill out your local parameters:

```ini
# Flask Setup
PORT=5001
SECRET_KEY=generate-a-strong-random-key

# Database
DATABASE_URL=sqlite:///finance.db

# API Credentials (Fill out as needed)
GEMINI_API_KEY=your_gemini_api_key_here
FINNHUB_API_KEY=your_finnhub_api_key_here

# Optional: Reddit API credentials (PRAW)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=finance-terminal-v1
```

---

### 💻 Installation & Execution

The easiest way to start both the Python backend server and the React dev environment is by using the preconfigured launch script:

```bash
# Return to the analysis root and run the launch script
cd analysis
chmod +x start.sh
./start.sh
```

The script will automatically:
1. Initialize a Python virtual environment (`venv`).
2. Install all python libraries defined in `requirements.txt`.
3. Check and install all React packages.
4. Launch the Flask backend at `http://localhost:5001`.
5. Run the background Alert Daemon.
6. Spin up the React UI dashboard at `http://localhost:5173`.

---

## 🔌 API Reference Controller

### 📂 Portfolio Services
- `GET /api/portfolio/status` - Returns credentials connected status and session timers.
- `POST /api/portfolio/connect` - Authenticates to Robinhood securely using OTP challenge-response.
- `POST /api/portfolio/disconnect` - Logs out from current broker session and clears active cache structures.
- `POST /api/portfolio/sync` - Re-syncs holdings from Robinhood to local SQLite database.
- `POST /api/portfolio/import` - Manually imports portfolios using standard CSV format.
- `GET /api/portfolio/holdings` - Fetches holdings combined with live yfinance prices.

### 🔬 Deep AI Research
- `GET /api/research/<ticker>` - Obtains standard cached deep research report and LLM thesis. (Append `?refresh=true` to force a live calculation).
- `GET /api/research/<ticker>/stream` - Server-Sent Events (SSE) streaming API providing progressive updates.

### ⚖️ Rebalancer
- `POST /api/research/compare` - Compare metrics and thesis points across up to 4 assets.
- `GET /api/research/sector/<sector_name>` - Returns overall statistical trends and top performers in a sector.

### 🔔 Watches & Alerts
- `GET /api/watchlist` - Returns your tracked watchlists.
- `POST /api/watchlist` - Adds asset ticker to watchlist.
- `GET /api/alerts` - Returns price targets and triggered flags.
- `POST /api/alerts` - Installs a price alert target.

---

## 🎨 Premium Dark Aesthetic & UI/UX Design

The application's interface features a highly optimized Bloomberg-style dark trading interface:
- **Base Color Architecture:** Deep space navy background (`#0b0f19`) paired with subtle glassmorphic grid systems.
- **Dynamic Feedback UI:** HSL Hues tailored specifically for rapid scannability—positive earnings/gains highlight in electric green, and negative shifts light up in vibrant red.
- **Modern Typography:** Complete inclusion of custom fonts designed for number-heavy, high-readability financial data (Inter + JetBrains Mono).
- **Responsive Layout:** Responsive dashboard layouts incorporating micro-animations and smooth transitions.

---

## 🔒 Security & Persistence Integrity
- **Zero-Storage Password Architecture:** When connecting to external broker accounts via Robinhood, the application strictly processes your credentials locally to authenticate via OAuth. The raw password is *never* saved.
- **SQLite Database Encapsulation:** Watchlists, settings parameters, active price alerts, and LLM keys are stored locally within an active database instance (`finance.db`) which includes robust recovery handlers.
- **Robust Cache Strategy:** The API utilizes SQLite cache layers for complex analysis files (like SEC EDGAR parses) that are automatically invalidated every 24 hours to conserve server speed.

---

## 🛠️ Testing the Setup

To verify that the service is running, you can run a local test on your health-check endpoints:

```bash
curl -s http://localhost:5001/api/health
```

Output:
```json
{
  "status": "healthy",
  "data_available": true,
  "company_count": 503,
  "last_updated": "2026-05-17T01:20:00"
}
```
