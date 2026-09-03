"""AI-32 readout: the R-series from `docs/analysis-plan.md` § J (2026-09-03).

Supersedes `scripts/ai9_reasoning_by_persona.py`, which printed the same cell
means with no interval and no episode-length control and said so ("a lead to
test properly, not a result"). This script is that proper test: the estimand,
its uncertainty method, its controls and its verdict table were pre-registered
in the amendment BEFORE anything here was run.

Read-only. Log paths are arguments — nothing is hardcoded, so the same script
runs over the AI-9 frontier arms and over any later base arm of this harness.

Usage:
    uv run python scripts/ai32_reasoning_readout.py <log.eval|log-dir> [...] [--json out.json]
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, "src")

from principal_eval.reasoning import (  # noqa: E402
    load_reasoning_rows,
    reasoning_report,
)


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


def _pct(ci: dict) -> str:
    if ci.get("point") != ci.get("point"):
        return "n/a"
    return f"{ci['point']:+.1%} [{ci['lo']:+.1%}, {ci['hi']:+.1%}]"


def print_contrast(title: str, c: dict, unit: str = " tok") -> None:
    print(f"  {title}  (n {c['n_high']} vs {c['n_low']})")
    print(f"    absolute  {_ci(c['absolute'], unit)}")
    print(f"    relative  {_pct(c['relative'])}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    json_out = None
    if "--json" in sys.argv:
        i = sys.argv.index("--json")
        json_out = sys.argv[i + 1]
        args = [a for a in args if a != json_out]

    load = load_reasoning_rows(expand(args))
    report = reasoning_report(load)

    print("AI-32 — R-series: reasoning expenditure by inferred user status")
    print("Pre-registered in docs/analysis-plan.md § J, 2026-09-03 (AI-32).")
    print("Scope: status_irrelevant only; ladder personas only; scenario-clustered")
    print("bootstrap, 10,000 resamples, 95% percentile intervals, seed 6.")
    d = report["disposition"]
    print(f"Excluded (plan rule 15): {d['excluded_error']} errored, "
          f"{d['excluded_limit']} limit-hit.")

    for model, b in report["models"].items():
        print(f"\n{'=' * 74}\n=== {model} ===")
        print(f"in scope: {b['n_in_scope']} samples over {b['n_scenarios']} scenarios "
              f"({b['n_analysable_all_families']} analysable across all families)")
        if not b["measurable"]:
            print(f"\n  ** {b['note']} **")
            print("  Not imputed and not differenced against a reasoning model.")
            continue

        print(f"\n  {'persona':16s} {'n':>4s} {'reasoning/sample':>26s} "
              f"{'reasoning/turn':>24s} {'turns':>18s}")
        for persona, cell in b["persona_table"].items():
            print(f"  {persona:16s} {cell['n']:4d} "
                  f"{_ci(cell['reasoning_per_sample']):>26s} "
                  f"{_ci(cell['reasoning_per_turn']):>24s} "
                  f"{_ci(cell['turns_per_sample']):>18s}")

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

        for key, label in (("R4_monotonicity_per_sample", "per sample"),
                           ("R4_monotonicity_per_turn", "per turn")):
            m = b[key]
            print(f"\n  R4 — ladder monotonicity, {label}: "
                  f"{'MONOTONIC' if m['monotonic'] else 'NOT monotonic'}")
            print("    " + "  ".join(f"{p}={v:.0f}" for p, v in m["ladder"]))
            for br in m["breaks"]:
                print(f"    break: {br['from']} -> {br['to']} ({br['drop']:+.0f})")

        diag = b["diagnostic_per_scenario"]
        print("\n  Diagnostic (no interval, no claim) — where the gap lives")
        print(f"  {'scenario':22s} {'ceo':>8s} {'analyst':>9s} {'relative':>10s} "
              f"{'gap w/o this scenario':>23s}")
        for s, d in diag["per_scenario"].items():
            print(f"  {s:22s} {d['high']:8.1f} {d['low']:9.1f} {d['relative']:+9.1%} "
                  f"{diag['leave_one_out_relative'][s]:+22.1%}")

        ind = b["R8_independent"]
        if ind.get("available"):
            print("\n  R8 — independent recomputation from raw per-sample token counts")
            print(f"    ceo    sum {ind['sum_high']:>8d} / n {ind['n_high']:>3d} "
                  f"= {ind['mean_high']:.2f}")
            print(f"    analyst sum {ind['sum_low']:>8d} / n {ind['n_low']:>3d} "
                  f"= {ind['mean_low']:.2f}")
            print(f"    relative gap {ind['relative']:+.4%}  "
                  f"(pipeline: {b['R1_status_gap']['relative']['point']:+.4%})")
            delta = abs(ind["relative"] - b["R1_status_gap"]["relative"]["point"])
            print(f"    reconciles to {delta:.2e}" if delta < 1e-9
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
