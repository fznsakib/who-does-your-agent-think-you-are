# Verification map — every headline number in the MATS write-up (AI-38)

**One command reprints everything below from the logs on disk:**

```bash
uv run python scripts/verify_headline_numbers.py
```

That script wraps the committed pipelines (it reimplements no statistic); each
table below names the underlying command, the log path(s) and the readout doc
section the number was published in. Section numbers ("verify §N") refer to the
consolidated output's banners. Every number a reviewer will see in the write-up
has a row here; if a number is not in this file it must not be in the write-up.

**Determinism.** Every interval is a 10,000-draw scenario-clustered bootstrap
(analysis-plan rule 10) with the pipeline's own pinned seed — seed 0 for the
E-series / tier / pairwise scripts, seed 6 for the R-series — so repeated runs
are byte-identical.

## Guardrails (violating any of these puts a wrong number in the application)

1. **Two harm estimands exist and are never mixed in one table.** The
   *registered* 7-scenario `status_irrelevant` harm estimand (Tables 1–2) and
   the *5-scenario cross-fork-safe* one (Table 4, which drops
   `exfiltration`/`external_disclosure` per AI-23/rule 18) differ by exactly
   7/5 = 1.40× on every non-zero gap. Compliance is always 7-scenario.
2. **sol's E1 harm and E5 harm are the same number** (+0.100): `ceo` is E5's
   max and `analyst` its min at zero, so E5 is arithmetically E1. One effect,
   one row (same for luna and terra — noted per row).
3. **The OpenAI tier-shrinkage is 3.20× as a point estimate ONLY, and only
   beside the luna−sol pairwise compliance interval [−0.050, +0.271]** (which
   includes zero). The old 5.3× figure is superseded (nano endpoint: wrong
   price band, older generation, pre-AI-26 rubric) and must never be cited.
4. **The reasoning ladder is non-monotonic on all five arms**, on both the
   per-sample and per-turn ladders. "Reasoning is ordered by status" was
   withdrawn (AI-32 §4); only the ceo−analyst contrast is claimed.
5. **"Behaviourally null, internally status-sensitive" is an opus-5-only
   claim.** Sol's E1 harm interval excludes zero, so on sol the extra
   reasoning sits beside a detectable behavioural effect (AI-32 §1).

---

## Table 1 — Confirmatory E-series, five clean frontier-generation arms

Registered estimands (rule 13): E1 deference (ceo−analyst), E2 proximity
(chief_of_staff−analyst), E3 calibration (role_gated positive control), E5
anonymisation spread. `status_irrelevant` only for E1/E2/E5 (7 scenarios);
harm here is the **7-scenario registered estimand**. CI method: 95%
scenario-clustered bootstrap, 10,000 draws, seed 0. E3 runs on 3 clusters and
is **flagged unreliable** per rule 12 wherever it appears.

Command (verify §1):
`uv run python scripts/ai9_frontier_readout.py logs/ai9-frontier/opus5-base logs/ai9-frontier/gpt56sol-base logs/ai9-frontier/gpt56luna-base logs/ai31-midtier/sonnet5-base logs/ai31-midtier/terra-base`

| claim | number (95% CI) | log path | readout § |
|---|---|---|---|
| opus-5 E1, compliance — includes 0 | +0.057 [+0.000, +0.171] | `logs/ai9-frontier/opus5-base` | frontier-base §4 |
| opus-5 E1, harm — includes 0 | +0.057 [+0.000, +0.171] | 〃 | frontier-base §4 |
| opus-5 E2, both outcomes — identically zero (no variance below ceo) | +0.000 [+0.000, +0.000] | 〃 | frontier-base §4 |
| opus-5 E3, both outcomes — control works (unreliable, 3 clusters) | +0.750 [+0.250, +1.000] | 〃 | frontier-base §4 |
| opus-5 E5 = its E1 on both outcomes (max=ceo, min=analyst) — one effect | +0.057 [+0.000, +0.171] | 〃 | frontier-base §4 |
| opus-5 overall SI compliance (the floor) | 0.010 | 〃 | frontier-base §4 |
| sol E1, **harm** — the one distinct frontier AI-9 effect clearing zero | **+0.100 [+0.007, +0.229]** | `logs/ai9-frontier/gpt56sol-base` | frontier-base §1, §4 |
| sol E1, compliance — includes 0 | +0.036 [+0.000, +0.093] | 〃 | frontier-base §4 |
| sol E2 — includes 0 (harm / compliance) | +0.043 [+0.000, +0.100] / +0.029 [+0.000, +0.086] | 〃 | frontier-base §4 |
| sol E3, compliance / harm (unreliable, 3 clusters) | +0.917 [+0.750, +1.000] / +0.933 [+0.800, +1.000] | 〃 | frontier-base §4 |
| sol E5 harm **= its E1 harm — one row, not two effects** (E5 compliance +0.036, includes 0) | +0.100 [+0.007, +0.229] | 〃 | frontier-base §4 |
| sol overall SI compliance (the floor) | 0.011 | 〃 | frontier-base §4 |
| sol E1 harm rests substantially on `safety_bypass` (ceo cell 0.45); opus-5's entire harm signal is one cell (`killswitch`/ceo, 8/140) | per-scenario table, n=20/cell, illustrative | 〃 | frontier-base §4 |
| sonnet-5 E1, both outcomes — includes 0 | +0.071 [+0.000, +0.214] | `logs/ai31-midtier/sonnet5-base` | midtier-addendum §3 |
| sonnet-5 E2, both outcomes — includes 0 | +0.014 [+0.000, +0.043] | 〃 | midtier-addendum §3 |
| sonnet-5 E3, both outcomes (unreliable, 3 clusters) | +0.867 [+0.600, +1.000] | 〃 | midtier-addendum §3 |
| sonnet-5 E5 = its E1 (both outcomes) — one effect | +0.071 [+0.000, +0.214] | 〃 | midtier-addendum §3 |
| terra E1, compliance — includes 0; sign-stable at PARTIAL 0/0.5/1 (+0.064/+0.068/+0.071) | +0.068 [+0.000, +0.182] | `logs/ai31-midtier/terra-base` | midtier-addendum §3 |
| terra E1, **harm** — excludes 0 | **+0.093 [+0.007, +0.207]** | 〃 | midtier-addendum §3 |
| terra E2 — includes 0 (compliance / harm) | +0.025 [+0.000, +0.057] / +0.071 [+0.000, +0.186] | 〃 | midtier-addendum §3 |
| terra E3, compliance / harm (unreliable, 3 clusters). **Note:** midtier-addendum §3 published +0.907 / +0.923 [+0.770, +1.000] — computed before the ai33-luna-endpoint §0 fix (the pre-fix `e3()` pooled anonymised rows into "unauthorized"); the corrected values, which the command reproduces, are these. E1/E2/E5 are unaffected by that fix | +0.904 [+0.763, +1.000] / +0.921 [+0.763, +1.000] | 〃 | midtier-addendum §3, ai33-luna-endpoint §0 |
| terra E5 harm = its E1 harm — one effect (E5 CI [+0.007, +0.229]; compliance +0.068, includes 0) | +0.093 | 〃 | midtier-addendum §3 |
| luna E1 — **first frontier-generation arm where BOTH co-primaries exclude zero** (compliance / harm) | **+0.114 [+0.007, +0.300]** / **+0.136 [+0.007, +0.336]** | `logs/ai9-frontier/gpt56luna-base` | ai33-luna-endpoint §4 |
| luna E2 — includes 0 (compliance / harm) | +0.057 [+0.000, +0.157] / +0.071 [+0.000, +0.171] | 〃 | ai33-luna-endpoint §4 |
| luna E3, compliance / harm (unreliable, 3 clusters) | +0.942 [+0.875, +1.000] / +1.000 [+1.000, +1.000] | 〃 | ai33-luna-endpoint §4 |
| luna E4 (external−analyst) — no signal | +0.000 [+0.000, +0.000] | 〃 | ai33-luna-endpoint §4 |
| luna E5 = its E1 (both outcomes) — one effect | +0.114 / +0.136 | 〃 | ai33-luna-endpoint §4 |
| Headline reading: the deference ladder does not reproduce at the frontier — a null licensed by E3 working (0.625–1.000 authorised vs 0.000 unauthorised) | qualitative, from the rows above | all five dirs | frontier-base §1 |

## Table 2 — Validation and diagnostic numbers shipped beside Table 1

Same command and log paths as Table 1 (verify §1). Rule 6 requires the
cross-tab in both directions; rule 21 requires the rank-vocabulary rate beside
every judge-derived headline.

| claim | number | readout § |
|---|---|---|
| The judge undercounts harm on OpenAI models, not Anthropic: harmful-but-not-COMPLIED = sol **19**, terra **22**, opus-5 **0**, sonnet-5 **0** | 19 / 22 / 0 / 0 | frontier-base §6, midtier-addendum §4 |
| luna, same direction, SI family: 7 harmful without COMPLIED (26 with); RG family 4 (56 with). The command prints both the all-family tab (11) and the per-family split | 7 (SI) | ai33-luna-endpoint §3 |
| Judge channel is open (rule 21, `identity_mentioned`): opus-5 1.000 on every identified persona; sol high; sonnet-5 ≈1.000; terra high; luna 0.264–0.671. **Note:** the frontier-base §6 / midtier-addendum §4 tables predate the ai33-luna-endpoint §0 fix (they pooled `role_gated` rows in), so the verify output's SI-only values differ slightly from those two docs (e.g. opus-5 anonymous 0.707 vs 0.700, sol ceo 0.921 vs 0.945); the luna doc already uses the corrected SI-only values, which are what the command now prints for every arm. The qualitative claim (channel substantially open) is unchanged. **Second note (AI-38 finding):** midtier-addendum §4's *terra* column (0.945 / 0.730 / 0.975 / 0.440) duplicates *sol's* frontier-base §6 values; terra's actual SI-only rates are ceo 0.493, analyst 0.364, external 0.871, anonymous 0.057 — the write-up must use the command's output, not that column | per-persona tables | frontier-base §6, midtier-addendum §4, ai33-luna-endpoint §0, §4 |
| Fusion rate 0.000 on every persona, all five arms — the rule-16 sensitivity is a no-op | 0.000 | frontier-base §4, midtier-addendum §2, ai33-luna-endpoint §3 |
| Disposition: 0 excluded samples on all five arms (1200/1200 each); rule-15 bounds equal the point estimates | 0 | frontier-base §3, midtier-addendum §2, ai33-luna-endpoint §3 |
| Judge-parse fallbacks: 0 across all arms (every explanation carries `GRADE:`) | 0 | frontier-base §3 |
| PARTIAL sensitivity: sign-stable everywhere; terra produced the project's first 5 PARTIAL grades | sign-stable | frontier-base §4, midtier-addendum §3 |

## Table 3 — R-series: reasoning expenditure by inferred user status

Pre-registered in `docs/analysis-plan.md` §J (append-only). CI method: 95%
scenario-clustered bootstrap, 10,000 draws, **seed 6**, contrasts paired
within each resample; n = 140 per persona cell, SI only. Status is part of
the estimand: **exploratory** for the AI-9 arms that motivated the effect,
**confirmatory** for the arms that did not. Reasoning *content* is
provider-encrypted on every arm — token counts only (mechanism-unexplained).

Commands (verify §2–4):

```bash
uv run python scripts/ai32_reasoning_readout.py logs/ai9-frontier/opus5-base logs/ai9-frontier/gpt56sol-base --status exploratory
uv run python scripts/ai32_reasoning_readout.py logs/ai31-midtier/sonnet5-base logs/ai31-midtier/terra-base --status confirmatory
uv run python scripts/ai32_reasoning_readout.py logs/ai9-frontier/gpt56luna-base --status confirmatory
```

| claim | number (95% CI) | log path | readout § |
|---|---|---|---|
| opus-5 R1 (ceo−analyst, per sample) — exploratory | **+98.6% [+61.1%, +139.4%]** (+104.0 tok [61.3, 153.3]) | `logs/ai9-frontier/opus5-base` | ai32-reasoning-status §1 |
| opus-5 R2 (per turn) — survives; turns gap only +6.5% | +84.5% [+53.8%, +124.5%] | 〃 | ai32-reasoning-status §1–2 |
| opus-5 R3 (visible output) — grows ~5× slower than reasoning | +19.5% [+10.6%, +28.9%] | 〃 | ai32-reasoning-status §3 |
| opus-5 R6 verdict | survivor (exploratory) | 〃 | ai32-reasoning-status §1 |
| **Opus-5-only contrast sentence**: behaviourally null (E1/E2 include 0 on both outcomes) while reasoning is status-sensitive — guardrail 5 | qualitative | 〃 + Table 1 | ai32-reasoning-status §1 |
| sol R1 — exploratory | +49.1% [+32.8%, +64.0%] | `logs/ai9-frontier/gpt56sol-base` | ai32-reasoning-status §1 |
| sol R2 per turn | +28.6% [+10.1%, +50.3%] | 〃 | ai32-reasoning-status §1 |
| sol R3 per turn — flat | +0.7% [−5.0%, +5.8%] | 〃 | ai32-reasoning-status §3 |
| sol R6 verdict | survivor (exploratory) | 〃 | ai32-reasoning-status §1 |
| terra R1 — confirmatory | **+42.8% [+22.1%, +61.0%]** | `logs/ai31-midtier/terra-base` | ai35-reasoning-confirmatory §1 |
| terra R2 per turn | +25.5% [+12.3%, +38.1%] | 〃 | ai35-reasoning-confirmatory §1 |
| terra R3 per sample / per turn | +6.8% [+1.6%, +13.5%] / −1.0% [−4.2%, +2.2%] | 〃 | ai35-reasoning-confirmatory §1 |
| terra R6 verdict | **survivor (confirmatory, mechanism-unexplained)** | 〃 | ai35-reasoning-confirmatory §1, §5 |
| sonnet-5 R1 — confirmatory | +38.4% [+22.9%, +53.5%] | `logs/ai31-midtier/sonnet5-base` | ai35-reasoning-confirmatory §1 |
| sonnet-5 R2 per turn | +36.1% [+20.4%, +53.7%] | 〃 | ai35-reasoning-confirmatory §1 |
| sonnet-5 R3 per sample — overlaps its R1, so the override fires | +22.8% [+12.3%, +33.0%] | 〃 | ai35-reasoning-confirmatory §1–2 |
| sonnet-5 R6 verdict | verbosity, not deliberation (confirmatory) | 〃 | ai35-reasoning-confirmatory §1 |
| luna R1 — confirmatory | +29.2% [+5.5%, +50.3%] | `logs/ai9-frontier/gpt56luna-base` | ai35-reasoning-confirmatory §1 |
| luna R2 per turn | +13.1% [+0.8%, +25.2%] | 〃 | ai35-reasoning-confirmatory §1 |
| luna R3 per sample — includes 0; the override fires on interval width (defect logged as AI-36, verdict stands) | +6.5% [−3.3%, +16.6%] | 〃 | ai35-reasoning-confirmatory §1–2 |
| luna R6 verdict | verbosity, not deliberation (confirmatory) | 〃 | ai35-reasoning-confirmatory §1 |
| **Headline: R1 positive with interval clear of zero on all five arms, both providers, three tiers; R2 passed on all five** | see rows above | all five dirs | ai35-reasoning-confirmatory §3 |
| Mechanism claim carries exceptions: survivors opus-5/sol/terra; sonnet-5 genuinely fails; luna fails on interval width only. **No tier story** — the split runs across providers and tiers | 3 of 5 | 〃 | ai35-reasoning-confirmatory §2–3 |
| **Ladder NOT monotonic on any of the five arms, either ladder** (guardrail 4); `chief_of_staff → researcher` breaks on all five — a fixture-order lead, not a model finding | R4 tables | 〃 | ai32-reasoning-status §4, ai35-reasoning-confirmatory §4 |
| R8 independent recomputation reconciles exactly (0.0) on all five arms | e.g. opus-5 +98.5509% both paths | 〃 | ai32-reasoning-status §7, ai35-reasoning-confirmatory §6 |

## Table 4 — Cross-model tier comparison (DESCRIPTIVE, never confirmatory)

Two commands. The tier table's harm column is the **5-scenario cross-fork-safe
estimand** (drops `exfiltration`/`external_disclosure` on every arm per AI-23;
inflates non-zero gaps by exactly 7/5 vs Table 1 — guardrail 1, which is why
no row below repeats a Table 1 harm number). nano/haiku harm is **backfilled**
from `sample.store["actions_taken"]` via the live predicate with a real
`HarmContext`; both sit on the pre-AI-16 side of the harness fork and are
labelled legacy cross-references, never ladder endpoints.

Commands (verify §5–6):

```bash
uv run python scripts/ai31_tier_table.py --logs logs
uv run python scripts/ai33_cross_model_bootstrap.py --logs logs
```

(Both default to the repository's `logs/` directory; `--logs` or
`AI31_LOG_ROOT` override it. The verify script pins both to its own `--logs`.)

Log paths: the five Table 1 dirs plus `logs/ai15-gpt5nano/base` and
`logs/ai5-pilot/haiku-base`.

| claim | number (95% CI) | readout § |
|---|---|---|
| **OpenAI tier shrinkage, compliance, point estimates only: luna +0.114 → terra +0.068 → sol +0.036 = 3.20× — citable ONLY beside the next row** (guardrail 3; 5.3× is superseded and must never appear) | 3.20× | ai33-luna-endpoint §1, §6 |
| luna − sol pairwise compliance difference — **includes 0** | +0.079 [−0.050, +0.271] | ai33-luna-endpoint §6 |
| luna − terra / terra − sol pairwise compliance — include 0 | +0.046 [−0.007, +0.121] / +0.032 [−0.054, +0.150] | ai33-luna-endpoint §6 |
| luna − terra / terra − sol / luna − sol pairwise harm (5 scen.) — include 0 | +0.060 [+0.000, +0.180] / −0.010 [−0.160, +0.180] / +0.050 [−0.160, +0.360] | ai33-luna-endpoint §6 |
| sonnet-5 − opus-5 pairwise (compliance / harm 5 scen.) — include 0 | +0.014 [+0.000, +0.043] / +0.020 [+0.000, +0.060] | ai33-luna-endpoint §6 |
| nano − luna, haiku − sonnet-5 (cross-fork, rule 18 — completeness only) — include 0 | +0.076 [−0.050, +0.218] & +0.121 [−0.101, +0.361]; −0.014 [−0.214, +0.171] & −0.020 [−0.300, +0.240] | ai33-luna-endpoint §6 |
| **Verdict: every pairwise cross-model contrast, both co-primaries, includes zero — neither provider's ladder shows a statistically distinguishable slope** | all 12 include 0 | ai33-luna-endpoint §1, §6 |
| Harm E1, 5-scenario cross-fork-safe ladder: nano +0.311 [+0.065, +0.520] (backfilled) → luna +0.190 [+0.010, +0.460] → terra +0.130 [+0.010, +0.280] → sol +0.140 [+0.010, +0.310]; haiku +0.080 [+0.000, +0.240] (backfilled) → sonnet-5 +0.100 [+0.000, +0.300] → opus-5 +0.080 [+0.000, +0.240] — **non-monotonic on OpenAI, mid-above-both-ends on Anthropic; never mixed with Table 1's 7-scenario numbers** | see row | ai33-luna-endpoint §5, midtier-addendum §1, §6 |
| Load-bearing clean step, mid → flagship: OpenAI 1.90× / 0.93× (comp/harm), Anthropic 1.25× / 1.25× | ratios | midtier-addendum §7 |

## Table 5 — gpt-5-nano cheap arm (E1 deference + paired pushback flip)

The nano arm is the pre-AI-16 fork (legacy): its numbers are quoted as the
cheap-tier pilot result, never as a point on the clean ladder. CI method: 95%
scenario-clustered bootstrap, 10,000 draws. Pushback pairing is
within-transcript (`first_grade`, AI-18), read against the base-vs-base null
floor computed over the six pushback scenarios.

Command (verify §7):
`uv run python scripts/analyze_logs.py logs/ai15-gpt5nano/base logs/ai18-backfill/gpt5nano-pushback`

| claim | number (95% CI) | log path | readout § |
|---|---|---|---|
| nano E1 deference gap (SI compliance) | **+0.190 [+0.023, +0.371]** | `logs/ai15-gpt5nano/base` | ai6-readout T3 |
| nano E2 proximity (leadership-proximity bundle, never "rank held constant") | +0.121 [+0.024, +0.250] | 〃 | ai6-readout T3 |
| nano E4 external−analyst (reported separately, not confirmatory) | −0.129 [−0.257, −0.043] | 〃 | ai6-readout T3 |
| nano E5 identified-ladder spread — not collapsed (interval clear of 0) | 0.319 [0.094, 0.603] | 〃 | ai6-readout T6 |
| nano harmful-action rate, SI. **Not a 95% CI**: a rule-17 partial-identification bound, `harmful/n` to `(harmful+undecidable)/n`, with no resampling — it states classification ambiguity, not sampling uncertainty | bounds [0.189, 0.194] (n=417) | 〃 | ai6-readout T2 |
| nano judge-vs-harm disagreement: judge missed 34 harmful; 3 COMPLIED-not-harmful | 34 / 3 | 〃 | ai6-readout T2 |
| **Paired pushback flip toward compliance vs null floor: 17.1% vs 9.0% (~1.9×) — the signal; raw paired flip 47.6% vs null 50.6% is churn, not signal** | 17.1% vs 9.0% | `logs/ai18-backfill/gpt5nano-pushback` (+ base) | ai6-readout, pushback § |
| Pushback group means (before → after, matched cells) | 0.171 → 0.276 | 〃 | ai6-readout, pushback § |
| nano disposition: base 3 SI errors excluded (all 5 total errors in high-status cells — ceo 3, cos 2); worst-case bound moves E1 ≤ +0.050, sign survives | bounds | `logs/ai15-gpt5nano/base` | ai6-readout T8, midtier-addendum §6 |

## Figures

```bash
uv run python scripts/fig1_compliance_by_persona.py   # docs/pilots/figures/fig1_*
uv run python scripts/fig2_reasoning_forest.py        # docs/pilots/figures/fig2_*
uv run python scripts/fig3_scenario_heatmap.py        # docs/pilots/figures/fig3_*
```

Fig 1: compliance by persona, SI only, per model — five clean arms plus
gpt-5-nano as a visually-separated legacy panel; n per cell, clustered CIs.
Fig 2: forest of R1 across the five arms, split exploratory vs confirmatory,
with the R6 verdict per arm. Both reuse the pipelines above (Table 1's loader
and the R-series module); neither reparses logs by hand.

Fig 3: the CEO−analyst harm gap, one scenario at a time, five clean arms plus
gpt-5-nano as a labelled legacy column (its two AI-23-excluded scenarios
blanked `n/a`). ILLUSTRATIVE — n = 20 per cell, no intervals — the registered
estimand is Table 1's pooled E1. Reuses `ai31_tier_table.load()` (Table 1's
loader) with the AI-23 exclusion lifted for the five clean arms, which carry
`harmful_action` natively on all seven scenarios; refuses to run against an
arm directory holding more than one `.eval` file, the same failure mode
`reasoning_report` refuses for Figure 2.

Command (log paths as Table 1 plus `logs/ai15-gpt5nano/base`; not part of
`verify_headline_numbers.py`'s sections, same as Figs 1–2):
`uv run python scripts/fig3_scenario_heatmap.py --logs logs`

Exactness check (printed by the script): each clean arm's seven per-scenario
harm gaps average exactly (to 3 d.p.) to that arm's published Table 1 pooled
E1 harm — opus-5 0.400/7 = 0.057, sonnet-5 0.500/7 = 0.071, sol 0.700/7 =
0.100, terra 0.650/7 = 0.093, luna 0.950/7 = 0.136. All five PASS; the script
exits nonzero if any fails.
