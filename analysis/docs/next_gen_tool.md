# Next-Gen AI Portfolio Intelligence Tool — Specification

> **Status**: Implemented v1.0 — Core suite fully built and operational  
> **Last Updated**: May 2026  
> **Supersedes**: `spec.md` (analysis-only tool)

---

## 1. Vision & Motivation

The original tool was a passive S&P 500 viewer. It showed what the market was doing, but didn't help you *act* on it. This Next-Gen tool bridges that gap.

**The core idea**: Connect to your real portfolio (Robinhood or manual entry), run deep AI-powered research across fundamental analysis, technical patterns, market sentiment, and macroeconomic signals, and deliver **concrete, actionable portfolio decisions** — not just data dumps.

It is part research terminal, part AI portfolio advisor, and part trading journal. Think Bloomberg Terminal meets ChatGPT, built for a single investor.

---

## 2. Core Capabilities

### 2.1 Portfolio Ingestion (Implemented)
- **Robinhood Integration** (primary): Connects via the `robin_stocks` library (unofficial API) using secure OAuth credentials + OTP. Pulls current open positions and cost basis.
- **Manual Entry** (fallback): Fast CSV parsing to enter ticker + shares + avg cost.
- **Unified Portfolio Model**: Regardless of source, all holdings normalize into a standard internal schema and sync with `yfinance` to fetch live P&L data and portfolio weights.

### 2.2 Deep Research Engine (Implemented)
For any stock or ETF, the tool runs a multi-layer analysis:

| Layer | What It Does |
|-------|-------------|
| **Fundamental Analysis** | Fetches P/E, revenue/margin trends, EPS, balance sheet health (debt/equity, current ratio) via `yfinance`. |
| **Technical Analysis** | 11 chart patterns, RSI, MACD, Bollinger Bands, moving averages (50/200 DMA), support/resistance levels. |
| **Market Sentiment** | News sentiment (Finnhub + fallback NLP scoring), social sentiment (Reddit WSB + r/investing via `praw`), and analyst ratings aggregation. |
| **SEC Filings** | Direct integration with SEC EDGAR pulling 10-K and 10-Q JSON filings for institutional-grade disclosures. |
| **AI Synthesis** | LLM reads all of the above and writes a structured investment thesis: Bull case / Bear case / Key catalysts / Actionable recommendations. |

### 2.3 Portfolio Rebalancing Engine (Implemented)
- Computes current allocation (% per sector, per stock).
- Defines a **target portfolio** based on customizable risk tolerances: Conservative / Moderate / Aggressive.
- Identifies: what is overweight, what is underweight, what to trim, what to add.
- Outputs: A prioritized action list with specific trade quantities and percentage differentials.

### 2.4 Research Mode & Watchlist (Implemented)
User can search or select:
- Any US ticker (beyond S&P 500 — any publicly traded stock or ETF).
- S&P 500 Market Mode (legacy technical pattern scanning).
- **Watchlist**: Track saved ideas with personal notes, and click a quick-action "microscope" icon to instantly run Deep Research.

### 2.5 Alerts & Monitoring Daemon (Implemented)
- **Price Alerts**: Set target thresholds (Price Above / Price Below).
- **Background Daemon**: A multithreaded daemon (`alert_worker.py`) constantly polls live prices every 60 seconds without blocking the UI and records triggers directly into the database.

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│  React + Vite (dark terminal aesthetic, Recharts, animations)   │
│                                                                 │
│  Pages: Portfolio | Research | Rebalance | Alerts | Watchlist   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST / CORS
┌──────────────────────────▼──────────────────────────────────────┐
│                     FLASK BACKEND (app.py)                      │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Portfolio    │  │ Research     │  │ Rebalancing          │  │
│  │ Router       │  │ Router       │  │ Engine               │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                     │               │
│  ┌──────▼─────────────────▼─────────────────────▼───────────┐  │
│  │                  AI ANALYSIS ENGINE                       │  │
│  │  ┌──────────────┐  ┌─────────────┐  ┌────────────────┐   │  │
│  │  │ Fundamental  │  │ Technical   │  │ Sentiment      │   │  │
│  │  │ Analyzer     │  │ Analyzer    │  │ Analyzer       │   │  │
│  │  │ (yfinance +  │  │ (existing   │  │ (News NLP +    │   │  │
│  │  │  pandas)     │  │  patterns)  │  │  Reddit/praw)  │   │  │
│  │  └──────┬───────┘  └──────┬──────┘  └───────┬────────┘   │  │
│  │         └─────────────────┴──────────────────┘           │  │
│  │                          │                                │  │
│  │              ┌───────────▼──────────┐                    │  │
│  │              │   LLM Synthesizer    │                    │  │
│  │              │  (Gemini / Claude /  │                    │  │
│  │              │   Ollama)            │                    │  │
│  │              └──────────────────────┘                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               DATA LAYER                                │    │
│  │  SQLite DB (finance.db) │  JSON Cache (.cache/)         │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    EXTERNAL DATA SOURCES                        │
│                                                                 │
│  Robinhood API    yfinance        Reddit API      LLM API       │
│  (robin_stocks)   (live prices)   (praw)          (Gemini)      │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1 Backend Modules

| Module | Purpose |
|--------|---------|
| `db.py` | Robust SQLite abstraction with automatic migrations (portfolio, watchlist, alerts, settings, research cache). |
| `portfolio_service.py` | Robinhood connector (OTP auth via `robin_stocks`) + manual entry normalization. Handles live P&L. |
| `research_engine.py` | Orchestrates fundamental + technical + sentiment + SEC filing analysis into a massive context bundle. |
| `llm_service.py` | Multi-provider abstraction. Features Smart Cost Routing (e.g., fast model for sentiment, deep model for thesis). |
| `rebalancing_engine.py` | Portfolio optimization algorithm comparing holdings vs S&P 500 benchmarks. |
| `sentiment_service.py` | Subreddit scraping (`praw`) + Finnhub news + yfinance fallback with smart composite weighting. |
| `edgar_service.py` | Connects directly to SEC data APIs to fetch 10-K/10-Q json archives. |
| `alert_worker.py` | Daemon thread polling prices for alert triggers in the background. |

---

## 4. Data Sources & APIs (Current Usage)

| Source | Data | Cost | Status |
|--------|------|------|--------------|
| `robin_stocks` | Portfolio holdings | Free | ✅ Integrated |
| `yfinance` | Prices, financials, fundamentals | Free | ✅ Integrated |
| `Finnhub` | News, analyst ratings | Free tier | ✅ Integrated |
| `praw` (Reddit API) | WSB + r/investing posts/sentiment | Free tier | ✅ Integrated |
| Google Gemini | LLM synthesis (`gemini-3.1-flash-lite`, `gemini-2.5-pro`) | Free tier available | ✅ Primary Engine |
| SEC EDGAR | Full 10-K/10-Q filings | Free | ✅ Integrated |
| Wikipedia | S&P 500 list | Free | ✅ Integrated (Requires `lxml`) |

---

## 5. API Endpoints

### Portfolio
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/portfolio/connect/robinhood` | POST | Authenticate with Robinhood via OTP |
| `/api/portfolio/import` | POST | Manual CSV import |
| `/api/portfolio/holdings` | GET | Current holdings with live P&L |
| `/api/portfolio/status` | GET | Connection and auth status |
| `/api/portfolio/rebalance` | POST | Run rebalancing analysis against a risk profile |

### Research & Watchlist
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/research/<ticker>` | GET | Full deep research report & AI Thesis (uses `?refresh=true` to bypass DB cache) |
| `/api/watchlist` | GET/POST | Fetch Watchlist / Add ticker |
| `/api/watchlist/<ticker>` | DELETE | Remove ticker from Watchlist |

### Alerts
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/alerts` | GET/POST | Fetch Alerts / Create Alert |
| `/api/alerts/<id>` | DELETE | Remove Alert |
| `/api/alerts?active_only=true` | GET | Fetch only active/triggered alerts |

---

## 6. LLM Integration Design

### Multi-Provider LLM Routing

User configures in `LLM Settings` UI:
- **Provider**: Google Gemini / Anthropic Claude / Ollama
- **API Key**: Saved securely in SQLite (hidden from UI)
- **Fast Model**: e.g., `gemini-3.1-flash-lite` (Used for quick sentiment summaries)
- **Deep Model**: e.g., `gemini-3.1-flash-lite` or `gemini-2.5-pro` (Used for full thesis generation)

### Prompt Architecture & Output Schema
The LLM is fed a highly structured markdown bundle containing Prices, SEC Filings, Reddit Sentiment, Analyst Ratings, and Technical indicators. It outputs strict JSON conforming to this schema:
```json
{
  "summary": "One-sentence verdict",
  "bull_case": ["reason 1", "reason 2", "reason 3"],
  "bear_case": ["risk 1", "risk 2", "risk 3"],
  "key_catalysts": ["upcoming event 1", "event 2"],
  "recommendation": "BUY | HOLD | TRIM | AVOID",
  "conviction": "HIGH | MEDIUM | LOW",
  "target_price_range": {"low": 0, "high": 0, "timeframe": "12 months"},
  "action_items": ["Specific action 1", "Specific action 2"]
}
```

---

## 7. Portfolio Rebalancing Engine

### Process
1. Compute current allocation matrix.
2. Run deep comparison against standard benchmark allocations.
3. Compare to user-selected target allocation based on risk profile:
   - **Conservative**: 60% equities, low concentration
   - **Moderate**: 80% equities
   - **Aggressive**: 95% equities, higher concentration limits
4. Generate delta logic: Computes exact share diffs to hit target weights.
5. Output: Prioritized action list detailing trims and additions.

---

## 8. UI/UX Design

**Aesthetic**: Dark trading terminal — deep navy/black base, electric blue accents, green/red for gains/losses, JetBrains Mono for prices, glassmorphism cards with blur effects.

### Application Structure
```
Sidebar (persistent navigation) + Live React Routing

├── 📊  Portfolio      — Holdings table, allocation donut, connection CTA
├── 🔬  Research       — Deep search -> AI report with tabs (Overview, Fundamentals, SEC)
├── 👀  Watchlist      — Tracked stocks with custom notes and one-click research
├── ⚖️   Rebalance      — Risk profile picker, current vs. target, specific trade actions
├── 🔔  Alerts         — Price thresholds with real-time backend triggers
├── 📈  S&P 500        — Legacy S&P 500 technical scanner and spotlight
└── ⚙️  LLM Settings   — Configuration for models and API keys
```

---

## 9. Future Vision (Phase 2+)

- **Voice interface**: "What's my NVDA thesis today?" — Whisper STT + LLM response
- **Automated trade execution**: With broker API, execute the AI's suggestions directly (Auto-rebalance)
- **Email/SMS Push Notifications**: Hook the background `alert_worker.py` into Twilio or SendGrid.
- **Options flow tracking**: Unusual options activity as a leading sentiment indicator
- **Custom fine-tuning**: Train on your own historical trades + outcomes
