---
title: Troubleshooting
order: 4
category: Daily use
---

# Troubleshooting

Common failure modes and what to do about them.

---

## Backend will not start

**Symptom**: `analysis/start.sh` errors, or the frontend shows the API as offline.

Check:

1. Python version: `python3 --version` should be 3.9+.
2. Dependencies: `cd analysis && pip install -r requirements.txt`.
3. Port 5001: `lsof -i :5001`.
4. SQLite directory: `ls -ld ~/.portfolio_intelligence`.

The backend runs from `analysis/app.py` on port 5001.

---

## Frontend will not start

**Symptom**: Vite fails, or the app shell does not load.

Check:

1. `cd analysis/web && npm install` if dependencies are missing.
2. `npm run build` to catch compile errors.
3. Make sure `VITE_API_BASE` is unset or points at `http://localhost:5001/api`.

All frontend API calls should flow through `src/utils/api.js`.

---

## LLM call times out or errors

**Symptom**: Console stalls at a planner, debate, judge, or memo step.

Possible causes:

- API key missing or wrong. Open **Settings → LLM** and verify the provider.
- Provider rate limit. Wait and rerun, or switch provider.
- Local model unavailable. If using Ollama, confirm the model is running.
- Network failure.

The agent loop has a wall-clock budget. If it runs out, it should return a partial result instead of hanging indefinitely.

---

## Console stream looks incomplete

**Symptom**: `/thesis` starts but the UI does not show expected progress.

Check:

1. Backend logs for exceptions from `console_orchestrator.py` or `agent_loop.py`.
2. Browser console for SSE parsing errors.
3. The event vocabulary in `next_gen_tool.md` if a new event is emitted but not rendered.

The endpoint is `/api/research/<ticker>/v2/stream`.

---

## No data from a tool

**Symptom**: A card or report section shows low confidence, an empty payload, or a yfinance/SEC error.

Common causes:

- The ticker is delisted, renamed, foreign, or a non-equity instrument.
- yfinance throttled or returned an empty response.
- An optional provider key is not configured.
- The source does not publish that field.

Tools should degrade gracefully with `confidence="low"` and a clear `error`. A missing input should not crash the whole research run.

---

## S&P 500 Screener data looks stale

**Symptom**: S&P 500 rules, market caps, 52-week-high distance, or sector constituents look old.

Open **Settings → Data Tiers** and use the **S&P 500 snapshot** refresh button. This calls `POST /api/market/refresh-sp500`, which rebuilds `.cache/sp500_data.json` through the `sp500_refresh` Tool.

Theme heat for S&P sectors uses live quotes for daily moves, but fast Screener rules use the cached snapshot for fundamentals.

---

## Screener is slow

**Symptom**: A screen over the S&P 500 takes much longer than expected.

Check whether the screen has pattern rules or `scan: true`. Fast fields use cached data. Pattern scans fetch price history and run detectors per ticker, so they are intentionally slower.

Use a smaller theme or watchlist universe when testing a new screen.

---

## Stale research

**Symptom**: A report references old data.

Reports and tools are cached. For a fresh research run, use the Console option or endpoint parameter that forces refresh for that session. For S&P 500 fast-screen data, refresh the snapshot from Settings.

---

## Tests fail locally

**Symptom**: `python3 -m pytest tests/` fails.

Common causes:

- Running from the wrong directory. Use `cd analysis && python3 -m pytest tests/`.
- Stale Python cache. Remove `__pycache__` directories if needed.
- Missing dependency after a requirements change.
- A test accidentally hit live network instead of a mock.

Frontend checks:

```text
cd analysis/web
npm run build
npx playwright test
```

---

## When in doubt

Read the backend logs and trace from the route to the service or Tool. The app is intentionally small enough that most failures can be followed end to end.
