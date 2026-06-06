# tests/ — Testing Suite Conventions (Gemini Developer Guide)

This directory contains backend pytest scripts.

- **Fast Checks**: Run tests when modifying tools or agents to ensure no contracts were broken.
- **Mocking**: Use `unittest.mock` to mock endpoints. Consult `tests/test_agent_loop.py` to see the structure of `FakeProvider`.
- **E2E tests**: Frontend browser UAT specifications are located separately in `analysis/web/tests/e2e/` using Playwright.
