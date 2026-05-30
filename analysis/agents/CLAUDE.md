# agents/ — LLM Reasoning Agents

Each agent is a focused LLM call: specialized system prompt + structured-JSON output + parsing.

## Roster

| Agent | Role | Reads | Emits |
|---|---|---|---|
| `planner` | Decides which tools to call next | memo open questions, ledger, budget, sector required tools | `{next_calls, done, summary}` |
| `bull` | Strongest bull case | evidence ledger only | `{thesis_md, key_drivers[], price_target_methodology}` |
| `bear` | Attack bull + independent bear | ledger + bull's output | `{attack_md, independent_bear_md, key_risks[], thesis_falsifiers_for_bull}` |
| `judge` | Final verdict + trade plan | ledger + bull + bear | `{recommendation, conviction, what_would_change_mind, trade_plan}` |
| `self_critique` | Find weakest claims, may trigger more research | ledger + verdict | `{weakest_claims, should_revise_verdict, additional_tools_to_call}` |
| `memo_synth` | Propose Living Memo delta | old memo + ledger + verdict | `{new_memo, delta_summary}` |

## Citation enforcement

**Bull and Bear MUST cite evidence by tool name in `evidence_refs` for every claim.** The judge prompt requires the same. If you weaken these constraints, the whole "no naked numbers" guarantee breaks. Don't.

`agents.evidence_validation.validate_claim_refs()` enforces this after each LLM call. Every structured claim ref must resolve to a real `ledger.results` tool name. Invalid refs are dropped from the claim; claims with no valid refs are removed and recorded in `dropped_uncited_claims`.

## Falsifiability

The Judge must always emit at least 3 `what_would_change_mind` conditions. An empty list is a *bug*, not a recommendation. The default judge prompt enforces "at least 3 specific conditions, each monitorable (a number, a date, an event)" — preserve this language.

This list is for manual review and future pull-triggered checks. Do not wire it to background alerts.

## System prompts live with agent files

Don't centralize prompt strings into a config file. Each agent's prompt evolves with its parsing/output schema; coupling them keeps changes coherent. If a prompt grows large, split it into module-level constants in the same file (see `judge.py`).

## Adding a new agent

1. Create `analysis/agents/<name>.py`
2. Define a `<verb>(...) -> Dict` function — not a class (we don't need state)
3. Use `from llm_service import _get_provider_and_model` to get the provider
4. Pick `task_type`:
   - `"analysis"` for planner / critique (mid-cost reasoning)
   - `"thesis"` for bull/bear/judge (deep reasoning — uses `model_deep`)
5. Wrap LLM calls in try/except; return a structured fallback on failure (see `judge._fallback_verdict`)
6. Add integration tests in `tests/test_agent_loop.py` using `FakeProvider`

## Budget awareness

Agents themselves don't manage budget — `agent_loop.py` does. But:
- Keep prompts compact (use `ledger.evidence_prompt(max_chars_per_tool=N)`)
- Don't loop within an agent (let the agent_loop trigger another planner round instead)
- For the planner: respect the `MAX_PLANNER_ITERATIONS` cap
