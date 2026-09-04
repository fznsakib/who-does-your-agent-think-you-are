"""Figure 1 (AI-46): the CEO-analyst deference gap as one forest, both provider
ladders, one panel.

The previous Figure 1 (`fig1_compliance_by_persona.py`) showed six small
panels of per-persona compliance; a reader had to subtract two bars by eye to
see the number the write-up actually leads with. This script plots that
number directly -- one row per model, ordered provider then tier, each row
carrying two markers (compliance gap, harmful-action gap) with a 95%
scenario-clustered CI whisker, status_irrelevant scenarios only.

Six rows: claude-haiku-4-5, claude-sonnet-5, claude-opus-5, gpt-5.6-luna,
gpt-5.6-terra, gpt-5.6-sol, with a thin rule between the two providers'
blocks. Five of the six (every row but haiku) are the mutually clean
frontier-generation arms and are read with `ai9_frontier_readout.load()` /
`estimands()` / `bootstrap()` -- the exact functions behind Table 1 in
docs/verification.md, so this script cannot silently drift from that table.
haiku is drawn from an earlier version of the harness, before harmful_action
was added to score metadata; it is read the same way the tier table
(`ai31_tier_table.py`) reads it -- compliance over all 7 status_irrelevant
scenarios, harmful action backfilled from the recorded tool arguments via
`principal_eval.harm.harm_verdict` over 5 of those 7 scenarios (two are
dropped everywhere that arm appears, because its logs predate the structural
predicates that make those two scenarios' harm outcome decidable). haiku is
drawn grey with hollow/hatched markers and labelled "earlier harness version;
shown for reference" -- never treated as a seventh clean ladder point.

Both loaders use the same bootstrap machinery: 10,000 draws, seed 0,
scenario-clustered resampling (never sample-level).

The script prints, for every row and outcome, the plotted estimate/CI next to
the published value from docs/verification.md, with PASS/FAIL, and exits
non-zero on any FAIL -- this figure is not allowed to show a number that
disagrees with the table a reader would cross-check it against.

Usage:
    uv run python scripts/fig1_deference_forest.py [--logs <root>]

Writes docs/pilots/figures/fig1_deference_forest.{png,pdf}.
"""
from __future__ import annotations

import argparse
import os
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, f"{ROOT}/src")
sys.path.insert(0, HERE)

import ai9_frontier_readout as F  # noqa: E402
import ai31_tier_table as T  # noqa: E402

# (row label, tier word, log dir relative to --logs, clean?)
ROWS = [
    ("claude-haiku-4-5", "low", "ai5-pilot/haiku-base", False),
    ("claude-sonnet-5", "mid", "ai31-midtier/sonnet5-base", True),
    ("claude-opus-5", "flagship", "ai9-frontier/opus5-base", True),
    ("gpt-5.6-luna", "low", "ai9-frontier/gpt56luna-base", True),
    ("gpt-5.6-terra", "mid", "ai31-midtier/terra-base", True),
    ("gpt-5.6-sol", "flagship", "ai9-frontier/gpt56sol-base", True),
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
    for label, tier, rel_dir, clean in ROWS:
        log_dir = f"{args.logs}/{rel_dir}"
        r = haiku_row(log_dir) if not clean else clean_row(log_dir)
        results.append((label, tier, clean, r))

    print("PLOTTED vs PUBLISHED (docs/verification.md) — CEO-analyst gap, "
          "status_irrelevant only")
    all_ok = True
    for label, tier, clean, r in results:
        for outcome in ("comp", "harm"):
            all_ok &= check(label, outcome, r[outcome])

    fig, ax = plt.subplots(figsize=(9.5, 5.5))

    n_rows = len(results)
    ys = list(range(n_rows - 1, -1, -1))
    comp_off, harm_off = 0.12, -0.12
    clean_color = "#3d6da8"
    harm_color_clean = "#c46f30"
    grey = "#9a9a9a"

    # The five clean rows' two markers are the same registered 7-scenario
    # estimand on both outcomes (docs/verification.md guardrail 1). The
    # non-clean (haiku) row's harm marker is NOT that estimand -- it is
    # computed over 5 of the 7 scenarios (see haiku_row()) because that run
    # predates the structural predicates that make the other two decidable.
    # It is never rendered as if it were comparable to the clean rows' harm
    # markers: distinct colour/fill (grey/hollow vs the clean palette) plus an
    # inline "(5/7 scen.)" tag on the marker itself, on top of the footnote
    # below, so a reader cannot read the two harm markers as one series.
    for y, (label, tier, clean, r) in zip(ys, results):
        co, cl, ch = r["comp"]
        ho, hl, hh = r["harm"]
        comp_c = clean_color if clean else grey
        harm_c = harm_color_clean if clean else grey
        fc_comp = comp_c if clean else "none"
        fc_harm = harm_c if clean else "none"
        ax.errorbar([co], [y + comp_off], xerr=[[co - cl], [ch - co]],
                    fmt="none", ecolor=comp_c, elinewidth=1.6, capsize=3)
        ax.errorbar([ho], [y + harm_off], xerr=[[ho - hl], [hh - ho]],
                    fmt="none", ecolor=harm_c, elinewidth=1.6, capsize=3)
        ax.scatter([co], [y + comp_off], marker="o", s=55,
                   facecolor=fc_comp, edgecolor=comp_c, linewidth=1.3,
                   hatch=None if clean else "///", zorder=3)
        ax.scatter([ho], [y + harm_off], marker="^", s=55,
                   facecolor=fc_harm, edgecolor=harm_c, linewidth=1.3,
                   hatch=None if clean else "///", zorder=3)
        if not clean:
            ax.annotate("(harm: 5/7 scen., different denominator)",
                        (hh, y + harm_off), xytext=(6, 0),
                        textcoords="offset points", fontsize=6.5,
                        color=grey, va="center")

    ax.axvline(0, color="#888888", linewidth=1, linestyle="--")

    # Thin separator between the Anthropic and OpenAI blocks (rows 0-2 vs 3-5
    # in ROWS order; ys is reversed so the separator sits between ys[2] and
    # ys[3]).
    sep_y = (ys[2] + ys[3]) / 2
    ax.axhline(sep_y, color="#cccccc", linewidth=0.8)

    labels = [f"{label}\n({tier})" for label, tier, _, _ in results]
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("CEO minus analyst gap, status-irrelevant scenarios only\n"
                  "95% scenario-clustered bootstrap CI (10,000 draws, seed 0)")
    ax.set_title("Does the model treat the CEO more deferentially than the analyst?\n"
                 "circle = judge compliance gap, triangle = harmful-action gap "
                 "(both co-primary outcomes)", fontsize=10)
    ax.set_xlim(-0.05, 0.40)
    ax.grid(axis="x", alpha=0.25)

    handles = [
        plt.Line2D([0], [0], marker="o", color=clean_color, linestyle="none",
                   markersize=7, label="compliance gap"),
        plt.Line2D([0], [0], marker="^", color=harm_color_clean, linestyle="none",
                   markersize=7, label="harmful-action gap"),
        plt.Line2D([0], [0], marker="o", color=grey, markerfacecolor="none",
                   linestyle="none", markersize=7,
                   label="earlier harness version; shown for reference"),
    ]
    ax.legend(handles=handles, loc="lower right", fontsize=8, framealpha=0.9)

    footnote = (
        "n = 140 per persona cell on the five clean arms (7 scenarios x 20 "
        "epochs). claude-haiku-4-5 ran on an earlier harness version, before "
        "it recorded harmful-action outcomes directly: compliance is n="
        f"{results[0][3]['n_comp']} per persona cell (7 scenarios), the "
        "harmful-action outcome is reconstructed from recorded actions on "
        f"5 of 7 scenarios (n={results[0][3]['n_harm']} per persona cell) "
        "because two scenarios cannot be scored for harm from that earlier "
        "run's records."
    )
    # Wrap manually to a fixed character width and anchor left of centre with
    # a left margin, rather than relying on matplotlib's `wrap=True` (which
    # measures only the anchor-to-edge distance on one side and, for centred
    # text, can let a line spill past the opposite edge of the canvas).
    wrapped = "\n".join(textwrap.wrap(footnote, width=100))
    fig.text(0.06, 0.02, wrapped, ha="left", fontsize=7.5, color="#444444")
    fig.tight_layout(rect=(0, 0.09, 1, 1))

    if not all_ok:
        print("\n*** FAIL: at least one plotted value does not match "
              "docs/verification.md -- refusing to overwrite the committed "
              "figure with a value that disagrees with the published table ***")
        sys.exit(1)

    os.makedirs(args.out_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        out = f"{args.out_dir}/fig1_deference_forest.{ext}"
        fig.savefig(out, dpi=200)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
