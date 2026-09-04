"""Figure: discovery -- does the model look up who is asking?

Answers the first of the three research questions (discovery / deference /
calibration). One row per model, two marks per row: the CEO and analyst rates
of active identity lookup on the status-irrelevant scenarios, i.e. any cue
read beyond the forced initial identity read. The two markers carry a small
fixed vertical offset (applied to every row, whether or not the two values
coincide) so a row where CEO and analyst land on the same rate -- sonnet-5
and opus-5 both sit at 1.000 -- still shows two visible markers.

Six rows, grouped by provider and ordered by tier, matching every other
figure in this set: claude-haiku-4-5, claude-sonnet-5, claude-opus-5,
gpt-5.6-luna, gpt-5.6-terra, gpt-5.6-sol, with the same thin provider rule as
`fig_deference.py` (between claude-opus-5 and gpt-5.6-luna -- haiku is an
earlier-harness Anthropic row, not a separated reference row here). gpt-5-nano
is excluded -- it is a cheap development subject, not a tier-ladder endpoint
(see CLAUDE.md).

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

from inspect_ai.log import read_eval_log  # noqa: E402

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


def _require_complete(path: str) -> None:
    """Refuses a non-terminal or truncated log before any rate is computed.

    `load_rows()` deliberately tolerates a non-success log by reading only
    the samples present (`all_samples_required=False` in that case) -- the
    right behaviour for a general-purpose loader, but wrong for a figure
    script: a uniformly truncated subset can still land on the same
    three-decimal rates as the full run (by chance, or because the rates
    genuinely are that stable), pass the PLOTTED vs PUBLISHED check, and
    silently overwrite the committed figure with numbers that no longer
    reproduce Table 6's actual denominators. Mirrors the completeness check
    `ai49_identity_seeking.py` runs before reporting.
    """
    header = read_eval_log(path, header_only=True)
    if header.status != "success":
        raise SystemExit(
            f"{path}: log status is {header.status!r}, not 'success' -- "
            f"refusing to treat a non-terminal log as a complete run.")
    expected = header.results.total_samples if header.results else None
    if expected is not None:
        report = load_rows([path])
        if len(report.rows) != expected:
            raise SystemExit(
                f"{path}: loaded {len(report.rows)} samples but the log header "
                f"reports total_samples={expected} -- refusing to treat this as "
                f"a complete run.")


def model_rates(log_dir: str) -> dict:
    path = one_eval(log_dir)
    _require_complete(path)
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

    fig, ax = plt.subplots(figsize=(9, 5.5))
    n_rows = len(results)
    ys = list(range(n_rows - 1, -1, -1))
    ceo_off, ana_off = 0.12, -0.12

    for y, (label, clean, r) in zip(ys, results):
        ceo_v, ceo_n = r["ceo"]
        ana_v, ana_n = r["analyst"]
        ax.scatter([ceo_v], [y + ceo_off], marker="o", s=70, facecolor=CEO_COLOR,
                   edgecolor=CEO_COLOR, zorder=3)
        ax.scatter([ana_v], [y + ana_off], marker="s", s=60, facecolor=ANALYST_COLOR,
                   edgecolor=ANALYST_COLOR, zorder=3)

    labels = [label for label, _, _ in results]
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=9)

    # Same provider rule as fig_deference.py: between claude-opus-5 (index 2)
    # and gpt-5.6-luna (index 3) in ROWS order -- haiku sits in the Anthropic
    # block, not set apart as a separate reference row.
    sep_y = (ys[2] + ys[3]) / 2
    ax.axhline(sep_y, color="#cccccc", linewidth=0.8)

    # A rate can legitimately sit exactly at 0.000 or 1.000 (four of the six
    # rows have at least one persona at 1.000); tight [0, 1] limits centre
    # those markers on the spine and Matplotlib clips half of each one.
    ax.set_xlim(-0.03, 1.03)
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
    # Outside the axes (below the x-axis label) so the legend can never sit
    # on top of a data marker -- sol's CEO rate (0.907) previously fell
    # directly under an in-axes legend box.
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.14),
              ncol=2, fontsize=9, frameon=False)

    fig.tight_layout(rect=(0, 0.06, 1, 1))

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
