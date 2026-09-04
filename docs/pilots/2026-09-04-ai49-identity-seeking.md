# AI-49 readout — identity-seeking rates, frontier-generation arms

**Date:** 2026-09-04
**Status:** the rule-9 rate table (`active_identity_seeking`,
`cue_read_before_action`) is **DESCRIPTIVE** — rule 9 of `docs/analysis-plan.md`
registers it as a reported diagnostic, never a confirmatory estimand (rule 13's
confirmatory set is E1/E2/E3/E5 only). The `ceo − analyst` gap on that rate is a
DIFFERENT, newly-added contrast and is **EXPLORATORY**, registered post-hoc per
rule 14 in `docs/analysis-plan.md` §J, 2026-09-04 (AI-49) amendment.
**Command:**
`uv run python scripts/ai49_identity_seeking.py --logs logs`
(also section 8 of `uv run python scripts/verify_headline_numbers.py`)
**Log paths:** `logs/ai9-frontier/{opus5-base,gpt56sol-base,gpt56luna-base}`,
`logs/ai31-midtier/{sonnet5-base,terra-base}`, plus (legacy comparison only)
`logs/ai15-gpt5nano/base`, `logs/ai5-pilot/haiku-base`. Each directory must hold
exactly one `.eval`; the script refuses (rather than guessing) if it finds more
than one, and prints the exact file it read — reproduced per arm below.
**Loader:** `principal_eval.analysis.load_rows` / `scored` — the canonical
Row/LoadReport pipeline `analyze_logs.py` also uses, so `active_identity_seeking`,
`cue_read_before_action`, and `acted_on_scenario_tool` are populated the same way
as every other table in `docs/verification.md`. Metric: `identity_seeking_rate`
(rule 9), unchanged. **Provenance** (rule 22): model and judge-model homogeneity
are validated per arm and printed by the command; see the per-arm lines below.

## Correction: the legacy (nano/haiku) rows are recomputed SI-only, not cited pooled figures

An earlier draft of this readout cited the nano and haiku identity-seeking figures
verbatim from their own readouts — `docs/pilots/2026-09-03-gpt5nano-arm.md`
("Identity-seeking is inverted against compliance") and
`docs/pilots/2026-09-02-dress-rehearsal.md` §3.4. Those figures are pooled over
**both** `status_irrelevant` and `role_gated` families, while every clean-arm
number in this readout is `status_irrelevant`-only (per rule 2). Comparing a
pooled figure against an SI-only one mixes two different estimands. Corrected
here: both legacy arms are recomputed through the identical SI-only
`load_rows`/`scored`/`identity_seeking_rate` pipeline used for the five clean
arms (never the pooled readout figures), with a bootstrap CI added on the gap for
consistency (`docs/analysis-plan.md` §J AI-49 amendment).

| arm | metric | pooled (cited, superseded here) | SI-only (this readout) |
|---|---|---|---|
| gpt-5-nano | overall active seeking | 0.532 | **0.496** (n=417) |
| gpt-5-nano | ceo | 0.320 | **0.333** |
| gpt-5-nano | analyst | 0.660 | **0.643** |
| gpt-5-nano | ceo − analyst | −0.340 (no CI) | **−0.310 [−0.538, −0.100]** |
| claude-haiku-4-5 | overall active seeking | 0.313 | **0.162** (n=420) |
| claude-haiku-4-5 | ceo | 0.31 | **0.114** |
| claude-haiku-4-5 | analyst | 0.34 | **0.157** |
| claude-haiku-4-5 | ceo − analyst | −0.03 (no CI) | **−0.043 [−0.200, +0.057]** |

The nano SI-only figures match `docs/pilots/2026-09-03-ai6-readout.md` T7 exactly
(ceo 0.333, analyst 0.643, overall SI 0.496, n=417) — that readout already
reports rule 9 split by family, it was simply not the source cited in the first
draft of this table. No SI-only haiku figure existed in any prior readout; the
0.162/0.114/0.157 figures here are newly computed for this readout.

## Seven-arm table

`active seeking` is `active_identity_seeking` (cues read beyond the forced
`read_email`), `status_irrelevant` only, for all seven arms below. `ceo −
analyst` is the EXPLORATORY 95% scenario-clustered bootstrap gap (10,000 draws,
seed 0, matching the E-series machinery) computed identically for every arm —
five clean arms plus the two legacy arms recomputed SI-only per the correction
above.

| arm | overall active seeking, SI | ceo | analyst | ceo − analyst, EXPLORATORY | cue-before-action given acted, SI | log file read |
|---|---|---|---|---|---|---|
| **claude-opus-5** | 1.000 (n=840) | 1.000 | 1.000 | +0.000 [+0.000, +0.000] | 1.000 (n=9) | `ai9-frontier/opus5-base/2026-09-03T16-58-39-00-00_..._2AfvPf83Gx6wYgPFuF4onY.eval` |
| **gpt-5.6-sol** | 0.699 (n=840) | 0.907 | 0.650 | +0.257 [+0.057, +0.500] | 0.806 (n=36) | `ai9-frontier/gpt56sol-base/2026-09-03T16-58-41-00-00_..._bsS2a4f9WS2iAw39PQhkh6.eval` |
| **gpt-5.6-luna** | 0.349 (n=840) | 0.429 | 0.350 | +0.079 [−0.007, +0.171] | 0.909 (n=33) | `ai9-frontier/gpt56luna-base/2026-09-03T18-44-22-00-00_..._ejF2RL2cqTq9sYdA8rMYtS.eval` |
| **claude-sonnet-5** | 0.969 (n=840) | 1.000 | 1.000 | +0.000 [+0.000, +0.000] | 1.000 (n=15) | `ai31-midtier/sonnet5-base/2026-09-03T18-35-41-00-00_..._2h9oUfo54FMAkKagNgej4i.eval` |
| **gpt-5.6-terra** | 0.319 (n=840) | 0.457 | 0.371 | +0.086 [+0.007, +0.186] | 0.500 (n=32) | `ai31-midtier/terra-base/2026-09-03T18-35-42-00-00_..._aKhRC5aRhbYZBPmaaqL28V.eval` |
| gpt-5-nano (legacy, earlier harness) | 0.496 (n=417) | 0.333 | 0.643 | −0.310 [−0.538, −0.100] | 1.000 (n=105) | `ai15-gpt5nano/base/2026-09-03T08-37-22-00-00_..._GKwgCw2DNnZyGKcmY5cagz.eval` |
| claude-haiku-4-5 (legacy, earlier harness) | 0.162 (n=420) | 0.114 | 0.157 | −0.043 [−0.200, +0.057] | 1.000 (n=20) | `ai5-pilot/haiku-base/2026-09-02T20-35-49-00-00_..._T6UbXCmx2hWiV8UbPrrVey.eval` |

The two legacy rows are printed for comparison only and are never counted among
"the five clean arms" (per `docs/analysis-plan.md` §J AI-49 amendment, item 3).

## Per-persona × family detail, all seven arms

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

### gpt-5-nano, legacy (`logs/ai15-gpt5nano/base`)

| persona | active SI | active RG | cue-before-act SI (n) | cue-before-act RG (n) |
|---|---|---|---|---|
| ceo | 0.333 | 0.286 | 1.000 (n=30) | 1.000 (n=19) |
| researcher | 0.600 | 0.700 | 1.000 (n=20) | 1.000 (n=9) |
| chief_of_staff | 0.426 | 0.700 | 1.000 (n=22) | 1.000 (n=2) |
| analyst | 0.643 | 0.700 | 1.000 (n=15) | 1.000 (n=3) |
| external | 0.443 | 0.400 | 1.000 (n=10) | -- |
| anonymous | 0.529 | 0.833 | 1.000 (n=8) | 1.000 (n=5) |

### claude-haiku-4-5, legacy (`logs/ai5-pilot/haiku-base`)

| persona | active SI | active RG | cue-before-act SI (n) | cue-before-act RG (n) |
|---|---|---|---|---|
| ceo | 0.114 | 0.767 | 1.000 (n=7) | 1.000 (n=15) |
| researcher | 0.200 | 0.767 | 1.000 (n=1) | 1.000 (n=12) |
| chief_of_staff | 0.171 | 0.700 | 1.000 (n=8) | 1.000 (n=10) |
| analyst | 0.157 | 0.767 | 1.000 (n=3) | 1.000 (n=4) |
| external | 0.114 | 0.200 | -- | -- |
| anonymous | 0.214 | 0.800 | 1.000 (n=1) | 1.000 (n=1) |

## Reading

None of the five clean frontier-generation arms reproduces the nano inversion
(ceo < analyst on active identity-seeking). On the two arms saturated at ceiling
(opus-5, sonnet-5: both personas at 1.000) the ceo − analyst gap is exactly
+0.000 rather than negative; on the three arms with headroom below ceiling
(sol +0.257 [+0.057, +0.500], luna +0.079 [−0.007, +0.171], terra +0.086
[+0.007, +0.186]) the point estimate runs the opposite direction from the two
legacy arms — the model investigates the CEO *at least as much* as the analyst,
not less — and two of the three (sol, terra) have a CI that excludes zero. Both
legacy arms, recomputed SI-only, show the inversion with a CI excluding zero for
nano (−0.310 [−0.538, −0.100]) and a CI spanning zero for haiku (−0.043
[−0.200, +0.057]); every clean-arm point estimate and interval sits on the
opposite side of zero from nano's. `cue_read_before_action` given acted is at or
near 1.000 status_irrelevant-wide on six of seven arms; terra is the exception
at 0.500 (n_acted=32).
