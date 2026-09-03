"""Figure 3 (AI-43): where each model defers — the CEO-analyst harm gap, scenario by model.

One cell per (scenario, arm): E1 on the harmful-action co-primary, computed
inside a single scenario, `status_irrelevant` only. A cell is BLANK when the arm
produced zero harmful episodes in that scenario, because a gap of +0.000 with no
harmful episode anywhere in the cell says "no opportunity", not "no deference",
and painting it the same colour as a measured zero would be misleading.

WHAT THIS IS NOT. n = 20 per (scenario, persona) cell, so no cell carries an
interval and none is a test. The registered E1 estimand pools the seven
scenarios and is the only quantity with an honest uncertainty statement
(`scripts/ai9_frontier_readout.py`, Table 1 of `docs/verification.md`). This
figure exists to answer a different, descriptive question: is the pooled effect
spread across the scenario set, or carried by one scenario? It is ILLUSTRATIVE,
exactly as the per-scenario tables in the readout docs are.

Loader reuse. Cell values come from `scripts/ai31_tier_table.py`'s `load()`, the
same loader the tier table, the cross-model bootstrap and Figure 1 use, so no
two of them can disagree about a cell. One documented override: that module
drops `exfiltration`/`external_disclosure` from the harm outcome (the AI-23
cross-fork rule, rule 18). This figure reports the REGISTERED seven-scenario
harm outcome for the five mutually clean arms, which all carry `harmful_action`
natively, so the exclusion is lifted for them. `gpt-5-nano` stays on the
pre-AI-16 fork with a backfilled harm outcome that is structurally undecidable
on those two scenarios; it is drawn as a labelled legacy column with both
scenarios blanked, never as a sixth clean point.

Multi-run refusal. `T.load()` silently reads the LAST `.eval` file it finds
under a directory (sorted by filename, which sorts by timestamp) — it does not
itself refuse a directory holding more than one run. Pooling a smoke run into
an arm's numbers the way `reasoning_report` (Figure 2's loader) explicitly
refuses to is exactly the failure mode this script must not reproduce, so it
globs each arm's directory itself and refuses, loudly, if it finds anything but
one `.eval` file.

Exactness check. Every clean arm's harm outcome carries `harmful_action`
natively on all seven scenarios (no AI-23 exclusion), so the pooled E1 the
readout docs publish is exactly the mean of the seven per-scenario gaps this
figure plots — same 20-per-cell counts, same arithmetic, no resampling. The
script recomputes that mean per clean arm and compares it against the
published Table 1 value (itself printed to 3 decimal places), rounding the
computed mean to the same 3 decimal places before comparing — `docs/
verification.md` never publishes more precision than that — and prints
PASS/FAIL for each.

Usage:
    uv run python scripts/fig3_scenario_heatmap.py [--logs <root>] [--out-dir <dir>]
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, f"{ROOT}/src")
sys.path.insert(0, HERE)

import ai31_tier_table as T  # noqa: E402

# The seven status_irrelevant scenarios, in the README's order.
SCENARIOS = [
    "exfiltration",
    "safety_bypass",
    "records_tampering",
    "access_escalation",
    "external_disclosure",
    "surveillance",
    "killswitch",
]

# (column label, log dir relative to --logs, clean?)
ARMS = [
    ("claude-opus-5\nflagship", "ai9-frontier/opus5-base", True),
    ("claude-sonnet-5\nmid", "ai31-midtier/sonnet5-base", True),
    ("gpt-5.6-sol\nflagship", "ai9-frontier/gpt56sol-base", True),
    ("gpt-5.6-terra\nmid", "ai31-midtier/terra-base", True),
    ("gpt-5.6-luna\nlow", "ai9-frontier/gpt56luna-base", True),
    ("gpt-5-nano\nLEGACY", "ai15-gpt5nano/base", False),
]

# Published Table 1 pooled E1 harm, five clean arms (docs/verification.md).
# Keyed on the arm's short label (first line of the column label above).
PUBLISHED_E1_HARM = {
    "claude-opus-5": 0.057,
    "claude-sonnet-5": 0.071,
    "gpt-5.6-sol": 0.100,
    "gpt-5.6-terra": 0.093,
    "gpt-5.6-luna": 0.136,
}


def one_eval(log_dir: str) -> None:
    """Refuse a directory holding anything but exactly one `.eval` run.

    `T.load()` would silently pick the lexicographically-last file (i.e. the
    most recent run by timestamp) and drop the rest. That is the same
    smoke-run-beside-production-run failure mode `reasoning_report` refuses
    for Figure 2 — refuse it here too, rather than let a cell silently draw
    on the wrong run.
    """
    found = sorted(glob.glob(f"{log_dir}/**/*.eval", recursive=True))
    if len(found) != 1:
        raise SystemExit(
            f"refusing to pool separate runs into one arm: {log_dir} holds "
            f"{len(found)} .eval files ({found}). Same directory does not mean "
            f"same run -- a smoke run sitting beside a production run would "
            f"silently be dropped by ai31_tier_table.load()'s 'take the last "
            f"file' rule. Point --logs at a tree with exactly one run per arm "
            f"directory.")


def scenario_gaps(harm: dict) -> dict[str, tuple[float, int, int]]:
    """scenario -> (ceo - analyst, harmful episodes in the scenario, n per cell)."""
    out: dict[str, tuple[float, int, int]] = {}
    for s in SCENARIOS:
        ceo = harm.get("ceo", {}).get(s, [])
        ana = harm.get("analyst", {}).get(s, [])
        if not ceo or not ana:
            continue
        harmful = sum(int(v) for p in harm for v in harm[p].get(s, []))
        gap = sum(ceo) / len(ceo) - sum(ana) / len(ana)
        out[s] = (gap, harmful, len(ceo))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default=f"{ROOT}/logs")
    ap.add_argument("--out-dir", default=f"{ROOT}/docs/pilots/figures")
    args = ap.parse_args()
    T.set_log_root(args.logs)
    # Lift the AI-23 harm exclusion: every clean arm carries `harmful_action`
    # natively on all seven scenarios, and this figure reports the registered
    # seven-scenario harm outcome. nano's two excluded scenarios are re-blanked
    # below.
    T.HARM_EXCLUDED = set()

    cols = []
    for label, rel_dir, clean in ARMS:
        log_dir = f"{args.logs}/{rel_dir}"
        one_eval(log_dir)
        comp, harm, native, backfilled, *_ = T.load(log_dir)
        gaps = scenario_gaps(harm)
        cgaps = scenario_gaps(comp)
        excluded_here: set[str] = set()
        if not clean:
            excluded_here = {"exfiltration", "external_disclosure"}
            # Backfilled harm is structurally undecidable on these two (AI-23).
            for s in excluded_here:
                gaps.pop(s, None)
        cols.append((label, clean, gaps, excluded_here, backfilled))
        name = label.splitlines()[0]
        print(f"HARM  {name:16s} native={native} backfilled={backfilled} "
              + " ".join(f"{s}={gaps[s][0]:+.3f}(h={gaps[s][1]})" for s in SCENARIOS
                         if s in gaps))
        # Per-scenario COMPLIANCE gaps are not published in any readout section;
        # they are printed here so the write-up's table is reproducible from the
        # same loader that produces every other cell value in the project.
        print(f"COMP  {name:16s} "
              + " ".join(f"{s}={cgaps[s][0]:+.3f}" for s in SCENARIOS if s in cgaps))

    print("\n--- EXACTNESS CHECK: per-scenario row mean vs. published pooled E1 (harm) ---")
    all_pass = True
    for label, clean, gaps, excluded_here, _ in cols:
        name = label.splitlines()[0]
        if name not in PUBLISHED_E1_HARM:
            continue
        total = sum(gaps[s][0] for s in SCENARIOS)
        computed = total / len(SCENARIOS)
        published = PUBLISHED_E1_HARM[name]
        ok = round(computed, 3) == published
        all_pass &= ok
        print(f"  {name:16s} {total:.3f}/{len(SCENARIOS)} = {computed:.3f}  "
              f"vs published {published:.3f}  {'PASS' if ok else 'FAIL'}")
    if not all_pass:
        raise SystemExit("exactness check FAILED: a per-scenario row does not "
                          "average to its arm's published pooled E1 harm.")
    print("all five clean arms PASS.")

    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    norm = TwoSlopeNorm(vmin=-0.5, vcenter=0.0, vmax=0.5)
    cmap = plt.get_cmap("RdBu_r")

    for x, (label, clean, gaps, excluded_here, _) in enumerate(cols):
        for y, s in enumerate(SCENARIOS):
            if s in excluded_here:
                ax.add_patch(plt.Rectangle((x - .5, y - .5), 1, 1,
                                           facecolor="#f2f2f2", edgecolor="white",
                                           hatch="//"))
                ax.text(x, y, "n/a", ha="center", va="center",
                        fontsize=8, color="#777777")
                continue
            if s not in gaps or gaps[s][1] == 0:
                ax.add_patch(plt.Rectangle((x - .5, y - .5), 1, 1,
                                           facecolor="#f2f2f2", edgecolor="white"))
                ax.text(x, y, "no harm", ha="center", va="center",
                        fontsize=7.5, color="#999999")
                continue
            gap, harmful, n = gaps[s]
            ax.add_patch(plt.Rectangle((x - .5, y - .5), 1, 1,
                                       facecolor=cmap(norm(gap)), edgecolor="white"))
            ax.text(x, y, f"{gap:+.2f}\nn={n}", ha="center", va="center",
                    fontsize=8, color="#111111" if abs(gap) < 0.3 else "#ffffff")

    ax.set_xlim(-.5, len(cols) - .5)
    ax.set_ylim(len(SCENARIOS) - .5, -.5)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([c[0] for c in cols], fontsize=8)
    for tick, (_, clean, _, _, _) in zip(ax.get_xticklabels(), cols):
        if not clean:
            tick.set_color("#888888")
    ax.set_yticks(range(len(SCENARIOS)))
    ax.set_yticklabels(SCENARIOS, fontsize=9)
    ax.set_title("Figure 3. CEO minus analyst, harmful-action outcome, one scenario "
                 "at a time\nstatus_irrelevant only · n = 20 per cell · "
                 "ILLUSTRATIVE, no intervals", fontsize=10)
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax,
                 label="CEO − analyst harmful-action rate", shrink=0.85)
    fig.text(0.5, 0.015,
             "\"no harm\": the arm produced no harmful episode in that scenario, so there "
             "was no opportunity to defer. \"n/a\": structurally undecidable under AI-23. "
             "gpt-5-nano (grey label) is a legacy cross-fork arm with a backfilled harm "
             "outcome and is not a sixth clean point.",
             ha="center", fontsize=7.5, color="#444444", wrap=True)
    fig.tight_layout(rect=(0, 0.05, 1, 1))

    os.makedirs(args.out_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        out = f"{args.out_dir}/fig3_scenario_heatmap.{ext}"
        fig.savefig(out, dpi=200)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
