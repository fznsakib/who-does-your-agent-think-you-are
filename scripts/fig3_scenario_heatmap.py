"""Figure 3 (AI-43): where each model defers — the CEO-analyst harm gap, scenario by model.

One cell per (scenario, arm): E1 on the harmful-action co-primary, computed
inside a single scenario, `status_irrelevant` only. A cell is BLANK when the arm
produced zero harmful episodes in that scenario, because a gap of +0.000 with no
harmful episode anywhere in the cell says "no opportunity", not "no deference",
and painting it the same colour as a measured zero would be misleading.

WHAT THIS IS NOT. n = 20 per (scenario, persona) cell ON THE FIVE CLEAN ARMS
ONLY, so no cell carries an interval and none is a test. The registered E1
estimand pools the seven scenarios and is the only quantity with an honest
uncertainty statement (`scripts/ai9_frontier_readout.py`, Table 1 of
`docs/verification.md`). This figure exists to answer a different, descriptive
question: is the pooled effect spread across the scenario set, or carried by
one scenario? It is ILLUSTRATIVE, exactly as the per-scenario tables in the
readout docs are. The legacy `gpt-5-nano` column is NOT n=20: its run has 10
observations per persona per scenario (9 on `killswitch`, where one CEO sample
is excluded — rules 15/17), so its cells report both persona denominators
(e.g. "n=9/10" when they differ) rather than a single shared n.

Loader reuse. Table 1 is produced by
`scripts/ai9_frontier_readout.py`'s `load()` — strict (`all_samples_required`
whenever the log's own header reports `success`), native `harmful_action` only,
no backfill. This figure reuses THAT loader, not `ai31_tier_table.load()`, for
the five clean arms, so a per-scenario cell here cannot silently draw on a
truncated read or a backfilled row Table 1 would have excluded or read
natively. `ai31_tier_table.load()` is used ONLY for the `gpt-5-nano` legacy
column, exactly as `scripts/ai33_cross_model_bootstrap.py` and the tier table
itself use it there: nano predates AI-20, carries no native `harmful_action`
field at all, and needs that module's backfill through
`principal_eval.harm.harm_verdict` to have a harm outcome in the first place.
The two loaders are NOT claimed to agree in general — they differ in
strictness and in whether they backfill — only that on these five clean,
complete, `harmful_action`-native logs they read the identical rows, which the
exactness check below verifies empirically rather than asserts.

Multi-run refusal. Both loaders read the LAST `.eval` file they find under a
directory (sorted by filename, which sorts by timestamp) — neither itself
refuses a directory holding more than one run. Pooling a smoke run into an
arm's numbers the way `reasoning_report` (Figure 2's loader) explicitly
refuses to is exactly the failure mode this script must not reproduce, so it
globs each arm's directory itself and refuses, loudly, if it finds anything but
one `.eval` file.

Exactness check. Every clean arm's harm outcome carries `harmful_action`
natively on all seven scenarios (no AI-23 exclusion), so the pooled E1 the
readout docs publish is exactly the mean of the seven per-scenario gaps this
figure plots — same 20-per-cell counts, same arithmetic, no resampling, and
now the SAME loader Table 1 itself uses. The script recomputes that mean per
clean arm and compares it against the published Table 1 value (itself printed
to 3 decimal places), rounding the computed mean to the same 3 decimal places
before comparing — `docs/verification.md` never publishes more precision than
that — and prints PASS/FAIL for each.

Colour scale. The symmetric colour limits are sized from the largest observed
|gap| across every plotted cell (never hard-coded), so no cell saturates the
colourbar's endpoint and reads as indistinguishable from a smaller value.

Usage:
    uv run python scripts/fig3_scenario_heatmap.py [--logs <root>] [--out-dir <dir>]
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, f"{ROOT}/src")
sys.path.insert(0, HERE)

import ai9_frontier_readout as T9  # noqa: E402
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
    ("gpt-5-nano\n(earlier harness)", "ai15-gpt5nano/base", False),
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

    Both loaders below would silently pick the lexicographically-last file
    (i.e. the most recent run by timestamp) and drop the rest. That is the
    same smoke-run-beside-production-run failure mode `reasoning_report`
    refuses for Figure 2 — refuse it here too, rather than let a cell
    silently draw on the wrong run.
    """
    found = sorted(glob.glob(f"{log_dir}/**/*.eval", recursive=True))
    if len(found) != 1:
        raise SystemExit(
            f"refusing to pool separate runs into one arm: {log_dir} holds "
            f"{len(found)} .eval files ({found}). Same directory does not mean "
            f"same run -- a smoke run sitting beside a production run would "
            f"silently be dropped by the 'take the last file' rule both loaders "
            f"use. Point --logs at a tree with exactly one run per arm "
            f"directory.")


def clean_arm_cells(log_dir: str) -> tuple[dict, dict]:
    """comp/harm cells for a clean arm, from Table 1's own loader.

    `ai9_frontier_readout.load()` reads `harmful_action` natively (no
    backfill) and enforces `all_samples_required` whenever the log's header
    reports `success`, which is exactly how Table 1 is produced. Built here
    rather than imported because Table 1's script reports pooled estimands,
    not per-scenario cells -- this reshapes its `rows` into the same
    dict[persona][scenario] -> [values] shape `scenario_gaps()` expects.
    """
    loaded = T9.load(log_dir)
    comp: dict = defaultdict(lambda: defaultdict(list))
    harm: dict = defaultdict(lambda: defaultdict(list))
    for r in loaded["rows"]:
        if r.family != "status_irrelevant":
            continue
        comp[r.persona][r.scenario].append(r.compliance(0.5))
        harm[r.persona][r.scenario].append(1.0 if r.harm else 0.0)
    if loaded["excluded"] or any(loaded["missing"].values()):
        print(f"  ! {log_dir}: {len(loaded['excluded'])} excluded sample(s), "
              f"missing-metadata counts {dict(loaded['missing'])} -- see rules 15/17")
    return comp, harm


def scenario_gaps(harm: dict) -> dict[str, tuple[float, int, int, int]]:
    """scenario -> (ceo - analyst, harmful episodes in the scenario, n_ceo, n_analyst)."""
    out: dict[str, tuple[float, int, int, int]] = {}
    for s in SCENARIOS:
        ceo = harm.get("ceo", {}).get(s, [])
        ana = harm.get("analyst", {}).get(s, [])
        if not ceo or not ana:
            continue
        harmful = sum(int(v) for p in harm for v in harm[p].get(s, []))
        gap = sum(ceo) / len(ceo) - sum(ana) / len(ana)
        out[s] = (gap, harmful, len(ceo), len(ana))
    return out


def n_label(n_ceo: int, n_ana: int) -> str:
    return f"n={n_ceo}" if n_ceo == n_ana else f"n={n_ceo}/{n_ana}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default=f"{ROOT}/logs")
    ap.add_argument("--out-dir", default=f"{ROOT}/docs/pilots/figures")
    args = ap.parse_args()
    T.set_log_root(args.logs)
    # Lift the AI-23 harm exclusion for the T.load() (nano-only) path: nano's
    # two excluded scenarios are re-blanked explicitly below instead.
    T.HARM_EXCLUDED = set()

    cols = []
    for label, rel_dir, clean in ARMS:
        log_dir = f"{args.logs}/{rel_dir}"
        one_eval(log_dir)
        if clean:
            comp, harm = clean_arm_cells(log_dir)
            native, backfilled = "all", 0
        else:
            comp, harm, native, backfilled, *_ = T.load(log_dir)
        gaps = scenario_gaps(harm)
        cgaps = scenario_gaps(comp)
        excluded_here: set[str] = set()
        if not clean:
            excluded_here = {"exfiltration", "external_disclosure"}
            # Backfilled harm is structurally undecidable on these two (AI-23).
            for s in excluded_here:
                gaps.pop(s, None)
        cols.append((label, clean, gaps, excluded_here))
        name = label.splitlines()[0]
        print(f"HARM  {name:16s} native={native} backfilled={backfilled} "
              + " ".join(f"{s}={gaps[s][0]:+.3f}(h={gaps[s][1]},"
                         f"{n_label(gaps[s][2], gaps[s][3])})" for s in SCENARIOS
                         if s in gaps))
        # Per-scenario COMPLIANCE gaps are not published in any readout section;
        # they are printed here so the write-up's table is reproducible from the
        # same loader that produces every other cell value in the project.
        print(f"COMP  {name:16s} "
              + " ".join(f"{s}={cgaps[s][0]:+.3f}" for s in SCENARIOS if s in cgaps))

    print("\n--- EXACTNESS CHECK: per-scenario row mean vs. published pooled E1 (harm) ---")
    all_pass = True
    for label, clean, gaps, excluded_here in cols:
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

    # Symmetric colour limits sized from what is actually plotted, never
    # hard-coded -- a cell outside a fixed range would saturate at the
    # endpoint colour and read as indistinguishable from a smaller value
    # (observed max here is luna/access_escalation +0.70).
    plotted_gaps = [gaps[s][0] for _, _, gaps, excluded_here in cols
                    for s in SCENARIOS if s in gaps and s not in excluded_here
                    and gaps[s][1] > 0]
    vlim = max(0.5, max((abs(g) for g in plotted_gaps), default=0.5))
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    norm = TwoSlopeNorm(vmin=-vlim, vcenter=0.0, vmax=vlim)
    cmap = plt.get_cmap("RdBu_r")

    for x, (label, clean, gaps, excluded_here) in enumerate(cols):
        for y, s in enumerate(SCENARIOS):
            if s in excluded_here:
                ax.add_patch(plt.Rectangle((x - .5, y - .5), 1, 1,
                                           facecolor="#f2f2f2", edgecolor="white",
                                           hatch="//"))
                ax.text(x, y, "not scored", ha="center", va="center",
                        fontsize=7, color="#777777")
                continue
            if s not in gaps or gaps[s][1] == 0:
                ax.add_patch(plt.Rectangle((x - .5, y - .5), 1, 1,
                                           facecolor="#f2f2f2", edgecolor="white"))
                ax.text(x, y, "no harm", ha="center", va="center",
                        fontsize=7.5, color="#999999")
                continue
            gap, harmful, n_ceo, n_ana = gaps[s]
            ax.add_patch(plt.Rectangle((x - .5, y - .5), 1, 1,
                                       facecolor=cmap(norm(gap)), edgecolor="white"))
            ax.text(x, y, f"{gap:+.2f}\n{n_label(n_ceo, n_ana)}", ha="center", va="center",
                    fontsize=8, color="#111111" if abs(gap) < 0.6 * vlim else "#ffffff")

    ax.set_xlim(-.5, len(cols) - .5)
    ax.set_ylim(len(SCENARIOS) - .5, -.5)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([c[0] for c in cols], fontsize=8)
    for tick, (_, clean, _, _) in zip(ax.get_xticklabels(), cols):
        if not clean:
            tick.set_color("#888888")
    ax.set_yticks(range(len(SCENARIOS)))
    ax.set_yticklabels(SCENARIOS, fontsize=9)
    ax.set_title("CEO minus analyst, harmful-action rate, by scenario — descriptive only\n"
                 "(status-irrelevant scenarios; n = 20 per cell on the five main arms; "
                 "no intervals shown)",
                 fontsize=10)
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax,
                 label="CEO − analyst harmful-action rate", shrink=0.85)
    fig.text(0.5, 0.015,
             "\"no harm\": the arm produced no harmful episode in that scenario, so there "
             "was no opportunity to defer. \"not scored\": the harmful outcome cannot be "
             "decided from the recorded tool arguments for this scenario on the earlier "
             "harness. gpt-5-nano (grey label) ran on an earlier harness version with "
             "n = 9-10 per cell, not 20, using a backfilled harm outcome, and is not a "
             "sixth directly comparable arm.",
             ha="center", fontsize=7.5, color="#444444", wrap=True)
    fig.tight_layout(rect=(0, 0.05, 1, 1))

    os.makedirs(args.out_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        out = f"{args.out_dir}/fig3_scenario_heatmap.{ext}"
        fig.savefig(out, dpi=200)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
