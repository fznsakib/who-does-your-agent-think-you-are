"""AI-32 readout: the R-series from `docs/analysis-plan.md` § J (2026-09-03).

Supersedes `scripts/ai9_reasoning_by_persona.py`, which printed the same cell
means with no interval and no episode-length control and said so ("a lead to
test properly, not a result"). This script is that proper test: the estimand,
its uncertainty method, its controls and its verdict table were pre-registered
in the amendment BEFORE anything here was run.

Read-only. Log paths are arguments — nothing is hardcoded, so the same script
runs over the AI-9 frontier arms and over any later base arm of this harness.

`--status` is REQUIRED. The amendment gives R-numbers different evidentiary
status depending on which arm produced them -- exploratory against the AI-9 logs
that motivated the effect, confirmatory against an arm that did not -- and log
paths alone cannot tell the script which it is holding. Rather than print a
generic banner over either, it refuses to emit a number until the caller says.

Usage:
    uv run python scripts/ai32_reasoning_readout.py <log.eval|log-dir> [...] \
        --status exploratory|confirmatory [--json out.json] [--allow-mixed-runs]
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, "src")

from principal_eval.reasoning import (  # noqa: E402
    attach_independent_checks,
    load_reasoning_rows,
    reasoning_report,
)

STATUS_BANNER = {
    "exploratory": (
        "STATUS: EXPLORATORY. These logs motivated the effect, so they cannot also\n"
        "confirm it (plan rules 13, 14, 20). The estimand, controls and verdict table\n"
        "were fixed before recomputation, but every number below is exploratory and\n"
        "must be labelled as such wherever it is quoted."
    ),
    "confirmatory": (
        "STATUS: CONFIRMATORY. This arm did not motivate the effect and was not read\n"
        "before the amendment was committed, so the pre-registration applies to it in\n"
        "full."
    ),
}


def expand(args: list[str]) -> list[str]:
    paths: list[str] = []
    for a in args:
        if os.path.isdir(a):
            paths.extend(sorted(glob.glob(f"{a}/**/*.eval", recursive=True)))
        else:
            paths.append(a)
    if not paths:
        raise SystemExit(f"no .eval logs found in: {' '.join(args)}")
    return paths


def _ci(ci: dict, unit: str = "") -> str:
    if ci.get("point") != ci.get("point"):
        return "n/a"
    return f"{ci['point']:.1f}{unit} [{ci['lo']:.1f}, {ci['hi']:.1f}]"


def print_contrast(title: str, c: dict, unit: str = " tok") -> None:
    # `n_high`/`n_low` are the ELIGIBLE counts for this statistic; when a
    # per-turn estimate used fewer rows than the cell holds, show both so the
    # printed denominator is the one the estimate actually had.
    n = f"n {c['n_high']} vs {c['n_low']}"
    if (c["n_high"], c["n_low"]) != (c["n_high_all"], c["n_low_all"]):
        n += f" eligible of {c['n_high_all']} vs {c['n_low_all']}"
    print(f"  {title}  ({n})")
    print(f"    absolute  {_ci(c['absolute'], unit)}")
    rel = c["relative"]
    relative_str = (
        "n/a"
        if rel.get("point") != rel.get("point")
        else f"{rel['point']:+.1%} [{rel['lo']:+.1%}, {rel['hi']:+.1%}]"
    )
    print(f"    relative  {relative_str}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    consumed = []
    json_out = None
    if "--json" in sys.argv:
        json_out = sys.argv[sys.argv.index("--json") + 1]
        consumed.append(json_out)
    status = None
    if "--status" in sys.argv:
        status = sys.argv[sys.argv.index("--status") + 1]
        consumed.append(status)
    args = [a for a in args if a not in consumed]

    if status not in STATUS_BANNER:
        raise SystemExit(
            "--status is required and must be 'exploratory' or 'confirmatory'.\n"
            "The amendment requires every R-number to carry its evidentiary status, "
            "and log paths cannot tell the script which arm they are. Against the "
            "AI-9 frontier logs (the arm that motivated the effect) pass "
            "--status exploratory."
        )

    paths = expand(args)
    load = load_reasoning_rows(paths)
    # R8 goes back to the source logs by a second extraction path, so it is a
    # separate pass over `paths` rather than a read of the rows above.
    try:
        report = reasoning_report(
            load, allow_mixed_runs="--allow-mixed-runs" in sys.argv)
    except ValueError as e:  # a refusal, not a crash -- report it as one
        raise SystemExit(str(e))
    report = attach_independent_checks(report, paths)
    report["status"] = status

    print("AI-32 — R-series: reasoning expenditure by inferred user status")
    print("Pre-registered in docs/analysis-plan.md § J, 2026-09-03 (AI-32).")
    print(STATUS_BANNER[status])
    print("Scope: status_irrelevant only; ladder personas only; scenario-clustered")
    print("bootstrap, 10,000 resamples, 95% percentile intervals, seed 6.")
    d = report["disposition"]
    print(f"Excluded (plan rule 15): {d['excluded_error']} errored, "
          f"{d['excluded_limit']} limit-hit.")

    for label, b in report["models"].items():
        print(f"\n{'=' * 82}\n=== {label} ===")
        exc = b["excluded_by_reason"]
        print(f"in scope: {b['n_in_scope']} samples over {b['n_scenarios']} scenarios "
              f"({b['n_analysable_all_families']} analysable across all families; "
              f"excluded: {exc['error']} errored, {exc['limit']} limit-hit)")
        print(f"run_id: {', '.join(b['run_ids']) or 'n/a'} | epochs: "
              f"{b.get('n_epochs', 0)}")
        if b.get("warning"):
            print(f"  !! {b['warning']}")
        if b.get("note") and not b["measurable"]:
            print(f"\n  ** {b['note']} **")
            print("  Not imputed and not differenced against a reasoning model.")
            continue

        print(f"\n  {'persona':16s} {'n':>4s} {'n/turn':>7s} {'reasoning/sample':>26s} "
              f"{'reasoning/turn':>24s} {'turns':>18s}")
        for persona, cell in b["persona_table"].items():
            print(f"  {persona:16s} {cell['n']:4d} {cell['n_per_turn']:7d} "
                  f"{_ci(cell['reasoning_per_sample']):>26s} "
                  f"{_ci(cell['reasoning_per_turn']):>24s} "
                  f"{_ci(cell['turns_per_sample']):>18s}")
        ext = b.get("external_cell")
        if ext:
            print(f"  {'external*':16s} {ext['n']:4d} {ext['n_per_turn']:7d} "
                  f"{_ci(ext['reasoning_per_sample']):>26s} "
                  f"{_ci(ext['reasoning_per_turn']):>24s} "
                  f"{_ci(ext['turns_per_sample']):>18s}")
            print("  * external is NOT a rung (plan rule E4: it varies affiliation as well")
            print("    as status). Reported beside the ladder, excluded from R1/R4.")
        zero = sum(c["n_zero_turn"] for c in b["persona_table"].values())
        if zero:
            print(f"  ({zero} zero-turn samples: counted in n, excluded from per-turn "
                  f"means — see the n/turn column)")

        print("\n  R1 — reasoning per sample (headline)")
        print_contrast("ceo - analyst (status)", b["R1_status_gap"])
        print_contrast("chief_of_staff - analyst (leadership-proximity bundle)",
                       b["R1_proximity_gap"])

        print("\n  R2 — episode-length control (PRIMARY: per-turn normalisation)")
        print_contrast("ceo - analyst, reasoning per turn", b["R2_per_turn_gap"])
        print_contrast("ceo - analyst, turns per sample", b["R2_turns_gap"], " turns")

        sens = b["R2_sensitivity_turns_covariate"]
        print("\n  R2 sensitivity — turns as a covariate (OLS, analyst reference)")
        if not sens.get("available"):
            print(f"    unavailable: {sens.get('reason')}")
        else:
            for name, ci in sens["coefficients"].items():
                print(f"    {name:18s} {_ci(ci)}")

        print("\n  R3 — verbosity placebo (visible output = output - reasoning)")
        print_contrast("ceo - analyst, visible per sample", b["R3_visible_gap"])
        print_contrast("ceo - analyst, visible per turn", b["R3_visible_per_turn_gap"])

        for key, scale in (("R4_monotonicity_per_sample", "per sample"),
                           ("R4_monotonicity_per_turn", "per turn")):
            m = b[key]
            state = ("MONOTONIC" if m["monotonic"] else "NOT monotonic"
                     ) if m["monotonic"] is not None else (
                     f"INCOMPLETE — cannot be stated (missing {m['missing_rungs']}, "
                     f"non-finite {m['non_finite_rungs']})")
            print(f"\n  R4 — ladder monotonicity, {scale}: {state}")
            print("    " + "  ".join(f"{p}={v:.0f}" for p, v in m["ladder"]))
            for br in m["breaks"]:
                print(f"    break: {br['from']} -> {br['to']} ({br['drop']:+.0f})")

        diag = b["diagnostic_per_scenario"]
        print("\n  Diagnostic (no interval, no claim) — where the gap lives")
        print(f"  {'scenario':22s} {'ceo':>8s} {'analyst':>9s} {'relative':>10s} "
              f"{'gap w/o this scenario':>23s}")
        for scenario, row in diag["per_scenario"].items():
            print(f"  {scenario:22s} {row['high']:8.1f} {row['low']:9.1f} "
                  f"{row['relative']:+9.1%} "
                  f"{diag['leave_one_out_relative'][scenario]:+22.1%}")

        ind = b.get("R8_independent") or {}
        if ind.get("available"):
            print("\n  R8 — independent recomputation, re-read from the source logs by a")
            print("       second extraction/scoping path sharing no code with the pipeline")
            print(f"    ceo     sum {ind['sum_high']:>8d} / n {ind['n_high']:>3d} "
                  f"= {ind['mean_high']:.2f}")
            print(f"    analyst sum {ind['sum_low']:>8d} / n {ind['n_low']:>3d} "
                  f"= {ind['mean_low']:.2f}")
            print(f"    relative gap {ind['relative']:+.4%}  "
                  f"(pipeline: {b['R1_status_gap']['relative']['point']:+.4%})")
            delta = abs(ind["relative"] - b["R1_status_gap"]["relative"]["point"])
            print(f"    reconciles to {delta:.2e}" if b.get("R8_reconciles")
                  else f"    !! DISCREPANCY {delta:.6f} — do not publish")

        v = b["R6_verdict"]
        print(f"\n  R6 VERDICT: {v['verdict'].upper()}")
        print(f"    {v['reason']}")

    if json_out:
        with open(json_out, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nwrote {json_out}")


if __name__ == "__main__":
    main()
