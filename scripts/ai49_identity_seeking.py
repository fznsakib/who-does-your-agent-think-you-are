"""AI-49: rule-9 identity-seeking rates for the five clean frontier-generation arms.

Discovery is one of the research spec's three questions (discovery / deference /
calibration) and, until now, the write-up reported it only for the two cheap
pre-AI-16 arms (nano, haiku) -- never for the five clean frontier-generation base
arms that carry every confirmatory E-series claim. This script fills that gap.

The rule-9 rate table (active_identity_seeking / cue_read_before_action, by persona
x condition x family) is DESCRIPTIVE: rule 9 of docs/analysis-plan.md registers it
as a reported diagnostic, never a confirmatory estimand (rule 13's confirmatory set
is E1/E2/E3/E5 only), and this script prints it unchanged -- nothing here enters
that set.

The ceo-analyst active-seeking gap this script ALSO computes is a different thing:
a NEW contrast on the registered rate, invented after the underlying logs already
existed, and per rule 14 it is recorded in docs/analysis-plan.md Section J's
2026-09-04 (AI-49) amendment (append-only -- see that entry for the full estimand
definition). It is labelled EXPLORATORY throughout this script's output, the
verification doc and the readout -- not DESCRIPTIVE, and not part of any
confirmatory set.

This script reimplements no statistic. It is a thin driver over three functions
that already exist and are unchanged:

  * `principal_eval.analysis.load_rows` / `scored`     -- the same loader every
    other verify-script section uses (AI-38's canonical Row/LoadReport pipeline,
    not the bespoke `Row` class in `ai9_frontier_readout.py`, so that
    `active_identity_seeking` / `cue_read_before_action` / `acted_on_scenario_tool`
    are populated exactly as `analyze_logs.py` and the AI-6/AI-15 readouts compute
    them).
  * `principal_eval.analysis.identity_seeking_rate` (rule 9) -- the by-persona x
    family table (active_identity_seeking; cue_read_before_action given acted),
    printed unchanged.
  * `principal_eval.analysis.bootstrap_ci` -- the same scenario-clustered
    bootstrap every E-series number uses, with the E-series seed (0) and 10,000
    draws, applied to the ceo-minus-analyst gap in ACTIVE identity-seeking
    (status_irrelevant only, mirroring `deference_gap_by_rung`'s ceo/analyst gap
    machinery but on the seeking outcome instead of compliance).

The two extra numbers per arm (the overall status-irrelevant active-seeking rate,
and cue-read-before-action given acted pooled over personas) are plain means over
`identity_seeking_rate`'s own inputs -- no new statistical machinery.

Each arm dir must hold exactly one `.eval` file; the script REFUSES (SystemExit)
when it finds more than one, rather than silently picking a "latest" -- a stray
smoke-test or rerun log alongside the production run must not silently double- or
wrong-count a denominator, and this way section 8 is guaranteed to read the same
file section 1's five `docs/verification.md` Table 1 paths do (`ai9-frontier/
opus5-base`, `ai9-frontier/gpt56sol-base`, `ai9-frontier/gpt56luna-base`,
`ai31-midtier/sonnet5-base`, `ai31-midtier/terra-base` -- the ARMS table below is
byte-identical to that list). It also prints the loaded file's path, validates the
rows' model against the expected id for that arm, and reports epoch count and
judge-model homogeneity (rule 22) -- a misplaced file under the wrong arm label
fails loudly rather than printing a plausible-looking wrong number.

LEGACY (earlier-harness) COMPARISON: the pre-AI-16 nano/haiku arms are reported
alongside the five clean arms for comparison ONLY, computed through this exact
same status_irrelevant-only pipeline (never the pooled-all-family numbers
published in their own readouts, which are a DIFFERENT estimand and must not be
compared point-for-point against an SI-only figure -- see
docs/pilots/2026-09-04-ai49-identity-seeking.md for the full explanation). They
are never counted among "the five clean arms".

Usage:
    uv run python scripts/ai49_identity_seeking.py [--logs <root>]
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

sys.path.insert(0, "src")
from principal_eval.analysis import (  # noqa: E402
    bootstrap_ci, identity_seeking_rate, load_rows, mean, scored,
)
from principal_eval.personas import PERSONA_ORDER  # noqa: E402

BOOT, SEED = 10_000, 0  # E-series convention (see docs/verification.md determinism note)

# (label, log dir relative to --logs, expected model id) -- the five clean
# frontier-generation base arms, same set and same order as
# verify_headline_numbers.py section 1 / ai9_frontier_readout.py's PRICE table.
ARMS = [
    ("opus-5",   "ai9-frontier/opus5-base",     "anthropic/claude-opus-5"),
    ("sol",      "ai9-frontier/gpt56sol-base",  "openai/gpt-5.6-sol"),
    ("luna",     "ai9-frontier/gpt56luna-base", "openai/gpt-5.6-luna"),
    ("sonnet-5", "ai31-midtier/sonnet5-base",   "anthropic/claude-sonnet-5"),
    ("terra",    "ai31-midtier/terra-base",     "openai/gpt-5.6-terra"),
]

# Pre-AI-16 fork, printed for comparison only -- never part of "the five clean arms".
LEGACY_ARMS = [
    ("gpt-5-nano (earlier harness)",       "ai15-gpt5nano/base",  "openai/gpt-5-nano"),
    ("claude-haiku-4-5 (earlier harness)", "ai5-pilot/haiku-base", "anthropic/claude-haiku-4-5"),
]


def _single_log(logs_root: str, rel_dir: str) -> str:
    """The one `.eval` under `rel_dir`. Refuses (rather than silently picking a
    "latest" file) when a directory holds more than one run -- a stray
    smoke-test log alongside the production run, or a rerun, would otherwise
    change or double the denominator without warning, and could make this
    section read different data than section 1
    (`ai9_frontier_readout.load()` / `ai31_tier_table.load()`) reads for the
    same arm."""
    d = os.path.join(logs_root, rel_dir)
    found = sorted(glob.glob(f"{d}/**/*.eval", recursive=True))
    if not found:
        raise SystemExit(f"no .eval under {d!r}")
    if len(found) > 1:
        raise SystemExit(
            f"{len(found)} .eval files under {d!r}: {[os.path.basename(p) for p in found]}. "
            f"Refusing to guess -- move/remove the extra run(s) (e.g. a smoke-test log) "
            f"so exactly one production .eval remains, matching what section 1 "
            f"(ai9_frontier_readout.load()) would select for this arm.")
    return found[0]


def _active_mean(rows) -> float:
    return mean([1.0 if r.active_identity_seeking else 0.0 for r in rows])


def ceo_minus_analyst_active_seeking(si_rows) -> dict:
    """EXPLORATORY (docs/analysis-plan.md Section J, 2026-09-04 AI-49 amendment):
    ceo - analyst gap in ACTIVE identity-seeking, status_irrelevant only, 95%
    scenario-clustered bootstrap (E-series seed 0, 10,000 draws). Mirrors
    `deference_gap_by_rung`'s ceo/analyst combined-rows-then-lambda pattern so the
    contrast is computed WITHIN each resampled scenario set, exactly like every
    other gap in this codebase."""
    ceo = [r for r in si_rows if r.persona == "ceo" and r.condition == "identified"]
    analyst = [r for r in si_rows if r.persona == "analyst" and r.condition == "identified"]
    combined = ceo + analyst

    def stat(rs):
        c = [r for r in rs if r.persona == "ceo"]
        a = [r for r in rs if r.persona == "analyst"]
        return _active_mean(c) - _active_mean(a)

    return bootstrap_ci(combined, stat, n_boot=BOOT, seed=SEED)


def _fmt(x) -> str:
    return f"{x:.3f}" if x is not None else "--"


def _fmt_before(d) -> str:
    return f"{d['rate']:.3f} (n={d['n_acted']})" if d else "--"


def _provenance(rows, label: str, expected_model: str) -> str:
    """Rule 22: every number attributed to a model, epoch count, and judge --
    not just a hard-coded arm label. ABORTS (SystemExit), rather than merely
    warning, on a mixed model set, a mixed/non-base variant, or a
    non-homogeneous judge -- including a mixture of a known judge_model and
    rows where it is unset, which is heterogeneous provenance too, not a
    clean "no judge recorded" case. `docs/analysis-plan.md` forbids mixed-
    judge comparisons (rule 22) and requires arm separation by variant
    (rule 5 / docs/analysis-plan.md:67-69); silently continuing past either
    would publish a combined result that violates both."""
    models = sorted({r.model for r in rows})
    variants = sorted({r.variant for r in rows})
    judge_values = sorted({r.judge_model for r in rows}, key=lambda j: (j is None, j))
    epochs = sorted({r.epoch for r in rows})
    problems = []
    if models != [expected_model]:
        problems.append(f"expected model {expected_model!r}, got {models!r}")
    if variants != ["base"]:
        problems.append(f"expected variant ['base'] only, got {variants!r}")
    if len(judge_values) > 1:
        problems.append(f"non-homogeneous judge_model: {judge_values!r}")
    if problems:
        raise SystemExit(f"{label}: refusing to report -- " + "; ".join(problems))
    judge = judge_values[0] if judge_values[0] is not None else \
        "unset (predates judge_model in score metadata)"
    return f"model={models[0]}  judge={judge}  epochs={epochs[0]}-{epochs[-1]} (n={len(epochs)})"


def _persona_counts(rows) -> dict:
    counts: dict = {}
    for r in rows:
        counts[r.persona] = counts.get(r.persona, 0) + 1
    return counts


def _fmt_active(rate, n) -> str:
    return f"{rate:.3f} (n={n})" if rate is not None else "--"


def _disposition(report) -> str:
    """Rule 15/17: excluded samples are bounded, not just counted -- and per
    rule 17 counted BY persona/family, since an exclusion concentrated in one
    cell (rather than spread evenly) silently reweights that cell's rate.
    `_malformed_row` (hard errors, no score) and limit-hit rows both carry
    persona/family metadata even though `scored()` drops them, so this reads
    that metadata off `report.rows` directly rather than off the `scored()`
    output the rest of `_run_arm` uses."""
    excluded = [r for r in report.rows if r.nonterminating or r.limit_hit]
    if not excluded:
        return (f"disposition: 0 excluded (n_errors={report.n_errors}, "
                f"n_malformed={report.n_malformed}, n_limit_hit=0)")
    by_cell: dict = {}
    for r in excluded:
        key = (r.persona, r.family, "limit_hit" if r.limit_hit else "error/malformed")
        by_cell[key] = by_cell.get(key, 0) + 1
    cells = ", ".join(f"{p}/{f}/{why}={n}" for (p, f, why), n in sorted(by_cell.items()))
    return (f"disposition: {len(excluded)} excluded (n_errors={report.n_errors}, "
            f"n_malformed={report.n_malformed}) -- by cell: {cells}")


def _run_arm(label: str, path: str, expected_model: str) -> None:
    report = load_rows([path])
    rows = scored(report.rows)
    si_rows = [r for r in rows if r.family == "status_irrelevant"]
    rg_rows = [r for r in rows if r.family == "role_gated"]
    si_n, rg_n = _persona_counts(si_rows), _persona_counts(rg_rows)

    table = identity_seeking_rate(rows)
    si, rg = table["status_irrelevant"], table["role_gated"]

    print(f"\n--- {label} " + "-" * (74 - len(label)))
    print(f"  arm: {os.path.relpath(path)}  (n_scored={len(rows)})")
    print(f"  provenance: {_provenance(rows, label, expected_model)}")
    print(f"  {_disposition(report)}")
    print("  DESCRIPTIVE -- rule-9 table, by persona x family (n is the scored")
    print("  cell denominator -- rule 15 exclusions already removed from `rows`):")
    print(f"  {'persona':<16}{'active SI (n)':>18}{'active RG (n)':>18}"
          f"{'cue<-act SI (n)':>20}{'cue<-act RG (n)':>20}")
    for p in PERSONA_ORDER + ["anonymous"]:
        print(f"  {p:<16}"
              f"{_fmt_active(si['active_identity_seeking'].get(p), si_n.get(p)):>18}"
              f"{_fmt_active(rg['active_identity_seeking'].get(p), rg_n.get(p)):>18}"
              f"{_fmt_before(si['cue_read_before_action_given_acted'].get(p)):>20}"
              f"{_fmt_before(rg['cue_read_before_action_given_acted'].get(p)):>20}")

    overall_si = _active_mean(si_rows)
    print(f"\n  DESCRIPTIVE: overall status-irrelevant active-seeking rate: "
          f"{overall_si:.3f} (n={len(si_rows)})")

    gap = ceo_minus_analyst_active_seeking(si_rows)
    print(f"  EXPLORATORY (analysis-plan.md §J AI-49): ceo - analyst active-seeking gap "
          f"(status_irrelevant, 95% scenario-clustered bootstrap, seed={SEED}, "
          f"{BOOT} draws): "
          f"{gap['point']:+.3f} [{gap['lo']:+.3f}, {gap['hi']:+.3f}]")

    acted_si = [r for r in si_rows if r.acted_on_scenario_tool]
    overall_before = (mean([1.0 if r.cue_read_before_action else 0.0 for r in acted_si])
                       if acted_si else float("nan"))
    print(f"  DESCRIPTIVE: overall cue-read-before-action given acted "
          f"(status_irrelevant): {overall_before:.3f} (n_acted={len(acted_si)})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--logs", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"),
        help="root of the local logs tree (default: <repo>/logs)")
    args = ap.parse_args()
    logs_root = os.path.abspath(args.logs)

    print("=" * 78)
    print("AI-49 -- RULE-9 IDENTITY-SEEKING, FIVE CLEAN FRONTIER-GENERATION ARMS")
    print("The rule-9 rate table is DESCRIPTIVE (a registered secondary diagnostic,")
    print("never confirmatory -- rule 13's set is E1/E2/E3/E5 only). The ceo-analyst")
    print("gap is EXPLORATORY, registered post-hoc in docs/analysis-plan.md Section J,")
    print("2026-09-04 (AI-49) amendment -- not part of any confirmatory set.")
    print("=" * 78)

    for label, rel_dir, expected_model in ARMS:
        path = _single_log(logs_root, rel_dir)
        _run_arm(label, path, expected_model)

    print("\n" + "=" * 78)
    print("LEGACY, EARLIER-HARNESS COMPARISON ONLY (pre-AI-16 fork; NOT part of")
    print("the five clean arms). Computed through the identical SI-only pipeline")
    print("above -- NOT the pooled-all-family numbers in their own readouts,")
    print("which are a different estimand (see the readout doc for the nano/")
    print("haiku pooled-vs-SI-only distinction).")
    print("=" * 78)
    for label, rel_dir, expected_model in LEGACY_ARMS:
        path = _single_log(logs_root, rel_dir)
        _run_arm(label, path, expected_model)

    print("\n" + "=" * 78)


if __name__ == "__main__":
    main()
