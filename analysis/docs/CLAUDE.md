# docs/ — Source of truth

Two documents. Keep them in sync with the code.

| Doc | Source of truth for | Audience |
|---|---|---|
| `next_gen_tool.md` | Architecture, data model, endpoints, phasing | Engineers / Claude agents |
| `deep_research_guide.md` | UX semantics, philosophy, how to interpret output | The user (power-user manual) |

## Drift rule

If runtime behavior diverges from these docs, fix the code OR update the doc in the same PR. Never leave them silently desynced — future agents will assume the docs are accurate.

When in doubt: docs describe *intent*. Code describes *current reality*. If they conflict, ask the user which to follow before changing either.
