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
   - https://inspect.aisi.org.uk/ (intro page)
   - https://inspect.aisi.org.uk/tutorial.html
   - https://inspect.aisi.org.uk/options.html (CLI options: `--model`, `--epochs`, `--limit`)
   - https://inspect.aisi.org.uk/log-viewer.html (`inspect view` — you'll live in this)
   - *Why:* Task/Sample/solver/scorer is 90% of the mental model.

2. **Solvers, tools, agents** (~45 min) — how tool-using agents work:
   - https://inspect.aisi.org.uk/solvers.html
   - https://inspect.aisi.org.uk/tools.html (the `@tool` pattern used in `toy_eval.py`)
   - https://inspect.aisi.org.uk/agents.html (the `react()` agent — likely the real
     harness's solver; multi-step tool use with a submit tool)
   - *Why:* the real eval is "agent gets tools whose outputs leak identity cues".
     Note: you do **not** need a sandbox — your tools return hand-written fixtures.
   - Concept checklist — can you explain each? `Task`, `Sample`, solver chain,
     `TaskState` (messages/output/metadata), `@tool`, scorer vs metric, epochs,
     `eval()` from Python vs `inspect eval` CLI.

3. **Scorers + a real example** (~30 min):
   - https://inspect.aisi.org.uk/scorers.html (esp. model-graded + custom scorers)
   - Skim one eval in https://github.com/UKGovernmentBEIS/inspect_evals for
     conventions (a sycophancy or agentic one, e.g. `sycophancy` or `agentharm`).
   - *Why:* your headline metric comes from an LLM judge you must later validate.

4. Optional (15 min): Anthropic's *Recommended directions* — the "persona effects on
   behaviour in safety-critical settings" section, for write-up framing.
   https://alignment.anthropic.com/2025/recommended-directions/

### Hands-on (~1–1.5h)

- [ ] `cp .env.example .env`, paste in your Anthropic + OpenAI keys
- [ ] `uv run inspect eval src/principal_eval/toy_eval.py --model anthropic/claude-haiku-4-5 --epochs 3`
- [ ] `uv run inspect view` — read full transcripts; find the judge's reasoning
- [ ] Run the tool variant: `...toy_eval.py@deference_toy_tools` — watch the model
      call `lookup_directory` in the transcript
- [ ] Re-run with `--model openai/<current-mini-model>` (proves both providers wired)
- [ ] Modify something: add a 4th persona, or a second scenario Sample, and re-run.
      You're ready for tomorrow when editing the eval feels routine.

---

## Sprint (the ~16h application clock)

### Sept 1 (full day, ~8h): build the real harness
- `tools.py`: mock `read_email`, `search_files`, `lookup_directory`, `read_calendar`,
  `send_message` — identity cues live in tool *outputs*, not the user message
- `personas.py`: exec / AI safety researcher / mid-level employee / civilian /
  anonymised control — as fixture sets the tools draw from
- `scenarios/`: 6–8 scenarios, each identity-irrelevant by design
  (borderline-policy, pushback-required, escalation-required, ambiguous-sensitive-info)
- Solver: `react()` agent with the mock tools
- Judge: model-graded scorer with a written rubric →
  {COMPLIED, PARTIAL, REFUSED, PUSHED_BACK, ESCALATED}; store persona/scenario in
  metadata for later grouping
- Smoke-run everything on haiku / gpt-mini

### Sept 2 (~4h): pilot run + validation
- Full pilot: 6–8 scenarios × 5 conditions × 2 frontier models × ~10 epochs
- Hand-label ~30 episodes; report judge agreement
- Paired comparison (same scenario+epoch across personas); first plots
  (compliance rate by persona, per model)

### Sept 3 (~3h): analysis + start write-up
- Anonymisation arm analysis: do disparities collapse?
- If time, one ablation: which cue carries the effect (domain vs title vs signature)?
- Cheap extra if time: ask each model whether identity *should* affect its behaviour;
  compare stated policy vs revealed behaviour (the "hypocrisy gap")
- Draft write-up skeleton

### Sept 4 (~3h + 2h polish): write-up + submit
- 1–3 pages: exec summary → method → key graph(s) → limitations →
  next steps (probing for inferred-user-status features; model organism of secret loyalty)
- Application form answers (adapt from the project doc)
- Submit before 11:59pm PT

### Budget
Haiku / gpt-mini for all debugging; frontier models only for the real pilot runs.
Expected spend: well under £50 at pilot scale.
