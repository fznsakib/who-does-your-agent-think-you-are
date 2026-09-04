# AI-49 readout — identity-seeking rates, frontier-generation arms

**Date:** 2026-09-04
**Status:** DESCRIPTIVE throughout (rule 9 of `docs/analysis-plan.md` registers
identity-seeking as a reported diagnostic, not a confirmatory estimand — rule 13's
confirmatory set is E1/E2/E3/E5 only). `docs/analysis-plan.md` is not amended by
this ticket.
**Command:**
`uv run python scripts/ai49_identity_seeking.py --logs logs`
(also section 8 of `uv run python scripts/verify_headline_numbers.py`)
**Log paths:** `logs/ai9-frontier/{opus5-base,gpt56sol-base,gpt56luna-base}`,
`logs/ai31-midtier/{sonnet5-base,terra-base}`
**Loader:** `principal_eval.analysis.load_rows` / `scored` — the canonical
Row/LoadReport pipeline `analyze_logs.py` also uses, so `active_identity_seeking`,
`cue_read_before_action`, and `acted_on_scenario_tool` are populated the same way
as every other table in `docs/verification.md`. Metric: `identity_seeking_rate`
(rule 9), unchanged.

## Six-arm table

`active seeking` is `active_identity_seeking` (cues read beyond the forced
`read_email`), `status_irrelevant` only. `ceo − analyst` is the 95%
scenario-clustered bootstrap gap (10,000 draws, seed 0, matching the E-series)
for the five clean arms computed here; the nano and haiku rows are point
estimates cited verbatim from their own readouts (no CI recomputed).

| arm | overall active seeking, SI | ceo | analyst | ceo − analyst | cue-before-action given acted, SI | source |
|---|---|---|---|---|---|---|
| **claude-opus-5** | 1.000 (n=840) | 1.000 | 1.000 | +0.000 [+0.000, +0.000] | 1.000 (n=9) | this readout |
| **gpt-5.6-sol** | 0.699 (n=840) | 0.907 | 0.650 | +0.257 [+0.057, +0.500] | 0.806 (n=36) | this readout |
| **gpt-5.6-luna** | 0.349 (n=840) | 0.429 | 0.350 | +0.079 [−0.007, +0.171] | 0.909 (n=33) | this readout |
| **claude-sonnet-5** | 0.969 (n=840) | 1.000 | 1.000 | +0.000 [+0.000, +0.000] | 1.000 (n=15) | this readout |
| **gpt-5.6-terra** | 0.319 (n=840) | 0.457 | 0.371 | +0.086 [+0.007, +0.186] | 0.500 (n=32) | this readout |
| gpt-5-nano (earlier harness) | 0.532 | 0.320 | 0.660 | **−0.340** (no CI reported) | 1.000 | `2026-09-03-gpt5nano-arm.md` §"Identity-seeking is inverted against compliance" |
| claude-haiku-4-5 (earlier harness) | 0.313 | 0.31 | 0.34 | **−0.03** (no CI reported) | 1.000 (conditional on acted) | AI-5/AI-6 readouts (`2026-09-02-dress-rehearsal.md` §3.4, `2026-09-03-ai6-readout.md` T7) |

## Per-persona × family detail, five clean arms

`SI` = status_irrelevant, `RG` = role_gated. Both signals, both families, all six
personas (`--` = no cell / no acted samples).

### opus-5 (`logs/ai9-frontier/opus5-base`)

| persona | active SI | active RG | cue-before-act SI (n) | cue-before-act RG (n) |
|---|---|---|---|---|
| ceo | 1.000 | 1.000 | 1.000 (n=8) | 1.000 (n=25) |
| researcher | 1.000 | 1.000 | -- | 1.000 (n=20) |
| chief_of_staff | 1.000 | 1.000 | -- | -- |
| analyst | 1.000 | 1.000 | -- | -- |
| external | 1.000 | 1.000 | 1.000 (n=1) | -- |
| anonymous | 1.000 | 1.000 | -- | -- |

### sol (`logs/ai9-frontier/gpt56sol-base`)

| persona | active SI | active RG | cue-before-act SI (n) | cue-before-act RG (n) |
|---|---|---|---|---|
| ceo | 0.907 | 1.000 | 1.000 (n=14) | 1.000 (n=36) |
| researcher | 0.614 | 1.000 | 1.000 (n=4) | 1.000 (n=20) |
| chief_of_staff | 0.671 | 1.000 | 1.000 (n=6) | -- |
| analyst | 0.650 | 1.000 | -- | -- |
| external | 0.700 | 0.983 | 0.222 (n=9) | -- |
| anonymous | 0.650 | 1.000 | 1.000 (n=3) | -- |

### luna (`logs/ai9-frontier/gpt56luna-base`)

| persona | active SI | active RG | cue-before-act SI (n) | cue-before-act RG (n) |
|---|---|---|---|---|
| ceo | 0.429 | 0.733 | 1.000 (n=19) | 0.600 (n=40) |
| researcher | 0.336 | 0.950 | 1.000 (n=2) | 1.000 (n=20) |
| chief_of_staff | 0.400 | 0.967 | 0.900 (n=10) | -- |
| analyst | 0.350 | 0.883 | -- | -- |
| external | 0.279 | 0.550 | -- | -- |
| anonymous | 0.300 | 0.833 | 0.000 (n=2) | -- |

### sonnet-5 (`logs/ai31-midtier/sonnet5-base`)

| persona | active SI | active RG | cue-before-act SI (n) | cue-before-act RG (n) |
|---|---|---|---|---|
| ceo | 1.000 | 1.000 | 1.000 (n=10) | 1.000 (n=32) |
| researcher | 1.000 | 1.000 | -- | 1.000 (n=20) |
| chief_of_staff | 0.964 | 1.000 | 1.000 (n=2) | -- |
| analyst | 1.000 | 1.000 | -- | -- |
| external | 0.871 | 1.000 | 1.000 (n=3) | -- |
| anonymous | 0.979 | 1.000 | -- | -- |

### terra (`logs/ai31-midtier/terra-base`)

| persona | active SI | active RG | cue-before-act SI (n) | cue-before-act RG (n) |
|---|---|---|---|---|
| ceo | 0.457 | 0.933 | 0.769 (n=13) | 0.889 (n=36) |
| researcher | 0.350 | 0.933 | 0.333 (n=6) | 1.000 (n=20) |
| chief_of_staff | 0.350 | 1.000 | 0.400 (n=10) | 1.000 (n=3) |
| analyst | 0.371 | 0.967 | -- | -- |
| external | 0.171 | 0.183 | -- | -- |
| anonymous | 0.214 | 0.850 | 0.000 (n=3) | -- |

## Reading

None of the five clean frontier-generation arms reproduces the nano inversion
(ceo < analyst on active identity-seeking). On the two arms saturated at ceiling
(opus-5, sonnet-5: both personas at 1.000) the ceo − analyst gap is exactly
+0.000 rather than negative; on the three arms with headroom below ceiling
(sol +0.257 [+0.057, +0.500], luna +0.079 [−0.007, +0.171], terra +0.086
[+0.007, +0.186]) the point estimate runs the opposite direction from nano —
the model investigates the CEO *at least as much* as the analyst, not less —
and two of the three (sol, terra) have a CI that excludes zero. The nano and
haiku point estimates (−0.340 and −0.03 respectively) sit outside every one of
the five clean-arm intervals reported here. `cue_read_before_action` given
acted is at or near 1.000 status_irrelevant-wide on four of five arms (opus-5,
sol, luna, sonnet-5); terra is the exception at 0.500 (n_acted=32).
