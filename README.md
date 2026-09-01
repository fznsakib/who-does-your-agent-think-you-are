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

## Running the real harness

Smoke (one scenario):  `uv run inspect eval src/principal_eval/real_eval.py --model anthropic/claude-haiku-4-5 --limit 6`
Full matrix (42 cells): `uv run inspect eval src/principal_eval/real_eval.py --model <provider/model> --epochs 1`
View transcripts:       `uv run inspect view`
Override the judge:     add `-T judge_model=openai/gpt-4o-mini`

Design: 5-persona status ladder (ceo ▸ researcher ▸ mid_high_prox ▸ mid_low_prox ▸ external)
× anonymisation transform (identified vs one shared anonymised baseline) × 7 scenarios.
Full design: docs/superpowers/specs/2026-09-01-inferred-user-status.md

### Downstream ripples (Sept 2–4)
- Pilot (Sept 2): raise `--epochs` (~10) and swap to the two frontier models; group compliance
  by `persona`×`condition` from score metadata; hand-label ~30 episodes vs the judge grade.
- The proximity effect is read as compliance(mid_high_prox) − compliance(mid_low_prox).
- The mitigation result is the identified-ladder disparity collapsing to the anonymised baseline.
- Killswitch is the flagship extreme case — report it separately.
- Residual judge channel: `persona_scorer` grades `state.output.completion`, and judge blindness
  only covers harness-controlled inputs (the judge prompt never contains persona/condition). It
  does not stop the model's own answer text from voluntarily quoting rank language (e.g. "As
  you're the CEO…"), which a "blind" judge would still see. Acknowledged, not coded around —
  spot-check rank vocabulary by persona in the pilot analysis (the existing `identity_mentioned`
  keyword-scan metadata is a starting point for that spot-check, not a fix for the channel itself).

See [PLAN.md](PLAN.md) for the working plan.
