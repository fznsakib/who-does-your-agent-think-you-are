"""Figure: discovery -- does the model look up who is asking?

Answers the first of the three research questions (discovery / deference /
calibration). One row per model, two marks per row: the CEO and analyst rates
of active identity lookup on the status-irrelevant scenarios, i.e. any cue
read beyond the forced initial identity read. A small pooled-overall tick
sits beside the two persona marks.

Six rows, grouped by provider and ordered by tier, matching every other
figure in this set: claude-haiku-4-5, claude-sonnet-5, claude-opus-5,
gpt-5.6-luna, gpt-5.6-terra, gpt-5.6-sol. gpt-5-nano is excluded -- it is a
cheap development subject, not a tier-ladder endpoint (see CLAUDE.md).

Reuses `principal_eval.analysis.load_rows` / `scored` / `identity_seeking_rate`
-- the exact functions behind Table 6 of docs/verification.md
(`scripts/ai49_identity_seeking.py`) -- so a plotted rate cannot silently
drift from that table. haiku is read through the identical status_irrelevant-
only pipeline, exactly as Table 6's legacy comparison row is (an earlier
harness version, n=70 per persona cell rather than n=140).

The script prints every plotted rate next to the published Table 6 value with
PASS/FAIL, and exits non-zero on any FAIL.

Usage:
    uv run python scripts/fig_discovery.py [--logs <root>]

Writes docs/pilots/figures/fig_discovery.{png,pdf}.
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

from principal_eval.analysis import identity_seeking_rate, load_rows, scored  # noqa: E402

# (row label, log dir relative to --logs, clean?)
ROWS = [
    ("claude-haiku-4-5", "ai5-pilot/haiku-base", False),
    ("claude-sonnet-5", "ai31-midtier/sonnet5-base", True),
    ("claude-opus-5", "ai9-frontier/opus5-base", True),
    ("gpt-5.6-luna", "ai9-frontier/gpt56luna-base", True),
    ("gpt-5.6-terra", "ai31-midtier/terra-base", True),
    ("gpt-5.6-sol", "ai9-frontier/gpt56sol-base", True),
]

# Published Table 6 values (docs/verification.md): ceo, analyst, overall.
PUBLISHED = {
    "claude-haiku-4-5": {"ceo": 0.114, "analyst": 0.157, "overall": 0.162},
    "claude-sonnet-5": {"ceo": 1.000, "analyst": 1.000, "overall": 0.969},
    "claude-opus-5": {"ceo": 1.000, "analyst": 1.000, "overall": 1.000},
    "gpt-5.6-luna": {"ceo": 0.429, "analyst": 0.350, "overall": 0.349},
    "gpt-5.6-terra": {"ceo": 0.457, "analyst": 0.371, "overall": 0.319},
    "gpt-5.6-sol": {"ceo": 0.907, "analyst": 0.650, "overall": 0.699},
}

CEO_COLOR = "#009E73"      # Okabe-Ito teal -- distinct from the deference figure's blue/orange
ANALYST_COLOR = "#CC79A7"  # Okabe-Ito reddish-purple


def one_eval(log_dir: str) -> str:
    found = sorted(glob.glob(f"{log_dir}/**/*.eval", recursive=True))
    if len(found) != 1:
        raise SystemExit(f"expected exactly one .eval under {log_dir}, found {len(found)}")
    return found[0]


def model_rates(log_dir: str) -> dict:
    path = one_eval(log_dir)
    report = load_rows([path])
    rows = scored(report.rows)
    si_rows = [r for r in rows if r.family == "status_irrelevant"]
    table = identity_seeking_rate(rows)["status_irrelevant"]["active_identity_seeking"]
    ceo = [r for r in si_rows if r.persona == "ceo"]
    analyst = [r for r in si_rows if r.persona == "analyst"]
    overall = sum(1.0 for r in si_rows if r.active_identity_seeking) / len(si_rows)
    return {
        "ceo": (table.get("ceo"), len(ceo)),
        "analyst": (table.get("analyst"), len(analyst)),
        "overall": (overall, len(si_rows)),
    }


def check(label: str, key: str, got: float) -> bool:
    pub = PUBLISHED[label][key]
    ok = abs(got - pub) < 0.0006
    tag = "PASS" if ok else "FAIL"
    print(f"  {label:18s} {key:8s}  plotted {got:.3f}  published {pub:.3f}  {tag}")
    return ok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default=f"{ROOT}/logs")
    ap.add_argument("--out-dir", default=f"{ROOT}/docs/pilots/figures")
    args = ap.parse_args()

    results = []
    for label, rel_dir, clean in ROWS:
        r = model_rates(f"{args.logs}/{rel_dir}")
        results.append((label, clean, r))

    print("PLOTTED vs PUBLISHED (docs/verification.md, Table 6) -- active identity "
          "lookup rate, status_irrelevant only")
    all_ok = True
    for label, clean, r in results:
        for key in ("ceo", "analyst", "overall"):
            all_ok &= check(label, key, r[key][0])

    fig, ax = plt.subplots(figsize=(9, 5))
    n_rows = len(results)
    ys = list(range(n_rows - 1, -1, -1))

    for y, (label, clean, r) in zip(ys, results):
        ceo_v, ceo_n = r["ceo"]
        ana_v, ana_n = r["analyst"]
        overall_v, overall_n = r["overall"]
        ax.scatter([overall_v], [y], marker="|", s=260, color="#888888",
                   linewidth=1.4, zorder=2)
        ax.scatter([ceo_v], [y], marker="o", s=70, facecolor=CEO_COLOR,
                   edgecolor=CEO_COLOR, zorder=3)
        ax.scatter([ana_v], [y], marker="s", s=60, facecolor=ANALYST_COLOR,
                   edgecolor=ANALYST_COLOR, zorder=3)

    labels = [label for label, _, _ in results]
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=9)

    sep_y = (ys[0] + ys[1]) / 2
    ax.axhline(sep_y, color="#cccccc", linewidth=0.8)

    ax.set_xlim(0, 1)
    ax.set_xlabel("share of episodes with an identity lookup beyond the forced email read",
                  fontsize=9)
    ax.set_title("Does the agent look up who is asking?", fontsize=11)
    ax.grid(axis="x", alpha=0.25)

    handles = [
        plt.Line2D([0], [0], marker="o", color=CEO_COLOR, linestyle="none",
                   markersize=8, label="CEO"),
        plt.Line2D([0], [0], marker="s", color=ANALYST_COLOR, linestyle="none",
                   markersize=7, label="analyst"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=9, framealpha=0.9)

    fig.tight_layout()

    if not all_ok:
        print("\n*** FAIL: at least one plotted value does not match "
              "docs/verification.md -- refusing to overwrite the committed "
              "figure with a value that disagrees with the published table ***")
        sys.exit(1)

    os.makedirs(args.out_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        out = f"{args.out_dir}/fig_discovery.{ext}"
        fig.savefig(out, dpi=200)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
