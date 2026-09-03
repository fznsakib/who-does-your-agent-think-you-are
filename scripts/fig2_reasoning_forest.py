"""Figure 2 (AI-38): forest plot of R1 — the ceo − analyst reasoning-token gap (%).

Five arms, split by evidentiary status per the AI-32 pre-registration
(`docs/analysis-plan.md` § J): the AI-9 arms that motivated the effect
(opus-5, sol) are EXPLORATORY; the arms that did not (terra, sonnet-5, luna)
are CONFIRMATORY. The split is drawn on the figure, not left to a caption.

Reuses `principal_eval.reasoning` — `load_reasoning_rows`, `ladder_rows`,
`contrast` with `REASONING_PER_SAMPLE` — i.e. exactly the pipeline behind
`scripts/ai32_reasoning_readout.py`, so the plotted intervals are the readout's
own (95% scenario-clustered bootstrap, 10,000 draws, seed 6, contrasts paired
within each resample). Never unzips `.eval` files; `inspect_ai.log` API only.

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

from principal_eval.reasoning import (  # noqa: E402
    HIGH_STATUS,
    REASONING_PER_SAMPLE,
    REFERENCE,
    contrast,
    ladder_rows,
    load_reasoning_rows,
)

# (label, log dir relative to --logs, status, R6 verdict from the readout docs)
ARMS = [
    ("claude-opus-5 (frontier)", "ai9-frontier/opus5-base", "exploratory", "survivor"),
    ("gpt-5.6-sol (frontier)", "ai9-frontier/gpt56sol-base", "exploratory", "survivor"),
    ("gpt-5.6-terra (mid)", "ai31-midtier/terra-base", "confirmatory", "survivor"),
    ("claude-sonnet-5 (mid)", "ai31-midtier/sonnet5-base", "confirmatory", "verbosity"),
    ("gpt-5.6-luna (low)", "ai9-frontier/gpt56luna-base", "confirmatory", "verbosity"),
]


def r1_relative(log_dir: str) -> dict:
    """R1's relative gap {point, lo, hi} for one production arm."""
    paths = sorted(glob.glob(f"{log_dir}/**/*.eval", recursive=True))
    if not paths:
        raise SystemExit(f"no .eval under {log_dir}")
    # Production dirs hold a single run; take the latest, matching the
    # per-arm convention of ai9_frontier_readout.py / ai31_tier_table.py.
    load = load_reasoning_rows([paths[-1]])
    scoped = ladder_rows(load.analysable())
    c = contrast(scoped, HIGH_STATUS, REFERENCE, REASONING_PER_SAMPLE)
    return {**c["relative"], "n_high": c["n_high"], "n_low": c["n_low"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default=f"{ROOT}/logs")
    ap.add_argument("--out-dir", default=f"{ROOT}/docs/pilots/figures")
    args = ap.parse_args()

    results = []
    for label, rel_dir, status, verdict in ARMS:
        ci = r1_relative(f"{args.logs}/{rel_dir}")
        results.append((label, status, verdict, ci))
        print(f"{label:28s} {status:12s} R1 {ci['point']:+.1%} "
              f"[{ci['lo']:+.1%}, {ci['hi']:+.1%}]  n {ci['n_high']} vs {ci['n_low']}")

    fig, ax = plt.subplots(figsize=(9, 5))
    ys = list(range(len(results) - 1, -1, -1))
    for y, (label, status, verdict, ci) in zip(ys, results):
        color = "#c46f30" if status == "exploratory" else "#3d7a4f"
        ax.errorbar([ci["point"] * 100], [y],
                    xerr=[[(ci["point"] - ci["lo"]) * 100], [(ci["hi"] - ci["point"]) * 100]],
                    fmt="o", color=color, ecolor=color, elinewidth=2, capsize=4,
                    markersize=6)
        ax.annotate(f"{ci['point']*100:+.1f}%  [{ci['lo']*100:+.1f}, {ci['hi']*100:+.1f}]"
                    f"   R6: {verdict}",
                    (ci["hi"] * 100, y), xytext=(8, -3), textcoords="offset points",
                    fontsize=8, color="#333333")

    ax.axvline(0, color="#888888", linewidth=1, linestyle="--")
    # Visual split between the exploratory pair and the confirmatory trio.
    n_expl = sum(1 for _, s, _, _ in results if s == "exploratory")
    split_y = ys[n_expl - 1] - 0.5
    ax.axhline(split_y, color="#bbbbbb", linewidth=0.8)
    ax.text(ax.get_xlim()[1] * 0.02 + 145, split_y + 0.15, "EXPLORATORY (motivated the effect — AI-9 arms)",
            fontsize=8, color="#c46f30", ha="right")
    ax.text(ax.get_xlim()[1] * 0.02 + 145, split_y - 0.35, "CONFIRMATORY (out-of-sample — AI-31 / AI-33 arms)",
            fontsize=8, color="#3d7a4f", ha="right")

    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in results], fontsize=9)
    ax.set_xlabel("R1: ceo − analyst reasoning tokens per sample, relative gap (%)\n"
                  "95% scenario-clustered bootstrap CI (7 clusters, 10,000 draws, seed 6)")
    ax.set_title("Status-sensitive reasoning expenditure — R1 across five arms\n"
                 "(positive and clear of zero on all five; the R6 mechanism verdict "
                 "is the deliberation-vs-verbosity call)", fontsize=10)
    ax.set_xlim(-15, 160)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()

    os.makedirs(args.out_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        out = f"{args.out_dir}/fig2_reasoning_forest.{ext}"
        fig.savefig(out, dpi=200)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
