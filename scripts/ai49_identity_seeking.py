"""AI-49: rule-9 identity-seeking rates for the five clean frontier-generation arms.

Discovery is one of the research spec's three questions (discovery / deference /
calibration) and, until now, the write-up reported it only for the two cheap
pre-AI-16 arms (nano, haiku) -- never for the five clean frontier-generation base
arms that carry every confirmatory E-series claim. This script fills that gap.

Every number here is DESCRIPTIVE. Rule 9 of docs/analysis-plan.md registers
identity-seeking as a reported diagnostic, not a confirmatory estimand (rule 13's
confirmatory set is E1/E2/E3/E5 only) -- so nothing below is pre-registered, and
docs/analysis-plan.md is not touched by this ticket.

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
    draws, applied to a new estimand this ticket adds: the ceo-minus-analyst gap
    in ACTIVE identity-seeking (status_irrelevant only, mirroring
    `deference_gap_by_rung`'s ceo/analyst gap machinery but on the seeking
    outcome instead of compliance).

The two extra numbers per arm (the overall status-irrelevant active-seeking rate,
and cue-read-before-action given acted pooled over personas) are plain means over
`identity_seeking_rate`'s own inputs -- no new statistical machinery.

Usage:
    uv run python scripts/ai49_identity_seeking.py [--logs <root>]
"""
from __future__ import annotations

import argparse
import os
import sys

from inspect_ai.log import list_eval_logs

sys.path.insert(0, "src")
from principal_eval.analysis import (  # noqa: E402
    bootstrap_ci, identity_seeking_rate, load_rows, mean, scored,
)
from principal_eval.personas import PERSONA_ORDER  # noqa: E402

BOOT, SEED = 10_000, 0  # E-series convention (see docs/verification.md determinism note)

# (label, log dir relative to --logs) -- the five clean frontier-generation base
# arms, same set and same order as verify_headline_numbers.py section 1.
ARMS = [
    ("opus-5",   "ai9-frontier/opus5-base"),
    ("sol",      "ai9-frontier/gpt56sol-base"),
    ("luna",     "ai9-frontier/gpt56luna-base"),
    ("sonnet-5", "ai31-midtier/sonnet5-base"),
    ("terra",    "ai31-midtier/terra-base"),
]


def _expand(logs_root: str, rel_dir: str) -> list[str]:
    d = os.path.join(logs_root, rel_dir)
    out = [info.name for info in list_eval_logs(d, recursive=True)]
    if not out:
        raise SystemExit(f"no .eval logs under {d}")
    return out


def _active_mean(rows) -> float:
    return mean([1.0 if r.active_identity_seeking else 0.0 for r in rows])


def ceo_minus_analyst_active_seeking(si_rows) -> dict:
    """DESCRIPTIVE: ceo - analyst gap in ACTIVE identity-seeking, status_irrelevant
    only, 95% scenario-clustered bootstrap (E-series seed 0, 10,000 draws). Mirrors
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--logs", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"),
        help="root of the local logs tree (default: <repo>/logs)")
    args = ap.parse_args()
    logs_root = os.path.abspath(args.logs)

    print("=" * 78)
    print("AI-49 -- RULE-9 IDENTITY-SEEKING, FIVE CLEAN FRONTIER-GENERATION ARMS")
    print("Every number in this section is DESCRIPTIVE (rule 9 is a reported")
    print("diagnostic, not in the confirmatory set -- see docs/analysis-plan.md")
    print("rule 13). docs/analysis-plan.md is not amended by this ticket.")
    print("=" * 78)

    for label, rel_dir in ARMS:
        paths = _expand(logs_root, rel_dir)
        report = load_rows(paths)
        rows = scored(report.rows)
        si_rows = [r for r in rows if r.family == "status_irrelevant"]

        table = identity_seeking_rate(rows)
        si, rg = table["status_irrelevant"], table["role_gated"]

        print(f"\n--- {label} " + "-" * (74 - len(label)))
        print(f"  arm: {rel_dir}  (n_scored={len(rows)})")
        print("  DESCRIPTIVE -- rule-9 table, by persona x family:")
        print(f"  {'persona':<16}{'active SI':>10}{'active RG':>10}"
              f"{'cue<-act SI (n)':>20}{'cue<-act RG (n)':>20}")
        for p in PERSONA_ORDER + ["anonymous"]:
            print(f"  {p:<16}"
                  f"{_fmt(si['active_identity_seeking'].get(p)):>10}"
                  f"{_fmt(rg['active_identity_seeking'].get(p)):>10}"
                  f"{_fmt_before(si['cue_read_before_action_given_acted'].get(p)):>20}"
                  f"{_fmt_before(rg['cue_read_before_action_given_acted'].get(p)):>20}")

        overall_si = _active_mean(si_rows)
        print(f"\n  DESCRIPTIVE: overall status-irrelevant active-seeking rate: "
              f"{overall_si:.3f} (n={len(si_rows)})")

        gap = ceo_minus_analyst_active_seeking(si_rows)
        print(f"  DESCRIPTIVE: ceo - analyst active-seeking gap (status_irrelevant, "
              f"95% scenario-clustered bootstrap, seed={SEED}, {BOOT} draws): "
              f"{gap['point']:+.3f} [{gap['lo']:+.3f}, {gap['hi']:+.3f}]")

        acted_si = [r for r in si_rows if r.acted_on_scenario_tool]
        overall_before = (mean([1.0 if r.cue_read_before_action else 0.0 for r in acted_si])
                           if acted_si else float("nan"))
        print(f"  DESCRIPTIVE: overall cue-read-before-action given acted "
              f"(status_irrelevant): {overall_before:.3f} (n_acted={len(acted_si)})")

    print("\n" + "=" * 78)


if __name__ == "__main__":
    main()
