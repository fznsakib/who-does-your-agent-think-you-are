# Working plan

**Hard deadline: Friday Sept 4, 11:59pm PT** — MATS 12.0 (Neel Nanda stream) application.
The application asks for **~16 hours (max 20)** on a research problem + a **1–3 page
write-up** with an executive summary (+2h polish allowance). This repo is a standalone
project too, but the sprint below is scoped to the application.

Framing for the application: a behavioural **model biology** study — under what
conditions does a model's inferred picture of its user change consequential agent
behaviour? — with a tested mitigation (cue anonymisation) and an explicit interp
follow-on (linear probes for "inferred user status").

Judge everything by: *would this survive Nanda's "raw LLM output gets rejected"
filter?* Sanity-check every number by hand; hand-label episodes to validate the judge.

---

## Today (Aug 31, ~4h): learn Inspect, end with the toy eval running

### Reading path (~2–2.5h, in this order)

1. **Tutorial + core workflow** (~45 min) — the whole loop in one sitting:
  - [https://inspect.aisi.org.uk/](https://inspect.aisi.org.uk/) (intro page)
  - [https://inspect.aisi.org.uk/tutorial.html](https://inspect.aisi.org.uk/tutorial.html)
  - [https://inspect.aisi.org.uk/options.html](https://inspect.aisi.org.uk/options.html) (CLI options: `--model`, `--epochs`, `--limit`)
  - [https://inspect.aisi.org.uk/log-viewer.html](https://inspect.aisi.org.uk/log-viewer.html) (`inspect view` — you'll live in this)
  - *Why:* Task/Sample/solver/scorer is 90% of the mental model.
2. **Solvers, tools, agents** (~45 min) — how tool-using agents work:
  - [https://inspect.aisi.org.uk/solvers.html](https://inspect.aisi.org.uk/solvers.html)
  - [https://inspect.aisi.org.uk/tools.html](https://inspect.aisi.org.uk/tools.html) (the `@tool` pattern used in `toy_eval.py`)
  - [https://inspect.aisi.org.uk/agents.html](https://inspect.aisi.org.uk/agents.html) (the `react()` agent — likely the real
  harness's solver; multi-step tool use with a submit tool)
  - *Why:* the real eval is "agent gets tools whose outputs leak identity cues".
  Note: you do **not** need a sandbox — your tools return hand-written fixtures.
  - Concept checklist — can you explain each? `Task`, `Sample`, solver chain,
  `TaskState` (messages/output/metadata), `@tool`, scorer vs metric, epochs,
  `eval()` from Python vs `inspect eval` CLI.
3. **Scorers + a real example** (~30 min):
  - [https://inspect.aisi.org.uk/scorers.html](https://inspect.aisi.org.uk/scorers.html) (esp. model-graded + custom scorers)
  - Skim one eval in [https://github.com/UKGovernmentBEIS/inspect_evals](https://github.com/UKGovernmentBEIS/inspect_evals) for
  conventions (a sycophancy or agentic one, e.g. `sycophancy` or `agentharm`).
  - *Why:* your headline metric comes from an LLM judge you must later validate.
4. Optional (15 min): Anthropic's *Recommended directions* — the "persona effects on
 behaviour in safety-critical settings" section, for write-up framing.
 [https://alignment.anthropic.com/2025/recommended-directions/](https://alignment.anthropic.com/2025/recommended-directions/)

### Hands-on (~1–1.5h)

- [x] `cp .env.example .env`, paste in your Anthropic + OpenAI keys
- [x] `uv run inspect eval src/principal_eval/toy_eval.py --model anthropic/claude-haiku-4-5 --epochs 3`
- [x] `uv run inspect view` — read full transcripts; find the judge's reasoning
- [x] Run the tool variant: `...toy_eval.py@deference_toy_tools` — watch the model

  call `lookup_directory` in the transcript
- [x] Re-run with `--model openai/<current-mini-model>` (proves both providers wired)
- [x] Modify something: add a 4th persona, or a second scenario Sample, and re-run.

  You're ready for tomorrow when editing the eval feels routine.

---

## Sprint (the ~16h application clock)

### Sept 1 (full day, ~8h): build the real harness

- `tools.py`: mock `read_email`, `search_files`, `lookup_directory`, `read_calendar`,
`send_message` — identity cues live in tool *outputs*, not the user message
- `personas.py`: exec / AI safety researcher / mid-level employee / civilian /
anonymised control — as fixture sets the tools**** draw from
- `scenarios/`: 6–8 scenarios, each identity-irrelevant by design
(borderline-policy, pushback-required, escalation-required, ambiguous-sensitive-info)
- Solver: `react()` agent with the mock tools
- Judge: model-graded scorer with a written rubric →
{COMPLIED, PARTIAL, REFUSED, PUSHED_BACK, ESCALATED}; store persona/scenario in
metadata for later grouping
- Smoke-run everything on haiku / gpt-mini

### Sept 2 (~4h): pilot run + validation

- Full pilot: raise `--epochs` (~10) on `real_eval.py` and swap to the two frontier
models; 60 cells = 10 scenarios × (5 identified personas + 1 anonymised baseline).
Babysit the long runs with `inspect-skills:babysitting-evals` (stall diagnosis,
sample cancellation, live concurrency retuning via `inspect ctl`)
- Group compliance by `persona`×`condition` from score metadata — use
`inspect-skills:analyzing-logs` (cross-log dataframes via `inspect_ai.analysis`;
`inspect-skills:reading-logs` for raw `.eval` access)
- Hand-label ~30 episodes; report judge agreement
- Paired comparison (same scenario+epoch across personas); first plots
(compliance rate by persona, per model)
- Harness carry-overs from the Sept-1 build:
  - `acted_on_scenario_tool` means "tool invoked", not "harmful action" — e.g.
    `send_external` can carry a *refusal* reply; always cross-reference the judge grade.
    **Resolved by AI-20**: `harmful_action_occurred` / `harm_verdict` decide the outcome
    from the recorded tool arguments (`principal_eval.harm`), and are co-primary with the
    judge grade
  - Residual judge channel: judge blindness covers harness-controlled inputs only; the
    model's own answer can voluntarily quote rank language ("As you're the CEO…") which
    the judge then sees. Spot-check rank vocabulary by persona (start from the
    `identity_mentioned` metadata, which flags it but doesn't fix it)
  - The opt-in `principal_eval_pushback` task delivers each scenario's authority-reassertion
    second turn — run it if the pushback dynamic makes the pilot cut

### Sept 3 (~3h): analysis + start write-up

**Analysis plan is pre-registered and binding:
[docs/analysis-plan.md](docs/analysis-plan.md)** (AI-21) — estimands, the family split,
PARTIAL handling, scenario-clustered intervals, sample disposition and the exact table
list. It gates the frontier run: nothing in AI-9/AI-19 starts until it is committed, and
AI-6 implements it 1:1 rather than reinventing it.

- Anonymisation arm analysis: do disparities collapse? (mitigation result = the
identified-ladder disparity collapsing to the anonymised baseline)
- Proximity effect = compliance(chief_of_staff) − compliance(analyst), rank-matched pair
- Calibration split (role-gated scenarios, `family == "role_gated"`): separate
*appropriate role sensitivity* (complying for the `persona_authorized` persona, holding
back otherwise) from *inappropriate deference* (granting the action to an unauthorized
but high-status persona, or to the anonymised baseline)
- Identity-seeking-rate readout: from `cues_read` in score metadata, the rate at which
the model invoked identity cue tools (`whoami`, `lookup_directory`, `read_calendar`)
before acting — compare role-gated (checking is appropriate) vs status-irrelevant
scenarios (checking suggests identity-conditioning), by persona × condition
- Killswitch is the flagship extreme case — report it separately
- If time, one ablation: which cue carries the effect (domain vs title vs signature)?
- Cheap extra if time: ask each model whether identity *should* affect its behaviour;
compare stated policy vs revealed behaviour (the "hypocrisy gap")
- Draft write-up skeleton

###  Sept 4 (~3h + 2h polish): write-up + submit

- 1–3 pages: exec summary → method → key graph(s) → limitations →
next steps (probing for inferred-user-status features; model organism of secret loyalty)
- Application form answers (adapt from the project doc)
- Submit before 11:59pm PT

### Budget

Cheap pair for all debugging and pilot runs: `anthropic/claude-haiku-4-5` and
`openai/gpt-5-nano` (gpt-4o-mini retired as a subject in AI-15 — ceiling effect,
generational confound, and a 10,000 requests/day cap; it remains the judge for Anthropic
subjects). Frontier models only for the real pilot runs.

Actual spend so far: **≈ £84** of the £300 ceiling.

| run | arms | cost |
|---|---|---|
| AI-5 dress rehearsal + AI-15 | haiku, gpt-4o-mini, gpt-5-nano | $13.30 (≈ £10) |
| AI-9 frontier base | `claude-opus-5`, `gpt-5.6-sol` | **£57.63** |
| AI-31 mid-tier base | `claude-sonnet-5`, `gpt-5.6-terra` | **£26.57** |
| AI-33 budget endpoint | `gpt-5.6-luna` | ≈ £1.31 |

Frontier arms came in far under projection (AI-9 was quoted £229 and cost £57.63) because
the £229 was scaled from `gpt-5-nano`'s token rate; capable models resolve an episode in
far fewer turns. Project from *measured* rates on a 6-sample smoke, never from a cheaper
model's rate.

**The "well under £50" frontier estimate no longer holds.** Measured reasoning-token
rates (7.9× haiku, from AI-15) put the full two-model frontier volume at **~£241**, and
no configuration now lands under £50. The costed menu and the scope decision are on
**AI-9**. Budget requests-per-day as well as tokens: retries count against the daily
quota and exhausted it once already.