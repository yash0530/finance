"""
analysis.agents — LLM-driven reasoning agents.

Each module here is a specialized prompt + parsing pipeline:
  - planner       — decides which tools to call next
  - bull          — argues the bullish case from evidence
  - bear          — argues the bearish case + attacks the bull
  - judge         — weighs both, produces the structured verdict + falsifiability
  - self_critique — finds weak claims in the verdict, may trigger more research
  - memo_synth    — proposes the Living Memo delta after a session
"""
