---
title: Troubleshooting
order: 4
category: Daily use
---

# Troubleshooting

Common failure modes and what to do about them.

---

## Backend won't start

**Symptom**: `analysis/start.sh` errors out, or the frontend shows "API offline."

Check:
1. Python version: `python3 --version` should be 3.9+.
2. Dependencies: `cd analysis && pip install -r requirements.txt`.
3. Port 5001 free: `lsof -i :5001`. Kill any conflicting process.
4. SQLite directory writable: `ls -ld ~/.portfolio_intelligence`. Should exist and be writable.

---

## LLM call times out / errors

**Symptom**: Research run hangs at a planner/judge step; SSE stream goes silent.

Possible causes:
- **API key missing or wrong**. Open LLM Settings and verify the key.
- **Rate limit**. Wait 60 seconds and re-run. If persistent, switch to a different provider.
- **Network**. The tool retries on transient failures, but if your connection is down, nothing helps.
- **Provider outage**. Anthropic / Google / OpenRouter dashboards will tell you.

The agent loop's Budget has a wall-clock cap (default 300s). If a session exceeds that, it short-circuits and returns whatever it has so far. Look at the partial verdict — it may still be informative.

---

## Robinhood session expired

**Symptom**: Portfolio page shows "Connection error" or "Holdings unavailable."

Robinhood session tokens expire periodically. Fix:
1. Delete `~/.portfolio_intelligence/.cache/rh_session.json`.
2. Re-enter credentials on the Portfolio page.

If you have 2FA enabled (you should), be ready to enter the code when prompted.

---

## "No data" for a fundamentals call

**Symptom**: A tool returns empty data with `confidence='low'` and an error like "yfinance returned no data."

Causes:
- The ticker is delisted or recently renamed.
- yfinance throttled you. Wait 5–10 minutes; try again.
- The ticker is foreign or non-equity (e.g. an ADR, a SPAC unit, an ETF). Some tools (DCF, QoE) explicitly skip non-equity instruments.

For ETFs: this is expected behavior. DCF and QoE return `{"skipped": true, "reason": "Not applicable for ETFs"}`. The verdict will still produce, just without those tools' input.

---

## Monitor digest is empty

**Symptom**: Open the Advisor page, click "Run digest now," nothing appears.

Reasons:
- **No `monitoring_enabled` tickers**. The default is to monitor every holding, but if you have no holdings, there's nothing to monitor.
- **Throttle cooldown**. Tickers that returned `thesis_intact=True` in the last 30 minutes are skipped. Wait or trigger manually.
- **LLM provider unavailable**. The monitor uses the fast/cheap model (`monitor` task type). If that provider is down, no signals get generated.

Check the backend logs: `tail -f ~/.portfolio_intelligence/logs/server.log` (path may vary by your config).

---

## Calibration page shows "n too small"

**Symptom**: The Calibration page says you don't have enough data.

This is by design. You need at least 20 closed recommendations with at least the 1-month outcome populated before the tool will display a calibration number. Earlier than that, the sample is dominated by variance and would mislead you.

To accelerate:
- Run more Deep Research sessions (each produces a recommendation).
- Wait — the outcome worker backfills returns daily.
- Manually trigger: `POST /api/advisor/calibration?backfill=1`.

---

## Stale research / old data

**Symptom**: A research report references prices from days ago.

Reports are cached. The cache TTL is per-tool (most are 4–24 hours). To force a fresh run:
- Add `?force_refresh=true` to the research URL.
- Or delete the row from `research_reports` for that ticker.

---

## Tests are failing locally

**Symptom**: `python3 -m pytest tests/` shows failures.

Common causes:
- **`HOME` not redirected**. Tests use `conftest.py` to send the DB to a tempdir. If you ran pytest from outside the `analysis/` directory, conftest may not load. Always run from `analysis/`.
- **Stale `.pyc`**. `find analysis -name "*.pyc" -delete && find analysis -name "__pycache__" -type d -exec rm -rf {} +`.
- **New dependency**. `pip install -r analysis/requirements.txt`.

The `e2e_real` marker is opt-in and excluded by default. If you want to run it:
```
cd analysis && python3 -m pytest tests/test_e2e_real_ticker.py -m e2e_real -v -s
```

---

## When in doubt

Read the backend logs. Most non-trivial bugs leave a clear stack trace there. The tool is intentionally small enough that you (or Claude) can trace any failure end-to-end in under an hour.
