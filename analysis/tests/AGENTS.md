# tests/ — Testing Suite Conventions (Rules for AI Assistants)

Testing rules to keep code coverage high and tests green.

## Rules
1. **Mocking Required**: Never invoke real external APIs or LLMs in pytest. Always mock network requests and return deterministic results.
2. **Database Cleanliness**: Use the temporary sqlite session fixtures for DB operations. Never write tests that leave side effects in the developer's default `~/.edge_terminal/finance.db`.
3. **Verify Before Check-in**: Propose a test run using `python3 -m pytest tests/` before completing tasks.
