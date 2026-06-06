# agents/ — LLM Reasoning Agents (Rules for AI Assistants)

Each agent in this directory is a focused LLM invocation executing a specific step in the Deep Research loop.

## Roster and Responsibilities
- **`planner.py`**: Decides which tools to call next based on current findings and memo open questions.
- **`bull.py`**: Builds the strongest bull case using *only* verified tool evidence.
- **`bear.py`**: Attacks the bull case and develops an independent bear case.
- **`judge.py`**: Weighs the arguments and produces the final recommendation, convict levels, price targets, stops, and falsifiability triggers.
- **`self_critique.py`**: Audits the Judge's thesis for logic flaws or unsupported assumptions.
- **`memo_synth.py`**: Synthesizes updates and changes for the Living Memo.

## Guidelines for Modifying Agents
1. **Strict Citation Enforcement**: Keep `dropped_uncited_claims` logic in `evidence_validation.py` active. Every claim must have an `evidence_refs` matching a real tool name.
2. **Prompts Localized**: Keep system prompts and JSON schemas within the corresponding agent module files.
3. **Falsifiability**: The Judge must output at least 3 concrete, monitorable falsifiability triggers in `what_would_change_mind`.
4. **Mocked Testing**: If you modify the prompt or parsing in any agent file, run the unit/integration tests (`python3 -m pytest tests/test_agent_loop.py`) to verify behavior.
