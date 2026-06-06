# agents/ — LLM Reasoning Agents (Gemini Developer Guide)

This folder contains the prompt templates, response schemas, and parsers for the Deep Research agentic debate team.

## Prompt and Parsing Patterns
- **Provider Routing**: Look up models using `_get_provider_and_model(db_conn, task_type)` from `llm_service.py`.
- **System Prompts**: Kept inside each agent file as constants.
- **Output Schema**: Keep structure strict and parse output as standard JSON. Handle parsing failures gracefully by falling back to default structures.
- **Citation Check**: Keep `evidence_validation.py` validation strict to ensure all claims map back to actual evidence tools.

## Key Development Rules
1. Never weaken validation logic for citations.
2. Ensure `what_would_change_mind` always has a minimum of 3 monitorable conditions.
3. Test changes using `python3 -m pytest tests/test_agent_loop.py`.
