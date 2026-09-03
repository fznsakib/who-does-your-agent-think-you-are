# AI-6 — analysis pipeline and hand-labelling enablement

**Date:** 2026-09-03
**What this is:** the tooling AI-6 asked for, not a results readout. Run it against
`logs/ai15-gpt5nano/{base,pushback}` (the load-bearing arm) once you're ready to produce
numbers for the write-up.

## 1. Hand-labelling (faiz's tool)

Two steps: build a stratified sample manifest, then run a local page to grade it.

```bash
uv run python scripts/ai6_sample_for_labelling.py \
    logs/ai15-gpt5nano/base logs/ai15-gpt5nano/pushback \
    --n 60 --out docs/pilots/data/ai6-manifest.json

uv run python scripts/ai6_label_server.py \
    --manifest docs/pilots/data/ai6-manifest.json \
    --out docs/pilots/data/ai6-hand-labels.csv
```

The server opens `http://127.0.0.1:8765/` in your browser. One episode at a time:
read the transcript, pick a grade (`1`–`5` or click), toggle identity-fusion language
with `F` if the model speaks as the sender ("I am a.rivera…"), add a note if useful, hit
Enter to save. The judge's grade only appears **after** you submit — you never see it
first. It's resumable: quitting and re-running the same command skips whatever's already
in the CSV.

When the manifest is exhausted the page shows raw agreement, Cohen's kappa, and the
human-verified fusion rate. Regenerate that summary any time without re-labelling:

```bash
uv run python scripts/ai6_label_summary.py docs/pilots/data/ai6-hand-labels.csv
```

### Sampling

`--n` defaults to 60 (midpoint of the ticket's 50–100 range). The sampler
(`src/principal_eval/ai6_sampling.py`) fills quotas in this order before topping up for
scenario/persona/condition coverage breadth:

| Stratum | Default share | Why |
|---|---|---|
| `harmful_disagreement` | 20% | Judge grade vs. AI-20's `harmful_action_occurred` disagree — **redistributed to the other three quotas for any log that predates AI-20** (the field is scored in, not derivable after the fact, so old logs never carry it), since the field is absent there |
| `role_gated` | 15% (→ ~22% on pre-AI-20 logs) | The ceo-gate inversion lead lives here |
| `whoami_caller` | 15% (→ ~22%) | The only episodes where identity fusion can occur |
| `partial_grade` | 25% (→ ~35%) | Where the judge is least trustworthy today |

AI-20 has merged (`principal_eval.harm`), so any **new** run of `principal_eval`/
`principal_eval_pushback` carries `harmful_action_occurred` in score metadata and the
`harmful_disagreement` stratum activates automatically — no code change needed. The
existing `logs/ai15-gpt5nano/{base,pushback}` logs were scored before AI-20 landed, so
they still don't carry the field (scoring happens at eval time, not on read), and the
sampler still redistributes their share. Re-run the eval, then re-run
`ai6_sample_for_labelling.py`, to get a labelling pass that covers this axis.

### Blindness

The manifest carries the judge's grade for bookkeeping, but the label server strips it
(`_judge_grade`) before the transcript ever reaches the browser — see
`LabelState.next_episode` in `scripts/ai6_label_server.py`. It only comes back in the
`/api/submit` response, after your grade is already recorded.

## 2. Analysis pipeline

```bash
uv run python scripts/ai6_analysis.py \
    logs/ai15-gpt5nano/base logs/ai15-gpt5nano/pushback \
    --out-json docs/pilots/data/ai6-report.json
```

Accepts any mix of `.eval` files and directories; groups everything by the model under
test and computes the full checklist per model. One call across all of a model's base +
pushback logs is enough — you don't need to run it once per scenario or persona.

### What each section is

| Key | Ticket item |
|---|---|
| `headline_table_status_irrelevant` | persona × condition, headline table |
| `deference_gap_by_rung` | deference gap by rung, with scenario-clustered bootstrap CI |
| `proximity_effect` | chief_of_staff − analyst, worded as a leadership-proximity bundle |
| `anonymisation_collapse` | identified-ladder spread vs. the anonymised baseline |
| `calibration_split_role_gated` | appropriate role sensitivity vs. inappropriate deference |
| `identity_seeking_rate` | AI-14's active-cue definition, role_gated vs. status_irrelevant, by persona |
| `killswitch_separate` | reported on its own, never folded into the headline |
| `pushback_paired_flip` | paired within-transcript flip once AI-18 lands; falls back to the AI-15 epoch-matched method (explicitly flagged `UNPAIRED`) until then |
| `harmful_action_rates` | co-primary harmful-rate INTERVAL (`[harmful, harmful+undecidable]`, AI-20 rule 17) + judge disagreement cross-tab, split by family |
| `fusion_robustness` | headline with vs. without fusion-flagged samples, once AI-16 lands |
| `partial_sensitivity` | headline compliance at PARTIAL = 0, 0.5, 1 |
| `nonterminating` | errored/cancelled samples, reported separately with worst-case bounds |
| `rank_vocabulary_spot_check` | `identity_mentioned` rate by persona — flags where to spot-check transcripts by hand, doesn't read them itself |

Every bootstrap interval resamples **scenario keys** with replacement (not individual
rows) — see `bootstrap_ci` in `src/principal_eval/ai6_analysis.py`. 10 scenarios × N
epochs are repeated draws of the same 10 scenarios, not 10N independent situations; a
row-level bootstrap would understate every interval.

### Reconciling with sibling PRs

This was built before AI-16/17/18/20/21/24 landed, against guessed metadata field names.
**Reconciled 2026-09-03** once AI-16/17/18/21/24 actually merged — none of the guesses
were quite right, which is exactly why this was built parameterized rather than wired in
directly:

- **AI-16 (fusion)** didn't add score metadata at all. `fusion.fusion_flag` is a
  standalone reviewed function over assistant text (AI-16 also shipped its own readout,
  `scripts/ai16_fusion_readout.py` / `docs/pilots/2026-09-03-fusion-readout.md`, with the
  first real numbers: haiku 22.5% of whoami-callers fused, gpt-5-nano 0%). `ai6_analysis.py`
  calls `fusion_flag` directly on each sample's transcript in `load_rows`, so
  `fusion_robustness` is always computed rather than gated behind `"available"`.
- **AI-17 (runaway-loop bounding)** didn't add a disposition metadata key either — it
  bounds samples with `message_limit`/`token_limit` on the `Task`, and Inspect's own
  `sample.limit` (an `EvalSampleLimit`) marks a hit. Per `real_eval.py`'s own comment, a
  limit hit "yields a normal limit/limit_reason-tagged sample" that's still gradeable, so
  it's counted in the headline like any other row — `nonterminating_report` only surfaces
  it (`n_limit_hit_status_irrelevant`, its own mean compliance) for transparency. The
  worst-case-bounds treatment is reserved for the OTHER disposition: a hard `sample.error`
  with no score at all, which is the only kind possible in the current gpt-5-nano/haiku
  logs (they predate AI-17).
- **AI-18 (paired pushback)** stores the first-turn grade as `first_grade` in score
  metadata, not `first_turn_grade` — fixed in `PAIRED_PUSHBACK_KEYS`.
- **AI-20 (harmful action)** merged with three metadata keys: `harmful_action` and
  `harmful_action_undecidable` are the canonical pair the analysis plan pre-registers
  (rule 6), and `harmful_action_occurred` is kept as an alias equal to `harmful_action`.
  `harmful_action_rates` was rewritten to report the harmful-rate as an INTERVAL
  (`[harmful_rate, harmful_rate + undecidable_rate]`, rule 17 — undecidable is residue,
  never folded into either side) split by family, matching AI-20's own review finding
  that pooling inflated gpt-5-nano's ceo reading from 0.377 (status_irrelevant) to 0.679
  (pooled with role_gated). The existing gpt-5-nano/haiku logs still report
  `"available": false` for this section — they were scored before AI-20 landed, so they
  never got the field; only a fresh run picks it up.

The lesson: even "parameterize now, reconcile later" needs the reconciliation pass done
by hand against the real diff, not assumed correct because the tests pass — the tests
only proved the None-vs-present *branches* worked, not that the guessed key *names*
would ever match. See the module docstring in `src/principal_eval/ai6_analysis.py` for
the up-to-date field mapping.

### Sanity-check helpers

`sanity_check_cell(rows, persona, condition, scenario)` in `ai6_analysis.py` returns the
raw grade list plus the tool-call cross-reference for one cell — for the "recompute by
hand" checklist item. Not wired into the CLI (it's a one-off verification step, not a
report section); call it from a REPL:

```python
from principal_eval.ai6_analysis import load_rows, sanity_check_cell
rows = load_rows(["logs/ai15-gpt5nano/base/<file>.eval"]).rows
sanity_check_cell(rows, "ceo", "identified", "killswitch")
```

## 3. Why `inspect_ai.log` instead of `inspect_ai.analysis` dataframes

The ticket points at `inspect-skills:analyzing-logs` (`inspect_ai.analysis` dataframes)
for the cross-log work here. This pipeline instead extends the row-flattening pattern
already proven in `scripts/ai5_validate_and_readout.py` (`inspect_ai.log` +
hand-rolled aggregation), for two reasons: it reuses code already validated against these
exact logs, and it avoids adding `pandas`/`pyarrow` as new project dependencies for a
one-scorer eval where `samples_df`'s main value (exploding multi-scorer columns) doesn't
apply. If the dataframe surface is preferred going forward — e.g. for AI-7's figures,
where `prepare()`'s plotting helpers would pay for themselves — flag it and this loader
can be swapped for `samples_df` without touching the checklist functions above, since
they only depend on the flat `Row` shape.
