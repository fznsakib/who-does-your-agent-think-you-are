"""Figure 1 (AI-38): compliance by persona, status_irrelevant scenarios only, per model.

One panel per arm: the five mutually-clean frontier-generation base arms, plus
`gpt-5-nano` as a labelled legacy extra (pre-AI-16 harness fork, pre-AI-26
rubric, one generation older — rule 18 forbids reading it as a sixth clean
point, so its panel is visually set apart).

Reuses `scripts/ai31_tier_table.py`'s `load()` for every cell value (the same
loader the tier table and the cross-model bootstrap use, so the three can never
disagree about a cell), and `principal_eval.analysis.bootstrap_ci` for the 95%
scenario-clustered interval on each persona mean (rule 10; 10,000 draws,
seed 6 — the module default). n per cell is printed on the panel.

Compliance is the judge co-primary on all 7 status_irrelevant scenarios
(COMPLIED=1, PARTIAL=0.5), identical to the E1 tables in the readout docs.

Usage:
    uv run python scripts/fig1_compliance_by_persona.py [--logs <root>]

Writes docs/pilots/figures/fig1_compliance_by_persona.{png,pdf}.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, f"{ROOT}/src")
sys.path.insert(0, HERE)

import ai31_tier_table as T  # noqa: E402
from principal_eval.analysis import bootstrap_ci, mean  # noqa: E402

PERSONAS = ["ceo", "chief_of_staff", "researcher", "anonymous", "analyst", "external"]
SHORT = {"ceo": "ceo", "chief_of_staff": "cos", "researcher": "res",
         "anonymous": "anon", "analyst": "ana", "external": "ext"}

# (panel title, log dir relative to --logs, clean?)
ARMS = [
    ("claude-opus-5 (flagship)", "ai9-frontier/opus5-base", True),
    ("gpt-5.6-sol (flagship)", "ai9-frontier/gpt56sol-base", True),
    ("claude-sonnet-5 (mid)", "ai31-midtier/sonnet5-base", True),
    ("gpt-5.6-terra (mid)", "ai31-midtier/terra-base", True),
    ("gpt-5.6-luna (low)", "ai9-frontier/gpt56luna-base", True),
    ("gpt-5-nano (LEGACY: cross-fork,\npre-AI-26 rubric, older generation)",
     "ai15-gpt5nano/base", False),
]


@dataclass
class Cell:
    scenario: str
    value: float


def persona_stats(comp: dict) -> dict[str, tuple[float, float, float, int]]:
    """persona -> (mean, lo, hi, n) with a scenario-clustered bootstrap CI."""
    out = {}
    for p in PERSONAS:
        rows = [Cell(s, v) for s, vals in comp.get(p, {}).items() for v in vals]
        if not rows:
            continue
        ci = bootstrap_ci(rows, lambda rs: mean([r.value for r in rs]))
        out[p] = (ci["point"], ci["lo"], ci["hi"], len(rows))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default=f"{ROOT}/logs")
    ap.add_argument("--out-dir", default=f"{ROOT}/docs/pilots/figures")
    args = ap.parse_args()

    fig, axes = plt.subplots(2, 3, figsize=(13, 7.5), sharey=True)
    fig.suptitle("Compliance by persona — status_irrelevant scenarios only "
                 "(judge co-primary, COMPLIED=1 / PARTIAL=0.5)\n"
                 "95% scenario-clustered bootstrap CIs (7 clusters, 10,000 draws)",
                 fontsize=11)

    for ax, (title, rel_dir, clean) in zip(axes.flat, ARMS):
        comp, *_ = T.load(f"{args.logs}/{rel_dir}")
        stats = persona_stats(comp)
        xs, means, los, his = [], [], [], []
        ticklabels = []
        for i, p in enumerate(PERSONAS):
            if p not in stats:
                ticklabels.append(SHORT[p])
                continue
            m, lo, hi, n = stats[p]
            xs.append(i)
            means.append(m)
            los.append(m - lo)
            his.append(hi - m)
            ticklabels.append(f"{SHORT[p]}\nn={n}")
        color = "#4878b0" if clean else "#b0b0b0"
        ax.bar(xs, means, color=color, width=0.62,
               hatch=None if clean else "//", edgecolor="white")
        ax.errorbar(xs, means, yerr=[los, his], fmt="none",
                    ecolor="#333333", elinewidth=1.2, capsize=3)
        ax.set_title(title, fontsize=9, color="#000000" if clean else "#666666")
        ax.set_xticks(range(len(PERSONAS)))
        ax.set_xticklabels(ticklabels, fontsize=7)
        ax.set_ylim(0, 0.45)
        ax.grid(axis="y", alpha=0.25)

    for ax in axes[:, 0]:
        ax.set_ylabel("mean compliance")
    fig.text(0.5, 0.005,
             "Clean arms (blue) share one harness/rubric/predicates; gpt-5-nano "
             "(grey, hatched) is a labelled legacy extra on the pre-AI-16 fork — "
             "not comparable under rule 18.",
             ha="center", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.03, 1, 0.99))

    os.makedirs(args.out_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        out = f"{args.out_dir}/fig1_compliance_by_persona.{ext}"
        fig.savefig(out, dpi=200)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
