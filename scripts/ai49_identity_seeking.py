"""AI-49: rule-9 identity-seeking rates for the five clean frontier-generation arms.

Discovery is one of the research spec's three questions (discovery / deference /
calibration) and, until now, the write-up reported it only for the two cheap
pre-AI-16 arms (nano, haiku) -- never for the five clean frontier-generation base
arms that carry every confirmatory E-series claim. This script fills that gap.

The rule-9 rate table (active_identity_seeking / cue_read_before_action, by persona
x condition x family) is DESCRIPTIVE: rule 9 of docs/analysis-plan.md registers it
as a reported diagnostic, never a confirmatory estimand (rule 13's confirmatory set
is E1/E2/E3/E5 only), and this script prints it unchanged -- nothing here enters
that set. Per rule 3, any individual table CELL with n < 20 is EXPLORATORY, flagged
inline with `*` (the active-seeking columns never drop below n=28 by design; only
the conditional cue-before-action-given-acted cells get this sparse).

This script ALSO computes three post-hoc numbers not in rule 9's registration --
the ceo-analyst active-seeking gap, and two pooled-across-persona overall rates
(overall SI active-seeking; overall cue-read-before-action given acted). All three
are NEW derived estimands, invented after the underlying logs already existed, and
per rule 14 all three are recorded in docs/analysis-plan.md Section J's 2026-09-04
(AI-49) amendment (append-only -- see that entry for the full estimand
definitions). All three are labelled EXPLORATORY throughout this script's output,
the verification doc and the readout -- not DESCRIPTIVE, and not part of any
confirmatory set, on any of the seven arms this script reports (five clean +
two legacy comparison-only).

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

The two pooled-mean numbers per arm (the overall status-irrelevant active-seeking
rate, and cue-read-before-action given acted pooled over personas) are plain means
over `identity_seeking_rate`'s own inputs -- no new statistical machinery, but
still new ESTIMANDS per the amendment above (a mean pooled across personas is not
the same claim as the per-persona rates rule 9 registers).

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

from inspect_ai.log import read_eval_log, read_eval_log_samples

sys.path.insert(0, "src")
from principal_eval.analysis import (  # noqa: E402
    bootstrap_ci, identity_seeking_rate, load_rows, mean, scored,
)
from principal_eval.judges import resolve_judge_model  # noqa: E402
from principal_eval.personas import PERSONA_ORDER  # noqa: E402

BOOT, SEED = 10_000, 0  # E-series convention (see docs/verification.md determinism note)

# Score-metadata keys this script's estimands depend on. load_rows() coerces
# an ABSENT key to False (via bool(meta.get(...))), which is indistinguishable
# from a real False -- so presence is checked directly against the raw score
# metadata (never through Row) before any rate is computed from these fields.
REQUIRED_SCORE_FIELDS = ("acted_on_scenario_tool", "cue_read_before_action")

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
# 4th element: allow_unset_judge. Only the haiku arm predates the judge_model
# field entirely (documented gap, see _provenance) -- nano already carries an
# explicit, correct judge_model and must be validated like every clean arm.
LEGACY_ARMS = [
    ("gpt-5-nano (earlier harness)",       "ai15-gpt5nano/base",  "openai/gpt-5-nano", False),
    ("claude-haiku-4-5 (earlier harness)", "ai5-pilot/haiku-base", "anthropic/claude-haiku-4-5", True),
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


def _validate_log(path: str, label: str) -> None:
    """Two checks that must happen against the RAW log, before `load_rows()`
    ever runs, because `load_rows()` itself is designed to tolerate both
    conditions silently (by contract -- see its docstring):

    1. **Completeness.** `load_rows()` reads with `all_samples_required=
       (header.status == "success")`, i.e. it deliberately accepts a
       truncated read on a non-`success` log. That is the right behaviour
       for a general-purpose loader, but this script must not then report
       "0 excluded" / a complete design as if every planned sample were
       present -- so a non-`success` status, or a loaded count under the
       header's own `total_samples`, aborts here.
    2. **Cue-timing field presence.** `acted_on_scenario_tool` and
       `cue_read_before_action` are coerced by `load_rows()` via
       `bool(meta.get(...))`, so an ABSENT key reads identically to a real
       `False` on the `Row`. This script's entire cue-before-action estimand
       depends on that distinction, so presence is checked directly against
       each scored sample's raw score metadata."""
    header = read_eval_log(path, header_only=True)
    if header.status != "success":
        raise SystemExit(
            f"{label}: log status is {header.status!r}, not 'success' -- "
            f"refusing to treat a non-terminal log as a complete design.")
    expected_n = header.results.total_samples if header.results else None
    seen = 0
    for s in read_eval_log_samples(path, all_samples_required=True):
        seen += 1
        if s.error is not None or s.limit is not None:
            continue
        score = next(iter(s.scores.values())) if s.scores else None
        if score is None:
            continue
        missing = [f for f in REQUIRED_SCORE_FIELDS if f not in (score.metadata or {})]
        if missing:
            raise SystemExit(
                f"{label}: sample {s.id!r} score metadata is missing {missing} -- "
                f"refusing to silently treat an absent field as False.")
    if expected_n is not None and seen != expected_n:
        raise SystemExit(
            f"{label}: loaded {seen} samples but the log header reports "
            f"total_samples={expected_n} -- refusing to treat this as a "
            f"complete design.")


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
    """Rule 3: any cell with n < 20 is exploratory, not descriptive, and must
    say so inline rather than only carrying its n -- flagged with a trailing
    `*` here, with the legend printed once per arm's table."""
    if not d:
        return "--"
    flag = "*" if d["n_acted"] < 20 else ""
    return f"{d['rate']:.3f} (n={d['n_acted']}){flag}"


def _provenance(rows, label: str, expected_model: str, allow_unset_judge: bool = False) -> str:
    """Rule 22: every number attributed to a model, epoch count, and judge --
    not just a hard-coded arm label. ABORTS (SystemExit), rather than merely
    warning, on a mixed model set, a mixed/non-base variant, a
    non-homogeneous judge (including a mixture of a known judge_model and
    rows where it is unset -- heterogeneous provenance too, not a clean "no
    judge recorded" case), OR a homogeneous judge that is simply the WRONG
    one: the repo requires opposite-provider judging
    (`principal_eval.judges.resolve_judge_model`), so a same-provider or
    otherwise misconfigured-but-consistent scorer must fail here too, not
    just an inconsistent one. `allow_unset_judge` is the one documented
    exception: the haiku legacy arm predates the `judge_model` field
    entirely, so `None` there is a known gap, not a validation failure --
    every OTHER arm must carry an explicit, correct judge_model."""
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
    elif judge_values[0] is None:
        if not allow_unset_judge:
            problems.append("judge_model is unset on every row (expected an explicit, "
                             "correct judge -- pass allow_unset_judge=True only for the "
                             "documented pre-judge_model legacy arm)")
    else:
        expected_judge = resolve_judge_model(expected_model)
        if judge_values[0] != expected_judge:
            problems.append(f"expected opposite-provider judge {expected_judge!r}, "
                             f"got {judge_values[0]!r}")
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


DISPOSITION_CAVEAT = (
    "disposition counts hard-error/no-score/limit-hit exclusions ONLY -- the "
    "rule-15 looper predicate (median + 5x IQR trajectory-length runaway) is "
    "NOT implemented here, matching the caveat already carried by "
    "ai9_frontier_readout.py (scripts/ai9_frontier_readout.py:255-258) and "
    "demonstrated non-trivial by the luna readout (164/1200 sol samples "
    "flagged when attempted -- docs/pilots/2026-09-03-ai33-luna-endpoint.md). "
    "\"0 excluded\" below means zero error/limit-hit exclusions, NOT zero "
    "looper-pattern trajectories."
)


def _disposition(report) -> str:
    """Rule 15/17: excluded samples are bounded, not just counted -- and per
    rule 17 counted BY persona/family, since an exclusion concentrated in one
    cell (rather than spread evenly) silently reweights that cell's rate.
    `_malformed_row` (hard errors, no score) and limit-hit rows both carry
    persona/family metadata even though `scored()` drops them, so this reads
    that metadata off `report.rows` directly rather than off the `scored()`
    output the rest of `_run_arm` uses. See DISPOSITION_CAVEAT for what this
    does NOT count (the unimplemented looper predicate)."""
    excluded = [r for r in report.rows if r.nonterminating or r.limit_hit]
    if not excluded:
        return (f"disposition: 0 error/limit-hit excluded (n_errors={report.n_errors}, "
                f"n_malformed={report.n_malformed}, n_limit_hit=0)")
    by_cell: dict = {}
    for r in excluded:
        key = (r.persona, r.family, "limit_hit" if r.limit_hit else "error/malformed")
        by_cell[key] = by_cell.get(key, 0) + 1
    cells = ", ".join(f"{p}/{f}/{why}={n}" for (p, f, why), n in sorted(by_cell.items()))
    return (f"disposition: {len(excluded)} error/limit-hit excluded "
            f"(n_errors={report.n_errors}, n_malformed={report.n_malformed}) "
            f"-- by cell: {cells}")


def _run_arm(label: str, path: str, expected_model: str, allow_unset_judge: bool = False) -> None:
    _validate_log(path, label)
    report = load_rows([path])
    rows = scored(report.rows)
    si_rows = [r for r in rows if r.family == "status_irrelevant"]
    rg_rows = [r for r in rows if r.family == "role_gated"]
    si_n, rg_n = _persona_counts(si_rows), _persona_counts(rg_rows)

    table = identity_seeking_rate(rows)
    si, rg = table["status_irrelevant"], table["role_gated"]

    print(f"\n--- {label} " + "-" * (74 - len(label)))
    print(f"  arm: {os.path.relpath(path)}  (n_scored={len(rows)})")
    print(f"  provenance: {_provenance(rows, label, expected_model, allow_unset_judge)}")
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
    print("  * n < 20: EXPLORATORY per rule 3, not DESCRIPTIVE -- the active-")
    print("    seeking columns are never below n=28 (design size), only the")
    print("    conditional cue<-act columns can be this sparse.")

    overall_si = _active_mean(si_rows)
    print(f"\n  EXPLORATORY (analysis-plan.md §J AI-49, item 1b): overall status-"
          f"irrelevant active-seeking rate (pooled across personas): "
          f"{overall_si:.3f} (n={len(si_rows)})")

    gap = ceo_minus_analyst_active_seeking(si_rows)
    print(f"  EXPLORATORY (analysis-plan.md §J AI-49, item 1a): ceo - analyst "
          f"active-seeking gap (status_irrelevant, 95% scenario-clustered "
          f"bootstrap, seed={SEED}, {BOOT} draws): "
          f"{gap['point']:+.3f} [{gap['lo']:+.3f}, {gap['hi']:+.3f}]")

    acted_si = [r for r in si_rows if r.acted_on_scenario_tool]
    overall_before = (mean([1.0 if r.cue_read_before_action else 0.0 for r in acted_si])
                       if acted_si else float("nan"))
    print(f"  EXPLORATORY (analysis-plan.md §J AI-49, item 1c): overall cue-read-"
          f"before-action given acted (status_irrelevant, pooled across personas): "
          f"{overall_before:.3f} (n_acted={len(acted_si)})"
          f"{'  *n<20' if len(acted_si) < 20 else ''}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--logs", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"),
        help="root of the local logs tree (default: <repo>/logs)")
    args = ap.parse_args()
    logs_root = os.path.abspath(args.logs)

    print("=" * 78)
    print("AI-49 -- RULE-9 IDENTITY-SEEKING, FIVE CLEAN FRONTIER-GENERATION ARMS")
    print("The rule-9 rate table (by persona x condition x family, unpooled, no")
    print("contrast) is DESCRIPTIVE -- a registered secondary diagnostic, never")
    print("confirmatory (rule 13's set is E1/E2/E3/E5 only). Any table cell with")
    print("n < 20 is EXPLORATORY per rule 3, flagged with * inline. The ceo-analyst")
    print("gap and the two pooled-across-persona overall rates are three separate")
    print("post-hoc estimands, all EXPLORATORY, registered in docs/analysis-plan.md")
    print("Section J's 2026-09-04 (AI-49) amendment -- none part of any")
    print("confirmatory set, on any of the seven arms below (five clean + two")
    print("legacy comparison-only).")
    print()
    print(DISPOSITION_CAVEAT)
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
    for label, rel_dir, expected_model, allow_unset_judge in LEGACY_ARMS:
        path = _single_log(logs_root, rel_dir)
        _run_arm(label, path, expected_model, allow_unset_judge)

    print("\n" + "=" * 78)


if __name__ == "__main__":
    main()
