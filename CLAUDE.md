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

- PR titles are always `<ticket-key>[<label>]: <concise title>` — e.g.
  `AI-23[harness]: structural harm arguments`. The key makes Linear auto-link; the label
  must already exist on the ticket (see the label list below).
- Branches use Linear's suggested branch name (feature/ai-N).
- PR bodies are concise: bullet points or tables when covering several things, and the
  same section headings from PR to PR (Summary / Evidence / Tests is the house pattern).
- Always wait for the codex review and resolve its comments before merging. A finding
  that doesn't block the PR becomes a Linear ticket via `linear-create-issue`, never a
  fix-later comment.
- **Every issue is assigned to `fznsakib`** — including ones you create. Delegating work to
  an agent never reassigns the ticket; faiz stays accountable for it.
- Work discovered mid-task becomes a Linear issue, never a line in chat — use the
  `linear-create-issue` skill, which sets the milestone and priority a bare create leaves empty.
- Label every issue with at least one of: `harness` (eval code), `run` (executes the eval,
  produces logs), `analysis` (logs to numbers/figures), `writeup` (prose deliverables),
  `docs` (repo docs and specs), `spend` (burns real money — needs a cost projection first),
  `tooling` (board and workflow plumbing — sits outside the M0–M5 research milestones).
- Finishing an issue: attach the PR, comment the headline numbers, then move to In Review.
  **Merging the PR and moving the issue to Done both require the ticket's "Done when"
  acceptance criteria to be genuinely met — never merge or close over unticked `- [ ]`
  boxes.**

## Gotchas (learned the hard way)

- Inspect's task loader execs eval files without package context: use **absolute
  imports** (`from principal_eval.x import y`) in `src/principal_eval/`, never relative.
- Parameterized `@tool` functions need Google-style `Args:` docstring sections or
  `ToolDef` raises at schema resolution.
- `acted_on_scenario_tool` in score metadata means "tool invoked", not "harmful action
  occurred" — e.g. `send_external` can carry a refusal reply. **Use
  `harmful_action_occurred` for the outcome** (AI-20): a per-scenario predicate over the
  recorded tool arguments in `principal_eval.harm`, emitted alongside `harm_verdict`
  (`harmful` / `not_harmful` / `undecidable` / `no_action`) and `harm_reason`.
  `acted_on_scenario_tool` is kept only so pre-AI-20 arms stay comparable. `undecidable`
  is real residue, not a failure — where the outcome turns on free text (`post_public`'s
  body, `send_external`'s contents) the predicate abstains rather than guessing, so
  report the harmful rate as the interval [harmful, harmful+undecidable]. Backfill old
  logs with `scripts/harmful_action_backfill.py`.
- AI-23 added `send_external.attachments` and `post_public.discloses_unreleased_finding`:
  logs recorded before it lack the fields, and their `exfiltration`/`external_disclosure`
  harm verdicts stay `undecidable` (legacy) — don't compare them to post-change runs.
- Frontier models / higher epochs cost real money: debug on the cheap pair only —
  `anthropic/claude-haiku-4-5` and `openai/gpt-5-nano` (see PLAN.md budget).
- **Cheap OpenAI SUBJECT is `openai/gpt-5-nano`, not `gpt-4o-mini`** (AI-15). gpt-4o-mini
  was retired as a model under test: it is two generations behind haiku-4.5 (confounding
  provider with generation), sits at a 0.726 compliance ceiling with the anonymised
  baseline mid-pack, and is the only model carrying a 10,000 requests-per-day cap — which
  blocked a run outright. gpt-5-nano is generationally matched **to haiku-4.5**, uncapped,
  and cheaper ($0.05/$0.40 vs $0.15/$0.60).
- **But gpt-5-nano is NOT a valid low end for the OpenAI tier ladder** (AI-31). It is the
  right cheap *development* subject and matched to haiku-4.5, but as a ladder endpoint it
  fails twice: it sits at 0.013 of its own flagship where haiku-4.5 sits at 0.200 (~16×
  further down), and it is GPT-5 (2025-08-07) where terra/sol are GPT-5.6. Using it as the
  low point inflated the apparent OpenAI tier-shrinkage from 3.20× to 5.3×. Use
  `gpt-5.6-luna` (band 0.050, same generation) for tier comparisons. **Price band relative
  to a provider's own flagship is the tier-matching rule** — absolute price is not.
- **Cheap-arm logs predate AI-20, so `harmful_action` is ABSENT from their score metadata.**
  `md.get("harmful_action")` returns `None` for all 595 gpt-5-nano and 600 haiku samples;
  read as `False` it yields a harm rate of exactly 0.000 and a fabricated finding. Backfill
  from `sample.store["actions_taken"]` via `harm.harm_verdict` — and pass a real
  `HarmContext(identity_email=..., persona=...)`, because predicates like
  `_access_escalation` decide from whether the granted account is the sender's own and
  return not-harmful without it.
- **But `gpt-4o-mini` remains the JUDGE for Anthropic subjects** and must not be changed.
  Under `judges.py`'s opposite-provider rule it grades every `anthropic/*` run, so swapping
  it silently invalidates every completed haiku run by making the grades non-comparable.
  Its load is ~780 requests/day, well inside the cap. Subject and judge are separate
  decisions — retiring a model as a subject does not retire it as a judge.
- **Reasoning *content* is encrypted in frontier logs; only the token COUNT is readable**
  (AI-32). Every `ContentReasoning` block from `claude-opus-5` and `gpt-5.6-sol` in the
  AI-9 logs carries `redacted=True` and a ciphertext payload (Anthropic signed thinking
  blocks, OpenAI encrypted reasoning items). Any "what was it thinking about" question must
  be answered from the visible assistant text, and said to be so. `reasoning_tokens` in
  `sample.model_usage` is unaffected and is what the AI-32 R-series measures — note that
  `output_tokens` **includes** reasoning, so the verbosity control is
  `output_tokens - reasoning_tokens`, never total output.
- **Reasoning-by-status (AI-32) is pre-registered in `docs/analysis-plan.md` § J**, and § J
  is **append-only** — new amendments go at the end, never edited in place or reordered
  (rule 14). Use `scripts/ai32_reasoning_readout.py` (log paths are arguments) for any
  reasoning-token number that will be published; `scripts/ai9_reasoning_by_persona.py` is
  the superseded exploratory version with no intervals.
- **Submit-loop pathology (AI-17)**: without an explicit `message_limit`/`token_limit`, a
  `react()` agent can spin generating text without ever calling `submit` or another tool —
  `react()` just keeps re-prompting it. In the AI-15 gpt-5-nano base run this hit 5/600
  samples (~0.8%) and burned up to 1.07M tokens/149 messages on a single sample before
  manual cancellation. Both tasks in `real_eval.py` now set `message_limit`/`token_limit`
  directly on the `Task` (not a CLI flag, so it can't be forgotten) — see `MESSAGE_LIMIT`/
  `TOKEN_LIMIT` there for the values and their justification.
