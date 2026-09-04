"""Figure: calibration -- does identity change behaviour where policy says it should?

Two panels, answering the calibration question from two angles.

LEFT: the role-gated positive control. One row per model, two marks: mean
compliance in the authorised cell and in the unauthorised cell, both
`role_gated`, `identified` only (the same rows Table 1's E3 estimand
contrasts). Reuses `ai9_frontier_readout.load()` and `cluster_mean()` --
Table 1's own loader and estimator -- so a plotted mean cannot silently drift
from the published E3 gap (authorised minus unauthorised). Five models: the
five mutually clean frontier-generation arms behind Table 1's E1/E2/E3/E5.
claude-haiku-4-5 is excluded -- its E3 does not appear in any committed
readout, and the brief for this figure gates a sixth row on that, not on
whether the number is computable.

The authorised/unauthorised split is NOT identically (x, 0.000) on every
model: terra's unauthorised mean is 0.013 (3 of 240 unauthorised-identified
rows), not 0.000 like the other four. This script computes and plots the
real per-model values rather than assuming the qualitative "0.000 on every
model" reading in docs/verification.md's Table 1 headline row, and adds the
five authorised/unauthorised pairs to that doc's Table 2 (see this script's
own printed output for the exact command).

RIGHT: the reasoning-token forest from `fig2_reasoning_forest.py`, stripped
of all per-point text (no value labels, no interval text, no verdict words,
no "models that motivated the test" / "held-out" annotations, no footnote).
The evidentiary-status split (exploratory vs confirmatory, per the AI-32
pre-registration in `docs/analysis-plan.md` §J) is kept as a thin horizontal
rule only; the mechanism verdict (R6) is encoded as a filled marker ("more
deliberation" -- the gap survives a per-turn control) versus a hollow marker
("verbosity, not separable" -- it does not), with a two-item legend. Reuses
`principal_eval.reasoning.load_reasoning_rows` / `reasoning_report` --
exactly the pipeline behind `scripts/ai32_reasoning_readout.py` -- so the
plotted intervals and the fill/hollow verdict encoding are computed from the
same loaded rows, never reparsed by hand.

Row order matches the other two figures in this set (provider then tier,
haiku first when present) within each evidentiary-status group: the
exploratory pair is opus-5 then sol, the confirmatory trio is sonnet-5, luna,
then terra -- so the split stays a single contiguous rule while each half
keeps the shared provider/tier ordering.

The script prints every plotted value next to the published value from
docs/verification.md with PASS/FAIL, and exits non-zero on any FAIL.

Usage:
    uv run python scripts/fig_calibration.py [--logs <root>]

Writes docs/pilots/figures/fig_calibration.{png,pdf}.
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
sys.path.insert(0, HERE)

import ai9_frontier_readout as F  # noqa: E402
from principal_eval.reasoning import load_reasoning_rows, reasoning_report  # noqa: E402

# ---------------------------------------------------------------- left panel

# (row label, log dir relative to --logs), provider-then-tier order, no haiku
# (its E3 is not in a committed readout -- see docstring).
LEFT_ROWS = [
    ("claude-sonnet-5", "ai31-midtier/sonnet5-base"),
    ("claude-opus-5", "ai9-frontier/opus5-base"),
    ("gpt-5.6-luna", "ai9-frontier/gpt56luna-base"),
    ("gpt-5.6-terra", "ai31-midtier/terra-base"),
    ("gpt-5.6-sol", "ai9-frontier/gpt56sol-base"),
]

# Published E3 compliance gaps (docs/verification.md Table 1) = authorised
# mean minus unauthorised mean -- checked against below, since authorised and
# unauthorised are not individually tabulated there.
PUBLISHED_E3_GAP = {
    "claude-sonnet-5": 0.867,
    "claude-opus-5": 0.750,
    "gpt-5.6-luna": 0.942,
    "gpt-5.6-terra": 0.904,
    "gpt-5.6-sol": 0.917,
}

# Published authorised/unauthorised means individually (docs/verification.md
# Table 2, AI-50 row). Checking both components, not just their difference,
# so a bug that shifts authorised and unauthorised by the same amount (which
# would leave the gap unchanged) cannot silently pass.
PUBLISHED_LEFT = {
    "claude-sonnet-5": (0.867, 0.000),
    "claude-opus-5": (0.750, 0.000),
    "gpt-5.6-luna": (0.942, 0.000),
    "gpt-5.6-terra": (0.917, 0.013),
    "gpt-5.6-sol": (0.917, 0.000),
}

AUTH_COLOR = "#009E73"     # Okabe-Ito teal, shared with the discovery figure
UNAUTH_COLOR = "#CC79A7"   # Okabe-Ito reddish-purple


def left_panel_values(log_dir: str) -> dict:
    """Authorised/unauthorised compliance means, role_gated + identified only,
    from Table 1's own loader and cluster-mean estimator."""
    data = F.load(log_dir)
    rows = data["rows"]
    rg_id = [r for r in rows if r.family == "role_gated" and r.condition == "identified"]
    scens = sorted({r.scenario for r in rg_id})
    auth = F.cluster_mean(rg_id, scens, lambda r: r.authorized, 0.5, None)
    unauth = F.cluster_mean(rg_id, scens, lambda r: not r.authorized, 0.5, None)
    n_auth = len([r for r in rg_id if r.authorized])
    n_unauth = len([r for r in rg_id if not r.authorized])
    return {"auth": auth, "unauth": unauth, "n_auth": n_auth, "n_unauth": n_unauth}


def check_left(label: str, got_auth: float, got_unauth: float) -> bool:
    """Checks the authorised and unauthorised means individually against
    docs/verification.md Table 2, AND their difference against Table 1's
    already-published E3 gap -- checking only the difference would let a bug
    that shifts both components by the same amount pass silently."""
    pub_auth, pub_unauth = PUBLISHED_LEFT[label]
    pub_gap = PUBLISHED_E3_GAP[label]
    got_gap = got_auth - got_unauth
    ok = (abs(got_auth - pub_auth) < 0.0006 and abs(got_unauth - pub_unauth) < 0.0006
          and abs(got_gap - pub_gap) < 0.0006)
    tag = "PASS" if ok else "FAIL"
    print(f"  {label:18s}  authorised {got_auth:.3f} (published {pub_auth:.3f})  "
          f"unauthorised {got_unauth:.3f} (published {pub_unauth:.3f})  "
          f"gap {got_gap:+.3f}  published gap {pub_gap:+.3f}  {tag}")
    return ok


# --------------------------------------------------------------- right panel

# (label, log dir relative to --logs, evidentiary status), grouped so the
# exploratory/confirmatory split stays one contiguous rule, provider-then-
# tier order preserved within each group.
RIGHT_ROWS = [
    ("claude-opus-5", "ai9-frontier/opus5-base", "exploratory"),
    ("gpt-5.6-sol", "ai9-frontier/gpt56sol-base", "exploratory"),
    ("claude-sonnet-5", "ai31-midtier/sonnet5-base", "confirmatory"),
    ("gpt-5.6-luna", "ai9-frontier/gpt56luna-base", "confirmatory"),
    ("gpt-5.6-terra", "ai31-midtier/terra-base", "confirmatory"),
]

# R6 verdict -> filled ("more deliberation", survives a per-turn control) vs
# hollow ("verbosity, not separable") marker.
FILLED_VERDICTS = {"survivor"}


def right_panel_block(log_dir: str) -> dict:
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
        raise SystemExit(f"{log_dir}: {b.get('note', 'no reasoning-gap block available')}")
    c = b["R1_status_gap"]
    verdict = b["R6_verdict"]["verdict"]
    return {**c["relative"], "verdict": verdict, "filled": verdict in FILLED_VERDICTS}


# Published R1 point/interval (docs/verification.md Table 3), checked below.
PUBLISHED_R1 = {
    "claude-opus-5": (0.986, 0.611, 1.394),
    "gpt-5.6-sol": (0.491, 0.328, 0.640),
    "claude-sonnet-5": (0.384, 0.229, 0.535),
    "gpt-5.6-luna": (0.292, 0.055, 0.503),
    "gpt-5.6-terra": (0.428, 0.221, 0.610),
}

# Published R6 verdict (docs/verification.md Table 3's "R6 verdict" rows),
# checked below so the filled/hollow marker encoding cannot silently drift
# from the table even though the interval it is derived from still passes.
PUBLISHED_VERDICT = {
    "claude-opus-5": "survivor",
    "gpt-5.6-sol": "survivor",
    "claude-sonnet-5": "verbosity, not deliberation",
    "gpt-5.6-luna": "verbosity, not deliberation",
    "gpt-5.6-terra": "survivor",
}


def check_right(label: str, got: dict) -> bool:
    pub = PUBLISHED_R1[label]
    got_t = (got["point"], got["lo"], got["hi"])
    pub_verdict = PUBLISHED_VERDICT[label]
    ok = (all(abs(g - p) < 0.0015 for g, p in zip(got_t, pub))
          and got["verdict"] == pub_verdict)
    tag = "PASS" if ok else "FAIL"
    print(f"  {label:18s}  plotted {got_t[0]:+.1%} [{got_t[1]:+.1%},{got_t[2]:+.1%}]  "
          f"published {pub[0]:+.1%} [{pub[1]:+.1%},{pub[2]:+.1%}]  "
          f"verdict {got['verdict']!r} (published {pub_verdict!r})  {tag}")
    return ok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default=f"{ROOT}/logs")
    ap.add_argument("--out-dir", default=f"{ROOT}/docs/pilots/figures")
    args = ap.parse_args()

    left_results = []
    for label, rel_dir in LEFT_ROWS:
        v = left_panel_values(f"{args.logs}/{rel_dir}")
        left_results.append((label, v))

    right_results = []
    for label, rel_dir, status in RIGHT_ROWS:
        v = right_panel_block(f"{args.logs}/{rel_dir}")
        right_results.append((label, status, v))

    print("PLOTTED vs PUBLISHED (docs/verification.md) -- left panel: authorised/"
          "unauthorised compliance, role_gated + identified only")
    all_ok = True
    for label, v in left_results:
        all_ok &= check_left(label, v["auth"], v["unauth"])

    print("\nPLOTTED vs PUBLISHED (docs/verification.md, Table 3) -- right panel: "
          "reasoning-token gap (CEO minus analyst, %)")
    for label, status, v in right_results:
        all_ok &= check_right(label, v)

    fig, (axl, axr) = plt.subplots(1, 2, figsize=(12.5, 5))

    # --- left panel ---
    n_left = len(left_results)
    ys_l = list(range(n_left - 1, -1, -1))
    for y, (label, v) in zip(ys_l, left_results):
        axl.scatter([v["auth"]], [y], marker="o", s=70, facecolor=AUTH_COLOR,
                    edgecolor=AUTH_COLOR, zorder=3)
        axl.scatter([v["unauth"]], [y], marker="s", s=60, facecolor=UNAUTH_COLOR,
                    edgecolor=UNAUTH_COLOR, zorder=3)
    axl.set_yticks(ys_l)
    axl.set_yticklabels([label for label, _ in left_results], fontsize=9)
    axl.set_xlim(-0.05, 1.05)
    axl.set_xlabel("mean compliance, role-gated scenarios", fontsize=9)
    axl.set_title("Where policy names who may ask,\ndo the models apply identity?",
                  fontsize=10)
    axl.grid(axis="x", alpha=0.25)
    left_handles = [
        plt.Line2D([0], [0], marker="o", color=AUTH_COLOR, linestyle="none",
                   markersize=8, label="authorised"),
        plt.Line2D([0], [0], marker="s", color=UNAUTH_COLOR, linestyle="none",
                   markersize=7, label="unauthorised"),
    ]
    # Outside the axes (below the x-axis label) -- an in-axes legend previously
    # sat directly over gpt-5.6-sol's authorised marker at 0.917.
    axl.legend(handles=left_handles, loc="upper center", bbox_to_anchor=(0.5, -0.16),
               ncol=2, fontsize=9, frameon=False)

    # --- right panel ---
    n_right = len(right_results)
    ys_r = list(range(n_right - 1, -1, -1))
    forest_color = "#3d6da8"
    for y, (label, status, v) in zip(ys_r, right_results):
        axr.errorbar([v["point"] * 100], [y],
                     xerr=[[(v["point"] - v["lo"]) * 100], [(v["hi"] - v["point"]) * 100]],
                     fmt="none", ecolor=forest_color, elinewidth=1.6, capsize=3)
        axr.scatter([v["point"] * 100], [y], marker="o", s=65,
                    facecolor=forest_color if v["filled"] else "none",
                    edgecolor=forest_color, linewidth=1.4, zorder=3)
    axr.axvline(0, color="#888888", linewidth=1, linestyle="--")

    n_explore = sum(1 for _, status, _ in right_results if status == "exploratory")
    split_y = (ys_r[n_explore - 1] + ys_r[n_explore]) / 2
    axr.axhline(split_y, color="#cccccc", linewidth=0.8)

    axr.set_yticks(ys_r)
    axr.set_yticklabels([label for label, _, _ in right_results], fontsize=9)
    axr.set_xlabel("CEO minus analyst reasoning-token gap (%, 95% CI)", fontsize=9)
    axr.set_title("Does the model reason more when it\nbelieves it is talking to the CEO?",
                  fontsize=10)
    axr.grid(axis="x", alpha=0.25)
    right_handles = [
        plt.Line2D([0], [0], marker="o", color=forest_color, linestyle="none",
                   markersize=8, label="more deliberation"),
        plt.Line2D([0], [0], marker="o", color=forest_color, markerfacecolor="none",
                   linestyle="none", markersize=8, label="verbosity, not separable"),
    ]
    axr.legend(handles=right_handles, loc="upper center", bbox_to_anchor=(0.5, -0.16),
               ncol=2, fontsize=9, frameon=False)

    fig.tight_layout(rect=(0, 0.08, 1, 1))

    if not all_ok:
        print("\n*** FAIL: at least one plotted value does not match "
              "docs/verification.md -- refusing to overwrite the committed "
              "figure with a value that disagrees with the published table ***")
        sys.exit(1)

    os.makedirs(args.out_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        out = f"{args.out_dir}/fig_calibration.{ext}"
        fig.savefig(out, dpi=200)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
