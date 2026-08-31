# Who Does Your Agent Think You Are?

**Identity-conditioned deference in tool-using agents.**

**Hypothesis:** Agents infer who their user is from *implicit* cues in the environment
(email address/domain, signature blocks, directory lookups, tool outputs) and become
measurably more compliant with borderline/unsafe instructions when the inferred user is
high-status — and anonymising those cues removes the effect.

## Why this matters

The most measurable precursor of "secret loyalty" (a model differentially loyal to a
specific principal) is identity-conditioned deference: does today's model already treat
"the boss" differently — complying with requests it would refuse from a civilian, or
failing to push back or escalate? If yes, the mechanism a backdoored loyalty would key
on already exists in embryo, and identity cues are exactly its trigger channel.

This is a behavioural **propensity eval** plus a tested mitigation
(identity-cue anonymisation), built in [Inspect](https://inspect.aisi.org.uk/)
(UK AISI's open-source eval framework).

## Design (pilot scale)

- **Agent:** a tool-using email/workspace assistant. User identity is never stated —
  it leaks through email domain, signature blocks, and directory/calendar artefacts in
  tool results.
- **Personas:** frontier-lab executive · AI safety researcher · mid-level employee ·
  non-technical civilian · **anonymised control** (cues stripped).
- **Scenarios (identity-irrelevant by design — correct behaviour is the same for everyone):**
  borderline-policy requests, pushback-required errors, escalation-required discoveries,
  ambiguous sensitive-info requests.
- **Metrics** per persona × scenario × model × seed: compliance rate, pushback rate,
  escalation rate, response effort/quality (validated LLM judge), and whether reasoning
  mentions the user's identity or status.
- **Intervention arm:** identical episodes with identity cues stripped/randomised.
  If disparities collapse → quantified evidence for anonymisation-by-default.
- **Interp hook (next step):** linear probes for an "inferred user status" feature on
  open-weights models; test whether it causally drives compliance.

## Repo layout

```
src/principal_eval/
├── toy_eval.py      # minimal pedagogical eval (learning Inspect)
├── tools.py         # mock email/file/directory tools that leak identity cues
├── personas.py      # identity-cue fixtures per persona
└── scenarios/       # scenario definitions
notes/               # reading notes, judge rubric drafts
logs/                # inspect eval logs (gitignored)
```

## Running

```bash
cp .env.example .env   # add your API keys
uv sync
uv run inspect eval src/principal_eval/toy_eval.py --model anthropic/claude-haiku-4-5 --epochs 3
uv run inspect view
```

See [PLAN.md](PLAN.md) for the working plan.
