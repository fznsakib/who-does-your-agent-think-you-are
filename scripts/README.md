# scripts/

23 scripts. Every script appears in exactly one table below.

## Live entry points

These are the pipelines a reviewer runs. Each is wrapped by
`verify_headline_numbers.py` or produces one of the committed figures; see
[docs/verification.md](../docs/verification.md) for the full claim-to-number
map.

| Script | Feeds |
|---|---|
| `verify_headline_numbers.py` | The whole verification map: wraps every command below and reprints Tables 1-5 in one run. |
| `ai9_frontier_readout.py` | verify §1, Tables 1-2 (confirmatory E-series, five clean frontier-generation arms). |
| `ai32_reasoning_readout.py` | verify §2-4, Table 3 (R-series reasoning expenditure). |
| `ai31_tier_table.py` | verify §5, Table 4 (cross-model tier comparison, descriptive). |
| `ai33_cross_model_bootstrap.py` | verify §6, Table 4 (pairwise cross-model bootstrap). |
| `analyze_logs.py` | verify §7, Table 5 (gpt-5-nano cheap arm). |
| `fig1_deference_forest.py` | Figures: `docs/pilots/figures/fig1_deference_forest.*` — the headline figure, the CEO-analyst gap as one forest across both provider ladders. Not wired into `verify_headline_numbers.py`; prints its own PASS/FAIL against `docs/verification.md`. |
| `fig1_compliance_by_persona.py` | Figures: `docs/pilots/figures/fig1_compliance_by_persona.*`, compliance by persona — now an appendix figure. Not wired into `verify_headline_numbers.py`. |
| `fig2_reasoning_forest.py` | Figures: `docs/pilots/figures/fig2_*`, R1 forest plot. Not wired into `verify_headline_numbers.py`. |
| `fig3_scenario_heatmap.py` | Figures: `docs/pilots/figures/fig3_*`, per-scenario CEO-analyst harm gap. Not wired into `verify_headline_numbers.py`. |
| `ai40_act_then_hedge.py` | `docs/pilots/2026-09-03-ai40-act-then-hedge.md`, a descriptive robustness check outside the pre-registered analysis plan. Not wired into `verify_headline_numbers.py`. |

## Pilot readouts

Each of these backs one dated pilot doc and is not part of the reproduction
chain above.

| Script | Cited by |
|---|---|
| `ai5_cue_isolation_check.py` | `docs/pilots/2026-09-02-dress-rehearsal.md` (§4, cue-isolation spot-check). |
| `ai5_frontier_projection.py` | `docs/pilots/2026-09-02-dress-rehearsal.md` (§4, frontier cost projection). |
| `ai5_quota_probe.py` | `docs/pilots/2026-09-02-dress-rehearsal.md` (rate-limit probe ahead of a run). |
| `ai5_validate_and_readout.py` | `docs/pilots/2026-09-02-dress-rehearsal.md` (log validation and per-model readout); also cited by `docs/analysis-plan.md` and `docs/analysis-and-hand-labelling.md`. Its loader is the pattern `ai16_fusion_readout.py` and `ai31_tier_table.py` follow: read the header with `read_eval_log(path, header_only=True)`, then stream samples with `read_eval_log_samples`. |
| `ai16_fusion_readout.py` | `docs/pilots/2026-09-03-fusion-readout.md`; also cited by `docs/analysis-and-hand-labelling.md`. |
| `ai32_reasoning_transcripts.py` | `docs/pilots/2026-09-03-ai32-reasoning-status.md` and `docs/pilots/2026-09-03-ai35-reasoning-confirmatory.md` (reasoning-episode transcript dumps). |

## Hand-labelling toolchain

| Script | Role |
|---|---|
| `label_server.py` | Serves the hand-labelling page (`principal_eval.label_ui`) and its JSON API. See `docs/analysis-and-hand-labelling.md`. |
| `label_summary.py` | Summarises a completed hand-labels CSV: raw/kappa judge agreement and the human-verified fusion rate. |
| `sample_for_labelling.py` | Draws the stratified sample a labelling pass runs over (`principal_eval.sampling`). |
| `harmful_action_backfill.py` | Backfills `harmful_action` onto pre-AI-20 logs from `sample.store["actions_taken"]`. |

## Superseded / one-off

| Script | Status |
|---|---|
| `ai9_reasoning_by_persona.py` | Superseded by `ai32_reasoning_readout.py`. Exploratory, carries no intervals. |
| `ai5_rerun_gpt_arms.sh` | Dead since gpt-4o-mini's retirement as a subject (AI-15). |
| `ai9_cost_projection.py` | One-off projection, superseded by `ai5_frontier_projection.py`. |
