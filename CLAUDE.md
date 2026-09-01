# CLAUDE.md

Inspect-based behavioural eval: does a model's *inferred* picture of its user change
agent behaviour? Design + matrix: [README.md](README.md). Binding design authority:
[docs/superpowers/specs/2026-09-01-inferred-user-status.md](docs/superpowers/specs/2026-09-01-inferred-user-status.md).
Working plan + next steps: [PLAN.md](PLAN.md).

## Inspect skills (installed via the `inspect-skills` plugin)

- Launching, watching, or unsticking a **running** eval (stalls, errors, cancelling
  samples, retuning concurrency) → use `inspect-skills:babysitting-evals`.
- Reading `.eval`/`.json` log files → use `inspect-skills:reading-logs` (never unzip a
  `.eval` file; use the `inspect_ai.log` API).
- Analysing results — per-sample questions, persona×condition grouping, cross-log
  dataframes, transcript pattern hunts → use `inspect-skills:analyzing-logs`.
- Unsure which Inspect ecosystem package handles a concern → use
  `inspect-skills:map-inspect-packages`.

## Invariants (violating any of these corrupts the experiment)

- Identity cues reach the model **only through tool outputs** — never in the system or
  user message. The system prompt carries lab framing only.
- The judge is **blind** (no persona/condition in its prompt) and **post-hoc** (never a
  react retry gate; `attempts=1` — this measures propensity, not capability).
- The `mid_high_prox`/`mid_low_prox` pair differs **only** in calendar content; every
  other channel is byte-identical (tests enforce this).
- The anonymised baseline is one shared neutral identity, identical for all personas.
- `src/principal_eval/toy_eval.py` is a frozen learning reference — leave it untouched.

## Gotchas (learned the hard way)

- Inspect's task loader execs eval files without package context: use **absolute
  imports** (`from principal_eval.x import y`) in `src/principal_eval/`, never relative.
- Parameterized `@tool` functions need Google-style `Args:` docstring sections or
  `ToolDef` raises at schema resolution.
- `acted_on_scenario_tool` in score metadata means "tool invoked", not "harmful action
  occurred" — e.g. `send_external` can carry a refusal reply; cross-reference `grade`.
- Frontier models / higher epochs cost real money: debug on `anthropic/claude-haiku-4-5`
  and `openai/gpt-4o-mini` only (see PLAN.md budget).
