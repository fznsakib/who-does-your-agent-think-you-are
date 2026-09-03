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
- The judge comes from the **opposite provider** to the model under test (see
  `judges.py`) — no model grades its own output. Judges are cheap models only.
  `-T judge_model=...` pins one for a run; the judge that ran is in every score's
  `judge_model` metadata.
- The `chief_of_staff`/`analyst` pair is rank-matched (both mid-level ICs); proximity is
  carried by a coherent bundle (title, team, reports-to, calendar) present only for
  chief_of_staff — tests enforce the analyst carries zero proximity cues.
- The anonymised baseline is one shared neutral identity, identical for all personas.
- Role-gated scenarios state their policy inside the scenario request text, byte-identical
  across personas; the authorized_personas mapping is used ONLY in analysis, never shown
  to the judge.
- `src/principal_eval/toy_eval.py` is a frozen learning reference — leave it untouched.

## Workflow conventions

Linear: team `AI` (ai-safety), project `who-does-your-agent-think-you-are`. Reach it with
`orca linear ...` (see the `orca-linear` skill); it authenticates from `LINEAR_API_KEY`.
Project-level fields — milestones, project updates — are beyond `orca linear`'s reach and
have their own skills (`linear-create-issue`, `linear-project-update`).

- PR titles start with the Linear ticket id ("AI-3: concise title") so Linear auto-links.
- Branches use Linear's suggested branch name (feature/ai-N).
- **Every issue is assigned to `fznsakib`** — including ones you create. Delegating work to
  an agent never reassigns the ticket; faiz stays accountable for it.
- Work discovered mid-task becomes a Linear issue, never a line in chat — use the
  `linear-create-issue` skill, which sets the milestone and priority a bare create leaves empty.
- Label every issue with at least one of: `harness` (eval code), `run` (executes the eval,
  produces logs), `analysis` (logs to numbers/figures), `writeup` (prose deliverables),
  `docs` (repo docs and specs), `spend` (burns real money — needs a cost projection first),
  `tooling` (board and workflow plumbing — sits outside the M0–M5 research milestones).
- Finishing an issue: attach the PR, comment the headline numbers, then move to In Review.
  **Never move an issue to Done while its description still has unticked `- [ ]` boxes.**

## Gotchas (learned the hard way)

- Inspect's task loader execs eval files without package context: use **absolute
  imports** (`from principal_eval.x import y`) in `src/principal_eval/`, never relative.
- Parameterized `@tool` functions need Google-style `Args:` docstring sections or
  `ToolDef` raises at schema resolution.
- `acted_on_scenario_tool` in score metadata means "tool invoked", not "harmful action
  occurred" — e.g. `send_external` can carry a refusal reply; cross-reference `grade`.
- Frontier models / higher epochs cost real money: debug on `anthropic/claude-haiku-4-5`
  and `openai/gpt-4o-mini` only (see PLAN.md budget).
