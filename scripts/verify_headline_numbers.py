"""AI-38: reprint every headline number in the MATS write-up from the logs on disk.

ONE command:

    uv run python scripts/verify_headline_numbers.py [--logs <root>]

This script is an orchestrator, not a pipeline. It WRAPS the committed readout
scripts — it reimplements no statistic, so it can never disagree with them:

  1. `scripts/ai9_frontier_readout.py`   — E1/E2/E3/E5 co-primary confirmatory
     intervals, rule-6 judge-vs-harm cross-tab, rule-21 tables, sensitivities —
     per arm, over the five frontier-generation base arms.
  2. `scripts/ai32_reasoning_readout.py` — the R-series reasoning-by-status
     numbers, run three times so the evidentiary status travels with each
     number: `--status exploratory` for the AI-9 arms that motivated the effect
     (opus-5, sol), `--status confirmatory` for the arms that did not
     (terra + sonnet-5 per AI-35 §7; luna per AI-35 §7).
  3. `scripts/ai31_tier_table.py`        — the descriptive tier table, including
     the luna→sol 3.20× compliance point-estimate ratio (which is only ever
     quoted beside the luna−sol pairwise interval from step 4).
  4. `scripts/ai33_cross_model_bootstrap.py` — pairwise cross-model contrasts
     (every one includes zero on both co-primaries).
  5. `scripts/analyze_logs.py`           — the gpt-5-nano cheap arm: E1 +0.190,
     and the paired pushback flip (17.1% toward compliance vs the 9.0% null
     floor) from the AI-18 backfill run.

Determinism: every wrapped script pins its own seed (bootstrap seed 0 for the
E-series/tier/pairwise scripts, seed 6 for the R-series) and 10,000 resamples,
so repeated runs print identical numbers. Nothing here adds randomness.

The consolidated output maps section-by-section onto `docs/verification.md`,
which ties each claim to its number, command, log path and readout doc.

Exit status is non-zero if any wrapped pipeline fails.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def sections(logs: str) -> list[tuple[str, list[str]]]:
    """(title, argv) per wrapped pipeline. Paths mirror docs/verification.md."""
    frontier = [
        f"{logs}/ai9-frontier/opus5-base",
        f"{logs}/ai9-frontier/gpt56sol-base",
        f"{logs}/ai9-frontier/gpt56luna-base",
        f"{logs}/ai31-midtier/sonnet5-base",
        f"{logs}/ai31-midtier/terra-base",
    ]
    return [
        (
            "1. E-SERIES CONFIRMATORY SETS — five frontier-generation base arms\n"
            "   (ai9_frontier_readout.py: E1/E2/E3/E5 x both co-primaries, rule-6\n"
            "   cross-tab, rule-21 rank-vocabulary, PARTIAL/fusion/disposition\n"
            "   sensitivities; readouts: frontier-base.md, midtier-addendum.md,\n"
            "   ai33-luna-endpoint.md)",
            [sys.executable, f"{HERE}/ai9_frontier_readout.py", *frontier],
        ),
        (
            "2. R-SERIES, EXPLORATORY — opus-5 + sol (the AI-9 arms that motivated\n"
            "   the effect; readout: ai32-reasoning-status.md §8)",
            [sys.executable, f"{HERE}/ai32_reasoning_readout.py",
             f"{logs}/ai9-frontier/opus5-base", f"{logs}/ai9-frontier/gpt56sol-base",
             "--status", "exploratory"],
        ),
        (
            "3. R-SERIES, CONFIRMATORY — sonnet-5 + terra (AI-31 arms; readout:\n"
            "   ai35-reasoning-confirmatory.md §7)",
            [sys.executable, f"{HERE}/ai32_reasoning_readout.py",
             f"{logs}/ai31-midtier/sonnet5-base", f"{logs}/ai31-midtier/terra-base",
             "--status", "confirmatory"],
        ),
        (
            "4. R-SERIES, CONFIRMATORY — luna (AI-33 arm; readout:\n"
            "   ai35-reasoning-confirmatory.md §7)",
            [sys.executable, f"{HERE}/ai32_reasoning_readout.py",
             f"{logs}/ai9-frontier/gpt56luna-base",
             "--status", "confirmatory"],
        ),
        (
            "5. TIER TABLE, DESCRIPTIVE — incl. the luna->sol 3.20x compliance point\n"
            "   ratio, quotable ONLY beside section 6's luna-sol interval\n"
            "   (ai31_tier_table.py; readouts: midtier-addendum.md, ai33-luna-endpoint.md)",
            [sys.executable, f"{HERE}/ai31_tier_table.py", "--logs", logs],
        ),
        (
            "6. PAIRWISE CROSS-MODEL BOOTSTRAP — every contrast includes zero on both\n"
            "   co-primaries (ai33_cross_model_bootstrap.py; readout:\n"
            "   ai33-luna-endpoint.md §6)",
            [sys.executable, f"{HERE}/ai33_cross_model_bootstrap.py", "--logs", logs],
        ),
        (
            "7. GPT-5-NANO CHEAP ARM — E1 deference gap +0.190 and paired pushback\n"
            "   flip 17.1% toward compliance vs 9.0% null floor (analyze_logs.py;\n"
            "   readout: ai6-readout.md)",
            [sys.executable, f"{HERE}/analyze_logs.py",
             f"{logs}/ai15-gpt5nano/base", f"{logs}/ai18-backfill/gpt5nano-pushback"],
        ),
    ]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Reprint every headline number for the MATS write-up from the "
                    "logs on disk. See docs/verification.md for the claim-by-claim map.")
    ap.add_argument("--logs", default=f"{ROOT}/logs",
                    help="root of the local logs tree (default: <repo>/logs)")
    ap.add_argument("--only", type=int, default=None, metavar="N",
                    help="run only section N (1-7), for a quick partial check")
    args = ap.parse_args()

    logs = os.path.abspath(args.logs)
    todo = sections(logs)
    if args.only is not None:
        if not 1 <= args.only <= len(todo):
            raise SystemExit(f"--only must be 1..{len(todo)}")
        todo = [todo[args.only - 1]]

    print("=" * 78)
    print("AI-38 — HEADLINE-NUMBER VERIFICATION")
    print("Every number below is produced by a committed pipeline over the logs on")
    print("disk, with the pipeline's own pinned seed. Map to claims via")
    print("docs/verification.md; guardrails (7- vs 5-scenario harm estimands, the")
    print("3.20x citation rule, sol E1=E5) are stated there and in each readout doc.")
    print("=" * 78)

    failures: list[str] = []
    t0 = time.time()
    for title, argv in todo:
        print(f"\n{'#' * 78}\n# {title}\n#\n# $ {' '.join(os.path.relpath(a, ROOT) if a.startswith(ROOT) else a for a in argv)}\n{'#' * 78}\n",
              flush=True)
        # Sections 5-6 also honour AI31_LOG_ROOT; pin it to --logs so no
        # section can read a different tree than the others (Codex, PR #30).
        env = {**os.environ, "AI31_LOG_ROOT": logs}
        proc = subprocess.run(argv, cwd=ROOT, env=env)
        if proc.returncode != 0:
            failures.append(title.splitlines()[0])
            print(f"\n*** SECTION FAILED (exit {proc.returncode}): {title.splitlines()[0]}",
                  flush=True)

    print(f"\n{'=' * 78}")
    print(f"VERIFICATION {'FAILED' if failures else 'COMPLETE'} "
          f"in {time.time() - t0:.0f}s "
          f"({len(todo) - len(failures)}/{len(todo)} sections ok)")
    for f in failures:
        print(f"  FAILED: {f}")
    print("=" * 78)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
