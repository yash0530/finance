"""
Regression guard for first-class product surfaces.

This test is intentionally simple: it catches accidental v2/v3 reconciliation
regressions where a page or endpoint disappears during a rewrite.
"""
from __future__ import annotations

from pathlib import Path

import app as _app


def test_first_class_routes_registered():
    routes = {rule.rule for rule in _app.app.url_map.iter_rules()}

    expected = {
        "/api/market/sp500/companies",
        "/api/stock/<ticker>/header",
        "/api/chart/<ticker>",
        "/api/console/run",
        "/api/research/<ticker>/v2/stream",
        "/api/library/memos",
        "/api/screener/run",
        "/api/terminal/movers",
        "/api/terminal/snapshot",
        "/api/calibration/dashboard",
        "/api/recommendations/<int:recommendation_id>/outcome",
        "/api/patterns/all",
        "/api/patterns/<pattern_type>/<ticker>",
        "/api/settings/data-tier",
    }

    missing = expected - routes
    assert not missing, f"Missing first-class routes: {sorted(missing)}"


def test_first_class_frontend_pages_exist():
    src = Path(__file__).resolve().parents[1] / "web" / "src" / "pages"
    expected = {
        "MarketPage.jsx",
        "StockViewPage.jsx",
        "TerminalPage.jsx",
        "ConsolePage.jsx",
        "CalibrationPage.jsx",
        "LibraryPage.jsx",
        "ScreenerPage.jsx",
        "TechnicalPatternsPage.jsx",
        "SettingsPage.jsx",
        "DocsPage.jsx",
    }

    missing = {name for name in expected if not (src / name).exists()}
    assert not missing, f"Missing first-class frontend pages: {sorted(missing)}"
