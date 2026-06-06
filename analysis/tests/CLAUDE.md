# tests/ — Testing Suite Conventions

This folder contains unit and integration tests for the Edge Personal Markets Terminal backend.

## Commands
Run the entire suite from the `analysis` directory:
```bash
python3 -m pytest tests/
```

Run a specific test file:
```bash
python3 -m pytest tests/test_agent_loop.py
```

Run a single test case:
```bash
python3 -m pytest tests/test_agent_loop.py -k "test_run_deep_research"
```

## Guidelines
- **Mocking**: All external API calls (yfinance, Finnhub, SEC EDGAR, FMP) and LLM endpoints MUST be mocked. Look at `conftest.py` and `tests/test_agent_loop.py` for standard mock fixtures (`FakeProvider`, mocked client requests).
- **Database**: Use the standard sqlite fixture to build a fresh, temporary test database for database-related test suites.
- **Assertion Coverage**: Ensure both successful execution and negative test cases (graceful degrading on timeouts/errors) are covered.
