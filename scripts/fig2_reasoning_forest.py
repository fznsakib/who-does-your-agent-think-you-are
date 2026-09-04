"""Figure 2 (AI-38): forest plot of R1 — the ceo − analyst reasoning-token gap (%).

Five arms, split by evidentiary status per the AI-32 pre-registration
(`docs/analysis-plan.md` § J): the AI-9 arms that motivated the effect
(opus-5, sol) are EXPLORATORY; the arms that did not (terra, sonnet-5, luna)
are CONFIRMATORY. The split is drawn on the figure, not left to a caption.

Reuses `principal_eval.reasoning` — `load_reasoning_rows` + `reasoning_report`
— i.e. exactly the pipeline behind `scripts/ai32_reasoning_readout.py`, so the
plotted R1 intervals AND the R6 verdict annotations are computed from the same
loaded rows (95% scenario-clustered bootstrap, 10,000 draws, seed 6, contrasts
paired within each resample). `reasoning_report` refuses to pool more than one
run into an arm, so a smoke log sitting beside a production log fails loudly
rather than being silently picked. Never unzips `.eval` files; `inspect_ai.log`
API only.

Usage:
    uv run python scripts/fig2_reasoning_forest.py [--logs <root>]

Writes docs/pilots/figures/fig2_reasoning_forest.{png,pdf}.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, f"{ROOT}/src")

from principal_eval.reasoning import load_reasoning_rows, reasoning_report  # noqa: E402

# (label, log dir relative to --logs, evidentiary status per the amendment).
# The R6 verdict is NOT listed here: it is computed from the logs below, so a
# rerun or corrected arm can never carry a stale annotation.
ARMS = [
    ("claude-opus-5 (frontier)", "ai9-frontier/opus5-base", "exploratory"),
    ("gpt-5.6-sol (frontier)", "ai9-frontier/gpt56sol-base", "exploratory"),
    ("gpt-5.6-terra (mid)", "ai31-midtier/terra-base", "confirmatory"),
    ("claude-sonnet-5 (mid)", "ai31-midtier/sonnet5-base", "confirmatory"),
    ("gpt-5.6-luna (low)", "ai9-frontier/gpt56luna-base", "confirmatory"),
]

SHORT_VERDICT = {
    "survivor": "more deliberation",
    "verbosity, not deliberation": "verbosity, not separable",
    "not established": "no reliable gap",
    "control unavailable": "gap found, per-turn check unavailable",
    "per-turn sign reversal — inconclusive": "gap found, per-turn check inconsistent",
    "artefact of episode length": "gap explained by longer episodes",
}


def r1_block(log_dir: str) -> dict:
    """R1's relative gap {point, lo, hi, n_high, n_low} plus the R6 verdict,
    from the full R-series pipeline over EVERY .eval in the arm directory.
    `reasoning_report` raises if those logs belong to more than one run."""
    paths = sorted(glob.glob(f"{log_dir}/**/*.eval", recursive=True))
    if not paths:
        raise SystemExit(f"no .eval under {log_dir}")
    report = reasoning_report(load_reasoning_rows(paths))
    blocks = [b for b in report["models"].values() if b["arm"] == "base"]
    if len(blocks) != 1:
        raise SystemExit(f"{log_dir}: expected exactly one base-arm model block, "
                         f"got {[b['model'] for b in blocks]}")
    b = blocks[0]
    if "R1_status_gap" not in b:
        raise SystemExit(f"{log_dir}: {b.get('note', 'no R1 available')}")
    c = b["R1_status_gap"]
    verdict = b["R6_verdict"]["verdict"]
    return {**c["relative"], "n_high": c["n_high"], "n_low": c["n_low"],
            "verdict": SHORT_VERDICT.get(verdict, verdict)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default=f"{ROOT}/logs")
    ap.add_argument("--out-dir", default=f"{ROOT}/docs/pilots/figures")
    args = ap.parse_args()

    results = []
    for label, rel_dir, status in ARMS:
        ci = r1_block(f"{args.logs}/{rel_dir}")
        results.append((label, status, ci["verdict"], ci))
        print(f"{label:28s} {status:12s} R1 {ci['point']:+.1%} "
              f"[{ci['lo']:+.1%}, {ci['hi']:+.1%}]  n {ci['n_high']} vs {ci['n_low']}"
              f"  R6: {ci['verdict']}")

    fig, ax = plt.subplots(figsize=(9, 5))
    ys = list(range(len(results) - 1, -1, -1))
    for y, (label, status, verdict, ci) in zip(ys, results):
        color = "#c46f30" if status == "exploratory" else "#3d7a4f"
        ax.errorbar([ci["point"] * 100], [y],
                    xerr=[[(ci["point"] - ci["lo"]) * 100], [(ci["hi"] - ci["point"]) * 100]],
                    fmt="o", color=color, ecolor=color, elinewidth=2, capsize=4,
                    markersize=6)
        ax.annotate(f"{ci['point']*100:+.1f}%  [{ci['lo']*100:+.1f}, {ci['hi']*100:+.1f}]"
                    f"   {verdict}",
                    (ci["hi"] * 100, y), xytext=(8, -3), textcoords="offset points",
                    fontsize=8, color="#333333")

    ax.axvline(0, color="#888888", linewidth=1, linestyle="--")
    # Visual split between the exploratory pair and the confirmatory trio.
    n_expl = sum(1 for _, s, _, _ in results if s == "exploratory")
    split_y = ys[n_expl - 1] - 0.5
    ax.axhline(split_y, color="#bbbbbb", linewidth=0.8)
    ax.text(ax.get_xlim()[1] * 0.02 + 145, split_y + 0.15, "arms that motivated the test",
            fontsize=8, color="#c46f30", ha="right")
    ax.text(ax.get_xlim()[1] * 0.02 + 145, split_y - 0.35, "held-out arms",
            fontsize=8, color="#3d7a4f", ha="right")

    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in results], fontsize=9)
    ax.set_xlabel("Reasoning-token gap: CEO minus analyst, as % of the analyst's mean "
                  "(labelled R1 in the underlying analysis)\n"
                  "95% scenario-clustered bootstrap CI (7 clusters, 10,000 draws, seed 6)")
    ax.set_title("Does the model reason more when it believes it is talking to the CEO?\n"
                 "(gap is positive and clear of zero on all five arms; label at each point "
                 "is the mechanism verdict — see legend)", fontsize=10)
    ax.set_xlim(-15, 160)
    ax.grid(axis="x", alpha=0.25)
    fig.text(0.5, 0.03,
             "R1 = CEO minus analyst reasoning tokens per sample.",
             ha="center", fontsize=7.5, color="#444444")
    fig.text(0.5, 0.005,
             "\"Arms that motivated the test\" first suggested this effect; "
             "\"held-out arms\" tested it on fresh models afterwards.",
             ha="center", fontsize=7.5, color="#444444")
    fig.tight_layout(rect=(0, 0.08, 1, 1))

    os.makedirs(args.out_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        out = f"{args.out_dir}/fig2_reasoning_forest.{ext}"
        fig.savefig(out, dpi=200)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
