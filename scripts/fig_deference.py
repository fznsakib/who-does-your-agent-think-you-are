"""Figure: the CEO-analyst deference gap as one forest, both provider ladders,
one panel. Renamed and adapted from `fig1_deference_forest.py` (AI-46) for the
one-figure-per-finding set: this is the Deference figure.

One row per model, ordered provider then tier, each row carrying two markers
(compliance gap, harmful-action gap) with a 95% scenario-clustered CI
whisker, status_irrelevant scenarios only.

Six rows: claude-haiku-4-5, claude-sonnet-5, claude-opus-5, gpt-5.6-luna,
gpt-5.6-terra, gpt-5.6-sol, with a thin rule between the two providers'
blocks, all drawn in the same colours and marker style -- no row is visually
singled out. Five of the six (every row but haiku) are the mutually clean
frontier-generation arms and are read with `ai9_frontier_readout.load()` /
`estimands()` / `bootstrap()` -- the exact functions behind Table 1 in
docs/verification.md, so this script cannot silently drift from that table.
haiku ran on an earlier version of the harness, before harmful_action was
added to score metadata; it is read the same way the tier table
(`ai31_tier_table.py`) reads it -- compliance over all 7 status_irrelevant
scenarios (n=70 per persona cell), harmful action backfilled from the
recorded tool arguments via `principal_eval.harm.harm_verdict` over 5 of
those 7 scenarios (n=50 per persona cell; two scenarios are dropped for this
arm everywhere it appears, because its logs predate the structural
predicates that make those two scenarios' harm outcome decidable). This
narrower harm estimand is not marked on the figure itself -- it belongs in
the prose caption -- but it is preserved here in the PLOTTED vs PUBLISHED
check and the script's printed output.

Both loaders use the same bootstrap machinery: 10,000 draws, seed 0,
scenario-clustered resampling (never sample-level).

The script prints, for every row and outcome, the plotted estimate/CI next to
the published value from docs/verification.md, with PASS/FAIL, and exits
non-zero on any FAIL -- this figure is not allowed to show a number that
disagrees with the table a reader would cross-check it against.

Usage:
    uv run python scripts/fig_deference.py [--logs <root>]

Writes docs/pilots/figures/fig_deference.{png,pdf}.
"""
from __future__ import annotations

import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, f"{ROOT}/src")
sys.path.insert(0, HERE)

import ai9_frontier_readout as F  # noqa: E402
import ai31_tier_table as T  # noqa: E402

# (row label, log dir relative to --logs, clean?)
ROWS = [
    ("claude-haiku-4-5", "ai5-pilot/haiku-base", False),
    ("claude-sonnet-5", "ai31-midtier/sonnet5-base", True),
    ("claude-opus-5", "ai9-frontier/opus5-base", True),
    ("gpt-5.6-luna", "ai9-frontier/gpt56luna-base", True),
    ("gpt-5.6-terra", "ai31-midtier/terra-base", True),
    ("gpt-5.6-sol", "ai9-frontier/gpt56sol-base", True),
]

# Published values from docs/verification.md, checked against below.
# Table 1 (five clean arms, both outcomes on the 7-scenario registered
# estimand) and Table 4 (haiku's row of the backfilled tier ladder: compliance
# is the unaffected 7-scenario number quoted in the ai33-luna-endpoint doc's
# Table-1-style row, harm is the 5-scenario cross-fork-safe number).
PUBLISHED = {
    "claude-haiku-4-5": {"comp": (0.057, 0.000, 0.171), "harm": (0.080, 0.000, 0.240)},
    "claude-sonnet-5": {"comp": (0.071, 0.000, 0.214), "harm": (0.071, 0.000, 0.214)},
    "claude-opus-5": {"comp": (0.057, 0.000, 0.171), "harm": (0.057, 0.000, 0.171)},
    "gpt-5.6-luna": {"comp": (0.114, 0.007, 0.300), "harm": (0.136, 0.007, 0.336)},
    "gpt-5.6-terra": {"comp": (0.068, 0.000, 0.182), "harm": (0.093, 0.007, 0.207)},
    "gpt-5.6-sol": {"comp": (0.036, 0.000, 0.093), "harm": (0.100, 0.007, 0.229)},
}


def clean_row(log_dir: str) -> dict:
    """CEO-analyst gap on compliance and harm, from the Table 1 pipeline."""
    data = F.load(log_dir)
    rows = data["rows"]
    _, subset, fn = F.estimands(rows)[0]  # E1 deference (ceo-analyst)
    scens = sorted({r.scenario for r in subset})
    n = len([r for r in rows if r.family == "status_irrelevant" and r.persona == "ceo"])
    co, cl, ch = F.bootstrap(lambda s: fn(s, 0.5, None), scens)
    ho, hl, hh = F.bootstrap(lambda s: fn(s, 0.5, 0.0), scens)
    return {"comp": (co, cl, ch), "harm": (ho, hl, hh), "n_comp": n, "n_harm": n,
            "n_harm_scenarios": len(scens), "n_comp_scenarios": len(scens)}


def haiku_row(log_dir: str) -> dict:
    """CEO-analyst gap on compliance (7 scenarios) and backfilled harm (5
    scenarios, per the AI-23 exclusion T.HARM_EXCLUDED enforces)."""
    comp, harm, *_ = T.load(log_dir)
    cs = sorted({s for v in comp.values() for s in v})
    hs = sorted({s for v in harm.values() for s in v})
    co, cl, ch = T.gap(comp, "ceo", "analyst", cs)
    ho, hl, hh = T.gap(harm, "ceo", "analyst", hs)
    n_comp = sum(len(v) for v in comp["ceo"].values())
    n_harm = sum(len(v) for v in harm["ceo"].values())
    return {"comp": (co, cl, ch), "harm": (ho, hl, hh), "n_comp": n_comp, "n_harm": n_harm,
            "n_harm_scenarios": len(hs), "n_comp_scenarios": len(cs)}


def check(label: str, outcome: str, got: tuple[float, float, float]) -> bool:
    pub = PUBLISHED[label][outcome]
    ok = all(abs(g - p) < 0.0006 for g, p in zip(got, pub))
    tag = "PASS" if ok else "FAIL"
    print(f"  {label:18s} {outcome:5s}  plotted {got[0]:+.3f} [{got[1]:+.3f},{got[2]:+.3f}]"
          f"  published {pub[0]:+.3f} [{pub[1]:+.3f},{pub[2]:+.3f}]  {tag}")
    return ok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default=f"{ROOT}/logs")
    ap.add_argument("--out-dir", default=f"{ROOT}/docs/pilots/figures")
    args = ap.parse_args()

    T.set_log_root(args.logs)

    results = []
    for label, rel_dir, clean in ROWS:
        log_dir = f"{args.logs}/{rel_dir}"
        r = haiku_row(log_dir) if not clean else clean_row(log_dir)
        results.append((label, clean, r))

    print("PLOTTED vs PUBLISHED (docs/verification.md) — CEO-analyst gap, "
          "status_irrelevant only")
    print(f"  note: {results[0][0]} harm covers 5 of 7 scenarios (n=50 per "
          f"persona cell); its compliance covers all 7 (n=70) -- narrower "
          f"harm estimand only, not shown on the figure (see docstring)")
    all_ok = True
    for label, clean, r in results:
        for outcome in ("comp", "harm"):
            all_ok &= check(label, outcome, r[outcome])

    fig, ax = plt.subplots(figsize=(9.5, 5.5))

    n_rows = len(results)
    ys = list(range(n_rows - 1, -1, -1))
    comp_off, harm_off = 0.12, -0.12
    comp_color = "#3d6da8"
    harm_color = "#c46f30"

    # Every row is drawn identically -- same colours, same marker style,
    # clean or not. The only place the haiku row's narrower harm estimand is
    # recorded is the PLOTTED vs PUBLISHED check above and this script's
    # docstring; it does not get a distinct look on the figure itself.
    for y, (label, clean, r) in zip(ys, results):
        co, cl, ch = r["comp"]
        ho, hl, hh = r["harm"]
        ax.errorbar([co], [y + comp_off], xerr=[[co - cl], [ch - co]],
                    fmt="none", ecolor=comp_color, elinewidth=1.6, capsize=3)
        ax.errorbar([ho], [y + harm_off], xerr=[[ho - hl], [hh - ho]],
                    fmt="none", ecolor=harm_color, elinewidth=1.6, capsize=3)
        ax.scatter([co], [y + comp_off], marker="o", s=55,
                   facecolor=comp_color, edgecolor=comp_color, linewidth=1.3,
                   zorder=3)
        ax.scatter([ho], [y + harm_off], marker="^", s=55,
                   facecolor=harm_color, edgecolor=harm_color, linewidth=1.3,
                   zorder=3)

    ax.axvline(0, color="#888888", linewidth=1, linestyle="--")

    # Thin separator between the Anthropic and OpenAI blocks (rows 0-2 vs 3-5
    # in ROWS order; ys is reversed so the separator sits between ys[2] and
    # ys[3]).
    sep_y = (ys[2] + ys[3]) / 2
    ax.axhline(sep_y, color="#cccccc", linewidth=0.8)

    labels = [label for label, _, _ in results]
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("CEO minus analyst gap, status-irrelevant scenarios only "
                  "(95% CI)", fontsize=9)
    ax.set_title("Does the model treat the CEO more deferentially than the analyst?",
                 fontsize=11)
    ax.set_xlim(-0.05, 0.40)
    ax.grid(axis="x", alpha=0.25)

    handles = [
        plt.Line2D([0], [0], marker="o", color=comp_color, linestyle="none",
                   markersize=7, label="compliance gap"),
        plt.Line2D([0], [0], marker="^", color=harm_color, linestyle="none",
                   markersize=7, label="harmful-action gap"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=8, framealpha=0.9)

    fig.tight_layout()

    if not all_ok:
        print("\n*** FAIL: at least one plotted value does not match "
              "docs/verification.md -- refusing to overwrite the committed "
              "figure with a value that disagrees with the published table ***")
        sys.exit(1)

    os.makedirs(args.out_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        out = f"{args.out_dir}/fig_deference.{ext}"
        fig.savefig(out, dpi=200)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
